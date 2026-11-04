# Distribuicao horaria (hora local da urna) dos votos manuais/sem biometria x biometricos, por turno (sem exterior)
import pandas as pd, numpy as np, glob, re, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
D = sys.argv[1]; B = 900  # blocos de 15 min
res = {}
for t in ['1t', '2t']:
    acc = np.zeros((3, 96), np.int64)
    for f in glob.glob(f'{D}/{t}_*_votos.parquet'):
        if '_ZZ_' in f: continue
        v = pd.read_parquet(f, columns=['t_voto', 'tipo']); v = v[v.tipo < 3]
        np.add.at(acc, (v.tipo.values, np.clip(v.t_voto.values // B, 0, 95)), 1)
    res[t] = acc
    h = acc.reshape(3, 24, 4).sum(2); tot = h.sum(0)
    df = pd.DataFrame({'hora': [f'{i:02d}h' for i in range(24)], 'manual': h[1], 'sem_cadastro': h[2], 'total': tot})
    df = df[df.total > 1000]
    df['%manual_na_hora'] = 100 * df.manual / df.total; df['%sem_cad_na_hora'] = 100 * df.sem_cadastro / df.total
    df['%do_dia_manual'] = 100 * df.manual / h[1].sum(); df['%do_dia_biometrico'] = 100 * h[0][df.index] / h[0].sum()
    df.to_csv(f'{D}/horario_manuais_{t}.csv', index=False)
    print(f'===== {t}'); print(df.round(2).to_string(index=False))
C = {'bio': '#2a78d6', 'man': '#eb6834', 'sem': '#1baf7a'}; ink2 = '#52514e'
fig, ax = plt.subplots(2, 2, figsize=(14, 8), sharex=True)
x = np.arange(96) / 4
for j, t in enumerate(['1t', '2t']):
    a = res[t]; m = a.sum(0) > 2000
    for k, nm, c in [(0, 'biométrico', C['bio']), (1, 'manual (digital falhou)', C['man']), (2, 'sem biometria cadastrada', C['sem'])]:
        ax[0, j].plot(x[m], 100 * a[k][m] / a[k].sum(), color=c, lw=2, label=nm)
        if k: ax[1, j].plot(x[m], 100 * a[k][m] / a.sum(0)[m], color=c, lw=2, label=nm)
    ax[0, j].set_title(f'{j+1}º turno — quando cada tipo de voto aconteceu\n(% dos votos daquele tipo no dia, por bloco de 15 min)', fontsize=10, loc='left')
    ax[1, j].set_title(f'{j+1}º turno — participação no bloco de 15 min\n(% dos votos do bloco)', fontsize=10, loc='left')
    for a_ in ax[:, j]:
        a_.grid(axis='y', color='#e6e5e0', lw=0.8); a_.spines[['top', 'right']].set_visible(False)
        a_.tick_params(colors=ink2); a_.set_xlim(6.5, 18.5); a_.set_xticks(range(7, 19))
    ax[1, j].set_xlabel('hora local da urna', color=ink2); ax[1, j].set_ylim(0, 12)
ax[0, 0].legend(frameon=False, fontsize=9); ax[1, 0].legend(frameon=False, fontsize=9)
fig.suptitle('Votos manuais x biométricos por horário — Brasil 2026 (sem exterior)', fontsize=13, x=0.01, ha='left')
plt.tight_layout(); plt.savefig(f'{D}/horario_manuais.png', dpi=120, facecolor='#fcfcfb')
