# Por secao: variacao do % manual (1t->2t) x variacao do % Lula (1t->2t), dentro de cada UF
import pandas as pd, numpy as np, glob, re
from scipy import stats
D = '/home/iago-rocha/Documentos/tese-urna-eletronica/dados_logs'; K = ['mun', 'zona', 'secao']
pr = pd.read_parquet(f'{D}/presidente_secao.parquet').rename(columns={'CD_MUNICIPIO': 'mun', 'NR_ZONA': 'zona', 'NR_SECAO': 'secao', 'SG_UF': 'uf'})
lula = pr[pr.NR_VOTAVEL == 13].groupby(['uf', 'NR_TURNO'] + K).QT_VOTOS.sum()
out = []; allp = []
for f in sorted(glob.glob(f'{D}/1t_*_votos.parquet')):
    uf = re.search(r'1t_(\w\w)_', f).group(1)
    if uf == 'ZZ': continue
    s = {}
    for i, t in [(1, '1t'), (2, '2t')]:
        v = pd.read_parquet(f.replace('1t_', t + '_'), columns=K + ['tipo'])
        g = v.assign(man=(v.tipo == 1)).groupby(K).agg(n=('man', 'size'), m=('man', 'sum'))
        g['lula'] = lula.loc[(uf, i)].reindex(g.index).fillna(0).values; s[t] = g
    p = s['1t'].join(s['2t'], lsuffix='1', rsuffix='2', how='inner'); p = p[(p.n1 >= 50) & (p.n2 >= 50)].copy()
    p['dman'] = 100 * (p.m2 / p.n2 - p.m1 / p.n1); p['dlula'] = 100 * (p.lula2 / p.n2 - p.lula1 / p.n1); p['uf'] = uf
    rho = stats.spearmanr(p.dman, p.dlula)[0]
    sub = p[p.dman > 5]; resto = p[p.dman <= 5]
    out.append(dict(uf=uf, rho=rho, secoes=len(p), secoes_manual_subiu5pp=len(sub),
                    dlula_nessas=sub.dlula.mean(), dlula_demais=resto.dlula.mean(),
                    dif=sub.dlula.mean() - resto.dlula.mean()))
    allp.append(p.reset_index())
r = pd.DataFrame(out).set_index('uf').sort_values('rho'); pd.set_option('display.width', 200); print(r.round(3).to_string())
a = pd.concat(allp); a['dman_c'] = a.dman - a.groupby('uf').dman.transform('mean'); a['dlula_c'] = a.dlula - a.groupby('uf').dlula.transform('mean')
print('\nBrasil (centrado por UF): rho', round(stats.spearmanr(a.dman_c, a.dlula_c)[0], 4), '| secoes', len(a))
sl = stats.linregress(a.dman_c, a.dlula_c); print(f'regressao: cada +1pp de manual -> {sl.slope:+.4f}pp de Lula (r2={sl.rvalue**2:.5f})')
r.round(4).to_csv(f'{D}/manuais_variacao_voto_uf.csv')
