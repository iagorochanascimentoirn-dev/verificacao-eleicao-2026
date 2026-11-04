"""Estudo para publicação: o processo eleitoral de 2026 do início ao fim e a verificação independente dos dados públicos."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.flowables import HRFlowable, CondPageBreak
from reportlab.platypus.tableofcontents import TableOfContents

AQUI = Path(__file__).parent
DL = AQUI / "dados_logs"
SAIDA = AQUI / "estudo_eleicao_presidencial_2026.pdf"
TITULO = "Verificação independente da eleição presidencial de 2026"

N = "/usr/share/fonts/truetype/noto/"
for nome, arq in [("Se", "NotoSerif-Regular"), ("Se-B", "NotoSerif-Bold"), ("Se-I", "NotoSerif-Italic"),
                  ("Se-BI", "NotoSerif-BoldItalic"), ("Sa", "NotoSans-Regular"), ("Sa-B", "NotoSans-Bold"),
                  ("Sa-I", "NotoSans-Italic"), ("Sa-BI", "NotoSans-BoldItalic")]:
    pdfmetrics.registerFont(TTFont(nome, N + arq + ".ttf"))
pdfmetrics.registerFontFamily("Se", normal="Se", bold="Se-B", italic="Se-I", boldItalic="Se-BI")
pdfmetrics.registerFontFamily("Sa", normal="Sa", bold="Sa-B", italic="Sa-I", boldItalic="Sa-BI")

TINTA = colors.HexColor("#1A1A1A")
CINZA_T = colors.HexColor("#5A5A5A")
REGUA = colors.HexColor("#8C8C8C")
FUNDO = colors.HexColor("#F3F3F1")
CAB = colors.HexColor("#E6E6E3")

corpo = ParagraphStyle("corpo", fontName="Se", fontSize=10.2, leading=15, alignment=TA_JUSTIFY, spaceAfter=7,
                       textColor=TINTA)
h1 = ParagraphStyle("h1", fontName="Sa-B", fontSize=14, leading=19, textColor=TINTA, spaceBefore=16, spaceAfter=8,
                    keepWithNext=1)
h2 = ParagraphStyle("h2", fontName="Sa-B", fontSize=11, leading=15, textColor=TINTA, spaceBefore=10, spaceAfter=5,
                    keepWithNext=1)
cel = ParagraphStyle("cel", fontName="Sa", fontSize=8.3, leading=11, textColor=TINTA, alignment=TA_LEFT)
celb = ParagraphStyle("celb", parent=cel, fontName="Sa-B")
legenda = ParagraphStyle("leg", fontName="Sa", fontSize=8.3, leading=11, textColor=CINZA_T, spaceBefore=3,
                         spaceAfter=12, alignment=TA_LEFT)
fonte_t = ParagraphStyle("fonte", parent=legenda, spaceBefore=2)
bullet = ParagraphStyle("bul", parent=corpo, leftIndent=16, bulletIndent=5, spaceAfter=4)
resumo = ParagraphStyle("resumo", parent=corpo, fontSize=10, leading=15)
destaque = ParagraphStyle("dest", parent=corpo, fontName="Se-B", fontSize=10.6, leading=16, backColor=FUNDO,
                          borderPadding=(10, 12, 10, 12), spaceBefore=14, spaceAfter=18)
ref = ParagraphStyle("ref", parent=corpo, fontSize=9, leading=13, leftIndent=16, firstLineIndent=-16, alignment=TA_LEFT)
nota = ParagraphStyle("nota", parent=corpo, fontName="Se-I", fontSize=9, leading=13, textColor=CINZA_T)

# ---------- numeração de tabelas e figuras ----------
CONT = {"tab": 0, "fig": 0}


def P(t, s=corpo):
    return Paragraph(t, s)


def bullets(itens):
    return [Paragraph(i, bullet, bulletText="•") for i in itens]


def tabela(titulo, cab, linhas, larguras, fonte=None, negrito_ultima=False, junto=True):
    CONT["tab"] += 1
    dados = [[P(c, celb) for c in cab]] + [[P(c, cel) for c in l] for l in linhas]
    k = 16.4 / sum(larguras)
    t = Table(dados, colWidths=[w * k * cm for w in larguras], repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), CAB),
          ("LINEABOVE", (0, 0), (-1, 0), 1.0, TINTA),
          ("LINEBELOW", (0, 0), (-1, 0), 0.6, TINTA),
          ("LINEBELOW", (0, -1), (-1, -1), 1.0, TINTA),
          ("LINEBELOW", (0, 1), (-1, -2), 0.25, REGUA),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if negrito_ultima:
        st.append(("BACKGROUND", (0, -1), (-1, -1), FUNDO))
    t.setStyle(TableStyle(st))
    partes = [P(f"<b>Tabela {CONT['tab']}.</b> {titulo}", ParagraphStyle("tt", parent=legenda, spaceBefore=6,
                                                                          spaceAfter=4, textColor=TINTA)), t]
    if fonte:
        partes.append(P(f"Fonte: {fonte}", fonte_t))
    else:
        partes.append(Spacer(1, 10))
    return KeepTogether(partes) if junto else partes


def figura(caminho, largura_cm, texto, fonte):
    CONT["fig"] += 1
    im = Image(str(caminho)); r = im.imageHeight / im.imageWidth
    im.drawWidth = largura_cm * cm; im.drawHeight = largura_cm * cm * r
    return KeepTogether([Spacer(1, 4), im, P(f"<b>Figura {CONT['fig']}.</b> {texto} Fonte: {fonte}", legenda)])


FONTE_TSE = "TSE, arquivos de urna (arqurnatot) 2026; elaboração própria."
FONTE_OF = "TSE, Dados Abertos, votação por seção 2026; elaboração própria."


# ---------- documento com sumário ----------
class Doc(BaseDocTemplate):
    def __init__(self, arq, **kw):
        super().__init__(arq, **kw)
        fr = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate("capa", [fr], onPage=lambda c, d: None),
                               PageTemplate("corpo", [fr], onPage=cabecalho)])

    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ("h1", "h2"):
            nivel = 0 if f.style.name == "h1" else 1
            texto = f.getPlainText()
            chave = f"s{id(f)}"
            self.canv.bookmarkPage(chave)
            self.canv.addOutlineEntry(texto, chave, level=nivel)
            self.notify("TOCEntry", (nivel, texto, self.page, chave))


def cabecalho(c, doc):
    c.saveState()
    c.setStrokeColor(REGUA); c.setLineWidth(0.4)
    y = A4[1] - 1.35 * cm
    c.line(doc.leftMargin, y, A4[0] - doc.rightMargin, y)
    c.setFont("Sa", 7.5); c.setFillColor(CINZA_T)
    c.drawString(doc.leftMargin, y + 4, TITULO)
    c.drawRightString(A4[0] - doc.rightMargin, y + 4, "Estudo independente · novembro de 2026")
    c.line(doc.leftMargin, 1.5 * cm, A4[0] - doc.rightMargin, 1.5 * cm)
    c.drawCentredString(A4[0] / 2, 1.0 * cm, str(doc.page))
    c.restoreState()


s = []

# ---------- capa ----------
capa_t = ParagraphStyle("ct", fontName="Sa-B", fontSize=24, leading=31, textColor=TINTA, alignment=TA_LEFT)
capa_s = ParagraphStyle("cs", fontName="Se", fontSize=13, leading=19, textColor=CINZA_T, alignment=TA_LEFT)
capa_m = ParagraphStyle("cm", fontName="Sa", fontSize=9.5, leading=14, textColor=TINTA, alignment=TA_LEFT)
s += [Spacer(1, 4.5 * cm),
      HRFlowable(width="100%", thickness=1.4, color=TINTA, spaceAfter=18),
      P("Verificação independente da eleição presidencial de 2026", capa_t), Spacer(1, 10),
      P("O processo eleitoral do início ao fim e a conferência dos dados públicos de todas as urnas do Brasil, "
        "1º e 2º turno", capa_s), Spacer(1, 18),
      HRFlowable(width="100%", thickness=0.5, color=REGUA, spaceAfter=14),
      P("<b>Autor:</b> Iago Rocha Nascimento", capa_m),
      P("<b>Data:</b> 4 de novembro de 2026", capa_m),
      P("<b>Natureza:</b> estudo independente, sem vínculo com o Tribunal Superior Eleitoral, partidos ou candidaturas", capa_m),
      P("<b>Base de dados:</b> arquivos públicos do TSE (resultado por seção, logs, Boletins de Urna, Registros "
        "Digitais do Voto e arquivos de assinatura de ~499 mil seções por turno)", capa_m),
      Spacer(1, 7.5 * cm),
      P("Todos os resultados podem ser reproduzidos com os scripts listados no Apêndice A, a partir dos arquivos "
        "publicados pelo TSE.", ParagraphStyle("cn", parent=capa_m, fontName="Sa-I", textColor=CINZA_T)),
      NextPageTemplate("corpo"), PageBreak()]

# ---------- resumo ----------
s += [P("Resumo", h1),
      P("Este estudo examina se a eleição presidencial de 2026 (Lula × Flávio Nantes Bolsonaro) apresenta sinais de "
        "fraude detectáveis nos dados que o Tribunal Superior Eleitoral torna públicos. Primeiro, descreve o processo "
        "eleitoral do cadastro do eleitor à totalização, identificando os controles de cada etapa. Em seguida, "
        "verifica os dados de todas as ~499 mil seções nos dois turnos. A verificação inclui testes forenses no "
        "resultado oficial, a reconstrução de 253 milhões de votos a partir dos logs das urnas, a análise da "
        "habilitação de eleitores sem biometria e a conferência criptográfica e aritmética dos Boletins de Urna "
        "(BU), dos Registros Digitais do Voto (RDV) e dos arquivos de assinatura.", resumo),
      P("Os arquivos das urnas conferem entre si e com o resultado oficial em todas as seções em que foram "
        "publicados. Os hashes SHA-512 conferem, o RDV reproduz o BU voto a voto em todos os cargos e a soma dos BUs "
        "e RDVs é igual ao total nacional divulgado. Os testes forenses não indicam manipulação das contagens. Foram "
        "identificados 13 achados, entre erros de publicação, falhas operacionais e vulnerabilidades de processo; "
        "nenhum deles indica voto alterado.", resumo),
      P("O mais grave é uma brecha de processo, a liberação manual do voto pelo mesário com digital fora do "
        "cadastro, que atingiu de 2,8 a 3,2 milhões de votos e não pode ser auditada com os dados públicos. Há ainda "
        "um limite de fundo: o software da urna, que nenhum dado publicado consegue testar.", destaque),
      P("<b>Palavras-chave:</b> urna eletrônica; auditoria eleitoral; Boletim de Urna; Registro Digital do Voto; "
        "biometria; forense eleitoral.", ParagraphStyle("pc", parent=resumo, alignment=TA_LEFT))]

s += [P("Principais resultados", h2),
      tabela("Síntese das verificações", ["Verificação", "Resultado"], [
          ["Consistência entre votos, comparecimento e eleitorado apto", "Consistente em 100% das seções"],
          ["Testes forenses (Klimek, último dígito, Benford no 2º dígito)", "Compatíveis com ausência de manipulação"],
          ["Log da urna × resultado oficial", "Iguais em 99,99% das seções; 15 logs incompletos, com BU correto"],
          ["Hash SHA-512 do BU, do RDV e da imagem do BU", "Conferem em 100% das seções com arquivo"],
          ["RDV × BU, voto a voto, todos os cargos", "Iguais em 100% das seções com ambos os arquivos"],
          ["BU × resultado oficial, por seção e no total nacional", "Iguais em 100%"],
          ["Liberação manual e voto sem biometria", "Vulnerabilidade real; sem sinal de uso em escala"],
          ["Integridade do software da urna", "Não verificável com dados públicos"],
      ], [9.0, 8.0], fonte="elaboração própria.")]

# ---------- sumário ----------
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle("t0", fontName="Sa-B", fontSize=10, leading=16, leftIndent=0),
                   ParagraphStyle("t1", fontName="Sa", fontSize=9, leading=13, leftIndent=14)]
toc.dotsMinLevel = 0
s += [PageBreak(), P("Sumário", ParagraphStyle("hs", parent=h1)), toc, PageBreak()]

# ---------- 1. introdução ----------
s += [P("1. Introdução", h1),
      P("A confiança no resultado de uma eleição depende de dois tipos de garantia: a de que cada etapa seguiu as "
        "regras e a de que é possível conferir, depois, que isso aconteceu. O Brasil vota em urnas eletrônicas desde "
        "1996 e publica, desde 2020, um volume crescente de arquivos produzidos pelas próprias urnas. Esses arquivos "
        "permitem uma verificação externa que não depende da palavra de nenhuma das partes."),
      P("Este estudo tem dois objetivos. O primeiro é descrever o processo eleitoral do início ao fim, apontando, em "
        "cada etapa, o controle existente e o que fica fora do alcance de quem está de fora (capítulo 2). O segundo "
        "é usar os dados públicos da eleição presidencial de 2026 para testar, na maior escala possível, se há sinais "
        "de fraude (capítulos 3 e 4). Os achados são consolidados no capítulo 5, e os limites do que se pode afirmar, "
        "no capítulo 6."),
      P("A pergunta é formulada de forma deliberadamente neutra: não se parte do pressuposto de que houve ou de que "
        "não houve fraude. Cada hipótese de fraude é traduzida no padrão que deixaria nos dados, e esse padrão é "
        "procurado.")]

# ---------- 2. processo eleitoral ----------
s += [P("2. O processo eleitoral do início ao fim", h1),
      P("Este capítulo descreve as etapas do processo, da formação do cadastro à divulgação dos arquivos de urna. A "
        "descrição segue a legislação (Código Eleitoral, Lei nº 9.504/1997) e as resoluções do TSE sobre fiscalização "
        "e auditoria do sistema eletrônico de votação. Os detalhes operacionais de cada eleição são fixados em "
        "resolução própria. Onde o comportamento descrito foi observado diretamente nos logs de 2026, isso é indicado.")]

s += [P("2.1 Cadastro eleitoral e biometria", h2),
      P("O eleitor se alista na Justiça Eleitoral e é vinculado a uma zona e a uma seção. A Justiça Eleitoral coleta "
        "as impressões digitais e a fotografia do eleitor para identificação biométrica. O cadastro é fechado 150 dias "
        "antes da eleição (Lei nº 9.504/1997, art. 91); a partir dele são gerados, para cada seção, a lista de "
        "eleitores carregada na urna e o caderno de votação impresso, no qual o eleitor assina."),
      P("<b>Controle:</b> revisões do eleitorado, cancelamento de inscrições de falecidos e duplicadas, batimento "
        "biométrico entre cadastros. <b>Observado em 2026:</b> cerca de 6% dos votos foram de eleitores sem "
        "biometria no cadastro, que se identificam apenas por documento.")]

s += [P("2.2 Desenvolvimento dos sistemas", h2),
      P("Os programas da urna e dos sistemas de apoio são desenvolvidos pelo próprio TSE. O código-fonte fica "
        "disponível para inspeção pelas entidades fiscalizadoras (partidos, Ministério Público, OAB, Polícia "
        "Federal, universidades, entre outras) a partir de um ano antes da eleição, em ambiente controlado no "
        "Tribunal. No ano anterior à eleição, o TSE realiza o Teste Público de Segurança (TPS), em que "
        "investigadores inscritos tentam violar o sistema, e as falhas encontradas são corrigidas e reavaliadas."),
      P("<b>Controle:</b> inspeção do código, TPS, testes internos. <b>Limite:</b> a inspeção é feita no "
        "Tribunal, por tempo limitado, e não há como o eleitor ou o fiscal confirmar, no dia, que a urna executa "
        "exatamente o código inspecionado.")]

s += [P("2.3 Assinatura digital e lacração dos sistemas", h2),
      P("Concluído o desenvolvimento, os programas são compilados, assinados digitalmente pelo TSE e pelas entidades "
        "fiscalizadoras presentes e lacrados em cerimônia pública. Os resumos digitais (hashes) dos arquivos são "
        "publicados, para que qualquer cópia possa ser comparada com a versão lacrada."),
      P("<b>Controle:</b> assinatura de múltiplas entidades; publicação dos hashes. <b>Limite:</b> a assinatura "
        "garante que o programa não mudou depois da lacração, não que o programa lacrado seja correto.")]

s += [P("2.4 Geração de mídias e carga das urnas", h2),
      P("Os Tribunais Regionais geram as mídias com os programas lacrados e os dados de cada seção (eleitores, "
        "candidatos). Em cerimônia pública, as urnas recebem a carga e são lacradas fisicamente. É gerada a tabela "
        "de correspondência, que associa cada urna física à sua seção; o sistema de totalização só aceita resultados "
        "de urnas que constem dessa tabela. Urnas sorteadas passam por verificação da integridade dos sistemas "
        "instalados."),
      P("<b>Controle:</b> cerimônia aberta, lacres, tabela de correspondência, verificação de hashes. "
        "<b>Observado em 2026:</b> os logs registram a data da carga, em geral cerca de dez dias antes do 1º turno.")]

s += [P("2.5 Abertura da seção e zerésima", h2),
      P("No dia da eleição, antes do início da votação, a urna imprime a zerésima: um relatório que mostra que não "
        "há nenhum voto registrado para nenhum candidato. A zerésima é assinada pelos mesários e pelos fiscais "
        "presentes. A votação ocorre das 8h às 17h, no horário de Brasília, em todo o país."),
      P("<b>Controle:</b> zerésima assinada; presença de fiscais de partido. <b>Observado em 2026:</b> o log de "
        "cada urna registra o início das operações, a impressão da zerésima e a abertura da votação, com horário.")]

s += [P("2.6 Identificação e habilitação do eleitor", h2),
      P("O mesário localiza o eleitor pelo número do título ou do documento e confere a foto. Há três caminhos para "
        "habilitar a urna, todos visíveis no log:"),
      tabela("Formas de habilitação do eleitor observadas nos logs de 2026",
             ["Forma", "Como ocorre", "Participação (1º / 2º turno)"], [
          ["Biométrica", "A urna reconhece a digital do eleitor.", "87,5% / 87,3%"],
          ["Manual", "A digital do eleitor não é reconhecida após até quatro tentativas. O mesário informa o ano de "
                     "nascimento do eleitor, conferido com o cadastro, e autoriza com a própria digital.",
           "6,7% / 6,7%"],
          ["Sem biometria cadastrada", "O eleitor não tem digital no cadastro; a habilitação é feita pelo documento, "
                                       "sem leitura de digital.", "5,8% / 6,0%"],
      ], [3.3, 9.5, 4.2], fonte=FONTE_TSE),
      P("O eleitor assina o caderno de votação, que é o único registro nominal de quem compareceu. "
        "<b>Limite:</b> o log não identifica o eleitor, e o caderno não é público. Por isso, não é possível verificar "
        "externamente se cada voto corresponde a um eleitor que de fato compareceu.")]

s += [P("2.7 Votação e registro do voto", h2),
      P("Na cabine, o eleitor digita os números dos candidatos e confirma. A urna registra cada voto em três lugares: "
        "no RDV, que guarda cada voto individualmente, em ordem embaralhada para preservar o sigilo; nos totais que "
        "formarão o BU; e no log, que registra que um voto foi computado, sem o conteúdo. Se a urna falhar, é "
        "substituída por uma urna de contingência, que recebe os votos já registrados; em último caso, a votação "
        "prossegue em cédula de papel."),
      P("<b>Controle:</b> o RDV permite recontar os votos de forma independente do BU. <b>Limite:</b> RDV, BU e "
        "log são gerados pelo mesmo software. Não existe registro do voto que o eleitor possa conferir.")]

s += [P("2.8 Encerramento, Boletim de Urna e transmissão", h2),
      P("Às 17h, encerrada a fila, o presidente da mesa encerra a votação. A urna imprime o Boletim de Urna em várias "
        "vias, uma delas afixada na seção e outras entregues aos fiscais, com QR Code que permite conferir o conteúdo "
        "com um aplicativo. O resultado é gravado em mídia, assinado digitalmente pela urna e transmitido pela rede "
        "da Justiça Eleitoral ao TSE."),
      P("<b>Controle:</b> BU impresso e público na seção, antes da transmissão; assinatura digital. "
        "<b>Observado em 2026:</b> o arquivo de assinatura (vota.vsc) contém o hash SHA-512 de cada arquivo da seção "
        "e duas assinaturas, uma de software e uma de hardware.")]

s += [P("2.9 Totalização e divulgação", h2),
      P("Desde 2020, a totalização é centralizada no TSE. O sistema confere a assinatura e a tabela de "
        "correspondência de cada BU recebido, soma os votos e divulga os resultados parciais e finais no mesmo dia. "
        "Os BUs de todas as seções ficam disponíveis na internet, e o resultado por seção é publicado no Portal de "
        "Dados Abertos."),
      P("<b>Controle:</b> qualquer pessoa pode comparar o BU da sua seção com o publicado e somar todos os BUs. "
        "Este estudo fez essa soma para o país inteiro (seção 4.6).")]

s += [P("2.10 Auditorias e publicação dos arquivos de urna", h2),
      P("No dia da eleição, urnas sorteadas na véspera são retiradas das seções e passam pelo Teste de Integridade: "
        "uma votação simulada, filmada, com votos conhecidos de antemão, cujo BU deve coincidir com eles. Desde 2022, "
        "parte desses testes usa a biometria de eleitores reais, para que a urna não consiga distinguir o teste da "
        "votação. Depois da eleição, o TSE publica os arquivos de cada urna: log, BU, RDV, imagem do BU e arquivo de "
        "assinatura. São esses arquivos que este estudo examina."),
      P("<b>Controle:</b> Teste de Integridade; auditoria pelos partidos; publicação integral dos arquivos. "
        "<b>Observado em 2026:</b> o TSE substituiu três arquivos publicados em 03/11, sem aviso (seção 4.7).")]

s += [P("2.11 Mapa de controles e do alcance deste estudo", h2),
      tabela("Etapas do processo, controles existentes e o que os dados públicos permitem verificar",
             ["Etapa", "Controle oficial", "Verificável com dados públicos?", "Coberto neste estudo"], [
          ["Cadastro e biometria", "Revisões, batimento biométrico", "Parcialmente (agregados)", "Proporção sem biometria"],
          ["Desenvolvimento do software", "Inspeção do código, TPS", "Não", "—"],
          ["Assinatura e lacração", "Cerimônia, hashes publicados", "Parcialmente", "—"],
          ["Carga das urnas", "Cerimônia, tabela de correspondência", "Parcialmente (log)", "Datas no log"],
          ["Zerésima", "Relatório assinado na seção", "Sim (log)", "Abertura no log"],
          ["Habilitação do eleitor", "Biometria, mesário, caderno", "Parcialmente (log, sem identidade)", "Seções 4.2–4.5"],
          ["Votação", "RDV", "Sim (RDV)", "RDV × BU"],
          ["Encerramento e BU", "BU impresso, assinatura", "Sim (hash; assinatura não)", "Seção 4.6"],
          ["Totalização", "Conferência no TSE", "Sim", "BU × oficial; soma nacional"],
          ["Publicação dos arquivos", "—", "Sim", "Seção 4.7"],
      ], [3.4, 4.6, 4.5, 4.5], fonte="elaboração própria.")]

# ---------- 3. dados e método ----------
s += [P("3. Dados e método", h1),
      P("<b>Fontes.</b> Todas as fontes são públicas e oficiais: (i) o arquivo de votação por seção do Portal de Dados "
        "Abertos do TSE, com votos por candidato, comparecimento, eleitorado apto e local de votação; (ii) os arquivos "
        "de urna, publicados em um arquivo compactado por unidade da federação e turno (cerca de 219 GB no total), "
        "com o log, o BU, o RDV, a imagem do BU e o arquivo de assinatura de cada seção."),
      P("<b>Leitura.</b> Os arquivos foram lidos diretamente do servidor do TSE por requisições parciais (HTTP "
        "<i>Range</i>), extraindo apenas os trechos necessários, com processamento paralelo e retomada automática. "
        "BU, RDV e arquivo de assinatura são estruturas binárias ASN.1. Como o formato de 2026 diverge da "
        "especificação publicada (achado 10), foi escrito um decodificador próprio, validado contra a imagem "
        "impressa do BU e contra o resultado oficial."),
      P("<b>Tratamento dos logs.</b> O log é cumulativo (o do 2º turno contém o do 1º), contém cópias idênticas das "
        "memórias interna e externa e, nas seções com troca de urna, o log da urna original. Foram usadas apenas as "
        "linhas do último dia de votação, descartadas as linhas duplicadas e somados os logs de urnas distintas."),
      P("<b>Análise estatística.</b> As comparações entre seções são feitas dentro da mesma zona e município, para "
        "isolar o efeito local do perfil regional. São usados a correlação de postos de Spearman, a inferência "
        "ecológica por regressão ponderada com efeito fixo de município, o pareamento da mesma seção entre turnos e o "
        "teste de sequências de Wald-Wolfowitz com correção para múltiplos testes.")]

# ---------- 4. resultados ----------
s += [P("4. Resultados", h1)]

s += [P("4.1 Testes forenses no resultado oficial", h2),
      tabela("Testes forenses aplicados ao resultado por seção", ["Teste", "Resultado", "Interpretação"], [
          ["Votos × comparecimento × aptos", "100% das seções consistentes; nenhuma acima do eleitorado",
           "Sem seção inflada"],
          ["Impressão digital de Klimek", "620 seções com comparecimento ≥ 95% em ~499 mil; correlação "
           "comparecimento × voto de −0,07 no município", "Sem padrão de enchimento de urna"],
          ["Último dígito (seções com ≥ 40 votos)", "Dentro da faixa de simulações sem fraude", "Sem contagens fabricadas"],
          ["Benford no 2º dígito", "Média de 3,82 a 3,97; simulação sem fraude: 3,78 a 3,98", "Compatível"],
      ], [4.2, 7.6, 5.2], fonte=FONTE_OF),
      figura(AQUI / "klimek.png", 15.5, "Comparecimento × participação de Lula por seção, 1º e 2º turno. O "
             "enchimento de urna apareceria como concentração isolada no canto superior direito.", FONTE_OF)]

s += [P("4.2 Validação dos logs", h2),
      P("Antes de servir de base para a análise, o log foi comparado com o resultado oficial, seção por seção."),
      tabela("Votos registrados nos logs × resultado oficial para Presidente", ["", "1º turno", "2º turno"], [
          ["Seções com log", "499.176", "499.177"],
          ["Votos no log", "125.274.428", "128.234.921"],
          ["Votos oficiais", "125.275.835", "128.236.074"],
          ["Seções sem log publicado", "30 (2 MG, 28 exterior)", "28 (exterior)"],
          ["Seções com log incompleto", "9 (63 votos)", "6 (cerca de 54 votos)"],
      ], [7.0, 5.0, 5.0], fonte=FONTE_TSE),
      P("Em 99,99% das seções, o log conta exatamente os votos oficiais. Nas 15 seções com log incompleto, a urna "
        "travou ou foi reiniciada; o BU e o RDV dessas seções conferem com o resultado oficial (seção 4.6), o que "
        "indica perda de linhas no log, e não de votos.")]

s += [P("4.3 Votos sem biometria e horário", h2),
      P("Uma fraude por voto em nome de eleitores ausentes tenderia a se concentrar no fim do dia, quando já se sabe "
        "quem não compareceu. O voto manual mostra o padrão oposto: tem maior peso às 8h (cerca de 9% dos votos) e cai "
        "ao longo do dia até cerca de 5,5%. O voto de eleitores sem biometria cadastrada aumenta no fim do dia: de "
        "5,46% para 6,44% nos últimos 10% dos votos de cada seção no 1º turno, e de 5,57% para 6,62% no 2º. Esse "
        "aumento é igual nos dois turnos, e sua variação por seção entre os turnos não tem relação com a variação do "
        "voto em Lula (ρ = −0,001)."),
      figura(DL / "horario_manuais.png", 15.5, "Distribuição horária dos votos por forma de habilitação e "
             "participação dos votos manuais e sem biometria em cada intervalo de 15 minutos.", FONTE_TSE)]

s += [P("4.4 Quem autorizou os votos manuais", h2),
      P("Na habilitação manual, o log registra quem autorizou. Quando a digital é de um mesário cadastrado, o registro "
        "é \"Mesário N habilitou o eleitor\". Quando não é, o log registra a gravação de uma nova digital (\"vai salvar "
        "a digital em novo arquivo\") ou a impossibilidade de associar a habilitação a um mesário, e a habilitação "
        "prossegue."),
      tabela("Autorização dos votos manuais", ["Autorização", "1º turno", "%", "2º turno", "%"], [
          ["Mesário com digital cadastrada", "5.118.861", "61,4", "5.840.628", "67,7"],
          ["Digital fora do cadastro, primeira ocorrência", "1.515.711", "18,2", "1.279.769", "14,8"],
          ["Digital fora do cadastro, ocorrência repetida", "1.705.023", "20,4", "1.511.180", "17,5"],
          ["<b>Sem mesário identificado</b>", "<b>3.220.734</b>", "<b>38,6</b>", "<b>2.790.949</b>", "<b>32,3</b>"],
      ], [7.6, 2.6, 1.6, 2.6, 1.6], fonte=FONTE_TSE, negrito_ultima=True),
      P("Os votos manuais sem mesário identificado correspondem a 2,58% de todos os votos no 1º turno e 2,18% no 2º. "
        "Em 52.856 seções no 1º turno e 32.361 no 2º, com dez ou mais votos manuais, todos foram autorizados dessa "
        "forma. O caso extremo é a seção 651 da zona 26, em Serra (ES), no 1º turno: 274 votos manuais em 279, "
        "201 consecutivos com a mesma digital não cadastrada; Lula obteve 47,7% na seção, contra 40,3% na zona. No 2º "
        "turno, a mesma seção apresentou padrão normal."),
      figura(DL / "mesario" / "mesario_por_uf.png", 12.0, "Proporção dos votos manuais autorizados por digital "
             "fora do cadastro, por unidade da federação.", FONTE_TSE),
      P("<b>Aviso \"o eleitor identificado já votou\".</b> Foram 118.272 avisos no 1º turno e 113.423 no 2º, cerca de "
        "9 a cada 10 mil votos, com frequência duas vezes maior em seções indígenas. A maioria ocorre segundos após o "
        "voto anterior. Nas seções em que o número de avisos se aproxima do número de votos, o log mostra o mesário "
        "digitando novamente o documento do eleitor que acabara de votar. A contagem dessas seções confere com o "
        "resultado oficial.")]

s += [P("4.5 Direção dos votos manuais", h2),
      P("O voto é secreto, e não é possível saber o voto de um eleitor habilitado manualmente. A hipótese de que esses "
        "votos tenham favorecido um candidato foi testada por três caminhos independentes."),
      tabela("Testes sobre a direção dos votos manuais", ["Teste", "Resultado", "Padrão esperado sob fraude"], [
          ["Inferência ecológica", "Lula entre manuais: 53,9%; entre biométricos: 51,4% (2º turno). A diferença caiu "
                                   "de 6,1 pontos (1º turno) para 2,5", "Diferença próxima de 30 pontos, crescente"],
          ["Correlação dentro da zona", "Manual sem mesário identificado: +0,024; \"já votou\": +0,025; sem biometria: "
                                        "+0,020", "Correlação forte"],
          ["Mesma seção entre turnos", "Variação de manuais × variação de Lula: ρ = −0,002", "Variação conjunta"],
      ], [3.6, 8.0, 5.4], fonte=FONTE_TSE + " TSE, Dados Abertos."),
      P("Mesmo que toda a diferença observada no 2º turno fosse atribuída a fraude, o efeito seria de 0,4 a "
        "0,5 milhão de votos, cerca de dez vezes menor que a margem de 4,43 milhões. Os resultados não se alteram com a "
        "exclusão das seções indígenas.")]

s += [P("4.6 Verificação dos arquivos de urna", h2),
      P("Para cada seção, nos dois turnos, foram conferidos: o hash SHA-512 do BU, do RDV e da imagem do BU contra os "
        "valores registrados no arquivo de assinatura; o hash do próprio arquivo de assinatura; o RDV contra o BU, "
        "voto a voto, em todos os cargos; a imagem impressa contra o BU; e o BU contra o resultado oficial."),
      tabela("Resultado da verificação dos arquivos de urna", ["Verificação", "1º turno", "2º turno", "Divergências"], [
          ["Seções com arquivos publicados", "499.207", "499.207", "—"],
          ["Hash do BU, do RDV e da imagem", "499.176", "499.178", "0"],
          ["RDV = BU, todos os cargos", "499.177", "499.180", "0"],
          ["Imagem impressa = BU", "499.176", "499.178", "0"],
          ["BU = resultado oficial", "499.176", "499.178", "0"],
          ["Seções sem BU, apenas com RDV", "30 (1.348 votos)", "27 (831 votos)", "RDV = oficial"],
      ], [6.8, 3.2, 3.2, 3.8], fonte=FONTE_TSE),
      tabela("Soma nacional dos Boletins de Urna × resultado oficial",
             ["", "Lula", "Flávio", "Brancos", "Nulos", "Total"], [
          ["1º turno, BUs", "53.878.914", "56.103.951", "2.300.777", "3.668.963", "125.274.487"],
          ["1º turno, oficial", "53.879.538", "56.104.503", "2.300.798", "3.669.003", "125.275.835"],
          ["2º turno, BUs", "64.255.787", "59.825.688", "1.430.484", "2.723.284", "128.235.243"],
          ["2º turno, oficial", "64.256.232", "59.826.041", "1.430.496", "2.723.305", "128.236.074"],
      ], [3.2, 2.6, 2.6, 2.4, 2.4, 3.8], fonte=FONTE_TSE + " TSE, Dados Abertos."),
      P("A diferença entre as somas, de 1.348 votos no 1º turno e 831 no 2º, corresponde exatamente às seções que têm "
        "apenas o RDV publicado, nas quais o total do RDV é igual ao oficial. Todo voto do resultado oficial tem "
        "correspondência em um arquivo de urna, e todo arquivo de urna está refletido no resultado oficial.")]

s += [P("4.7 Substituição de arquivos publicados", h2),
      P("Durante a verificação, em 03/11/2026, o TSE substituiu três arquivos no servidor, sem aviso, 12 dias após o "
        "1º turno e 8 dias após o 2º. Durante algumas horas, os arquivos de MA e MG foram servidos incompletos."),
      tabela("Arquivos substituídos em 03/11/2026", ["Arquivo", "Versão anterior", "Nova versão (UTC)", "Alteração"], [
          ["1º turno, MA", "22/10", "03/11, 19h59 · 3,27 GB", "Não identificável: não havia índice da versão anterior"],
          ["1º turno, MG", "22/10", "03/11, 21h08 · 9,64 GB", "Não identificável; mesmo número de logs (52.060)"],
          ["2º turno, SP", "26/10", "03/11, 19h48 · 25,76 GB", "Inclusão do log ausente da seção 64777/395/298 e de "
                                                               "novo arquivo de assinatura, ambos datados de 03/11"],
      ], [2.8, 2.6, 4.0, 7.6], fonte="servidor de arquivos do TSE (cdn.tse.jus.br); elaboração própria."),
      P("Nas versões finais, as três unidades conferem integralmente. O log incluído em SP registra 268 votos "
        "(135 Lula, 125 Flávio, 2 brancos, 6 nulos), iguais ao BU e ao resultado oficial, e seu hash confere com o novo "
        "arquivo de assinatura. A substituição completou um arquivo ausente e não alterou votos.")]

# ---------- 5. achados ----------
s += [P("5. Achados", h1),
      P("Os achados são classificados em três níveis. <b>Alto:</b> permite que uma fraude local ocorra sem ser "
        "detectável nos dados públicos. <b>Médio:</b> reduz a capacidade de auditoria externa. <b>Baixo:</b> falha "
        "operacional sem efeito sobre a contagem. Nenhum achado indica voto alterado."),
      tabela("Achados da verificação", ["Nº", "Achado", "Alcance", "Nível"], [
          ["1", "A habilitação manual prossegue quando a digital de autorização não pertence a mesário cadastrado; "
                "a digital é gravada no momento.", "3.220.734 votos (1º t.); 2.790.949 (2º t.)", "Alto"],
          ["2", "Seções em que todos os votos manuais foram autorizados por digital fora do cadastro, inclusive com "
                "sequências longas (Serra/ES, zona 26, seção 651).", "52.856 seções (1º t.); 32.361 (2º t.)", "Alto"],
          ["3", "Eleitor sem biometria cadastrada é habilitado sem leitura de digital; a proporção aumenta no fim "
                "do dia.", "7,28 mi (1º t.); 7,63 mi (2º t.)", "Alto"],
          ["4", "Seções sem BU e sem log publicados, apenas com RDV.", "30 (1º t.: 28 exterior, 2 MG); 27 (2º t.)",
           "Médio"],
          ["5", "Log incompleto por travamento ou reinício da urna.", "9 seções (1º t.); 6 (2º t.)", "Baixo"],
          ["6", "Urna de recuperação com log de outra seção.", "Vila Velha/ES, zona 9, seção 85 (2º t.)", "Baixo"],
          ["7", "Seções com RDV que não constam do resultado oficial.", "Exterior: 29564/1/91 e 30686/1/443", "Baixo"],
          ["8", "Substituição de arquivos publicados sem aviso nem registro de alteração; versão incompleta servida "
                "por horas.", "1º t. MA e MG; 2º t. SP", "Médio"],
          ["9", "Assinatura digital não verificável pelo público: algoritmo de software não publicado e chaves "
                "públicas das urnas sem acesso automatizado.", "Todas as seções", "Médio"],
          ["10", "A especificação publicada dos arquivos não corresponde ao formato de 2026.", "Todos os arquivos",
           "Médio"],
          ["11", "Encadeamento dos registros do BU e do RDV não reproduzível com as informações publicadas.",
           "Todos os arquivos", "Baixo"],
          ["12", "Aviso \"o eleitor identificado já votou\" frequente, por redigitação do documento pelo mesário.",
           "118 mil (1º t.); 113 mil (2º t.)", "Baixo"],
          ["13", "O log não identifica o eleitor, e o caderno de votação não é público.", "Todas as seções", "Alto"],
      ], [0.9, 9.0, 5.3, 1.8], fonte="elaboração própria.", junto=False)]

# ---------- 6. limitações ----------
s += [P("6. Limitações", h1)]
s += bullets([
    "<b>Software da urna.</b> BU, RDV, log e assinatura são produzidos pelo mesmo programa. Um programa adulterado "
    "produziria arquivos coerentes entre si, e todas as conferências da seção 4.6 seriam satisfeitas. Esse risco só "
    "pode ser enfrentado com um registro do voto independente do software, conferido pelo eleitor e auditado por "
    "amostragem.",
    "<b>Voto em nome de eleitor ausente.</b> Se realizado por mesário no ritmo normal da votação, não deixa padrão "
    "distinguível no log. A verificação exige o caderno de votação e a lista de mesários.",
    "<b>Inferência sobre o voto.</b> As estimativas da seção 4.5 são ecológicas e dependem da hipótese de que, "
    "dentro do município, eleitores com a mesma forma de habilitação votam de modo semelhante entre seções.",
    "<b>Fatores externos à urna.</b> Compra de voto, coação e irregularidades de cadastro não são observáveis nesses "
    "dados.",
    "<b>Assinaturas.</b> A verificação criptográfica limitou-se aos hashes; as assinaturas digitais não puderam "
    "ser validadas (achado 9).",
])

# ---------- 7. conclusões ----------
s += [P("7. Conclusões", h1),
      P("No plano aritmético e de integridade dos arquivos, o resultado é inequívoco: os arquivos das urnas conferem "
        "entre si e com o resultado oficial, voto por voto, em todas as seções em que foram publicados. Não há indício "
        "de alteração após a urna nem de erro de totalização, e os testes forenses não apontam manipulação das "
        "contagens."),
      P("No plano do processo, há vulnerabilidades reais. A principal permite que um mesário habilite o voto de um "
        "eleitor autorizando com uma digital que não consta do cadastro. Os dados não mostram uso dessa brecha em "
        "escala capaz de alterar o resultado: o efeito máximo compatível com os dados é cerca de dez vezes menor que a "
        "margem do 2º turno. Fraudes pequenas e localizadas, porém, não podem ser descartadas sem acesso ao caderno de "
        "votação."),
      P("Por fim, a garantia de que a urna registrou o que o eleitor digitou continua dependendo da confiança no "
        "software e em quem o controla. Os dados públicos, por mais completos que sejam, não alcançam essa pergunta.")]

# ---------- 8. recomendações ----------
s += [P("8. Recomendações", h1)]
s += bullets([
    "Impedir a habilitação manual autorizada por digital que não pertença a mesário nomeado para a seção.",
    "Publicar, por seção, o número de habilitações manuais e quantas ocorreram sem mesário identificado.",
    "Permitir a auditoria por amostragem do caderno de votação por entidades fiscalizadoras.",
    "Auditar as seções em que todos os votos manuais foram autorizados por digital fora do cadastro, começando "
    "pela seção 651 da zona 26 de Serra (ES).",
    "Publicar o BU das 57 seções que têm apenas RDV e esclarecer as duas seções de MG sem BU e sem log.",
    "Versionar os arquivos publicados, com data, hash e registro do que mudou em cada substituição.",
    "Publicar a especificação atualizada dos arquivos de 2026 e o meio de obter as chaves públicas das urnas.",
    "No longo prazo, adotar um registro do voto independente do software, conferido pelo eleitor e auditado "
    "estatisticamente.",
])

# ---------- referências ----------
s += [P("Referências", h1)]
for r in [
    "BRASIL. Lei nº 4.737, de 15 de julho de 1965. Código Eleitoral.",
    "BRASIL. Lei nº 9.504, de 30 de setembro de 1997. Estabelece normas para as eleições.",
    "BRASIL. Tribunal Superior Eleitoral. Resolução nº 23.673, de 14 de dezembro de 2021. Dispõe sobre os "
    "procedimentos de fiscalização e auditoria do sistema eletrônico de votação.",
    "BRASIL. Tribunal Superior Eleitoral. Portal de Dados Abertos: votação por seção eleitoral, 2026. "
    "dadosabertos.tse.jus.br.",
    "BRASIL. Tribunal Superior Eleitoral. Arquivos de urna (logs, BU, RDV, assinaturas), 2026. cdn.tse.jus.br.",
    "KLIMEK, P. et al. Statistical detection of systematic election irregularities. <i>Proceedings of the National "
    "Academy of Sciences</i>, v. 109, n. 41, 2012.",
    "LINDEMAN, M.; STARK, P. B. A gentle introduction to risk-limiting audits. <i>IEEE Security &amp; Privacy</i>, "
    "v. 10, n. 5, 2012.",
    "MEBANE, W. R. Election forensics: the second-digit Benford's law test and recent American presidential "
    "elections. 2006.",
    "RIVEST, R. L.; WACK, J. On the notion of \"software independence\" in voting systems. NIST/TGDC, 2006.",
    "THOMPSON, K. Reflections on trusting trust. <i>Communications of the ACM</i>, v. 27, n. 8, 1984.",
]:
    s.append(P(r, ref))

# ---------- apêndices ----------
s += [P("Apêndice A. Reprodutibilidade", h1),
      P("Os scripts estão na pasta <i>scripts_analise</i> e os resultados intermediários em <i>dados_logs</i>."),
      tabela("Scripts e respectivas etapas", ["Script", "Etapa"], [
          ["logs_brasil.py, logs_analise_brasil.py, horario_manuais.py", "Seções 4.2 e 4.3"],
          ["logs_mesario.py, mesario_refaz_erros.py, locais_secao.py, analise_mesario.py", "Seção 4.4"],
          ["manuais_voto_estimado.py, manuais_variacao_voto.py, manuais_variacao_uf.py", "Seção 4.5"],
          ["verifica_bu.py, analise_bu.py", "Seções 4.6 e 4.7"],
      ], [10.5, 6.5])]

s += [P("Apêndice B. Glossário", h1),
      tabela("Termos utilizados", ["Termo", "Significado"], [
          ["BU (Boletim de Urna)", "Resultado da seção: votos por candidato, brancos e nulos, impresso e gravado em "
                                   "arquivo assinado."],
          ["RDV (Registro Digital do Voto)", "Arquivo com cada voto individual, em ordem embaralhada, que permite "
                                             "recontar a seção."],
          ["Log da urna", "Registro cronológico dos eventos da urna, sem o conteúdo do voto nem a identidade do eleitor."],
          ["vota.vsc", "Arquivo de assinatura da seção, com o hash de cada arquivo e as assinaturas de software e "
                       "hardware."],
          ["Hash (SHA-512)", "Resumo matemático de um arquivo; qualquer alteração no arquivo muda o resumo."],
          ["Zerésima", "Relatório impresso antes da votação que mostra a urna sem nenhum voto."],
          ["Habilitação manual", "Liberação da urna pelo mesário quando a digital do eleitor não é reconhecida."],
          ["Tabela de correspondência", "Associação entre cada urna física e sua seção, usada na totalização."],
          ["Teste de Integridade", "Votação simulada e filmada, em urnas sorteadas, para conferir que o BU reflete "
                                   "os votos digitados."],
      ], [4.8, 12.2])]

# ---------- apêndice C: integridade ----------
import hashlib


def sha3(p):
    return hashlib.sha3_512(Path(p).read_bytes()).hexdigest()


mono = ParagraphStyle("mono", fontName="Courier", fontSize=6.4, leading=8.2, textColor=TINTA)
man = AQUI / "MANIFESTO_SHA3-512.txt"
scripts = sorted(AQUI.glob("scripts_analise/*.py")) + [AQUI / "gerar_estudo_publicacao.py", AQUI / "gera_manifesto.py"]
linhas_h = [[P(f.name, cel), P(sha3(f), mono)] for f in scripts]
linhas_h.append([P("<b>MANIFESTO_SHA3-512.txt</b>", cel), P(sha3(man), mono)])
CONT["tab"] += 1
th = Table([[P("Arquivo", celb), P("SHA3-512", celb)]] + linhas_h, colWidths=[4.6 * cm, 11.8 * cm], repeatRows=1)
th.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), CAB), ("LINEABOVE", (0, 0), (-1, 0), 1.0, TINTA),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.6, TINTA), ("LINEBELOW", (0, -1), (-1, -1), 1.0, TINTA),
                        ("LINEBELOW", (0, 1), (-1, -2), 0.25, REGUA), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
s += [P("Apêndice C. Integridade", h1),
      P("Os resumos abaixo usam o algoritmo SHA3-512 (FIPS 202), da família de hash mais recente padronizada pelo "
        "NIST, com saída de 512 bits. Qualquer alteração em um arquivo, mesmo de um único caractere, produz um resumo "
        "completamente diferente. O arquivo <i>MANIFESTO_SHA3-512.txt</i> lista o resumo de cada um dos scripts, "
        "figuras e resultados intermediários; o resumo do manifesto, na última linha, protege o conjunto inteiro."),
      P("O resumo deste PDF não pode constar dele próprio, pois incluí-lo alteraria o arquivo. Ele é publicado "
        "separadamente, no arquivo <i>estudo_eleicao_presidencial_2026.pdf.hashes.txt</i>. Para conferir: "
        "<font name='Courier'>openssl dgst -sha3-512 &lt;arquivo&gt;</font> ou, em Python, "
        "<font name='Courier'>hashlib.sha3_512</font>."),
      P(f"<b>Tabela {CONT['tab']}.</b> Resumos SHA3-512 dos scripts e do manifesto",
        ParagraphStyle("tt2", parent=legenda, spaceBefore=6, spaceAfter=4, textColor=TINTA)), th]


def achata(lst):
    for x in lst:
        if isinstance(x, list):
            yield from achata(x)
        else:
            if isinstance(x, Paragraph) and x.style.name in ("h1", "h2"):
                yield CondPageBreak(6.5 * cm if x.style.name == "h1" else 5.5 * cm)
            yield x


s = list(achata(s))
doc = Doc(str(SAIDA), pagesize=A4, leftMargin=2.3 * cm, rightMargin=2.3 * cm, topMargin=2.2 * cm,
          bottomMargin=2.2 * cm, title=TITULO, author="Iago Rocha Nascimento",
          subject="Eleição presidencial de 2026: processo eleitoral e verificação dos dados públicos")
doc.multiBuild(s)
print(SAIDA)
