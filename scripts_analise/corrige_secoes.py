# Reprocessa secoes especificas (ex.: divergentes log x BU) com o parser atual e substitui no parquet
# uso: corrige_secoes.py <OUT> <turno 1t|2t> <divergencias.csv>
import sys, os, zipfile, tempfile, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logs_brasil as L
OUT, t, csv = sys.argv[1:4]
d = pd.read_csv(csv); tmp = tempfile.mkdtemp()
for uf, g in d.groupby('uf'):
    fv, fs = f'{OUT}/{t}_{uf}_votos.parquet', f'{OUT}/{t}_{uf}_secoes.parquet'
    V = pd.read_parquet(fv); S = pd.read_parquet(fs)
    rf = L.RangeFile(L.URL.format(t=t, uf=uf)); z = zipfile.ZipFile(rf); idx = {i.filename[-23:]: i for i in z.infolist() if i.filename.endswith('-log.jez')}
    for _, r in g.iterrows():
        tag = f'{uf.lower()}{int(r.mun):05d}{int(r.zona):04d}{int(r.secao):04d}-log.jez'; i = idx[tag]
        votos, info = L.parse(L.log_text(L.fetch_member(rf.url, i.header_offset, i.compress_size, i.compress_type), tmp))
        k = (V.mun == r.mun) & (V.zona == r.zona) & (V.secao == r.secao); antes = int(k.sum())
        new = pd.DataFrame(votos, columns=['t_hab', 't_voto', 'tipo', 'tent', 'manual', 'susp']).assign(mun=r.mun, zona=r.zona, secao=r.secao)
        V = pd.concat([V[~k], new[V.columns].astype(V.dtypes.to_dict())], ignore_index=True)
        ks = (S.mun == r.mun) & (S.zona == r.zona) & (S.secao == r.secao)
        for c in info: S.loc[ks, c] = info[c]
        S.loc[ks, 'votos'] = len(votos)
        print(t, uf, r.mun, r.zona, r.secao, 'antes', antes, 'depois', len(votos), 'oficial', r.bu)
    V.to_parquet(fv, compression='zstd', index=False); S.to_parquet(fs, compression='zstd', index=False)
