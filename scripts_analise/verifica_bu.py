# Verificacao pos-urna, Brasil inteiro, em fluxo (mesma leitura remota do logs_brasil.py):
# por secao le bu.dat, rdv.dat, imgbu.dat e vota.vsc e confere
#   (a) hash SHA-512 do BU, RDV e imagem do BU contra o arquivo de assinatura da urna (listas SW e HW)
#       + hash do proprio conteudo assinado (autoAssinado)
#   (b) votos para Presidente: BU x RDV (voto a voto) x imagem impressa do BU
# A comparacao com o resultado oficial e a soma nacional ficam no analise_bu.py.
# uso: python verifica_bu.py <OUT> [UF,UF|ALL] [1t,2t] [workers]
import sys, os, re, time, hashlib, collections, traceback, zipfile, json
import pyarrow as pa, pyarrow.parquet as pq
from concurrent.futures import ProcessPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logs_brasil as L

# ---------------- DER minimo ----------------
def tlv(b, i):
    t = b[i]; cls = t >> 6; cons = (t >> 5) & 1; tag = t & 31; i += 1
    if tag == 31:
        tag = 0
        while True:
            x = b[i]; i += 1; tag = (tag << 7) | (x & 127)
            if not x & 128: break
    l = b[i]; i += 1
    if l & 128:
        n = l & 127; l = int.from_bytes(b[i:i + n], 'big'); i += n
    return cls, cons, tag, b[i:i + l], i + l

def tree(b):
    out = []; i = 0
    while i < len(b):
        cls, cons, tag, c, i = tlv(b, i)
        out.append((cls, tag, tree(c) if cons else bytes(c)))
    return out

def raw_children(b):
    """filhos do SEQUENCE externo como bytes crus"""
    _, _, _, c, _ = tlv(b, 0); out = []; j = 0
    while j < len(c):
        st = j; _, _, _, _, j = tlv(c, j); out.append(bytes(c[st:j]))
    return out

def env(b):
    t = tree(b)[0][2]; return [x for x in t if x[0] == 0 and x[1] == 4][-1][2]

iv = lambda x: int.from_bytes(x, 'big')

def votos_cargo(node, achou):
    """procura SEQUENCEs {codigoCargo [2,1|2], INTEGER, SEQUENCE OF ...} (BU: totalVotosCargo; RDV: votosCargo)"""
    for cls, tag, v in node:
        if isinstance(v, list):
            if (len(v) >= 3 and v[0][0] == 2 and not isinstance(v[0][2], list) and v[1][:2] == (0, 2)
                    and v[2][:2] == (0, 16) and isinstance(v[2][2], list)):
                achou.append((v[0][1], iv(v[0][2]), v[2][2]))
            else:
                votos_cargo(v, achou)

def conta_bu(b):
    """BU: {(tipoCargo, cargo): Counter{('n',num)|'branco'|'nulo'|('leg',partido): qtd}} ; tipoVoto 1 nominal 2 branco 3 nulo 4 legenda"""
    t = tree(env(b)); ach = []; votos_cargo(t, ach); out = {}
    for tc, cargo, tups in ach:
        c = collections.Counter()
        for _, _, f in tups:
            if not isinstance(f, list) or not f or f[0][:2] != (2, 1): continue
            tipo = iv(f[0][2]); q = iv(f[1][2])
            ident = f[2][2] if len(f) > 2 and f[2][:2] == (2, 3) and isinstance(f[2][2], list) else None
            if tipo == 1: c[('n', iv(ident[-1][2]))] += q  # identificacaoVotavel = {partido, codigo}
            elif tipo == 4: c[('leg', iv(ident[0][2]) if ident else 0)] += q
            elif tipo == 2: c['branco'] += q
            else: c['nulo'] += q
        out[(tc, cargo)] = out.get((tc, cargo), collections.Counter()) + c
    return out

def conta_rdv(b):
    """RDV: mesmos totais, voto a voto. TipoVoto RDV: 1 legenda 2 nominal 3 branco 4 nulo 5 brancoAposSusp 6 nuloAposSusp 7 nuloRepet 8 nuloSemCand 9..."""
    t = tree(b); ach = []; votos_cargo(t, ach); out = {}
    for tc, cargo, votos in ach:
        c = collections.Counter()
        for _, _, f in votos:
            if not isinstance(f, list) or not f or f[0][:2] != (0, 10): continue
            tipo = iv(f[0][2]); dig = f[1][2].decode('latin1') if len(f) > 1 and not isinstance(f[1][2], list) else ''
            if tipo == 2: c[('n', int(dig))] += 1
            elif tipo == 1: c[('leg', int(dig[:2]) if dig[:2].isdigit() else 0)] += 1  # legenda: numero digitado inteiro; partido = 2 primeiros digitos
            elif tipo in (3, 5): c['branco'] += 1
            else: c['nulo'] += 1
        out[(tc, cargo)] = out.get((tc, cargo), collections.Counter()) + c
    return out

RXP = re.compile(r'-+PRESIDENTE-+\n(.*?)\n-{10,}\n(.*?)Total Apurado\s+(\d+)', re.S)
def conta_img(b):
    """imagem impressa do BU: bloco PRESIDENTE"""
    txt = b.decode('latin1', 'replace'); m = RXP.search(txt)
    if not m: return None
    c = collections.Counter()
    for l in m.group(1).splitlines():
        x = re.match(r'\s+\S.*?\s(\d{2})\s+(\d{1,4})\s*$', l)
        if x: c[('n', int(x.group(1)))] += int(x.group(2))
    rest = m.group(2)
    for k, nm in [('branco', 'Brancos'), ('nulo', 'Nulos')]:
        x = re.search(nm + r'\s+(\d+)', rest)
        if x and int(x.group(1)): c[k] += int(x.group(1))
    return c

def confere_vsc(vsc, arquivos):
    """devolve (autohash_ok, {sufixo: ok}) para as assinaturas SW e HW"""
    res = {}; auto = True
    for parte in raw_children(vsc)[:2]:
        e = tree(parte)[0][2]
        aa = e[2][2]; conteudo = e[3][2]
        h_auto = [x for x in aa if x[:2] == (0, 16)][-1][2][1][2]
        auto &= hashlib.sha512(conteudo).digest() == h_auto
        for _, _, item in tree(conteudo)[0][2][0][2]:
            nome = item[0][2].decode('latin1'); h = item[1][2][1][2]
            suf = nome.split('-')[-1]
            if suf in arquivos:
                ok = hashlib.sha512(arquivos[suf]).digest() == h
                res[suf] = res.get(suf, True) and ok
    return auto, res

# ---------------- trabalho por secao ----------------
SUF = ['bu.dat', 'rdv.dat', 'imgbu.dat', 'vota.vsc']
RX = re.compile(r'o(\d{5})([a-z]{2})(\d{5})(\d{4})(\d{4})-(bu\.dat|rdv\.dat|imgbu\.dat|vota\.vsc)$')

def pres(d):
    """Presidente = cargoConstitucional (tag 1) codigo 1"""
    return d.get((1, 1), collections.Counter())

def verifica(arqs):
    r = dict(tem_bu=int('bu.dat' in arqs), tem_rdv=int('rdv.dat' in arqs), tem_img=int('imgbu.dat' in arqs), tem_vsc=int('vota.vsc' in arqs))
    bu = conta_bu(arqs['bu.dat']) if 'bu.dat' in arqs else {}
    rdv = conta_rdv(arqs['rdv.dat']) if 'rdv.dat' in arqs else None
    img = conta_img(arqs['imgbu.dat']) if 'imgbu.dat' in arqs else None
    pb = pres(bu)
    r['bu_lula'] = pb[('n', 13)]; r['bu_flavio'] = pb[('n', 22)]; r['bu_branco'] = pb['branco']; r['bu_nulo'] = pb['nulo']
    r['bu_outros'] = sum(v for k, v in pb.items() if k not in [('n', 13), ('n', 22), 'branco', 'nulo'])
    r['bu_total'] = sum(pb.values())
    r['bu_outros_json'] = json.dumps({str(k): v for k, v in pb.items() if k not in [('n', 13), ('n', 22), 'branco', 'nulo']})
    # RDV x BU para TODOS os cargos do BU
    if rdv is not None:
        difs = [f'{k}:{dict(bu.get(k, {}))}!={dict(rdv.get(k, {}))}' for k in set(bu) | set(rdv) if bu.get(k, collections.Counter()) != rdv.get(k, collections.Counter())]
        r['rdv_igual_bu'] = int(not difs); r['rdv_dif'] = '; '.join(difs)[:2000]
        r['rdv_total_pres'] = sum(pres(rdv).values()); r['n_cargos'] = len(bu)
    else:
        r['rdv_igual_bu'] = -1; r['rdv_dif'] = ''; r['rdv_total_pres'] = -1; r['n_cargos'] = len(bu)
    r['img_igual_bu'] = -1 if img is None else int(+img == +pb)
    if 'vota.vsc' in arqs:
        auto, hs = confere_vsc(arqs['vota.vsc'], {s: arqs[s] for s in ['bu.dat', 'rdv.dat', 'imgbu.dat'] if s in arqs})
        r['vsc_auto_ok'] = int(auto)
        for s in ['bu.dat', 'rdv.dat', 'imgbu.dat']: r['hash_' + s.split('.')[0]] = int(hs[s]) if s in hs else -1
    else:
        r['vsc_auto_ok'] = -1; r['hash_bu'] = r['hash_rdv'] = r['hash_imgbu'] = -1
    return r

def work(job):
    url, k, membros = job
    try:
        arqs = {s: L.fetch_member(url, off, cs, m) for s, (off, cs, m) in membros.items()}
        return k, verifica(arqs), None
    except Exception:
        return k, None, f'{k}: {traceback.format_exc(limit=3)}'

COLS_INT = ['tem_bu', 'tem_rdv', 'tem_img', 'tem_vsc', 'bu_lula', 'bu_flavio', 'bu_branco', 'bu_nulo', 'bu_outros', 'bu_total',
            'rdv_igual_bu', 'rdv_total_pres', 'n_cargos', 'img_igual_bu', 'vsc_auto_ok', 'hash_bu', 'hash_rdv', 'hash_imgbu']

def main():
    OUT = sys.argv[1]
    ufs = sys.argv[2].split(',') if len(sys.argv) > 2 and sys.argv[2] != 'ALL' else L.UFS
    turnos = sys.argv[3].split(',') if len(sys.argv) > 3 else ['1t', '2t']
    W = int(sys.argv[4]) if len(sys.argv) > 4 else 12
    os.makedirs(OUT, exist_ok=True)
    with ProcessPoolExecutor(W) as ex:
        for t in turnos:
            for uf in ufs:
                try:
                    fs = f'{OUT}/{t}_{uf}_bu.parquet'
                    if os.path.exists(fs): print(f'{t} {uf}: ja feito', flush=True); continue
                    t0 = time.time(); url = L.URL.format(t=t, uf=uf)
                    versao = lambda: (lambda h: (h.headers.get('Last-Modified'), h.headers.get('Content-Length')))(L.sess().head(url, timeout=60))
                    v0 = versao(); rf = L.RangeFile(url); z = zipfile.ZipFile(rf)
                    # guarda o diretorio do zip (nome, CRC32, tamanho) para detectar republicacao depois
                    with open(f'{OUT}/{t}_{uf}_indice.tsv', 'w') as fi:
                        fi.write(f'# versao {v0[0]} | {v0[1]} bytes\n')
                        for i in z.infolist(): fi.write(f'{i.filename}\t{i.CRC:08x}\t{i.file_size}\t{i.date_time}\n')
                    sec = collections.defaultdict(dict)
                    for i in z.infolist():
                        m = RX.search(i.filename)
                        if m: sec[(int(m.group(3)), int(m.group(4)), int(m.group(5)))][m.group(6)] = (i.header_offset, i.compress_size, i.compress_type)
                    D = collections.defaultdict(list); errs = []
                    for fut in as_completed([ex.submit(work, (rf.url, k, mb)) for k, mb in sec.items()]):
                        k, r, err = fut.result()
                        if err: errs.append(err); continue
                        for c, x in zip(['mun', 'zona', 'secao'], k): D[c].append(x)
                        for c in COLS_INT: D[c].append(int(r[c]))
                        for c in ['rdv_dif', 'bu_outros_json']: D[c].append(r[c])
                    if versao() != v0: raise IOError(f'{t} {uf}: arquivo republicado durante a leitura ({v0} -> {versao()})')
                    tb = pa.table({**{c: pa.array(D[c], pa.int32()) for c in ['mun', 'zona', 'secao'] + COLS_INT},
                                   **{c: pa.array(D[c], pa.string()) for c in ['rdv_dif', 'bu_outros_json']}})
                    pq.write_table(tb, fs, compression='zstd')
                    if errs: open(f'{OUT}/{t}_{uf}_bu_erros.txt', 'w').write('\n'.join(errs))
                    n = tb.num_rows; g = lambda c: sum(1 for x in D[c] if x == 1)
                    print(f'{t} {uf}: OK {n} secoes | hash BU ok {g("hash_bu")} RDV ok {g("hash_rdv")} img ok {g("hash_imgbu")} | '
                          f'RDV=BU {g("rdv_igual_bu")} | img=BU {g("img_igual_bu")} | {len(errs)} erros, {time.time()-t0:.0f}s | versao {v0[0]}', flush=True)
                except Exception as e:
                    print(f"{t} {uf}: FALHOU ({str(e)[:200]})", flush=True)


if __name__ == '__main__':
    main()
