"""
Motor do agente de revisao critica de artigos cientificos.

Logica pura (regras, rubricas e inferencias), SEM dependencia de interface.
A UI (Streamlit) vive em app.py e importa a classe daqui.
"""

import re
import unicodedata
from dataclasses import dataclass


@dataclass
class Achado:
    dimensao: str
    nivel: str
    mensagem: str
    trecho: str
    recomendacao: str
    # True  -> `trecho` e uma citacao literal extraida do artigo;
    # False -> `trecho` e uma constatacao da analise (ex.: "informacao nao localizada").
    trecho_literal: bool = False


class RevisorCientificoLocal:
    """
    Agente local de revisao critica.
    Usa regras, rubricas e inferencias simples criadas no proprio codigo.
    Nao usa API, LLM, ChatGPT, Gemini ou qualquer IA externa integrada.

    IMPORTANTE: os padroes regex sempre trabalham sobre o texto NORMALIZADO
    (minusculo e SEM acentos), por isso os padroes nao levam acento. Ja as
    mensagens exibidas ao usuario devem estar em portugues correto, com acento.
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
            "referencias": [r"\breferencias", r"\bbibliografia", r"\breferencia\b", r"\bobras\s+citadas", r"\btrabalhos\s+citados"],
        }

        # rotulos legiveis das secoes, para exibir ao usuario (com acento)
        self.rotulos_secoes = {
            "resumo": "resumo",
            "introducao": "introdução",
            "objetivo": "objetivo",
            "metodologia": "metodologia",
            "resultados": "resultados",
            "discussao": "discussão",
            "conclusao": "conclusão",
            "referencias": "referências",
        }

        self.padroes_graves = {
            "Manipulação de dados": [
                r"\b(inventei|inventamos|fabriquei|fabricamos|forjei|forjamos)\s+(os\s+)?dados\b",
                r"\b(dados|resultados)\s+(inventados|fabricados|forjados|falsificados)\b",
                r"\b(alterei|alteramos|manipulei|manipulamos)\s+(os\s+)?dados\b",
                r"\bremovi\s+(dados|outliers|amostras)\s+sem\s+justificativa\b",
                r"\bp-?hacking\b",
            ],
            "Ausência declarada de método": [
                r"\bnao\s+(usamos|utilizamos|aplicamos|seguimos)\s+(metodo|metodologia|criterio|criterios)\b",
                r"\bsem\s+(metodo|metodologia|criterio|criterios|procedimento\s+de\s+coleta)\b",
                r"\bos\s+dados\s+foram\s+coletados\s+sem\s+criterio\b",
            ],
            "Incoerência científica": [
                r"\b(cura|curar|prevenir)\s+(cancer|diabetes|calvicie|doencas?)\s+por\s+(wi-?fi|blockchain|roteador)\b",
                r"\b(geladeira|camisa|roteador)\s+(quantica|quantico)\b",
                r"\bblockchain\s+(quantico|quantica)\s+para\s+(curar|provar|garantir)\b",
            ],
        }

    def normalizar(self, texto):
        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(c for c in texto if not unicodedata.combining(c))
        texto = texto.lower()
        # junta palavras quebradas por hifen no fim da linha: "otimiza-\ncao" -> "otimizacao"
        texto = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)
        texto = texto.replace("\n", " ")
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
                r"\([a-z][a-z\s.&-]{1,40},\s*(19|20)\d{2}[a-z]?\)",   # (Autor, 2020)
                r"\b[a-z][a-z-]{1,30}\s+\((19|20)\d{2}\)",           # Autor (2020)
                r"\b[a-z][a-z-]{2,30},\s*(19|20)\d{2}\b",            # Autor, 2020 (nota de rodape)
                r"\[\d+\]",                                          # [12]
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

        pontuacao, graves, grave_integridade = self.calcular_pontuacao(dimensoes)
        decisao = self.definir_decisao(pontuacao, graves, grave_integridade)

        return {
            "pontuacao": pontuacao,
            "decisao": decisao,
            "dimensoes": dimensoes,
            "achados": achados,
            "secoes": [self.rotulos_secoes.get(s, s) for s in secoes],
            "citacoes": citacoes,
            "palavras": palavras,
            "pontos_fortes": self.gerar_pontos_fortes(dimensoes),
            "parecer": self.gerar_parecer(pontuacao, decisao, dimensoes, achados, grave_integridade),
            "perguntas": self.gerar_perguntas(dimensoes),
        }

    def rotular_secoes(self, chaves):
        return ", ".join(self.rotulos_secoes.get(c, c) for c in chaves)

    def avaliar_estrutura(self, texto, secoes, palavras):
        achados = []
        essenciais = ["resumo", "introducao", "metodologia", "resultados", "conclusao", "referencias"]
        ausentes = [s for s in essenciais if s not in secoes]
        nota = 100

        if palavras < 120:
            nota -= 35
            achados.append(Achado("Estrutura", "grave", "O texto é curto demais para uma revisão científica consistente.", f"{palavras} palavras detectadas.", "Desenvolver resumo, método, resultados, discussão e referências."))
        elif palavras < 250:
            nota -= 10
            achados.append(Achado("Estrutura", "alerta", "O texto é resumido; a revisão crítica pode ficar limitada.", f"{palavras} palavras detectadas.", "Ampliar o desenvolvimento caso este seja o artigo completo, não apenas um recorte."))
        if len(ausentes) >= 4:
            nota -= 45
            achados.append(Achado("Estrutura", "grave", "Faltam várias seções essenciais de artigo científico.", self.rotular_secoes(ausentes), "Organizar o artigo em seções acadêmicas reconhecíveis (resumo, introdução, metodologia, resultados, discussão, conclusão, referências)."))
        elif ausentes:
            nota -= 8 * len(ausentes)
            achados.append(Achado("Estrutura", "alerta", "Algumas seções essenciais não foram localizadas.", self.rotular_secoes(ausentes), "Adicionar ou nomear claramente as seções ausentes."))

        return self.dim("Estrutura e organização", 1.0, nota, achados)

    def avaliar_problema_objetivo(self, texto, sentencas):
        achados = []
        nota = 100
        tem_objetivo = self.contem(texto, [r"\bobjetivo\b", r"\bobjetiva\b", r"\btem\s+como\s+finalidade\b", r"\bbusca\s+analisar\b"])
        tem_problema = self.contem(texto, [r"\bproblema\s+de\s+pesquisa\b", r"\bquestao\s+de\s+pesquisa\b", r"\bpergunta\s+de\s+pesquisa\b", r"\blacuna\b"])

        if not tem_objetivo:
            nota -= 30
            achados.append(Achado("Problema e objetivo", "grave", "O objetivo da pesquisa não está claro.", "Nenhum marcador de objetivo foi encontrado.", "Declarar explicitamente o que o artigo pretende analisar, comparar ou demonstrar. Ex.: 'Este trabalho tem como objetivo avaliar...'."))
        if not tem_problema:
            nota -= 20
            achados.append(Achado("Problema e objetivo", "alerta", "A lacuna ou problema de pesquisa não aparece de forma explícita.", "Não foram encontrados termos como problema, pergunta de pesquisa ou lacuna.", "Explicar qual problema científico motiva o estudo e qual lacuna ele pretende preencher."))

        return self.dim("Problema, objetivo e relevância", 1.1, nota, achados)

    def avaliar_metodologia(self, texto, sentencas):
        achados = []
        nota = 100
        criterios = {
            "tipo de pesquisa": [r"\bqualitativ[ao]\b", r"\bquantitativ[ao]\b", r"\bmista\b", r"\brevisao\s+(sistematica|bibliografica|integrativa)\b", r"\bestudo\s+de\s+caso\b"],
            "amostra ou corpus": [r"\bamostra\b", r"\bparticipantes?\b", r"\bcorpus\b", r"\bdataset\b", r"\bbase\s+de\s+dados\b"],
            "coleta de dados": [r"\bcoleta\b", r"\bentrevista\b", r"\bquestionario\b", r"\bobservacao\b", r"\bexperimento\b"],
            "análise de dados": [r"\banalise\s+d[eo]s?\s+dados\b", r"\banalise\s+estatistica\b", r"\banalise\s+de\s+conteudo\b", r"\bteste\s+estatistico\b", r"\banalise\s+das\s+entrevistas\b", r"\banalise\s+tematica\b", r"\banalise\s+interpretativa\b", r"\btranscric\w*", r"\bcodificac\w*", r"\bcategorias?\s+(de\s+analise|analiticas|emergentes|tematicas)\b"],
        }
        criterios_graves = {"tipo de pesquisa", "análise de dados"}

        for nome, padroes in criterios.items():
            if not self.contem(texto, padroes):
                nota -= 18
                achados.append(Achado("Metodologia", "grave" if nome in criterios_graves else "alerta", f"A metodologia não descreve claramente: {nome}.", "Informação não localizada.", f"Incluir no método uma descrição objetiva de {nome}."))

        amostra_suspeita = self.primeiro_trecho(sentencas, [r"\b(amostra|n)\s*(=|de|foi\s+de|com)\s*(1|2|3|4|5)\b", r"\b(apenas|somente|so)\s+(1|2|3|4|5)\s+(participantes?|alunos?|estudantes?|pessoas?)\b"])
        if amostra_suspeita and not self.contem(amostra_suspeita, [r"\bqualitativ[ao]\b", r"\bexploratori[ao]\b", r"\bestudo\s+de\s+caso\b", r"\bpiloto\b"]):
            nota -= 20
            achados.append(Achado("Metodologia", "grave", "A amostra parece pequena e não foi justificada no mesmo contexto.", amostra_suspeita, "Justificar a amostra ou ampliar o tamanho amostral (ou explicitar que é um estudo qualitativo/piloto).", trecho_literal=True))

        return self.dim("Rigor metodológico", 1.4, nota, achados)

    def resultado_nao_rastreavel(self, texto, sentencas):
        """
        Deteccao de resultado inventado/contraditorio: uma sentenca afirma um
        ganho/reducao com um numero+unidade que nao aparece em nenhum outro lugar
        do artigo (nem na tabela, nem nos dados). Ex.: texto diz "reducao para 29ms"
        mas a tabela so mostra 45ms, 38ms e 49ms.

        So consideramos unidades de MEDIDA (ms, mb, gb...) e nao percentuais: "%"
        costuma aparecer em estatisticas descritivas legitimas citadas uma unica
        vez, o que geraria falso positivo.
        """
        unidade = r"(?:ms|mb|gb|kb|tb|km|kg|mhz|ghz|fps|bytes?)"
        melhora = r"\b(reduc\w+|reduziu|ganho|ganhos|aumento|aumentou|melhora|melhorou|caiu|subiu|elevou|queda|otimizou|acelerou|desempenho)\b"

        for sentenca in sentencas:
            if not re.search(melhora, sentenca):
                continue
            for m in re.finditer(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(" + unidade + r")", sentenca):
                valor, uni = m.group(1), m.group(2)
                ocorrencias = len(re.findall(r"(?<!\d)" + re.escape(valor) + r"\s*" + re.escape(uni), texto))
                if ocorrencias <= 1:
                    return sentenca, f"{valor}{uni}"
        return "", ""

    def avaliar_evidencias(self, texto, sentencas):
        achados = []
        nota = 100
        tem_resultado = self.contem(texto, [r"\bresultados?\b", r"\bachados\b", r"\bos\s+dados\s+indicam\b", r"\bobservou-se\b"])
        tem_numero = self.contem(texto, [r"\d+([,.]\d+)?\s*%", r"\bp\s*[<=>]\s*0[,.]\d+\b", r"\bmedia\b", r"\bdesvio\s+padrao\b", r"\btabela\s+\d+\b", r"\bfigura\s+\d+\b"])
        conclusao_forte = self.primeiro_trecho(sentencas, [r"\b(comprova|provamos|garante|garantimos)\s+(definitivamente|totalmente|sem\s+duvida)\b", r"\bcerteza\s+absoluta\b", r"\bverdade\s+absoluta\b", r"\b100%\s+(correto|eficaz|garantido)\b"])
        trecho_incoerente, valor_incoerente = self.resultado_nao_rastreavel(texto, sentencas)

        if not tem_resultado:
            nota -= 30
            achados.append(Achado("Evidências", "grave", "O artigo não apresenta resultados reconhecíveis.", "Resultados não localizados.", "Apresentar achados separados da introdução e da conclusão."))
        if not tem_numero:
            nota -= 15
            achados.append(Achado("Evidências", "alerta", "Não foram encontrados indicadores, tabela, figura ou medida objetiva.", "Sem métricas detectadas.", "Adicionar dados, categorias analíticas, frequências, exemplos ou medidas estatísticas."))
        if conclusao_forte:
            nota -= 25
            achados.append(Achado("Evidências", "grave", "A conclusão usa linguagem absoluta acima do que as evidências sustentam.", conclusao_forte, "Trocar a certeza absoluta por conclusões proporcionais aos dados e mencionar os limites.", trecho_literal=True))
        if trecho_incoerente:
            nota -= 30
            achados.append(Achado("Evidências", "grave", f"Um resultado citado ({valor_incoerente}) não aparece nos dados ou tabelas apresentados.", trecho_incoerente, "Garantir que todo número citado como resultado apareça de fato nos dados, tabelas ou figuras do artigo.", trecho_literal=True))

        return self.dim("Evidências e resultados", 1.3, nota, achados)

    def avaliar_referencias(self, texto, citacoes):
        achados = []
        nota = 100
        tem_ref = self.contem(texto, self.secoes["referencias"])
        fonte_fraca = self.primeiro_trecho(self.dividir_sentencas(texto), [r"\b(wikipedia|blog|youtube|instagram|tiktok|chatgpt)\s+(foi|e)\s+(a\s+)?(principal\s+)?fonte\b", r"\bbaseamos\s+o\s+artigo\s+em\s+(wikipedia|blog|youtube|instagram|tiktok|chatgpt)\b"])

        if not tem_ref:
            nota -= 35
            achados.append(Achado("Referencial teórico", "grave", "Não há seção de referências identificável.", "Referências não localizadas.", "Inserir uma seção de referências acadêmicas ao final do artigo."))
        if citacoes == 0:
            nota -= 35
            achados.append(Achado("Referencial teórico", "grave", "Não foram detectadas citações no corpo do texto.", "0 citações detectadas.", "Citar autores, anos ou referências numeradas ao fundamentar as afirmações."))
        elif citacoes < 3:
            nota -= 15
            achados.append(Achado("Referencial teórico", "alerta", "O texto tem poucas citações para sustentar a revisão crítica.", f"{citacoes} citação(ões) detectada(s).", "Ampliar o diálogo com literatura científica recente e relevante."))
        if fonte_fraca:
            nota -= 25
            achados.append(Achado("Referencial teórico", "grave", "Uma fonte fraca aparece como base principal.", fonte_fraca, "Substituir por artigos, livros, documentos técnicos ou bases científicas.", trecho_literal=True))

        return self.dim("Referencial teórico e citações", 1.2, nota, achados)

    def avaliar_argumentacao(self, texto, sentencas):
        achados = []
        nota = 100
        conectores = self.contar(texto, [r"\bportanto\b", r"\bcontudo\b", r"\bno\s+entanto\b", r"\balem\s+disso\b", r"\bpor\s+outro\s+lado\b", r"\bdessa\s+forma\b"])
        subjetivo = self.primeiro_trecho(sentencas, [r"\b(eu|nos)\s+(acho|achamos|acredito|acreditamos|sinto|sentimos)\b", r"\bachismo\b", r"\bna\s+minha\s+opiniao\b", r"\bbastou\s+observar\b"])

        if conectores < 2:
            nota -= 15
            achados.append(Achado("Argumentação", "alerta", "A argumentação tem poucos conectores lógicos.", f"{conectores} conector(es) detectado(s).", "Explicitar relações de causa, contraste, consequência e comparação entre as ideias."))
        if subjetivo:
            nota -= 25
            achados.append(Achado("Argumentação", "grave", "Há linguagem opinativa usada como critério científico.", subjetivo, "Substituir opiniões por evidências, autores, dados ou justificativas metodológicas.", trecho_literal=True))

        return self.dim("Argumentação crítica", 1.0, nota, achados)

    def avaliar_etica_integridade(self, sentencas):
        achados = []
        nota = 100

        for criterio, padroes in self.padroes_graves.items():
            trecho = self.primeiro_trecho(sentencas, padroes)
            if trecho:
                nota -= 45
                achados.append(Achado("Ética e integridade", "grave", f"{criterio} detectada.", trecho, "Revisar a integridade do estudo antes de qualquer aprovação.", trecho_literal=True))

        return self.dim("Ética e integridade científica", 1.5, nota, achados)

    def avaliar_limitacoes(self, texto):
        achados = []
        nota = 100
        if not self.contem(texto, [r"\blimitacao\b", r"\blimitacoes\b", r"\blimites\s+do\s+estudo\b", r"\bpesquisas\s+futuras\b"]):
            nota -= 25
            achados.append(Achado("Limitações", "alerta", "O artigo não explicita limitações ou trabalhos futuros.", "Limitações não localizadas.", "Adicionar uma discussão sobre limites, vieses, escopo e pesquisas futuras."))

        return self.dim("Limitações e transparência", 0.8, nota, achados)

    def dim(self, nome, peso, nota, achados):
        nota = max(0, min(100, round(nota)))
        return {"nome": nome, "peso": peso, "nota": nota, "achados": achados}

    def calcular_pontuacao(self, dimensoes):
        """
        Score com GATE de gravidade, em vez de media pura.

        A media ponderada sozinha "dilui" problemas graves: um artigo com varias
        falhas graves aterrissava em ~70% porque dimensoes intactas puxavam a media
        pra cima. Aqui a nota final e limitada por um teto que reflete a gravidade:

        - achado grave de integridade (fraude, pseudociencia, ausencia declarada de
          metodo) e eliminatorio -> teto 25;
        - demais graves reduzem o teto progressivamente (12 pontos por grave);
        - sem graves, a media vale integralmente.
        """
        peso_total = sum(d["peso"] for d in dimensoes)
        media = sum(d["nota"] * d["peso"] for d in dimensoes) / peso_total
        graves = [a for d in dimensoes for a in d["achados"] if a.nivel == "grave"]
        grave_integridade = any(a.dimensao.startswith("Ética") for a in graves)

        if grave_integridade:
            teto = 25
        elif graves:
            teto = max(40, 100 - 12 * len(graves))
        else:
            teto = 100

        pontuacao = max(0, min(round(media), teto))
        return pontuacao, graves, grave_integridade

    def definir_decisao(self, pontuacao, graves, grave_integridade):
        if grave_integridade or pontuacao < 50:
            return "Não recomendado na forma atual"
        if graves:
            return "Revisão substancial necessária"
        if pontuacao >= 85:
            return "Aceitável com pequenos ajustes"
        if pontuacao >= 70:
            return "Revisar antes de aceitar"
        return "Revisão substancial necessária"

    def gerar_pontos_fortes(self, dimensoes):
        fortes = []
        for dim in dimensoes:
            if dim["nota"] >= 85:
                fortes.append(f"{dim['nome']} está bem resolvida.")
        return fortes or ["Não foram identificados pontos fortes suficientes pela rubrica automática."]

    def gerar_parecer(self, pontuacao, decisao, dimensoes, achados, grave_integridade=False):
        piores = sorted(dimensoes, key=lambda d: d["nota"])[:3]
        nomes = ", ".join(d["nome"] for d in piores)
        graves = [a for a in achados if a.nivel == "grave"]

        parecer = f"O artigo recebeu {pontuacao}% e a decisão sugerida é: {decisao}. "
        parecer += f"Os pontos que mais exigem atenção são: {nomes}. "

        if grave_integridade:
            parecer += f"Foram detectados {len(graves)} problema(s) grave(s), incluindo falha(s) de integridade científica que limitam a pontuação a um teto eliminatório. "
        elif graves:
            parecer += f"Foram detectados {len(graves)} problema(s) grave(s), que limitam a pontuação e impedem a aprovação sem revisão humana cuidadosa. "
        else:
            parecer += "Não foram encontrados sinais graves, mas ainda há aspectos a melhorar. "

        parecer += "A avaliação deve ser entendida como apoio crítico local, não como decisão final automática."
        return parecer

    def gerar_perguntas(self, dimensoes):
        perguntas = []
        mapa = {
            "Problema, objetivo e relevância": "O objetivo responde claramente a uma lacuna científica?",
            "Rigor metodológico": "Outro pesquisador conseguiria reproduzir o método descrito?",
            "Evidências e resultados": "As conclusões são proporcionais aos dados apresentados?",
            "Referencial teórico e citações": "As afirmações principais dialogam com literatura confiável e recente?",
            "Argumentação crítica": "O texto compara ideias, reconhece limites e evita a opinião pessoal?",
            "Ética e integridade científica": "Os dados são rastreáveis, honestos e obtidos com critério?",
            "Limitações e transparência": "O artigo declara limites, vieses e possibilidades de pesquisa futura?",
        }

        for dim in sorted(dimensoes, key=lambda d: d["nota"])[:5]:
            if dim["nota"] < 85 and dim["nome"] in mapa:
                perguntas.append(mapa[dim["nome"]])

        return perguntas
