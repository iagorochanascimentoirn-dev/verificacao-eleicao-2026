import pandas as pd, zipfile, sys
S=sys.argv[1]
z=zipfile.ZipFile(f'{S}/dl_tse/votacao_secao_2026_BR.zip')
cols=['NR_TURNO','SG_UF','CD_MUNICIPIO','NM_MUNICIPIO','NR_ZONA','NR_SECAO','NR_VOTAVEL','NM_VOTAVEL','QT_VOTOS']
parts=[]
for ch in pd.read_csv(z.open('votacao_secao_2026_BR.csv'),sep=';',encoding='latin1',usecols=cols,chunksize=2_000_000,
                      dtype={'SG_UF':'category','NM_MUNICIPIO':'category','NM_VOTAVEL':'category'}):
    parts.append(ch)
v=pd.concat(parts); v.to_parquet(f'{S}/out/votos.parquet')
print(v.shape); print(v.groupby(['NR_TURNO','NR_VOTAVEL','NM_VOTAVEL'],observed=True).QT_VOTOS.sum().sort_values(ascending=False).groupby(level=0).head(12))
z=zipfile.ZipFile(f'{S}/dl_tse/detalhe.zip')
d=pd.read_csv(z.open('detalhe_votacao_secao_2026_BR.csv'),sep=';',encoding='latin1',
  usecols=['NR_TURNO','SG_UF','CD_MUNICIPIO','NM_MUNICIPIO','NR_ZONA','NR_SECAO','CD_CARGO','QT_APTOS','QT_COMPARECIMENTO','QT_ABSTENCOES','QT_VOTOS_NOMINAIS','QT_VOTOS_BRANCOS','QT_VOTOS_NULOS','NR_LOCAL_VOTACAO','DT_RECEBIMENTO_BU_HOR_TSE','DS_ORIGEM_VOTO','ST_SECAO_INSTALADA','ST_SECAO_ANULADA','CD_MODELO_URNA'])
print(d.CD_CARGO.value_counts()); print(d.groupby('NR_TURNO')[['QT_APTOS','QT_COMPARECIMENTO']].sum()); print(d.DS_ORIGEM_VOTO.value_counts()); print(d.CD_MODELO_URNA.value_counts()); print(d.ST_SECAO_ANULADA.value_counts())
d.to_parquet(f'{S}/out/detalhe.parquet')
