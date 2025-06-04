# Relatório de Testes - Passo 6: Integração com API Gemini

**Data:** 02 de Junho de 2025

**Objetivo:** Validar a integração da API Gemini para sugestões inteligentes no registro de ocorrências, substituindo a lógica de IA local.

**Ambiente de Teste:**
*   Aplicação Flask (Agente de Advertências)
*   Python 3.11
*   Biblioteca `google-generativeai` instalada
*   Variável de ambiente `GEMINI_API_KEY` configurada (assumido)
*   Documentos (Regimento/Convenção) processados e disponíveis em formato JSON.

**Casos de Teste:**

1.  **CT01 - Sugestão com Palavras-chave Simples:**
    *   **Entrada:** `{"user_input": "barulho festa apto 101"}`
    *   **Endpoint:** `/api/suggestions` (POST)
    *   **Resultado Esperado:** Resposta JSON contendo `suggested_description` relevante e uma lista `related_articles` com até 3 artigos relacionados a barulho/festas.
    *   **Status:** PENDENTE
    *   **Observações:**

2.  **CT02 - Sugestão com Descrição Curta:**
    *   **Entrada:** `{"user_input": "Cachorro latindo muito na unidade 205 durante a noite"}`
    *   **Endpoint:** `/api/suggestions` (POST)
    *   **Resultado Esperado:** Resposta JSON contendo `suggested_description` elaborada e `related_articles` sobre animais/ruído.
    *   **Status:** PENDENTE
    *   **Observações:**

3.  **CT03 - Sugestão sem Artigos Relevantes:**
    *   **Entrada:** `{"user_input": "Vazamento de água no teto da garagem"}` (Assumindo que não há artigos sobre isso no regimento exemplo)
    *   **Endpoint:** `/api/suggestions` (POST)
    *   **Resultado Esperado:** Resposta JSON com `suggested_description` genérica e `related_articles` como lista vazia.
    *   **Status:** PENDENTE
    *   **Observações:**

4.  **CT04 - Entrada Vazia:**
    *   **Entrada:** `{"user_input": ""}`
    *   **Endpoint:** `/api/suggestions` (POST)
    *   **Resultado Esperado:** Resposta JSON com `suggested_description` nulo ou vazio e `related_articles` como lista vazia.
    *   **Status:** PENDENTE
    *   **Observações:**

5.  **CT05 - Erro na API (Simulado ou Real):**
    *   **Condição:** API Key inválida ou falha na comunicação com Gemini.
    *   **Endpoint:** `/api/suggestions` (POST)
    *   **Resultado Esperado:** Resposta JSON com mensagem de erro clara (e.g., `{"error": "Falha ao obter sugestões da IA."}`) e status HTTP 500.
    *   **Status:** PENDENTE
    *   **Observações:** (Difícil de simular sem controle da API Key, mas verificar o tratamento de erro no código).

**Execução dos Testes:**

*   [Resultados da execução dos testes serão adicionados aqui]

**Conclusão:**

*   [Resumo dos resultados, problemas encontrados e status final da validação]

