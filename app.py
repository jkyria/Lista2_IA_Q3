import re
import unicodedata
from dataclasses import dataclass

import streamlit as st

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


@dataclass
class Achado:
    dimensao: str
    nivel: str
    mensagem: str
    trecho: str
    recomendacao: str


class RevisorCientificoLocal:
    """
    Agente local de revisao critica.
    Usa regras, rubricas e inferencias simples criadas no proprio codigo.
    Nao usa API, LLM, ChatGPT, Gemini ou qualquer IA externa integrada.
    """

    def __init__(self):
        self.secoes = {
            "resumo": [r"\bresumo\b", r"\babstract\b"],
            "introducao": [r"\bintroducao\b"],
            "objetivo": [r"\bobjetivo\b", r"\bobjetivos\b"],
            "metodologia": [r"\bmetodologia\b", r"\bmetodos?\b", r"\bprocedimentos?\b"],
            "resultados": [r"\bresultados?\b", r"\bachados\b"],
            "discussao": [r"\bdiscussao\b", r"\banalise\s+critica\b"],
            "conclusao": [r"\bconclusao\b", r"\bconsideracoes\s+finais\b"],
            "referencias": [r"\breferencias\b", r"\bbibliografia\b"],
        }

        self.padroes_graves = {
            "Manipulacao de dados": [
                r"\b(inventei|inventamos|fabriquei|fabricamos|forjei|forjamos)\s+(os\s+)?dados\b",
                r"\b(dados|resultados)\s+(inventados|fabricados|forjados|falsificados)\b",
                r"\b(alterei|alteramos|manipulei|manipulamos)\s+(os\s+)?dados\b",
                r"\bremovi\s+(dados|outliers|amostras)\s+sem\s+justificativa\b",
                r"\bp-?hacking\b",
            ],
            "Ausencia declarada de metodo": [
                r"\bnao\s+(usamos|utilizamos|aplicamos|seguimos)\s+(metodo|metodologia|criterio|criterios)\b",
                r"\bsem\s+(metodo|metodologia|criterio|criterios|procedimento\s+de\s+coleta)\b",
                r"\bos\s+dados\s+foram\s+coletados\s+sem\s+criterio\b",
            ],
            "Incoerencia cientifica": [
                r"\b(cura|curar|prevenir)\s+(cancer|diabetes|calvicie|doencas?)\s+por\s+(wi-?fi|blockchain|roteador)\b",
                r"\b(geladeira|camisa|roteador)\s+(quantica|quantico)\b",
                r"\bblockchain\s+(quantico|quantica)\s+para\s+(curar|provar|garantir)\b",
            ],
        }

    def normalizar(self, texto):
        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        texto = texto.lower().replace("\n", " ")
        texto = re.sub(r"\s+", " ", texto)
        return texto.strip()

    def dividir_sentencas(self, texto):
        partes = re.split(r"(?<=[.!?;:])\s+", texto)
        return [p.strip() for p in partes if len(p.strip()) >= 8]

    def contem(self, texto, padroes):
        return any(re.search(p, texto) for p in padroes)

    def primeiro_trecho(self, sentencas, padroes):
        for sentenca in sentencas:
            if self.contem(sentenca, padroes):
                return sentenca
        return ""

    def contar(self, texto, padroes):
        return sum(len(re.findall(p, texto)) for p in padroes)

    def detectar_secoes(self, texto):
        return [nome for nome, padroes in self.secoes.items() if self.contem(texto, padroes)]

    def contar_citacoes(self, texto):
        return self.contar(
            texto,
            [
                r"\([a-z][a-z\s,.-]{2,},\s*(19|20)\d{2}\)",
                r"\b[a-z][a-z\s,.-]{2,}\s+\((19|20)\d{2}\)",
                r"\[\d+\]",
            ],
        )

    def revisar(self, texto_original):
        texto = self.normalizar(texto_original)
        sentencas = self.dividir_sentencas(texto)
        secoes = self.detectar_secoes(texto)
        citacoes = self.contar_citacoes(texto)
        palavras = len(texto.split())

        dimensoes = [
            self.avaliar_estrutura(texto, secoes, palavras),
            self.avaliar_problema_objetivo(texto, sentencas),
            self.avaliar_metodologia(texto, sentencas),
            self.avaliar_evidencias(texto, sentencas),
            self.avaliar_referencias(texto, citacoes),
            self.avaliar_argumentacao(texto, sentencas),
            self.avaliar_etica_integridade(sentencas),
            self.avaliar_limitacoes(texto),
        ]

        achados = []
        for dim in dimensoes:
            achados.extend(dim["achados"])

        pontuacao = round(sum(dim["nota"] * dim["peso"] for dim in dimensoes) / sum(dim["peso"] for dim in dimensoes))
        decisao = self.definir_decisao(pontuacao, dimensoes)

        return {
            "pontuacao": pontuacao,
            "decisao": decisao,
            "dimensoes": dimensoes,
            "achados": achados,
            "secoes": secoes,
            "citacoes": citacoes,
            "palavras": palavras,
            "pontos_fortes": self.gerar_pontos_fortes(dimensoes),
            "parecer": self.gerar_parecer(pontuacao, decisao, dimensoes, achados),
            "perguntas": self.gerar_perguntas(dimensoes),
        }

    def avaliar_estrutura(self, texto, secoes, palavras):
        achados = []
        essenciais = ["resumo", "introducao", "metodologia", "resultados", "conclusao", "referencias"]
        ausentes = [s for s in essenciais if s not in secoes]
        nota = 100

        if palavras < 120:
            nota -= 35
            achados.append(Achado("Estrutura", "grave", "O texto e curto demais para uma revisao cientifica consistente.", f"{palavras} palavras detectadas.", "Desenvolver resumo, metodo, resultados, discussao e referencias."))
        elif palavras < 250:
            nota -= 10
            achados.append(Achado("Estrutura", "alerta", "O texto e resumido; a revisao critica pode ficar limitada.", f"{palavras} palavras detectadas.", "Ampliar o desenvolvimento caso este seja o artigo completo, nao apenas um recorte."))
        if len(ausentes) >= 4:
            nota -= 45
            achados.append(Achado("Estrutura", "grave", "Faltam varias secoes essenciais de artigo cientifico.", ", ".join(ausentes), "Organizar o artigo em secoes academicas reconheciveis."))
        elif ausentes:
            nota -= 8 * len(ausentes)
            achados.append(Achado("Estrutura", "alerta", "Algumas secoes essenciais nao foram localizadas.", ", ".join(ausentes), "Adicionar ou nomear claramente as secoes ausentes."))

        return self.dim("Estrutura e organizacao", 1.0, nota, achados)

    def avaliar_problema_objetivo(self, texto, sentencas):
        achados = []
        nota = 100
        tem_objetivo = self.contem(texto, [r"\bobjetivo\b", r"\bobjetiva\b", r"\btem\s+como\s+finalidade\b", r"\bbusca\s+analisar\b"])
        tem_problema = self.contem(texto, [r"\bproblema\s+de\s+pesquisa\b", r"\bquestao\s+de\s+pesquisa\b", r"\bpergunta\s+de\s+pesquisa\b", r"\blacuna\b"])

        if not tem_objetivo:
            nota -= 30
            achados.append(Achado("Problema e objetivo", "grave", "O objetivo da pesquisa nao esta claro.", "Nenhum marcador de objetivo foi encontrado.", "Declarar explicitamente o que o artigo pretende analisar, comparar ou demonstrar."))
        if not tem_problema:
            nota -= 20
            achados.append(Achado("Problema e objetivo", "alerta", "A lacuna ou problema de pesquisa nao aparece de forma explicita.", "Nao foram encontrados termos como problema, pergunta de pesquisa ou lacuna.", "Explicar qual problema cientifico motiva o estudo."))

        return self.dim("Problema, objetivo e relevancia", 1.1, nota, achados)

    def avaliar_metodologia(self, texto, sentencas):
        achados = []
        nota = 100
        criterios = {
            "tipo de pesquisa": [r"\bqualitativ[ao]\b", r"\bquantitativ[ao]\b", r"\bmista\b", r"\brevisao\s+(sistematica|bibliografica|integrativa)\b", r"\bestudo\s+de\s+caso\b"],
            "amostra ou corpus": [r"\bamostra\b", r"\bparticipantes?\b", r"\bcorpus\b", r"\bdataset\b", r"\bbase\s+de\s+dados\b"],
            "coleta de dados": [r"\bcoleta\b", r"\bentrevista\b", r"\bquestionario\b", r"\bobservacao\b", r"\bexperimento\b"],
            "analise de dados": [r"\banalise\s+dos\s+dados\b", r"\banalise\s+estatistica\b", r"\banalise\s+de\s+conteudo\b", r"\bteste\s+estatistico\b"],
        }

        for nome, padroes in criterios.items():
            if not self.contem(texto, padroes):
                nota -= 18
                achados.append(Achado("Metodologia", "grave" if nome in {"tipo de pesquisa", "analise de dados"} else "alerta", f"A metodologia nao descreve claramente: {nome}.", "Informacao nao localizada.", f"Incluir no metodo uma descricao objetiva de {nome}."))

        amostra_suspeita = self.primeiro_trecho(sentencas, [r"\b(amostra|n)\s*(=|de|foi\s+de|com)\s*(1|2|3|4|5)\b", r"\b(apenas|somente|so)\s+(1|2|3|4|5)\s+(participantes?|alunos?|estudantes?|pessoas?)\b"])
        if amostra_suspeita and not self.contem(amostra_suspeita, [r"\bqualitativ[ao]\b", r"\bexploratori[ao]\b", r"\bestudo\s+de\s+caso\b", r"\bpiloto\b"]):
            nota -= 20
            achados.append(Achado("Metodologia", "grave", "A amostra parece pequena e nao foi justificada no mesmo contexto.", amostra_suspeita, "Justificar a amostra ou ampliar o tamanho amostral."))

        return self.dim("Rigor metodologico", 1.4, nota, achados)

    def avaliar_evidencias(self, texto, sentencas):
        achados = []
        nota = 100
        tem_resultado = self.contem(texto, [r"\bresultados?\b", r"\bachados\b", r"\bos\s+dados\s+indicam\b", r"\bobservou-se\b"])
        tem_numero = self.contem(texto, [r"\b\d+([,.]\d+)?%\b", r"\bp\s*[<=>]\s*0[,.]\d+\b", r"\bmedia\b", r"\bdesvio\s+padrao\b", r"\btabela\s+\d+\b", r"\bfigura\s+\d+\b"])
        conclusao_forte = self.primeiro_trecho(sentencas, [r"\b(comprova|provamos|garante|garantimos)\s+(definitivamente|totalmente|sem\s+duvida)\b", r"\bcerteza\s+absoluta\b", r"\bverdade\s+absoluta\b", r"\b100%\s+(correto|eficaz|garantido)\b"])

        if not tem_resultado:
            nota -= 30
            achados.append(Achado("Evidencias", "grave", "O artigo nao apresenta resultados reconheciveis.", "Resultados nao localizados.", "Apresentar achados separados da introducao e da conclusao."))
        if not tem_numero:
            nota -= 15
            achados.append(Achado("Evidencias", "alerta", "Nao foram encontrados indicadores, tabela, figura ou medida objetiva.", "Sem metricas detectadas.", "Adicionar dados, categorias analiticas, frequencias, exemplos ou medidas estatisticas."))
        if conclusao_forte:
            nota -= 25
            achados.append(Achado("Evidencias", "grave", "A conclusao usa linguagem absoluta acima do que as evidencias sustentam.", conclusao_forte, "Trocar certeza absoluta por conclusoes proporcionais aos dados e mencionar limites."))

        return self.dim("Evidencias e resultados", 1.3, nota, achados)

    def avaliar_referencias(self, texto, citacoes):
        achados = []
        nota = 100
        tem_ref = self.contem(texto, self.secoes["referencias"])
        fonte_fraca = self.primeiro_trecho(self.dividir_sentencas(texto), [r"\b(wikipedia|blog|youtube|instagram|tiktok|chatgpt)\s+(foi|e)\s+(a\s+)?(principal\s+)?fonte\b", r"\bbaseamos\s+o\s+artigo\s+em\s+(wikipedia|blog|youtube|instagram|tiktok|chatgpt)\b"])

        if not tem_ref:
            nota -= 35
            achados.append(Achado("Referencial teorico", "grave", "Nao ha secao de referencias identificavel.", "Referencias nao localizadas.", "Inserir referencias academicas ao final do artigo."))
        if citacoes == 0:
            nota -= 35
            achados.append(Achado("Referencial teorico", "grave", "Nao foram detectadas citacoes no corpo do texto.", "0 citacoes detectadas.", "Citar autores, anos ou referencias numeradas ao fundamentar afirmacoes."))
        elif citacoes < 3:
            nota -= 15
            achados.append(Achado("Referencial teorico", "alerta", "O texto tem poucas citacoes para sustentar a revisao critica.", f"{citacoes} citacao(oes) detectada(s).", "Aumentar o dialogo com literatura cientifica recente e relevante."))
        if fonte_fraca:
            nota -= 25
            achados.append(Achado("Referencial teorico", "grave", "Fonte fraca aparece como base principal.", fonte_fraca, "Substituir por artigos, livros, documentos tecnicos ou bases cientificas."))

        return self.dim("Referencial teorico e citacoes", 1.2, nota, achados)

    def avaliar_argumentacao(self, texto, sentencas):
        achados = []
        nota = 100
        conectores = self.contar(texto, [r"\bportanto\b", r"\bcontudo\b", r"\bno\s+entanto\b", r"\balem\s+disso\b", r"\bpor\s+outro\s+lado\b", r"\bdessa\s+forma\b"])
        subjetivo = self.primeiro_trecho(sentencas, [r"\b(eu|nos)\s+(acho|achamos|acredito|acreditamos|sinto|sentimos)\b", r"\bachismo\b", r"\bna\s+minha\s+opiniao\b", r"\bbastou\s+observar\b"])

        if conectores < 2:
            nota -= 15
            achados.append(Achado("Argumentacao", "alerta", "A argumentacao tem poucos conectores logicos.", f"{conectores} conector(es) detectado(s).", "Explicitar relacoes de causa, contraste, consequencia e comparacao entre ideias."))
        if subjetivo:
            nota -= 25
            achados.append(Achado("Argumentacao", "grave", "Ha linguagem opinativa usada como criterio cientifico.", subjetivo, "Substituir opinioes por evidencias, autores, dados ou justificativas metodologicas."))

        return self.dim("Argumentacao critica", 1.0, nota, achados)

    def avaliar_etica_integridade(self, sentencas):
        achados = []
        nota = 100

        for criterio, padroes in self.padroes_graves.items():
            trecho = self.primeiro_trecho(sentencas, padroes)
            if trecho:
                nota -= 45
                achados.append(Achado("Etica e integridade", "grave", criterio + " detectada.", trecho, "Revisar a integridade do estudo antes de qualquer aprovacao."))

        return self.dim("Etica e integridade cientifica", 1.5, nota, achados)

    def avaliar_limitacoes(self, texto):
        achados = []
        nota = 100
        if not self.contem(texto, [r"\blimitacao\b", r"\blimitacoes\b", r"\blimites\s+do\s+estudo\b", r"\bpesquisas\s+futuras\b"]):
            nota -= 25
            achados.append(Achado("Limitacoes", "alerta", "O artigo nao explicita limitacoes ou trabalhos futuros.", "Limitacoes nao localizadas.", "Adicionar uma discussao sobre limites, vieses, escopo e pesquisas futuras."))

        return self.dim("Limitacoes e transparencia", 0.8, nota, achados)

    def dim(self, nome, peso, nota, achados):
        nota = max(0, min(100, round(nota)))
        return {"nome": nome, "peso": peso, "nota": nota, "achados": achados}

    def definir_decisao(self, pontuacao, dimensoes):
        tem_grave = any(a.nivel == "grave" for d in dimensoes for a in d["achados"])
        notas_baixas = [d for d in dimensoes if d["nota"] < 50]

        if pontuacao >= 85 and not tem_grave:
            return "Aceitavel com pequenos ajustes"
        if pontuacao >= 70 and len(notas_baixas) == 0:
            return "Revisar antes de aceitar"
        if pontuacao >= 50:
            return "Revisao substancial necessaria"
        return "Nao recomendado na forma atual"

    def gerar_pontos_fortes(self, dimensoes):
        fortes = []
        for dim in dimensoes:
            if dim["nota"] >= 85:
                fortes.append(f"{dim['nome']} esta bem resolvida.")
        return fortes or ["Nao foram identificados pontos fortes suficientes pela rubrica automatica."]

    def gerar_parecer(self, pontuacao, decisao, dimensoes, achados):
        piores = sorted(dimensoes, key=lambda d: d["nota"])[:3]
        nomes = ", ".join(d["nome"] for d in piores)
        graves = [a for a in achados if a.nivel == "grave"]

        parecer = f"O artigo recebeu {pontuacao}% e a decisao sugerida e: {decisao}. "
        parecer += f"Os pontos que mais exigem atencao sao: {nomes}. "

        if graves:
            parecer += "Ha problemas graves que impedem uma aprovacao sem revisao humana cuidadosa. "
        else:
            parecer += "Nao foram encontrados sinais graves, mas ainda ha aspectos a melhorar. "

        parecer += "A avaliacao deve ser entendida como apoio critico local, nao como decisao final automatica."
        return parecer

    def gerar_perguntas(self, dimensoes):
        perguntas = []
        mapa = {
            "Problema, objetivo e relevancia": "O objetivo responde claramente a uma lacuna cientifica?",
            "Rigor metodologico": "Outro pesquisador conseguiria reproduzir o metodo descrito?",
            "Evidencias e resultados": "As conclusoes sao proporcionais aos dados apresentados?",
            "Referencial teorico e citacoes": "As afirmacoes principais dialogam com literatura confiavel e recente?",
            "Argumentacao critica": "O texto compara ideias, reconhece limites e evita opiniao pessoal?",
            "Etica e integridade cientifica": "Os dados sao rastreaveis, honestos e obtidos com criterio?",
            "Limitacoes e transparencia": "O artigo declara limites, vieses e possibilidades de pesquisa futura?",
        }

        for dim in sorted(dimensoes, key=lambda d: d["nota"])[:5]:
            if dim["nota"] < 85 and dim["nome"] in mapa:
                perguntas.append(mapa[dim["nome"]])

        return perguntas


def extrair_texto_pdf(arquivo):
    if PdfReader is None:
        st.error("A biblioteca pypdf nao esta instalada. Instale com: pip install pypdf")
        return ""

    leitor = PdfReader(arquivo)
    paginas = []

    for pagina in leitor.pages:
        texto = pagina.extract_text()
        if texto:
            paginas.append(texto)

    return "\n".join(paginas)


st.set_page_config(page_title="Revisor Critico de Artigos", layout="wide")

st.title("Revisor Critico Local de Artigos Cientificos")
st.caption("Agente criado por rubrica propria: analisa estrutura, metodo, evidencias, citacoes, argumentacao e integridade.")

revisor = RevisorCientificoLocal()

col_entrada, col_resultado = st.columns([1, 1.25])

with col_entrada:
    st.subheader("Artigo para revisao")
    modo = st.radio("Entrada", ["Texto manual", "PDF"], horizontal=True)
    texto_artigo = ""

    if modo == "PDF":
        arquivo = st.file_uploader("Envie o artigo em PDF", type=["pdf"])
        if arquivo:
            texto_artigo = extrair_texto_pdf(arquivo)
            st.success("Texto extraido do PDF.")
            with st.expander("Ver texto extraido"):
                st.text(texto_artigo)
    else:
        texto_artigo = st.text_area("Cole o texto do artigo", height=360)

    analisar = st.button("Gerar revisao critica", use_container_width=True)

with col_resultado:
    st.subheader("Parecer critico")

    if not analisar:
        st.info("Informe o artigo e clique em gerar revisao critica.")
    elif not texto_artigo.strip():
        st.warning("Nenhum texto foi informado.")
    else:
        resultado = revisor.revisar(texto_artigo)

        st.metric("Indice de rigor cientifico", f"{resultado['pontuacao']}%")
        st.markdown(f"**Decisao sugerida:** {resultado['decisao']}")
        st.write(resultado["parecer"])

        st.markdown("#### Rubrica por dimensao")
        rubrica = [
            {"Dimensao": d["nome"], "Nota": d["nota"], "Peso": d["peso"], "Achados": len(d["achados"])}
            for d in resultado["dimensoes"]
        ]
        st.dataframe(rubrica, use_container_width=True, hide_index=True)

        aba1, aba2, aba3, aba4 = st.tabs(["Fragilidades", "Recomendacoes", "Pontos fortes", "Perguntas"])

        with aba1:
            if not resultado["achados"]:
                st.success("Nenhuma fragilidade relevante foi detectada pela rubrica.")
            else:
                for achado in resultado["achados"]:
                    with st.expander(f"{achado.dimensao} - {achado.nivel}"):
                        st.write(achado.mensagem)
                        st.caption(achado.trecho)

        with aba2:
            if not resultado["achados"]:
                st.success("Sem recomendacoes obrigatorias.")
            else:
                for achado in resultado["achados"]:
                    st.markdown(f"- **{achado.dimensao}:** {achado.recomendacao}")

        with aba3:
            for item in resultado["pontos_fortes"]:
                st.markdown(f"- {item}")

        with aba4:
            for pergunta in resultado["perguntas"]:
                st.markdown(f"- {pergunta}")

        st.markdown("#### Informacoes detectadas")
        st.write(f"Palavras: {resultado['palavras']}")
        st.write(f"Citacoes detectadas: {resultado['citacoes']}")
        st.write("Secoes detectadas: " + (", ".join(resultado["secoes"]) if resultado["secoes"] else "nenhuma"))

with st.expander("Textos para teste"):
    st.markdown("**Texto mais adequado:**")
    st.code(
        """Resumo
Este artigo investiga o uso de tecnologias educacionais no ensino superior.
Introducao
A literatura aponta que ambientes digitais podem apoiar a aprendizagem (Silva, 2021). A lacuna investigada esta na relacao entre planejamento pedagogico e uso de plataformas virtuais.
Objetivo
O objetivo e analisar como tecnologias educacionais contribuem para a organizacao dos estudos.
Metodologia
Foi realizada pesquisa qualitativa exploratoria com entrevistas semiestruturadas com 12 participantes. A coleta seguiu roteiro padronizado e a analise dos dados utilizou analise de conteudo.
Resultados
Os resultados indicam melhora percebida na organizacao dos estudos. A Tabela 1 resume as categorias encontradas.
Discussao
Os achados dialogam com Santos (2020), contudo possuem limites por causa do tamanho da amostra.
Conclusao
Conclui-se que a tecnologia pode contribuir quando associada ao planejamento pedagogico. As limitacoes incluem escopo reduzido e necessidade de pesquisas futuras.
Referencias
Silva, J. (2021). Educacao digital.
Santos, M. (2020). Aprendizagem e tecnologia.""",
        language="text",
    )

    st.markdown("**Texto problematico:**")
    st.code(
        """Este artigo prova com certeza absoluta que uma geladeira quantica cura diabetes por wi-fi.
Nao utilizamos metodologia.
A amostra foi de 3 alunos.
Inventamos os dados para comprovar definitivamente o resultado.
A Wikipedia foi a principal fonte.""",
        language="text",
    )
