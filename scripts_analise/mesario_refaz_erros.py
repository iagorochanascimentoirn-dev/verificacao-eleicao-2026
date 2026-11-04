# Refaz as secoes que falharam por rede no logs_mesario.py e acrescenta nos parquets
# uso: python mesario_refaz_erros.py <pasta mesario> <TMP>
import sys, os, glob, re, zipfile, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logs_brasil as L, logs_mesario as M
OUT, TMP = sys.argv[1], sys.argv[2]
for fe in sorted(glob.glob(f'{OUT}/*_mes_erros.txt')):
    t, uf = re.search(r'(\dt)_(\w\w)_mes_erros', fe).groups()
    nomes = set(re.findall(r'^(\S+-log\.jez):', open(fe).read(), re.M))
    rf = L.RangeFile(L.URL.format(t=t, uf=uf)); z = zipfile.ZipFile(rf)
    jobs = [(rf.url, i.filename, i.header_offset, i.compress_size, i.compress_type, TMP) for i in z.infolist() if i.filename.split('/')[-1] in nomes or i.filename in nomes]
    S, J, falhas = [], [], []
    for j in jobs:
        k, s, jav, err = M.work(j)
        if err: falhas.append(err); continue
        if s is None: continue
        S.append(dict(zip(['mun', 'zona', 'secao'], k), **{c: int(s.get(c, 0)) for c in M.COLS}))
        J += [dict(zip(['mun', 'zona', 'secao', 't', 'gap', 'tipo_anterior'], (*k, *x))) for x in jav]
    fs, fj = f'{OUT}/{t}_{uf}_mes_secoes.parquet', f'{OUT}/{t}_{uf}_jav.parquet'
    a = pd.read_parquet(fs); b = pd.DataFrame(S).astype('int32')
    a = pd.concat([a, b]).drop_duplicates(['mun', 'zona', 'secao'], keep='last'); a.to_parquet(fs, compression='zstd', index=False)
    if J: pd.concat([pd.read_parquet(fj), pd.DataFrame(J).astype('int32')]).to_parquet(fj, compression='zstd', index=False)
    print(t, uf, 'pedidas', len(nomes), 'achadas', len(jobs), 'ok', len(S), 'falhas', len(falhas), flush=True)
    if not falhas: os.rename(fe, fe + '.resolvido')
    else: open(fe, 'w').write('\n'.join(falhas))
