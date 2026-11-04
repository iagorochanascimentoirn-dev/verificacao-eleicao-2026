import pandas as pd, numpy as np, sys
from scipy import stats
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
S=sys.argv[1]; O=f'{S}/out'
m=pd.read_parquet(f'{O}/secao.parquet'); m=m[m._merge=='both']
m['ufkind']=np.where(m.SG_UF=='ZZ','EXT','BR')
t2=m[m.NR_TURNO==2].copy(); t1=m[m.NR_TURNO==1].copy()
for t in (t1,t2):
    t['turn']=t.QT_COMPARECIMENTO/t.QT_APTOS
    val=t.c13+t.c22; t['lula']=t.c13/val.replace(0,np.nan)
print('anomalas 85 left_only dropped')
# T1 Klimek fingerprint 2T
fig,ax=plt.subplots(1,2,figsize=(13,5))
for a,(t,nm) in zip(ax,[(t1,'1º turno'),(t2,'2º turno')]):
    x=t[(t.QT_APTOS>=50)&t.lula.notna()]
    a.hist2d(x.turn,x.lula,bins=[100,100],range=[[0.4,1],[0,1]],cmap='viridis',norm=matplotlib.colors.LogNorm())
    a.set_xlabel('comparecimento'); a.set_ylabel('Lula / (Lula+Flávio)'); a.set_title(f'Impressão digital (Klimek) — {nm}')
plt.tight_layout(); plt.savefig(f'{O}/klimek.png',dpi=110)
x=t2[t2.QT_APTOS>=50]
print('\n[T1] seções 2T com comparec>=95%:',(x.turn>=.95).sum(),' de',len(x),' | comparec>=95% e Lula>=95%:',((x.turn>=.95)&(x.lula>=.95)).sum(),' | comparec>=95% e Flávio>=95%:',((x.turn>=.95)&(x.lula<=.05)).sum())
print('     comparec 2T: média %.3f  p99 %.3f  máx %.3f'%(x.turn.mean(),x.turn.quantile(.99),x.turn.max()))
# correlação comparec x voto (2T) dentro de município
x=x.dropna(subset=['lula'])
for col in ['turn','lula']: x[col+'_dm']=x[col]-x.groupby(['SG_UF','CD_MUNICIPIO'])[col].transform('mean')
print('     corr(comparec, Lula) bruta %.3f | dentro do município %.3f'%(x.turn.corr(x.lula),x.turn_dm.corr(x.lula_dm)))
# T2 último dígito
def lastdig(s,nm):
    s=s[s>=40].astype(int); c=np.bincount(s%10,minlength=10); chi=stats.chisquare(c)
    print(f'[T2] último dígito {nm:22s} n={len(s):7d}  chi2={chi.statistic:6.1f} p={chi.pvalue:.3f}  freq%={np.round(c/c.sum()*100,2).tolist()}')
for t,tn in ((t1,'1T'),(t2,'2T')):
    lastdig(t.c13,f'Lula {tn}'); lastdig(t.c22,f'Flávio {tn}'); lastdig(t.QT_COMPARECIMENTO,f'Comparecimento {tn}')
# T3 2BL
def bl2(s,nm):
    s=s[s>=10].astype(int); dg=s.astype(str).str[1].astype(int)
    exp=np.array([sum(np.log10(1+1/(10*k+d)) for k in range(1,10)) for d in range(10)])
    c=np.bincount(dg,minlength=10); chi=stats.chisquare(c,exp*c.sum())
    print(f'[T3] 2BL {nm:14s} média={dg.mean():.3f} (Benford 4.187)  chi2={chi.statistic:8.1f} p={chi.pvalue:.2g}')
for t,tn in ((t1,'1T'),(t2,'2T')):
    bl2(t.c13,f'Lula {tn}'); bl2(t.c22,f'Flávio {tn}')
t1.to_parquet(f'{O}/t1.parquet'); t2.to_parquet(f'{O}/t2.parquet')
