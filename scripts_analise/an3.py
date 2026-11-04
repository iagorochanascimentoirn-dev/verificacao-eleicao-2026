import pandas as pd, numpy as np, sys
from scipy import stats
S=sys.argv[1]; O=f'{S}/out'; rng=np.random.default_rng(42)
exp2=np.array([sum(np.log10(1+1/(10*k+d)) for k in range(1,10)) for d in range(10)])
def d2(s): s=s[s>=10].astype(int); return s.astype(str).str[1].astype(int)
def ld(s): s=s[s>=40].astype(int); return s%10
for tn in (1,2):
    t=pd.read_parquet(f'{O}/t{tn}.parquet')
    # nulo: cada seção sorteia votos com a proporção da sua ZONA (sem fraude por construção)
    g=t.groupby(['SG_UF','CD_MUNICIPIO','NR_ZONA'])
    pz=(g.c13.transform('sum')/g.QT_COMPARECIMENTO.transform('sum')).values
    pf=(g.c22.transform('sum')/g.QT_COMPARECIMENTO.transform('sum')).values
    n=t.QT_COMPARECIMENTO.values.astype(int)
    for cand,col,p in (('Lula','c13',pz),('Flávio','c22',pf)):
        real2=d2(t[col]); realL=ld(t[col])
        sims2=[];simsL=[];simsC=[]
        for k in range(20):
            sim=pd.Series(rng.binomial(n,np.clip(p,0,1)))
            a=d2(sim); sims2.append(a.mean()); b=ld(sim)
            c=np.bincount(b,minlength=10); simsC.append(stats.chisquare(c).statistic)
        cR=np.bincount(realL,minlength=10)
        print(f'{tn}T {cand:6s} 2BL real={real2.mean():.3f}  nulo(sem fraude)={np.mean(sims2):.3f}±{np.std(sims2):.3f} | último dígito chi2 real={stats.chisquare(cR).statistic:.1f}  nulo={np.mean(simsC):.1f} [{np.min(simsC):.1f}–{np.max(simsC):.1f}]')
