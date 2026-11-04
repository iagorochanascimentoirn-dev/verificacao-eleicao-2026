# Tabela secao -> local de votacao (nome/endereco) a partir do votacao_secao_2026_BR.zip do TSE
# uso: python locais_secao.py <votacao_secao_2026_BR.zip> <saida.parquet>
import sys, zipfile, pandas as pd
z = zipfile.ZipFile(sys.argv[1]); parts = []
cols = ['NR_TURNO', 'SG_UF', 'CD_MUNICIPIO', 'NM_MUNICIPIO', 'NR_ZONA', 'NR_SECAO', 'CD_CARGO', 'NR_LOCAL_VOTACAO', 'NM_LOCAL_VOTACAO', 'DS_LOCAL_VOTACAO_ENDERECO']
for ch in pd.read_csv(z.open('votacao_secao_2026_BR.csv'), sep=';', encoding='latin1', usecols=cols, chunksize=2_000_000, dtype=str):
    parts.append(ch[ch.CD_CARGO == '1'].drop(columns='CD_CARGO').drop_duplicates())
d = pd.concat(parts).drop_duplicates()
for c in ['NR_TURNO', 'CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO']: d[c] = d[c].astype('int32')
d.to_parquet(sys.argv[2], index=False, compression='zstd'); print(len(d), d.NR_TURNO.value_counts().to_dict())
