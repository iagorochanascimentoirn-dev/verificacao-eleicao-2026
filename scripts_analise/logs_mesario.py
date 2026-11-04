# Por secao: quem liberou cada voto manual (mesario cadastrado / digital nova / digital nao associada) e
# eventos "O eleitor identificado ja votou" com o contexto (tempo desde o voto anterior e tipo dele).
# Le os -log.jez por HTTP Range (mesma infra do logs_brasil.py). Retoma por UF/turno.
# uso: python logs_mesario.py <OUT> <TMP> [UF,UF|ALL] [1t,2t] [workers]
import sys, os, re, time, collections, traceback, zipfile
import pyarrow as pa, pyarrow.parquet as pq
from concurrent.futures import ProcessPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logs_brasil as L

def hms(t): return int(t[0:2]) * 3600 + int(t[3:5]) * 60 + int(t[6:8])

def parse(txt):
    seen = set(); rows = []
    for l in txt.splitlines():
        if l in seen: continue
        seen.add(l); r = l.split('\t')
        if len(r) >= 5: rows.append(r)
    dias = collections.Counter(r[0][:10] for r in rows if r[4] == 'O voto do eleitor foi computado')
    if not dias: return None, []
    dia = max(dias, key=lambda d: (d[6:10], d[3:5], d[0:2]))
    S = collections.Counter(); mes = collections.Counter(); jav = []
    cyc = []; last_t = None; last_tipo = None; run_novo = 0; max_run_novo = 0
    for r in rows:
        if not r[0].startswith(dia): continue
        m = r[4]; t = hms(r[0][11:19]); cyc.append(m)
        if m == 'O eleitor identificado já votou':
            jav.append((t, t - last_t if last_t is not None else -1, last_tipo if last_tipo is not None else -1))
        elif m == 'Eleitor não encontrado para o identificador informado': S['nao_encontrado'] += 1
        elif m.startswith('Habilitação cancelada'): cyc = []
        elif m == 'O voto do eleitor foi computado':
            bio = any(x == 'Tipo de habilitação do eleitor [biométrica]' for x in cyc)
            man = any(x.startswith('Solicitação de dado pessoal do eleitor para habilitação manual') for x in cyc)
            S['votos'] += 1
            if bio: tipo = 0
            elif man:
                tipo = 1; S['manual'] += 1
                h = [x for x in cyc if x.startswith('Mesário ') and x.endswith(' habilitou o eleitor')]
                if h: S['man_mesario'] += 1; mes[h[-1]] += 1; quem = 0
                elif any('vai salvar a digital em novo arquivo' in x for x in cyc): S['man_digital_nova'] += 1; quem = 1
                elif any('Não é possível associar a habilitação a um mesário' in x for x in cyc): S['man_nao_assoc'] += 1; quem = 1
                else: S['man_outro'] += 1; quem = 0
                run_novo = run_novo + 1 if quem else 0; max_run_novo = max(max_run_novo, run_novo)
            else:
                tipo = 2; S['sem_cadastro'] += 1
            if tipo != 1: run_novo = 0
            last_t, last_tipo = t, tipo; cyc = []
    S['mesarios_liberaram'] = len(mes); S['max_lib_um_mesario'] = max(mes.values()) if mes else 0
    S['max_seq_digital_nao_cadastrada'] = max_run_novo; S['ja_votou'] = len(jav)
    return S, jav

RX = re.compile(r'o(\d{5})([a-z]{2})(\d{5})(\d{4})(\d{4})-log\.jez$')
COLS = ['votos', 'manual', 'man_mesario', 'man_digital_nova', 'man_nao_assoc', 'man_outro', 'sem_cadastro', 'nao_encontrado',
        'mesarios_liberaram', 'max_lib_um_mesario', 'max_seq_digital_nao_cadastrada', 'ja_votou']

def work(job):
    url, name, off, csize, method, tmp = job
    try:
        m = RX.search(name); k = (int(m.group(3)), int(m.group(4)), int(m.group(5)))
        S, jav = parse(L.log_text(L.fetch_member(url, off, csize, method), tmp))
        return k, S, jav, None
    except Exception:
        return None, None, None, f'{name}: {traceback.format_exc(limit=2)}'

def main():
    OUT, TMP = sys.argv[1], sys.argv[2]
    ufs = sys.argv[3].split(',') if len(sys.argv) > 3 and sys.argv[3] != 'ALL' else L.UFS
    turnos = sys.argv[4].split(',') if len(sys.argv) > 4 else ['1t', '2t']
    W = int(sys.argv[5]) if len(sys.argv) > 5 else 12
    os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
    with ProcessPoolExecutor(W) as ex:
        for t in turnos:
            for uf in ufs:
                fs, fj = f'{OUT}/{t}_{uf}_mes_secoes.parquet', f'{OUT}/{t}_{uf}_jav.parquet'
                if os.path.exists(fs): print(f'{t} {uf}: ja feito', flush=True); continue
                t0 = time.time(); rf = L.RangeFile(L.URL.format(t=t, uf=uf)); z = zipfile.ZipFile(rf)
                jobs = [(rf.url, i.filename, i.header_offset, i.compress_size, i.compress_type, TMP) for i in z.infolist() if i.filename.endswith('-log.jez')]
                SC = collections.defaultdict(list); J = collections.defaultdict(list); errs = []
                for fut in as_completed([ex.submit(work, j) for j in jobs]):
                    k, S, jav, err = fut.result()
                    if err: errs.append(err); continue
                    if S is None: continue
                    for c, x in zip(['mun', 'zona', 'secao'], k): SC[c].append(x)
                    for c in COLS: SC[c].append(int(S.get(c, 0)))
                    for (tt, gap, pt) in jav:
                        for c, x in zip(['mun', 'zona', 'secao', 't', 'gap', 'tipo_anterior'], (*k, tt, gap, pt)): J[c].append(x)
                pq.write_table(pa.table({c: pa.array(J[c], pa.int32()) for c in ['mun', 'zona', 'secao', 't', 'gap', 'tipo_anterior']}), fj, compression='zstd')
                pq.write_table(pa.table({c: pa.array(SC[c], pa.int32()) for c in ['mun', 'zona', 'secao'] + COLS}), fs, compression='zstd')
                if errs: open(f'{OUT}/{t}_{uf}_mes_erros.txt', 'w').write('\n'.join(errs))
                print(f'{t} {uf}: OK {len(jobs)} secoes, {sum(SC["manual"])} manuais, {len(J["t"])} ja_votou, {len(errs)} erros, {time.time()-t0:.0f}s', flush=True)

if __name__ == '__main__':
    main()
