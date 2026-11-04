# Variacao do % de votos manuais 1t -> 2t por UF: teste de proporcoes (agregado) e teste pareado por secao
import pandas as pd, numpy as np, glob, re
from scipy import stats
D = '/home/iago-rocha/Documentos/tese-urna-eletronica/dados_logs'; K = ['mun', 'zona', 'secao']; rows = []
for f in sorted(glob.glob(f'{D}/1t_*_votos.parquet')):
    uf = re.search(r'1t_(\w\w)_', f).group(1)
    if uf == 'ZZ': continue
    s = {}
    for t in ['1t', '2t']:
        v = pd.read_parquet(f.replace('1t_', t + '_'), columns=K + ['tipo'])
        s[t] = v.assign(man=(v.tipo == 1)).groupby(K).agg(n=('man', 'size'), m=('man', 'sum'))
    p = s['1t'].join(s['2t'], lsuffix='1', rsuffix='2', how='inner'); p = p[(p.n1 >= 30) & (p.n2 >= 30)]
    n1, m1, n2, m2 = p.n1.sum(), p.m1.sum(), p.n2.sum(), p.m2.sum(); p1, p2 = m1 / n1, m2 / n2
    pp = (m1 + m2) / (n1 + n2); z = (p2 - p1) / np.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    d = p.m2 / p.n2 - p.m1 / p.n1; tt = stats.ttest_1samp(d, 0)
    rows.append(dict(uf=uf, pct_1t=100 * p1, pct_2t=100 * p2, var_pp=100 * (p2 - p1), var_rel=100 * (p2 / p1 - 1), z_agregado=z,
                     secoes=len(p), media_secao_pp=100 * d.mean(), t_pareado=tt.statistic, p_pareado=tt.pvalue,
                     pct_secoes_subiu=100 * (d > 0).mean(), pct_secoes_caiu=100 * (d < 0).mean(),
                     secoes_subiu_5pp=int((d > .05).sum())))
r = pd.DataFrame(rows).set_index('uf')
m = len(r); o = r.p_pareado.rank(); r['p_bonf'] = np.minimum(1, r.p_pareado * m)
r.sort_values('var_pp', ascending=False).round(4).to_csv(f'{D}/manuais_variacao_uf.csv')
pd.set_option('display.width', 250); print(r.sort_values('var_pp', ascending=False).round(3).to_string())
