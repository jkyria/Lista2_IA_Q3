import streamlit as st

from revisor import RevisorCientificoLocal

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def resumir(texto, limite=200):
    """Encurta trechos longos para exibicao, sem cortar no meio de uma palavra."""
    texto = texto.strip()
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"


def extrair_texto_pdf(arquivo):
    if PdfReader is None:
        st.error("A biblioteca pypdf não está instalada. Instale com: pip install pypdf")
        return ""

    try:
        leitor = PdfReader(arquivo)
    except Exception as erro:
        st.error(f"Não foi possível ler o PDF: {erro}")
        return ""

    paginas = []
    for pagina in leitor.pages:
        texto = pagina.extract_text()
        if texto:
            paginas.append(texto)

    return "\n".join(paginas)


def main():
    st.set_page_config(page_title="Revisor Crítico de Artigos", layout="wide")

    st.title("Revisor Crítico Local de Artigos Científicos")
    st.caption("Agente criado por rubrica própria: analisa estrutura, método, evidências, citações, argumentação e integridade.")

    revisor = RevisorCientificoLocal()

    col_entrada, col_resultado = st.columns([1, 1.25])

    with col_entrada:
        st.subheader("Artigo para revisão")
        modo = st.radio("Entrada", ["Texto manual", "PDF"], horizontal=True)
        texto_artigo = ""

        if modo == "PDF":
            arquivo = st.file_uploader("Envie o artigo em PDF", type=["pdf"])
            if arquivo:
                texto_artigo = extrair_texto_pdf(arquivo)
                if texto_artigo.strip():
                    st.success("Texto extraído do PDF.")
                    with st.expander("Ver texto extraído"):
                        st.text(texto_artigo)
                else:
                    st.warning(
                        "Não foi possível extrair texto deste PDF. "
                        "Ele pode ser escaneado (imagem). Use um PDF com texto selecionável ou cole o conteúdo manualmente."
                    )
        else:
            texto_artigo = st.text_area("Cole o texto do artigo", height=360)

        analisar = st.button("Gerar revisão crítica", use_container_width=True)

    with col_resultado:
        st.subheader("Parecer crítico")

        if not analisar:
            st.info("Informe o artigo e clique em gerar revisão crítica.")
        elif not texto_artigo.strip():
            st.warning("Nenhum texto foi informado.")
        else:
            resultado = revisor.revisar(texto_artigo)

            st.metric("Índice de rigor científico", f"{resultado['pontuacao']}%")
            st.markdown(f"**Decisão sugerida:** {resultado['decisao']}")
            st.write(resultado["parecer"])

            st.markdown("#### Rubrica por dimensão")
            rubrica = [
                {"Dimensão": d["nome"], "Nota": d["nota"], "Peso": d["peso"], "Achados": len(d["achados"])}
                for d in resultado["dimensoes"]
            ]
            st.dataframe(rubrica, use_container_width=True, hide_index=True)

            aba1, aba2, aba3, aba4 = st.tabs(["Fragilidades", "Recomendações", "Pontos fortes", "Perguntas"])

            with aba1:
                if not resultado["achados"]:
                    st.success("Nenhuma fragilidade relevante foi detectada pela rubrica.")
                else:
                    st.caption("Cada fragilidade traz o que foi observado e uma orientação de como melhorar.")
                    for achado in resultado["achados"]:
                        with st.expander(f"{achado.dimensao} — {achado.nivel}"):
                            st.write(achado.mensagem)
                            if achado.trecho:
                                if achado.trecho_literal:
                                    st.caption(f"Trecho do artigo: “{resumir(achado.trecho)}”")
                                else:
                                    st.caption(f"O que foi observado: {achado.trecho}")
                            st.markdown(f"**Como melhorar:** {achado.recomendacao}")

            with aba2:
                if not resultado["achados"]:
                    st.success("Sem recomendações obrigatórias.")
                else:
                    for achado in resultado["achados"]:
                        st.markdown(f"- **{achado.dimensao}:** {achado.recomendacao}")

            with aba3:
                for item in resultado["pontos_fortes"]:
                    st.markdown(f"- {item}")

            with aba4:
                for pergunta in resultado["perguntas"]:
                    st.markdown(f"- {pergunta}")

            st.markdown("#### Informações detectadas")
            st.write(f"Palavras: {resultado['palavras']}")
            st.write(f"Citações detectadas: {resultado['citacoes']}")
            st.write("Seções detectadas: " + (", ".join(resultado["secoes"]) if resultado["secoes"] else "nenhuma"))

    with st.expander("Textos para teste"):
        st.markdown("**Texto mais adequado:**")
        st.code(
            """Resumo
Este artigo investiga o uso de tecnologias educacionais no ensino superior.
Introdução
A literatura aponta que ambientes digitais podem apoiar a aprendizagem (Silva, 2021). A lacuna investigada está na relação entre planejamento pedagógico e uso de plataformas virtuais.
Objetivo
O objetivo é analisar como tecnologias educacionais contribuem para a organização dos estudos.
Metodologia
Foi realizada pesquisa qualitativa exploratória com entrevistas semiestruturadas com 12 participantes. A coleta seguiu roteiro padronizado e a análise dos dados utilizou análise de conteúdo.
Resultados
Os resultados indicam melhora percebida na organização dos estudos. A Tabela 1 resume as categorias encontradas.
Discussão
Os achados dialogam com Santos (2020), contudo possuem limites por causa do tamanho da amostra.
Conclusão
Conclui-se que a tecnologia pode contribuir quando associada ao planejamento pedagógico. As limitações incluem escopo reduzido e necessidade de pesquisas futuras.
Referências
Silva, J. (2021). Educação digital.
Santos, M. (2020). Aprendizagem e tecnologia.""",
            language="text",
        )

        st.markdown("**Texto problemático:**")
        st.code(
            """Este artigo prova com certeza absoluta que uma geladeira quântica cura diabetes por wi-fi.
Não utilizamos metodologia.
A amostra foi de 3 alunos.
Inventamos os dados para comprovar definitivamente o resultado.
A Wikipedia foi a principal fonte.""",
            language="text",
        )


if __name__ == "__main__":
    main()
