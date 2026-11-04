# Inferencia ecologica: % estimado de Lula/Flavio entre votos manuais e sem biometria cadastrada.
# Modelo por secao (efeito fixo de municipio): share_i = a_mun + d_man*pman_i + d_sem*psem_i  (ponderado por votos)
# => p_bio = share_total - d_man*MAN - d_sem*SEM ; p_man = p_bio + d_man ; p_sem = p_bio + d_sem
import pandas as pd, numpy as np, glob, re
D = '/home/iago-rocha/Documentos/tese-urna-eletronica/dados_logs'; K = ['uf', 'mun', 'zona', 'secao']
pr = pd.read_parquet(f'{D}/presidente_secao.parquet').rename(columns={'CD_MUNICIPIO': 'mun', 'NR_ZONA': 'zona', 'NR_SECAO': 'secao', 'SG_UF': 'uf'})
for tn in [1, 2]:
    secs = []
    for f in glob.glob(f'{D}/{tn}t_*_votos.parquet'):
        uf = re.search(r't_(\w\w)_', f).group(1)
        if uf == 'ZZ': continue
        v = pd.read_parquet(f, columns=['mun', 'zona', 'secao', 'tipo'])
        g = v.groupby(['mun', 'zona', 'secao']).tipo.agg(n='size', nman=lambda x: (x == 1).sum(), nsem=lambda x: (x == 2).sum()).reset_index(); g['uf'] = uf; secs.append(g)
    s = pd.concat(secs); p = pr[pr.NR_TURNO == tn]
    for nr in [13, 22]: s = s.merge(p[p.NR_VOTAVEL == nr].groupby(K).QT_VOTOS.sum().rename(f'c{nr}').reset_index(), on=K, how='left')
    s = s.fillna(0); s = s[s.n >= 50]
    s['pman'] = s.nman / s.n; s['psem'] = s.nsem / s.n; w = s.n.values
    MAN = s.nman.sum() / s.n.sum(); SEM = s.nsem.sum() / s.n.sum()
    res = {}
    for nr, nm in [(13, 'Lula'), (22, 'Flavio')]:
        s['y'] = s[f'c{nr}'] / s.n
        gk = [s.uf, s.mun]; dm = pd.DataFrame(index=s.index)
        for c in ['y', 'pman', 'psem']:
            dm[c] = s[c] - (s[c] * s.n).groupby(gk).transform('sum') / s.n.groupby(gk).transform('sum')
        X = dm[['pman', 'psem']].values * np.sqrt(w)[:, None]; Y = dm.y.values * np.sqrt(w)
        (dman, dsem), *_ = np.linalg.lstsq(X, Y, rcond=None)
        tot = s[f'c{nr}'].sum() / s.n.sum(); pbio = tot - dman * MAN - dsem * SEM
        res[nm] = dict(total=tot, bio=pbio, manual=pbio + dman, sem=pbio + dsem)
    r = pd.DataFrame(res)
    r.loc['manual_valido'] = None
    print(f'\n===== {tn}º turno ({len(s):,} secoes; manual {100*MAN:.2f}%, sem cadastro {100*SEM:.2f}%) — % dos votos (comparecimento)')
    print((100 * r.drop('manual_valido')).round(1).to_string())
    for k in ['total', 'bio', 'manual', 'sem']:
        print(f'   {k:7s} Lula entre os votos dos dois: {100*r.loc[k,"Lula"]/(r.loc[k,"Lula"]+r.loc[k,"Flavio"]):.1f}%')
