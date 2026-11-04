# Resume a verificacao pos-urna (verifica_bu.py): hashes, RDV x BU, imagem x BU, e BU x resultado oficial (votacao_secao)
# uso: python analise_bu.py <pasta bu> <presidente_secao.parquet>
import pandas as pd, glob, re, sys, json
B, PRES = sys.argv[1], sys.argv[2]; K = ['uf', 'mun', 'zona', 'secao']
out = open(f'{B}/resumo_bu.txt', 'w')
def P(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); out.write(s + '\n')
pr = pd.read_parquet(PRES).rename(columns={'SG_UF': 'uf', 'CD_MUNICIPIO': 'mun', 'NR_ZONA': 'zona', 'NR_SECAO': 'secao'})
for tn in [1, 2]:
    T = f'{tn}t'; fs = sorted(glob.glob(f'{B}/{T}_*_bu.parquet'))
    if not fs: continue
    S = pd.concat([pd.read_parquet(f).assign(uf=re.search(rf'{T}_(\w\w)_', f).group(1)) for f in fs])
    P(f'\n================ {tn}º TURNO — {len(fs)} arquivos (UF), {len(S):,} secoes com arquivos ================')
    for c, nm in [('hash_bu', 'hash do BU confere com a assinatura'), ('hash_rdv', 'hash do RDV confere'), ('hash_imgbu', 'hash da imagem do BU confere'),
                  ('vsc_auto_ok', 'hash do proprio arquivo de assinatura confere'), ('rdv_igual_bu', 'RDV (voto a voto) = BU, todos os cargos'),
                  ('img_igual_bu', 'imagem impressa = BU (Presidente)')]:
        v = S[c].value_counts().to_dict()
        P(f'   {nm:48s} sim {v.get(1, 0):>8,} | nao {v.get(0, 0):>5,} | sem arquivo/nao lido {v.get(-1, 0):>5,}')
    for c in ['rdv_igual_bu', 'img_igual_bu', 'hash_bu', 'hash_rdv', 'hash_imgbu']:
        bad = S[S[c] == 0]
        if len(bad): bad.to_csv(f'{B}/falhas_{c}_{T}.csv', index=False); P(f'   -> {len(bad)} secoes com {c}=0 em falhas_{c}_{T}.csv')
    p = pr[pr.NR_TURNO == tn]
    of = p.pivot_table(index=K, columns='NR_VOTAVEL', values='QT_VOTOS', aggfunc='sum', fill_value=0)
    of['of_lula'] = of.get(13, 0); of['of_flavio'] = of.get(22, 0); of['of_branco'] = of.get(95, 0); of['of_nulo'] = of.get(96, 0)
    of['of_total'] = of[[c for c in of.columns if isinstance(c, (int,)) or str(c).isdigit()]].sum(axis=1)
    of = of[['of_lula', 'of_flavio', 'of_branco', 'of_nulo', 'of_total']].reset_index()
    M = S.merge(of, on=K, how='outer', indicator=True)
    P(f'\n   secoes: com BU e no oficial {(M._merge=="both").sum():,} | so BU {(M._merge=="left_only").sum():,} | so oficial {(M._merge=="right_only").sum():,}')
    b = M[M._merge == 'both'].copy()
    for a, o in [('bu_lula', 'of_lula'), ('bu_flavio', 'of_flavio'), ('bu_branco', 'of_branco'), ('bu_nulo', 'of_nulo'), ('bu_total', 'of_total')]:
        d = (b[a] != b[o]).sum(); P(f'   {a:10s} BU {b[a].sum():>12,} | oficial {b[o].sum():>12,} | secoes diferentes {d:,}')
    dif = b[(b.bu_total != b.of_total) | (b.bu_lula != b.of_lula) | (b.bu_flavio != b.of_flavio)]
    if len(dif): dif.to_csv(f'{B}/bu_x_oficial_{T}.csv', index=False)
    so_of = M[M._merge == 'right_only']; so_of.to_csv(f'{B}/so_oficial_{T}.csv', index=False)
    P(f'   secoes so no oficial (sem BU publicado) por UF: {so_of.uf.value_counts().to_dict()} | votos {so_of.of_total.sum():,}')
    P(f'\n   SOMA NACIONAL (BU publicados): Lula {S.bu_lula.sum():,} | Flavio {S.bu_flavio.sum():,} | brancos {S.bu_branco.sum():,} | nulos {S.bu_nulo.sum():,} | outros {S.bu_outros.sum():,} | total {S.bu_total.sum():,}')
    P(f'   SOMA NACIONAL (oficial por secao): Lula {of.of_lula.sum():,} | Flavio {of.of_flavio.sum():,} | brancos {of.of_branco.sum():,} | nulos {of.of_nulo.sum():,} | total {of.of_total.sum():,}')
out.close()
