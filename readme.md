# Agente de Revisão de Artigos

Este projeto é um Sistema Especialista Baseado em Regras projetado para auditar a conformidade metodológica de ártigos científicos. A aplicação opera de forma totalmente local e determinística, processando os dados textuais através de uma arquitetura de regras de produção e encadeamento para frente.

## Como Funciona

1. **Ingestão:** O sistema extrai o texto de arquivos PDF ou recebe digitacao manual.
2. **Normalização:** O texto é limpo, removendo quebras de linha abruptas e espacos duplos para evitar falhas de leitura.
3. **Auditoria:** O motor varre o texto dividindo-o em sentenças e buscando conceitos correlacionados na mesma frase.
4. **Inferência:** Regras compostas são aplicadas para gerar diagnósticos de alto nível e calcular o score de rigor acadêmico.

## Requisitos do Sistema

* Python 3.11 ou superior
* Streamlit
* PyPDF

## Como Instalar e Executar

1. Instale as dependências necessarias atraves do terminal:

python -m pip install streamlit pypdf

2. Execute a aplicação com o seguinte comando:

python -m streamlit run app.py

3. Abra o endereço local indicado no seu navegador, faça o upload do PDF do seu artigo e clique em iniciar a auditoria.