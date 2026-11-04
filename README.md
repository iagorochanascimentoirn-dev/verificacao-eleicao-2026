# Verificação independente da eleição presidencial de 2026

Estudo independente que verifica, com os **dados públicos do Tribunal Superior Eleitoral**, se a eleição presidencial brasileira de 2026 (1º e 2º turno) apresenta sinais de fraude. Foram verificados os arquivos de todas as urnas do país, cerca de 499 mil seções por turno.

> Estudo sem vínculo com o TSE, partidos ou candidaturas. Todos os números podem ser reproduzidos com o código deste repositório.

📄 **Estudo completo (PDF):** [`estudo_eleicao_presidencial_2026.pdf`](estudo_eleicao_presidencial_2026.pdf)
🔗 **DOI (Zenodo):** em breve

---

## Resultado em uma frase

Os arquivos das urnas conferem entre si e com o resultado oficial, voto por voto, em todas as seções em que foram publicados, e não há sinal de fraude capaz de mudar o resultado. Foram identificados 13 achados, nenhum deles indicando voto alterado.

> **O mais grave é uma brecha de processo, a liberação manual do voto pelo mesário com digital fora do cadastro, que atingiu de 2,8 a 3,2 milhões de votos e não pode ser auditada com os dados públicos. Há ainda um limite de fundo: o software da urna, que nenhum dado publicado consegue testar.**

## O que foi verificado

| Verificação | Resultado |
|---|---|
| Consistência entre votos, comparecimento e eleitorado apto | 100% das seções consistentes |
| Testes forenses (Klimek, último dígito, Benford no 2º dígito) | Compatíveis com ausência de manipulação |
| Log da urna × resultado oficial (253 milhões de votos reconstruídos) | Iguais em 99,99% das seções |
| Hash SHA-512 do BU, do RDV e da imagem do BU × arquivo de assinatura | Conferem em 100% das seções com arquivo |
| RDV × BU, voto a voto, todos os cargos | Iguais em 100% |
| BU × resultado oficial, por seção e no total nacional | Iguais em 100% |
| Liberação manual e voto sem biometria | Vulnerabilidade real; sem sinal de uso em escala |
| Integridade do software da urna | Não verificável com dados públicos |

### Soma nacional dos Boletins de Urna × resultado oficial

| | Lula | Flávio | Brancos | Nulos | Total |
|---|---:|---:|---:|---:|---:|
| 1º turno, BUs | 53.878.914 | 56.103.951 | 2.300.777 | 3.668.963 | 125.274.487 |
| 1º turno, oficial | 53.879.538 | 56.104.503 | 2.300.798 | 3.669.003 | 125.275.835 |
| 2º turno, BUs | 64.255.787 | 59.825.688 | 1.430.484 | 2.723.284 | 128.235.243 |
| 2º turno, oficial | 64.256.232 | 59.826.041 | 1.430.496 | 2.723.305 | 128.236.074 |

A diferença, de 1.348 votos no 1º turno e 831 no 2º, corresponde exatamente às seções que só têm o RDV publicado, sem BU. Nessas seções, o total do RDV é igual ao oficial.

## Os 13 achados

| Nº | Achado | Nível |
|---|---|---|
| 1 | A habilitação manual prossegue quando a digital de autorização não pertence a mesário cadastrado (3,2 mi de votos no 1º turno; 2,8 mi no 2º) | Alto |
| 2 | Seções em que todos os votos manuais foram autorizados por digital fora do cadastro (52.856 no 1º turno; 32.361 no 2º) | Alto |
| 3 | Eleitor sem biometria cadastrada é habilitado sem leitura de digital; a proporção aumenta no fim do dia | Alto |
| 4 | Seções sem BU e sem log publicados, apenas com RDV (30 no 1º turno; 27 no 2º) | Médio |
| 5 | Log incompleto por travamento ou reinício da urna (15 seções; BU correto) | Baixo |
| 6 | Urna de recuperação com log de outra seção (Vila Velha/ES) | Baixo |
| 7 | Seções com RDV que não constam do resultado oficial (2, no exterior) | Baixo |
| 8 | Substituição de arquivos publicados sem aviso em 03/11/2026 (1º turno MA e MG; 2º turno SP) | Médio |
| 9 | Assinatura digital não verificável pelo público | Médio |
| 10 | A especificação publicada dos arquivos não corresponde ao formato de 2026 | Médio |
| 11 | Encadeamento dos registros do BU e do RDV não reproduzível | Baixo |
| 12 | Aviso "o eleitor identificado já votou" frequente, por redigitação do documento | Baixo |
| 13 | O log não identifica o eleitor, e o caderno de votação não é público | Alto |

O detalhamento, as limitações e as recomendações estão no PDF.

## Fontes de dados

Todas públicas e oficiais, do TSE:

- **Votação por seção 2026**: Portal de Dados Abertos (`dadosabertos.tse.jus.br`), arquivo `votacao_secao_2026_BR.zip`.
- **Arquivos de urna**: `https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes2026/arqurnatot/bu_imgbu_logjez_rdv_vscmr_2026_{1t|2t}_{UF}.zip`, um por UF e turno (~219 GB no total). Contêm log, BU, RDV, imagem do BU e arquivo de assinatura de cada seção.

Os scripts leem os zips **direto do servidor do TSE** por requisições HTTP *Range*, sem baixar os arquivos inteiros.

## Como reproduzir

### Requisitos

- Python 3.12 ou superior
- `7z` (p7zip) no PATH, para descompactar os logs (`.jez`)
- Conexão estável: a leitura completa transfere dezenas de GB

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Etapas

`OUT` é a pasta de resultados (ex.: `dados_logs`) e `TMP` uma pasta temporária.

| Etapa | Comando | Seção do estudo |
|---|---|---|
| 1. Resultado oficial por seção | `python scripts_analise/prep.py <pasta>` (espera `<pasta>/dl_tse/votacao_secao_2026_BR.zip`) | 4.1 |
| 2. Testes forenses | `python scripts_analise/an1.py <pasta>`, `an2.py`, `an3.py` | 4.1 |
| 3. Logs voto a voto, Brasil inteiro | `python scripts_analise/logs_brasil.py OUT TMP ALL 1t,2t 12` | 4.2 |
| 4. Validação e horário | `python scripts_analise/logs_analise_brasil.py OUT 1` (e `2`); `horario_manuais.py OUT` | 4.2, 4.3 |
| 5. Locais de votação | `python scripts_analise/locais_secao.py votacao_secao_2026_BR.zip OUT/locais_secao.parquet` | 4.4 |
| 6. Quem liberou os votos manuais | `python scripts_analise/logs_mesario.py OUT/mesario TMP ALL 1t,2t 12`; `mesario_refaz_erros.py OUT/mesario TMP` | 4.4 |
| 7. Análise do mesário | `python scripts_analise/analise_mesario.py OUT/mesario OUT/presidente_secao.parquet 1` (e `2`) | 4.4 |
| 8. Direção dos votos manuais | `manuais_voto_estimado.py`, `manuais_variacao_voto.py`, `manuais_variacao_uf.py` | 4.5 |
| 9. Verificação dos arquivos de urna | `python scripts_analise/verifica_bu.py OUT/bu ALL 1t,2t 12` | 4.6, 4.7 |
| 10. Resumo da verificação | `python scripts_analise/analise_bu.py OUT/bu OUT/presidente_secao.parquet` | 4.6 |
| 11. PDF | `python gerar_estudo_publicacao.py` | — |

Observações:

- Os scripts `manuais_*.py` têm o caminho da pasta de dados fixo na variável `D`, na linha 4 ou 5. Ajuste para a sua pasta. Os arquivos foram mantidos idênticos aos usados no estudo para que os hashes do manifesto continuem conferindo.
- `presidente_secao.parquet` (votos para Presidente por seção) e todos os resultados intermediários estão no `resultados.zip` do Zenodo, para quem quiser pular as etapas de extração.
- `log_secao.py <1t|2t> <UF> <mun> <zona> <secao> <saida.txt>` baixa o log de uma seção específica para conferência manual.
- `verifica_bu.py` grava, para cada zip, a versão publicada (`Last-Modified`) e um índice dos arquivos (`*_indice.tsv`), o que permite detectar republicações futuras.

## Integridade

O PDF e os arquivos do estudo são protegidos por resumos criptográficos.

**SHA3-512 do PDF:**
```
3999801e2be95431fd762d70c8cb9398d38040fcef1d1f5940e8602323805f95ec251a4c2d3338b39041f73fa9fb44588968ed70bcf0624107b68c48263e05d1
```

- [`estudo_eleicao_presidencial_2026.pdf.hashes.txt`](estudo_eleicao_presidencial_2026.pdf.hashes.txt): SHA3-512, SHA-512, BLAKE2b-512 e SHA-256 do PDF.
- [`MANIFESTO_SHA3-512.txt`](MANIFESTO_SHA3-512.txt): SHA3-512 de 404 arquivos (scripts, figuras e resultados). O Apêndice C do PDF traz o hash de cada script e o do manifesto.

Conferir:

```bash
openssl dgst -sha3-512 estudo_eleicao_presidencial_2026.pdf

# todos os arquivos presentes, contra o manifesto
grep -v '^#' MANIFESTO_SHA3-512.txt | while read h f; do
  [ -f "$f" ] && [ "$(openssl dgst -sha3-512 -r "$f" | cut -d' ' -f1)" != "$h" ] && echo "DIFERENTE: $f"
done; echo fim
```

## Como citar

> NASCIMENTO, Iago Rocha. *Verificação independente da eleição presidencial de 2026: o processo eleitoral do início ao fim e a conferência dos dados públicos de todas as urnas do Brasil*. 2026. DOI: 10.5281/zenodo.XXXXXXX.

Ver também [`CITATION.cff`](CITATION.cff).

## Licença

- Código: MIT
- Texto do estudo, figuras e resultados: CC BY 4.0
- Dados de origem: Tribunal Superior Eleitoral, dados públicos

Detalhes em [`LICENSE`](LICENSE).
