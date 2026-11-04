# Extrai voto a voto (horario + tipo de habilitacao) dos logs de urna do TSE, Brasil inteiro, em fluxo:
# le o zip remoto por HTTP Range (so as entradas -log.jez), sem baixar o zip inteiro.
# Saida: <OUT>/<turno>_<UF>_votos.parquet e <turno>_<UF>_secoes.parquet. Retoma: pula UF/turno ja feito.
# uso: python logs_brasil.py <OUT> <TMP> [UF,UF,...] [1t,2t] [workers]
import sys, os, io, re, zlib, struct, zipfile, subprocess, tempfile, time, collections, traceback
import requests, pyarrow as pa, pyarrow.parquet as pq
from concurrent.futures import ProcessPoolExecutor, as_completed

URL = 'https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/arqurnatot/bu_imgbu_logjez_rdv_vscmr_2026_{t}_{uf}.zip'
UFS = 'AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ'.split()
TIPO = {'biometrica': 0, 'manual_apos_falha': 1, 'sem_biometria': 2, 'outro': 3}
S = None

def sess():
    global S
    if S is None: S = requests.Session()
    return S

def get_range(url, a, b, tries=8):
    for i in range(tries):
        try:
            r = sess().get(url, headers={'Range': f'bytes={a}-{b}'}, timeout=120)
            if r.status_code == 206 and len(r.content) == b - a + 1: return r.content
        except Exception: pass
        time.sleep(min(60, 2 ** i))
    raise IOError(f'range falhou {url} {a}-{b}')

class RangeFile(io.RawIOBase):
    """arquivo remoto so-leitura com cache de blocos, para o zipfile ler o diretorio central"""
    def __init__(self, url):
        r = sess().head(url, timeout=60, allow_redirects=True); r.raise_for_status()
        self.url, self.size, self.pos, self.cache = r.url, int(r.headers['Content-Length']), 0, {}
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, wh=0):
        self.pos = off if wh == 0 else (self.pos + off if wh == 1 else self.size + off); return self.pos
    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0: return b''
        BS = 4 << 20; out = bytearray(); p = self.pos
        while len(out) < n:
            blk = p // BS
            if blk not in self.cache:
                if len(self.cache) > 64: self.cache.clear()
                self.cache[blk] = get_range(self.url, blk * BS, min(self.size, (blk + 1) * BS) - 1)
            d = self.cache[blk][p - blk * BS:]; take = d[:n - len(out)]; out += take; p += len(take)
        self.pos = p; return bytes(out)
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

def fetch_member(url, off, csize, method):
    h = get_range(url, off, off + 30 + 1024 + csize - 1)
    assert h[:4] == b'PK\x03\x04'
    nl, el = struct.unpack('<HH', h[26:30]); st = 30 + nl + el
    data = h[st:st + csize]
    if len(data) < csize: data += get_range(url, off + st + len(data), off + st + csize - 1)
    if method == 0: return data
    if method == 8: return zlib.decompress(data, -15)
    raise ValueError(f'metodo {method}')

def log_text(jez_bytes, tmp):
    wd = tempfile.mkdtemp(dir=tmp); p = os.path.join(wd, 'a.jez'); open(p, 'wb').write(jez_bytes)
    pend, txts = [p], []
    while pend:
        a = pend.pop(); od = tempfile.mkdtemp(dir=wd)
        subprocess.run(['7z', 'x', '-y', a, '-o' + od], capture_output=True)
        for root, _, fs in os.walk(od):
            for f in fs:
                fp = os.path.join(root, f)
                if f.endswith('.jez'): pend.append(fp)
                elif f.startswith('logd'): txts.append(open(fp, 'rb').read().decode('latin1'))
    subprocess.run(['rm', '-rf', wd]); return '\n'.join(txts)

def hms(t): return int(t[0:2]) * 3600 + int(t[3:5]) * 60 + int(t[6:8])

def parse(txt):
    # o .jez pode trazer copias de seguranca do mesmo log (MI/ME): linha identica (hash encadeado) = copia
    seen = set(); lines = []
    for l in txt.splitlines():
        if l not in seen: seen.add(l); lines.append(l)
    rows = [r for r in (l.split('\t') for l in lines) if len(r) >= 5]
    dias = collections.Counter(r[0][:10] for r in rows if r[4] == 'O voto do eleitor foi computado')
    if not dias: return [], None
    # log e cumulativo (urna do 2o turno traz o 1o): usa o ULTIMO dia com votos
    dia = max(dias, key=lambda d: (d[6:10], d[3:5], d[0:2]))
    new = lambda: dict(bio=False, tent=0, man=False, susp=False, hab=None)
    cyc = new(); urnas = set(); cont = False; ini = fim = None; nev = 0; votos = []
    for r in rows:
        if not r[0].startswith(dia): continue
        nev += 1; msg = r[4]; t = hms(r[0][11:19]); urnas.add(r[2])
        if 'Urna de contingência' in msg: cont = True
        if msg.startswith('Solicita digital. Tentativa'): cyc['tent'] += 1
        elif msg == 'Tipo de habilitação do eleitor [biométrica]': cyc['bio'] = True
        elif msg.startswith('Solicitação de dado pessoal do eleitor para habilitação manual'): cyc['man'] = True
        elif msg == 'Eleitor foi habilitado': cyc['hab'] = t
        elif msg.startswith('Eleitor foi suspenso'): cyc['susp'] = True
        elif msg.startswith('Habilitação cancelada'): cyc = new()
        elif msg == 'O voto do eleitor foi computado':
            tipo = 'biometrica' if cyc['bio'] else ('manual_apos_falha' if cyc['man'] else ('sem_biometria' if cyc['tent'] == 0 else 'outro'))
            votos.append((cyc['hab'] if cyc['hab'] is not None else -1, t, TIPO[tipo], min(cyc['tent'], 127), int(cyc['man']), int(cyc['susp'])))
            ini = t if ini is None else min(ini, t); fim = t if fim is None else max(fim, t); cyc = new()
    return votos, dict(dia=dia, contingencia=int(cont), n_urnas=len(urnas), inicio=ini or -1, fim=fim or -1, eventos=nev)

RX = re.compile(r'o(\d{5})([a-z]{2})(\d{5})(\d{4})(\d{4})-log\.jez$')

def work(job):
    url, name, off, csize, method, tmp = job
    try:
        m = RX.search(name); mun, zona, sec = int(m.group(3)), int(m.group(4)), int(m.group(5))
        votos, info = parse(log_text(fetch_member(url, off, csize, method), tmp))
        return mun, zona, sec, votos, info, None
    except Exception:
        return None, None, None, None, None, f'{name}: {traceback.format_exc(limit=2)}'

def main():
    OUT, TMP = sys.argv[1], sys.argv[2]
    ufs = sys.argv[3].split(',') if len(sys.argv) > 3 and sys.argv[3] != 'ALL' else UFS
    turnos = sys.argv[4].split(',') if len(sys.argv) > 4 else ['1t', '2t']
    W = int(sys.argv[5]) if len(sys.argv) > 5 else 12
    os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
    with ProcessPoolExecutor(W) as ex:
        for t in turnos:
            for uf in ufs:
                fv, fs = f'{OUT}/{t}_{uf}_votos.parquet', f'{OUT}/{t}_{uf}_secoes.parquet'
                if os.path.exists(fs): print(f'{t} {uf}: ja feito', flush=True); continue
                t0 = time.time(); rf = RangeFile(URL.format(t=t, uf=uf)); z = zipfile.ZipFile(rf)
                jobs = [(rf.url, i.filename, i.header_offset, i.compress_size, i.compress_type, TMP)
                        for i in z.infolist() if i.filename.endswith('-log.jez')]
                V = collections.defaultdict(list); SEC = collections.defaultdict(list); errs = []
                for k, fut in enumerate(as_completed([ex.submit(work, j) for j in jobs])):
                    mun, zona, sec, votos, info, err = fut.result()
                    if err: errs.append(err); continue
                    SEC['mun'].append(mun); SEC['zona'].append(zona); SEC['secao'].append(sec)
                    for c in ['dia', 'contingencia', 'n_urnas', 'inicio', 'fim', 'eventos']:
                        SEC[c].append(info[c] if info else None)
                    SEC['votos'].append(len(votos))
                    for v in votos:
                        V['mun'].append(mun); V['zona'].append(zona); V['secao'].append(sec)
                        for c, x in zip(['t_hab', 't_voto', 'tipo', 'tent', 'manual', 'susp'], v): V[c].append(x)
                    if (k + 1) % 2000 == 0: print(f'{t} {uf}: {k+1}/{len(jobs)} {time.time()-t0:.0f}s', flush=True)
                tv = pa.table({'mun': pa.array(V['mun'], pa.int32()), 'zona': pa.array(V['zona'], pa.int16()), 'secao': pa.array(V['secao'], pa.int16()),
                               't_hab': pa.array(V['t_hab'], pa.int32()), 't_voto': pa.array(V['t_voto'], pa.int32()),
                               'tipo': pa.array(V['tipo'], pa.int8()), 'tent': pa.array(V['tent'], pa.int8()),
                               'manual': pa.array(V['manual'], pa.int8()), 'susp': pa.array(V['susp'], pa.int8())})
                pq.write_table(tv, fv, compression='zstd')
                pq.write_table(pa.table(dict(SEC)), fs, compression='zstd')  # por ultimo: marca UF/turno como feito
                if errs: open(f'{OUT}/{t}_{uf}_erros.txt', 'w').write('\n'.join(errs))
                print(f'{t} {uf}: OK {len(jobs)} secoes, {tv.num_rows} votos, {len(errs)} erros, {time.time()-t0:.0f}s', flush=True)

if __name__ == '__main__':
    main()
