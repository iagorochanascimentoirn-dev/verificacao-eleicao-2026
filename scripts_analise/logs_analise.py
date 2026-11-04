# Analise dos horarios e tipos de habilitacao (logs de urna) x resultado por secao
# uso: python logs_analise.py <pasta com v1.csv v2.csv s1.csv s2.csv vs_rr.zip>
import pandas as pd, numpy as np, sys, zipfile, os
from scipy import stats
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
D=sys.argv[1]; rng=np.random.default_rng(0)
key=['mun','zona','secao']
vs=pd.read_csv(f'{D}/vs_rr_all.csv',sep=';',encoding='latin1',
               usecols=['NR_TURNO','CD_MUNICIPIO','NR_ZONA','NR_SECAO','CD_CARGO','NR_VOTAVEL','NM_VOTAVEL','QT_VOTOS'])
vs=vs[vs.CD_CARGO==1].rename(columns={'CD_MUNICIPIO':'mun','NR_ZONA':'zona','NR_SECAO':'secao'})
fig,axs=plt.subplots(2,2,figsize=(13,9))
for i,tn in enumerate([1,2]):
    print(f'\n================ {tn}º TURNO ================')
    v=pd.read_csv(f'{D}/v{tn}.csv',dtype={'urna':str}); s=pd.read_csv(f'{D}/s{tn}.csv')
    v['nbio']=(v.tipo!='biometrica').astype(int)
    v['h']=pd.to_datetime(v.t_voto,format='%H:%M:%S'); v['hora']=v.h.dt.hour
    print('A) tipo de habilitacao:'); print(v.tipo.value_counts().to_frame('votos').assign(pct=lambda x:(100*x.votos/x.votos.sum()).round(2)))
    # B) por hora
    hh=v.groupby('hora').agg(votos=('nbio','size'),sem_bio=('nbio','sum')); hh['pct_sem_bio']=(100*hh.sem_bio/hh.votos).round(2)
    print('\nB) por hora:'); print(hh)
    # C) por secao
    sec=v.groupby(key).agg(votos=('nbio','size'),sem_bio=('nbio','sum')).reset_index(); sec['pct']=100*sec.sem_bio/sec.votos
    p0=sec.sem_bio.sum()/sec.votos.sum()
    sec['z']=(sec.sem_bio-sec.votos*p0)/np.sqrt(sec.votos*p0*(1-p0))
    print('\nC) % sem biometria por secao: ',sec.pct.describe(percentiles=[.5,.9,.99]).round(2).to_dict())
    print('   secoes acima de 30% sem biometria:',(sec.pct>30).sum(),'| top 8:'); print(sec.sort_values('pct',ascending=False).head(8).round(1).to_string(index=False))
    # D) agrupamento: runs test (Wald-Wolfowitz) por secao, sequencia ordenada por horario
    v=v.sort_values(key+['t_voto']); out=[]
    for k,g in v.groupby(key):
        x=g.nbio.values; n1=x.sum(); n0=len(x)-n1
        if n1<3 or n0<3: continue
        r=1+(np.diff(x)!=0).sum(); mu=1+2*n1*n0/(n1+n0); var=2*n1*n0*(2*n1*n0-n1-n0)/((n1+n0)**2*(n1+n0-1))
        # maior sequencia seguida de sem-biometria
        mx=max((len(s) for s in ''.join(map(str,x)).split('0') if s),default=0)
        out.append((*k,len(x),n1,r,(r-mu)/np.sqrt(var),mx))
    rt=pd.DataFrame(out,columns=key+['votos','sem_bio','runs','z_runs','maior_seq'])
    rt['p']=stats.norm.cdf(rt.z_runs)  # poucas runs = agrupamento
    m=len(rt); rt['q']=np.minimum(1,rt.p.sort_values().pipe(lambda s:s*m/np.arange(1,m+1))[::-1].cummin()[::-1].reindex(rt.index))
    print(f'\nD) runs test em {m} secoes: z medio {rt.z_runs.mean():.2f} (esperado 0, sd {rt.z_runs.std():.2f}); p<0.01: {(rt.p<.01).sum()} (esperado ~{m*.01:.0f}); significativas apos FDR 5%: {(rt.q<.05).sum()}')
    print('   secoes com mais agrupamento:'); print(rt.sort_values('z_runs').head(6).round(3).to_string(index=False))
    # E) ultimos 30 min
    late=v.t_voto>='16:30:00'
    print(f'\nE) sem biometria antes das 16:30: {100*v.nbio[~late].mean():.2f}% | 16:30-17:00+: {100*v.nbio[late].mean():.2f}% ({late.sum()} votos)')
    print('   votos computados apos 17:00:',(v.t_voto>='17:00:00').sum(),'| mais tarde:',v.t_voto.max())
    # F) log x resultado oficial
    r=vs[vs.NR_TURNO==tn]; tot=r.groupby(key).QT_VOTOS.sum().rename('bu').reset_index()
    cmp_=sec.merge(tot,on=key,how='outer',indicator=True)
    print(f'\nF) votos no log x total Presidente no resultado: secoes {cmp_._merge.value_counts().to_dict()}; diferenca!=0 em {(cmp_.votos!=cmp_.bu).sum()} secoes; soma log {int(cmp_.votos.sum())} x resultado {int(cmp_.bu.sum())}')
    top=r[r.NR_VOTAVEL<90].groupby(['NR_VOTAVEL','NM_VOTAVEL']).QT_VOTOS.sum().sort_values(ascending=False).head(2)
    print('   dois mais votados (RR):',top.to_dict())
    for (nr,nm),_ in top.items():
        c=r[r.NR_VOTAVEL==nr].groupby(key).QT_VOTOS.sum().rename('c').reset_index().merge(sec,on=key)
        c['share']=100*c.c/c.votos; rho,pp=stats.spearmanr(c.pct,c.share)
        print(f'   correlacao (Spearman) %sem_bio x %{nm[:25]}: rho={rho:.3f} p={pp:.2g}')
    print('\nG) secoes com urna de contingencia:',s[s.contingencia==1][key].to_dict('records'))
    ax=axs[0,i]; ax2=ax.twinx(); ax.bar(hh.index,hh.votos,color='#9bb'); ax2.plot(hh.index,hh.pct_sem_bio,'o-',color='#c33')
    ax.set_title(f'{tn}º turno RR: votos por hora (barra) e % sem biometria (linha)'); ax.set_xlabel('hora'); ax2.set_ylabel('% sem biometria')
    axs[1,i].hist(rt.z_runs,bins=50,density=True,color='#9bb'); xs=np.linspace(-5,5,200); axs[1,i].plot(xs,stats.norm.pdf(xs),'r')
    axs[1,i].set_title(f'{tn}º turno: z do runs test por seção (vermelho = acaso)')
    sec.to_csv(f'{D}/sec{tn}.csv',index=False); rt.to_csv(f'{D}/runs{tn}.csv',index=False)
plt.tight_layout(); plt.savefig(f'{D}/logs_rr.png',dpi=110)
