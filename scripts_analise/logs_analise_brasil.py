# Analise nacional dos logs de urna 2026: horario e tipo de habilitacao x resultado oficial
# Processa UF por UF (memoria) e agrega. uso: python logs_analise_brasil.py <pasta dados_logs> <turno 1|2>
import pandas as pd, numpy as np, sys, glob, re, collections
from scipy import stats
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
D, tn = sys.argv[1], int(sys.argv[2]); T = f'{tn}t'
K = ['uf', 'mun', 'zona', 'secao']
NOMES = {0: 'biometrica', 1: 'manual_apos_falha', 2: 'sem_biometria', 3: 'outro'}
out = open(f'{D}/resumo_{T}.txt', 'w')
def P(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); out.write(s + '\n')
def hmed(h):  # mediana a partir de histograma em segundos
    c = np.cumsum(h); return int(np.searchsorted(c, c[-1] / 2)) if c[-1] else np.nan

tipos = collections.Counter(); hh = np.zeros((2, 30), np.int64); late = np.zeros((2, 2), np.int64)
H = 3600; dur_b, dur_nb, gap_all, gap_seq = (np.zeros(H + 1, np.int64) for _ in range(4))
secs, rts, runs_top, sts, uf_rows = [], [], [], [], []
files = sorted(glob.glob(f'{D}/{T}_*_votos.parquet'))
for f in files:
    uf = re.search(rf'{T}_(\w\w)_votos', f).group(1)
    v = pd.read_parquet(f); s = pd.read_parquet(f.replace('_votos', '_secoes')); s['uf'] = uf; sts.append(s)
    v['nb'] = (v.tipo != 0).astype(np.int32)
    tipos.update(v.tipo.map(NOMES).value_counts().to_dict())
    np.add.at(hh, (v.nb.values, np.clip(v.t_voto.values // 3600, 0, 29)), 1)
    v = v.sort_values(['mun', 'zona', 'secao', 't_voto'], kind='stable').reset_index(drop=True)
    g = v.groupby(['mun', 'zona', 'secao'], sort=False)
    v['ordem'] = g.cumcount(); v['n'] = g.nb.transform('size')
    lt = (v.ordem >= 0.9 * v.n).values.astype(int); np.add.at(late, (lt, v.nb.values), 1)
    d = np.where(v.t_hab >= 0, v.t_voto - v.t_hab, -1); ok = (d >= 0)
    dur_b += np.bincount(np.clip(d[ok & (v.nb.values == 0)], 0, H), minlength=H + 1)
    dur_nb += np.bincount(np.clip(d[ok & (v.nb.values == 1)], 0, H), minlength=H + 1)
    gap = g.t_voto.diff().values; pnb = g.nb.shift().values
    okg = ~np.isnan(gap); gap_all += np.bincount(np.clip(gap[okg], 0, H).astype(int), minlength=H + 1)
    sq = okg & (v.nb.values == 1) & (pnb == 1); gap_seq += np.bincount(np.clip(gap[sq], 0, H).astype(int), minlength=H + 1)
    # sequencias de sem-biometria
    brk = (v.nb != v.nb.shift()) | (v.ordem == 0); v['gid'] = brk.cumsum()
    r = v[v.nb == 1].groupby('gid').agg(mun=('mun', 'first'), zona=('zona', 'first'), secao=('secao', 'first'),
                                        n=('nb', 'size'), ini=('t_voto', 'first'), fim=('t_voto', 'last'))
    r['uf'] = uf; runs_top.append(r[r.n >= 10]); maxrun = r.n.max()
    # runs test por secao
    v['ch'] = (v.nb.values != pnb) & (v.ordem.values > 0)
    rr = v.groupby(['mun', 'zona', 'secao']).agg(N=('nb', 'size'), n1=('nb', 'sum'), ch=('ch', 'sum')).reset_index(); rr['uf'] = uf
    rts.append(rr)
    sec = rr[['uf', 'mun', 'zona', 'secao', 'N', 'n1']].rename(columns={'N': 'votos', 'n1': 'sem_bio'}); secs.append(sec)
    uf_rows.append(dict(uf=uf, secoes=len(s), votos=len(v), sem_bio=int(v.nb.sum()), manual=int((v.tipo == 1).sum()),
                        sem_biometria=int((v.tipo == 2).sum()), contingencia=int(s.contingencia.fillna(0).sum()), maior_seq=int(maxrun or 0)))
    print(uf, len(v), flush=True); del v, g

s = pd.concat(sts); sec = pd.concat(secs, ignore_index=True); rr = pd.concat(rts, ignore_index=True)
uf_tab = pd.DataFrame(uf_rows).set_index('uf'); uf_tab['pct_sem_bio'] = 100 * uf_tab.sem_bio / uf_tab.votos
NV = int(uf_tab.votos.sum())
P(f'================ {tn}º TURNO — {len(files)} UFs, {len(s):,} secoes, {NV:,} votos ================')
errs = sum(sum(1 for _ in open(e)) for e in glob.glob(f'{D}/{T}_*_erros.txt'))
P('linhas em arquivos de erro:', errs, '| secoes sem voto no log:', int((s.votos == 0).sum()))
P('\nA) tipo de habilitacao (Brasil):')
for k, n in tipos.most_common(): P(f'   {k:20s} {n:>12,} {100*n/NV:6.2f}%')

pr = pd.read_parquet(f'{D}/presidente_secao.parquet'); pr = pr[pr.NR_TURNO == tn]
pr = pr.rename(columns={'SG_UF': 'uf', 'CD_MUNICIPIO': 'mun', 'NR_ZONA': 'zona', 'NR_SECAO': 'secao'})
bu = pr.groupby(K).QT_VOTOS.sum().rename('bu').reset_index()
m = sec.merge(bu, on=K, how='outer', indicator=True); m = m[m.uf.isin(sec.uf.unique())]
P(f'\nF) log x resultado oficial (Presidente): {m._merge.value_counts().to_dict()}')
dif = m[(m._merge == 'both') & (m.votos != m.bu)].merge(s[K + ['contingencia', 'n_urnas']], on=K, how='left')
P(f'   secoes com diferenca: {len(dif):,} | soma log {int(m.votos.sum()):,} x oficial {int(m.bu.sum()):,} | diferenca liquida {int((m.bu.fillna(0)-m.votos.fillna(0)).sum()):,}')
if len(dif): dif.to_csv(f'{D}/divergencias_{T}.csv', index=False); P('   contingencia entre as divergentes:', dif.contingencia.value_counts().to_dict())
only = m[m._merge != 'both']
if len(only): only.to_csv(f'{D}/so_num_lado_{T}.csv', index=False)

P('\nB) por hora local (votos / % sem biometria):')
for h in range(30):
    t = hh[:, h].sum()
    if t: P(f'   {h:02d}h {t:>12,} {100*hh[1,h]/t:6.2f}%')
P(f'\nE) % sem biometria — primeiros 90% dos votos de cada secao: {100*late[0,1]/late[0].sum():.2f}% | ultimos 10%: {100*late[1,1]/late[1].sum():.2f}%')
P(f'\nVoto rapido: duracao habilitacao->voto mediana bio {hmed(dur_b)}s | sem bio {hmed(dur_nb)}s; <10s: bio {100*dur_b[:10].sum()/dur_b.sum():.2f}% sem bio {100*dur_nb[:10].sum()/dur_nb.sum():.2f}%')
P(f'   pares sem-bio seguidos: {gap_seq.sum():,}; intervalo mediano {hmed(gap_seq)}s (geral {hmed(gap_all)}s); <30s: {100*gap_seq[:30].sum()/gap_seq.sum():.2f}% x geral {100*gap_all[:30].sum()/gap_all.sum():.2f}%')

rt = pd.concat(runs_top); rt['min_por_voto'] = (rt.fim - rt.ini) / 60 / (rt.n - 1)
P(f'\nSequencias de 10+ sem biometria seguidos: {len(rt):,} | 20+: {(rt.n>=20).sum():,} | 50+: {(rt.n>=50).sum():,} | maior: {rt.n.max() if len(rt) else 0}')
rt.sort_values('n', ascending=False).to_csv(f'{D}/sequencias_{T}.csv', index=False)
if len(rt): P(rt.sort_values('n', ascending=False).head(15).assign(ini=lambda x: pd.to_datetime(x.ini, unit='s').dt.strftime('%H:%M'),
                                                                fim=lambda x: pd.to_datetime(x.fim, unit='s').dt.strftime('%H:%M')).round(1).to_string(index=False))

rr['n0'] = rr.N - rr.n1; rr = rr[(rr.n1 >= 3) & (rr.n0 >= 3)].copy(); rr['runs'] = rr.ch + 1
mu = 1 + 2 * rr.n1 * rr.n0 / rr.N; var = 2 * rr.n1 * rr.n0 * (2 * rr.n1 * rr.n0 - rr.N) / (rr.N ** 2 * (rr.N - 1))
rr['z'] = (rr.runs - mu) / np.sqrt(var); rr['p'] = stats.norm.cdf(rr.z)
mm = len(rr); o = np.argsort(rr.p.values); q = np.empty(mm); q[o] = np.minimum.accumulate((rr.p.values[o] * mm / np.arange(1, mm + 1))[::-1])[::-1]; rr['q'] = np.minimum(q, 1)
P(f'\nD) runs test em {mm:,} secoes: z medio {rr.z.mean():.3f} (sd {rr.z.std():.3f}); p<0.01: {(rr.p<.01).sum():,} (esperado ~{mm*.01:,.0f}); FDR 5%: {(rr.q<.05).sum():,}')
rr.sort_values('z').head(2000).to_csv(f'{D}/agrupamento_{T}.csv', index=False)
uf_tab['runs_fdr'] = rr[rr.q < .05].groupby('uf').size(); uf_tab['runs_fdr'] = uf_tab.runs_fdr.fillna(0).astype(int)

sec['pct'] = 100 * sec.sem_bio / sec.votos
P(f'\nC) % sem biometria por secao: mediana {sec.pct.median():.2f} | p90 {sec.pct.quantile(.9):.2f} | p99 {sec.pct.quantile(.99):.2f} | max {sec.pct.max():.1f}; secoes >30%: {(sec.pct>30).sum():,} | >50%: {(sec.pct>50).sum():,}')
sec.sort_values('pct', ascending=False).head(2000).to_csv(f'{D}/secoes_mais_sem_bio_{T}.csv', index=False)

top = pr[pr.NR_VOTAVEL < 90].groupby(['NR_VOTAVEL', 'NM_VOTAVEL']).QT_VOTOS.sum().sort_values(ascending=False).head(2)
P('\nCorrelacao % sem biometria x % do candidato (Spearman; secoes com 50+ votos)')
for (nr, nm), _ in top.items():
    c = pr[pr.NR_VOTAVEL == nr].groupby(K).QT_VOTOS.sum().rename('c').reset_index().merge(sec, on=K)
    c = c[c.votos >= 50].copy(); c['share'] = 100 * c.c / c.votos
    rho, _ = stats.spearmanr(c.pct, c.share)
    dm = c.assign(x=c.pct - c.groupby(['uf', 'mun']).pct.transform('mean'), y=c.share - c.groupby(['uf', 'mun']).share.transform('mean'))
    rho2, _ = stats.spearmanr(dm.x, dm.y)
    P(f'   {nm[:28]:28s} Brasil bruta rho={rho:+.3f} | dentro do municipio rho={rho2:+.3f}')
    uf_tab[f'rho_{nr}_mun'] = dm.groupby('uf').apply(lambda d: stats.spearmanr(d.x, d.y)[0] if len(d) > 30 else np.nan)
uf_tab.round(3).to_csv(f'{D}/por_uf_{T}.csv')
P('\nPor UF:'); P(uf_tab.round(3).to_string())

fig, ax = plt.subplots(1, 2, figsize=(14, 5))
hs = [h for h in range(30) if hh[:, h].sum()]; tot = hh[:, hs].sum(0)
ax[0].bar(hs, tot / 1e6, color='#9bb'); a2 = ax[0].twinx(); a2.plot(hs, 100 * hh[1, hs] / tot, 'o-', color='#c33')
ax[0].set_title(f'{tn}º turno Brasil: votos/hora (mi, barra) e % sem biometria (linha)'); ax[0].set_xlabel('hora local')
ax[1].hist(rr.z.clip(-8, 8), bins=80, density=True, color='#9bb'); xs = np.linspace(-6, 6, 200); ax[1].plot(xs, stats.norm.pdf(xs), 'r')
ax[1].set_title(f'{tn}º turno: z do runs test por seção (vermelho = acaso)')
plt.tight_layout(); plt.savefig(f'{D}/brasil_{T}.png', dpi=110); out.close()
