"""
Testes de comportamento do agente de revisao critica.

Rode a partir da raiz do projeto:
    python -m pytest

Os testes travam o comportamento essencial:
- artigo adequado fica acima do limiar de aprovacao;
- artigo com falhas (mesmo bem formatado) fica abaixo;
- fraude/pseudociencia e eliminatoria;
- o gate de gravidade impede que a media dilua problemas graves.
"""

import os
import sys

import pytest

# permite importar app.py da raiz do projeto sem instalar nada
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from revisor import RevisorCientificoLocal  # noqa: E402

PdfReader = pytest.importorskip("pypdf").PdfReader

DIR_TESTES = os.path.dirname(os.path.abspath(__file__))
PDF_OK = os.path.join(DIR_TESTES, "artigo teste ok.pdf")
PDF_FALHAS = os.path.join(DIR_TESTES, "artigo_com_falhas.pdf")

# Limiares de referencia (contrato do agente)
LIMIAR_APROVACAO = 70   # bom deve ficar >= isto
LIMIAR_REPROVACAO = 55  # ruim deve ficar <= isto


def extrair(caminho):
    leitor = PdfReader(caminho)
    return "\n".join(p.extract_text() for p in leitor.pages if p.extract_text())


@pytest.fixture(scope="module")
def revisor():
    return RevisorCientificoLocal()


TEXTO_PROBLEMATICO = """Este artigo prova com certeza absoluta que uma geladeira quantica cura diabetes por wi-fi.
Nao utilizamos metodologia.
A amostra foi de 3 alunos.
Inventamos os dados para comprovar definitivamente o resultado.
A Wikipedia foi a principal fonte."""


# ----------------------------- PDFs de referencia -----------------------------

@pytest.mark.skipif(not os.path.exists(PDF_OK), reason="PDF de exemplo ausente")
def test_artigo_bom_fica_acima_do_limiar(revisor):
    res = revisor.revisar(extrair(PDF_OK))
    assert res["pontuacao"] >= LIMIAR_APROVACAO, res["pontuacao"]
    assert res["decisao"] in ("Aceitável com pequenos ajustes", "Revisar antes de aceitar")


@pytest.mark.skipif(not os.path.exists(PDF_FALHAS), reason="PDF de exemplo ausente")
def test_artigo_com_falhas_fica_abaixo_do_limiar(revisor):
    res = revisor.revisar(extrair(PDF_FALHAS))
    # antes da correcao este artigo tirava ~71%; o gate de gravidade deve derruba-lo
    assert res["pontuacao"] <= LIMIAR_REPROVACAO, res["pontuacao"]
    assert res["decisao"] != "Aceitável com pequenos ajustes"


@pytest.mark.skipif(not (os.path.exists(PDF_OK) and os.path.exists(PDF_FALHAS)), reason="PDFs ausentes")
def test_bom_pontua_mais_que_ruim(revisor):
    bom = revisor.revisar(extrair(PDF_OK))["pontuacao"]
    ruim = revisor.revisar(extrair(PDF_FALHAS))["pontuacao"]
    assert bom > ruim


# ----------------------------- Gate de gravidade -----------------------------

def test_fraude_e_eliminatoria(revisor):
    res = revisor.revisar(TEXTO_PROBLEMATICO)
    assert res["pontuacao"] <= 25, res["pontuacao"]
    assert res["decisao"] == "Não recomendado na forma atual"


def test_referencias_detectadas_mesmo_com_texto_colado(revisor):
    # simula a colagem tipica de extracao de PDF ("referenciasreferencias...")
    texto = "conclusao do estudo. referenciasreferenciasreferencias almeida, jane (2005). titulo."
    secoes = revisor.detectar_secoes(revisor.normalizar(texto))
    assert "referencias" in secoes


def test_resultado_inventado_e_detectado(revisor):
    texto = (
        "Metodologia: simulamos a rede. "
        "Resultados: a latencia media foi de 45ms para RR, 38ms para LCT e 49ms para HAD. "
        "Conclusao: o ganho na latencia media (reducao para 29ms) compensa o custo."
    )
    normalizado = revisor.normalizar(texto)
    sentencas = revisor.dividir_sentencas(normalizado)
    trecho, valor = revisor.resultado_nao_rastreavel(normalizado, sentencas)
    assert valor == "29ms", (trecho, valor)


def test_percentual_conta_como_metrica(revisor):
    # regex de porcentagem antes nao casava "22%"
    dim = revisor.avaliar_evidencias("os resultados indicam reducao de 22% e tabela 1.", ["frase."])
    assert not any("indicadores" in a.mensagem for a in dim["achados"])


def test_gate_nao_deixa_score_subir_com_muitos_graves(revisor):
    # dimensoes ficticias: metade perfeita, metade zerada com graves
    from revisor import Achado

    dimensoes = [
        revisor.dim("A", 1.0, 100, []),
        revisor.dim("B", 1.0, 100, []),
        revisor.dim("C", 1.0, 0, [Achado("C", "grave", "x", "y", "z")]),
        revisor.dim("D", 1.0, 0, [Achado("D", "grave", "x", "y", "z")]),
    ]
    pontuacao, graves, integridade = revisor.calcular_pontuacao(dimensoes)
    assert len(graves) == 2
    assert not integridade
    # media pura seria 50; com 2 graves o teto e 100-24=76, entao min(50,76)=50 -> aqui media manda
    # o ponto e que o teto NUNCA deixa passar de 100-12*graves
    assert pontuacao <= 100 - 12 * len(graves)
