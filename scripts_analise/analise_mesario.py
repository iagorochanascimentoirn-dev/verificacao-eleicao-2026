# Analise: quem liberou os votos manuais (mesario cadastrado x digital nao cadastrada) e eventos "eleitor ja votou"
# uso: python analise_mesario.py <pasta mesario> <presidente_secao.parquet> <turno 1|2>
import pandas as pd, numpy as np, glob, re, sys
from scipy import stats
M, PRES, tn = sys.argv[1], sys.argv[2], int(sys.argv[3]); T = f'{tn}t'; K = ['uf', 'mun', 'zona', 'secao']
out = open(f'{M}/resumo_mesario_{T}.txt', 'w')
def P(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); out.write(s + '\n')
S = pd.concat([pd.read_parquet(f).assign(uf=re.search(rf'{T}_(\w\w)_', f).group(1)) for f in sorted(glob.glob(f'{M}/{T}_*_mes_secoes.parquet'))])
J = pd.concat([pd.read_parquet(f).assign(uf=re.search(rf'{T}_(\w\w)_', f).group(1)) for f in sorted(glob.glob(f'{M}/{T}_*_jav.parquet'))])
S = S[S.uf != 'ZZ']; J = J[J.uf != 'ZZ']
import os
LC = pd.read_parquet(os.path.join(os.path.dirname(PRES), 'locais_secao.parquet')); LC = LC[LC.NR_TURNO == tn]
LC['indig'] = (LC.NM_LOCAL_VOTACAO.fillna('') + ' ' + LC.DS_LOCAL_VOTACAO_ENDERECO.fillna('')).str.contains('IND[IÍ]GENA|MALOCA|ALDEIA', regex=True)
LC = LC.rename(columns={'SG_UF': 'uf', 'CD_MUNICIPIO': 'mun', 'NR_ZONA': 'zona', 'NR_SECAO': 'secao'})[K + ['indig', 'NM_MUNICIPIO', 'NM_LOCAL_VOTACAO']].drop_duplicates(K)
S = S.merge(LC, on=K, how='left'); S['indig'] = S.indig.fillna(False).astype(bool)
S['nao_cad'] = S.man_digital_nova + S.man_nao_assoc
P(f'================ {tn}º TURNO — {len(S):,} secoes (sem exterior), {S.votos.sum():,} votos ================')
man = S.manual.sum()
P(f'\n1) Quem liberou os {man:,} votos manuais:')
for c, nm in [('man_mesario', 'mesario cadastrado (identificado)'), ('man_digital_nova', 'digital NAO cadastrada, 1a vez (gravada na hora)'),
              ('man_nao_assoc', 'digital NAO cadastrada, repetida (sem mesario associado)'), ('man_outro', 'outro')]:
    P(f'   {nm:58s} {S[c].sum():>11,} {100*S[c].sum()/man:6.2f}%')
P(f'   => manuais sem mesario cadastrado: {S.nao_cad.sum():,} = {100*S.nao_cad.sum()/man:.2f}% dos manuais = {100*S.nao_cad.sum()/S.votos.sum():.3f}% de todos os votos')
uf = S.groupby('uf')[['votos', 'manual', 'nao_cad', 'sem_cadastro', 'ja_votou', 'nao_encontrado']].sum()
uf['%manual_sem_mesario_cad'] = 100 * uf.nao_cad / uf.manual; uf['nao_cad_por_mil_votos'] = 1000 * uf.nao_cad / uf.votos
uf['ja_votou_por_10mil'] = 1e4 * uf.ja_votou / uf.votos
P('\n   por UF:'); P(uf.sort_values('%manual_sem_mesario_cad', ascending=False).round(2).to_string())
S['pct_nc'] = np.where(S.manual > 0, 100 * S.nao_cad / S.manual, 0)
P(f'\n   secoes com algum manual sem mesario cadastrado: {(S.nao_cad>0).sum():,} de {len(S):,}')
P(f'   secoes em que 100% dos manuais foram sem mesario cadastrado (com 10+ manuais): {((S.pct_nc==100)&(S.manual>=10)).sum():,}')
P(f'   maior sequencia seguida de manuais por digital nao cadastrada: {S.max_seq_digital_nao_cadastrada.max()} | secoes com 10+ seguidos: {(S.max_seq_digital_nao_cadastrada>=10).sum():,} | 20+: {(S.max_seq_digital_nao_cadastrada>=20).sum():,}')
S.sort_values('nao_cad', ascending=False).head(3000).to_csv(f'{M}/secoes_manual_sem_mesario_{T}.csv', index=False)
P('   top 10 secoes por manuais sem mesario cadastrado:'); P(S.sort_values('nao_cad', ascending=False).head(10)[K + ['votos', 'manual', 'nao_cad', 'max_seq_digital_nao_cadastrada', 'mesarios_liberaram']].to_string(index=False))

P(f'\n2) "O eleitor identificado ja votou": {len(J):,} eventos em {J.groupby(K).ngroups:,} secoes ({1e4*len(J)/S.votos.sum():.2f} por 10 mil votos)')
b = pd.cut(J.gap, [-2, -0.5, 30, 60, 180, 600, 3600, 1e6], labels=['sem voto antes', '<30s', '30-60s', '1-3min', '3-10min', '10-60min', '>1h'])
P('   tempo desde o ultimo voto computado na secao:'); P(b.value_counts().sort_index().to_frame('eventos').assign(pct=lambda x: (100 * x.eventos / x.eventos.sum()).round(1)).to_string())
P('   tipo do voto anterior (0 bio, 1 manual, 2 sem cadastro):', J.tipo_anterior.value_counts().sort_index().to_dict(),
  '| base geral:', {0: round(1 - (S.manual.sum() + S.sem_cadastro.sum()) / S.votos.sum(), 3), 1: round(S.manual.sum() / S.votos.sum(), 3), 2: round(S.sem_cadastro.sum() / S.votos.sum(), 3)})
P(f'   secoes com 5+ "ja votou": {(S.ja_votou>=5).sum():,} | 10+: {(S.ja_votou>=10).sum():,} | max {S.ja_votou.max()}')
for nm, q in [('indigenas', S[S.indig]), ('nao indigenas', S[~S.indig])]:
    P(f'   secoes {nm:14s}: {len(q):>7,} secoes | ja votou por 10 mil votos {1e4*q.ja_votou.sum()/q.votos.sum():6.2f} | manual sem mesario cad por mil {1000*q.nao_cad.sum()/q.votos.sum():5.2f} | sem cadastro {100*q.sem_cadastro.sum()/q.votos.sum():5.2f}%')
S.sort_values('ja_votou', ascending=False).head(3000).to_csv(f'{M}/secoes_ja_votou_{T}.csv', index=False)

P('\n3) Essas secoes votaram diferente? (Spearman dentro do mesmo municipio+zona; secoes com 50+ votos)')
pr = pd.read_parquet(PRES); pr = pr[pr.NR_TURNO == tn].rename(columns={'SG_UF': 'uf', 'CD_MUNICIPIO': 'mun', 'NR_ZONA': 'zona', 'NR_SECAO': 'secao'})
for nr in [13, 22]: S = S.merge(pr[pr.NR_VOTAVEL == nr].groupby(K).QT_VOTOS.sum().rename(f'c{nr}').reset_index(), on=K, how='left')
S = S[S.votos >= 50].copy(); S['lula'] = 100 * S.c13.fillna(0) / S.votos; S['flavio'] = 100 * S.c22.fillna(0) / S.votos
S['x_nc'] = 1000 * S.nao_cad / S.votos; S['x_jv'] = 1e4 * S.ja_votou / S.votos; S['x_sc'] = 100 * S.sem_cadastro / S.votos
S0 = S.copy()
for rot, S in [('TODAS', S0), ('SEM INDIGENAS', S0[~S0.indig].copy())]:
  P(f'  -- {rot} ({len(S):,} secoes) --')
  g = [S.uf, S.mun, S.zona]
  for c in ['lula', 'flavio', 'x_nc', 'x_jv', 'x_sc']: S[c + '_d'] = S[c] - S.groupby(g)[c].transform('mean')
  for x, nm in [('x_nc', 'manuais sem mesario cadastrado'), ('x_jv', '"ja votou"'), ('x_sc', 'sem biometria cadastrada')]:
      P(f'   {nm:32s} x Lula rho={stats.spearmanr(S[x+"_d"], S.lula_d)[0]:+.4f} | x Flavio rho={stats.spearmanr(S[x+"_d"], S.flavio_d)[0]:+.4f}')
  hi = S[(S.nao_cad >= 20)]
  P(f'   secoes com 20+ manuais sem mesario cadastrado ({len(hi):,}): Lula vs media da zona {hi.lula_d.mean():+.2f} p.p. | Flavio {hi.flavio_d.mean():+.2f} p.p.')
  hj = S[(S.ja_votou >= 5)]
  P(f'   secoes com 5+ "ja votou" ({len(hj):,}): Lula vs media da zona {hj.lula_d.mean():+.2f} p.p. | Flavio {hj.flavio_d.mean():+.2f} p.p.')
uf.round(3).to_csv(f'{M}/mesario_por_uf_{T}.csv'); out.close()
