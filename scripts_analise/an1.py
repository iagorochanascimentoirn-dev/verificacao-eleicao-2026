import pandas as pd, numpy as np, sys
from scipy import stats
S=sys.argv[1]; O=f'{S}/out'
v=pd.read_parquet(f'{O}/votos.parquet'); d=pd.read_parquet(f'{O}/detalhe.parquet')
K=['SG_UF','CD_MUNICIPIO','NR_ZONA','NR_SECAO']
v['SG_UF']=v.SG_UF.astype(str)
w=v.pivot_table(index=['NR_TURNO']+K,columns='NR_VOTAVEL',values='QT_VOTOS',aggfunc='sum',fill_value=0)
w.columns=[f'c{c}' for c in w.columns]; w=w.reset_index()
m=d.merge(w,on=['NR_TURNO']+K,how='outer',indicator=True)
print('merge',m._merge.value_counts().to_dict())
vc=[c for c in w.columns if c.startswith('c')]
m['soma']=m[vc].sum(axis=1)
# T0 consistência
for t in (1,2):
    x=m[m.NR_TURNO==t]
    print(f'T{t}: secoes={len(x)} soma_votos={x.soma.sum()} comparec={x.QT_COMPARECIMENTO.sum()} '
          f'soma!=comparec:{(x.soma!=x.QT_COMPARECIMENTO).sum()} comparec>aptos:{(x.QT_COMPARECIMENTO>x.QT_APTOS).sum()} '
          f'nom+br+nu!=soma:{(x.QT_VOTOS_NOMINAIS+x.QT_VOTOS_BRANCOS+x.QT_VOTOS_NULOS!=x.soma).sum()}')
bad=m[(m.soma!=m.QT_COMPARECIMENTO)]
print(bad[['NR_TURNO']+K+['QT_APTOS','QT_COMPARECIMENTO','soma','DS_ORIGEM_VOTO']].head(15).to_string())
m.to_parquet(f'{O}/secao.parquet')
