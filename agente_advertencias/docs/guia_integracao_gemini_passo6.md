# Guia de Uso e Integração - Agente de Advertências com IA Gemini (Passo 6)

**Data:** 02 de Junho de 2025

**Versão:** 6.0

## Introdução

Este documento descreve as alterações realizadas no Agente de Advertências Condominial para integrar a inteligência artificial com a API do Google Gemini, substituindo a lógica de IA local anterior. O objetivo é fornecer sugestões mais sofisticadas e contextualizadas durante o registro de ocorrências.

## Principais Alterações

1.  **Substituição da IA Local:** O módulo `smart_suggestions.py` foi completamente refatorado para utilizar a API do Gemini (`google-generativeai`). A lógica anterior baseada em FuzzyWuzzy e regras locais foi removida.
2.  **Novo Campo no Formulário:** O formulário de registro de ocorrência (`add_occurrence.html`) agora possui um campo "Descreva a ocorrência ou use palavras-chave para obter sugestões da IA" (`ai_input`).
3.  **Endpoint de API para Sugestões:** Uma nova rota `/api/suggestions` (POST) foi criada em `app.py` para receber o input do usuário e retornar as sugestões geradas pelo Gemini.
4.  **Interação Assíncrona:** A interface do formulário foi adaptada (via JavaScript básico em `add_occurrence.html`) para chamar a API `/api/suggestions` quando o usuário digita no campo `ai_input` e exibir as sugestões (descrição e artigos) dinamicamente abaixo do campo.
5.  **Configuração via Variável de Ambiente:** A autenticação com a API Gemini requer uma chave de API, que **deve** ser configurada como uma variável de ambiente chamada `GEMINI_API_KEY` no servidor onde a aplicação Flask será executada.

## Como Configurar e Executar

1.  **Obtenha sua Chave de API Gemini:** Crie ou utilize sua chave de API do Google AI Studio ou Google Cloud Console.
2.  **Configure a Variável de Ambiente:**
    *   No terminal onde você executará a aplicação Flask, defina a variável de ambiente. Exemplo (Linux/macOS):
        ```bash
        export GEMINI_API_KEY="SUA_CHAVE_DE_API_AQUI"
        ```
    *   **Importante:** Substitua `"SUA_CHAVE_DE_API_AQUI"` pela sua chave real. **Nunca coloque a chave diretamente no código.**
3.  **Instale as Dependências:** Certifique-se de que todas as dependências, incluindo `google-generativeai`, estão instaladas no ambiente virtual:
    ```bash
    source venv/bin/activate # Ou o comando equivalente no Windows
    pip install -r requirements.txt # Certifique-se que requirements.txt inclui google-generativeai
    ```
    *(Nota: A biblioteca foi instalada anteriormente, mas é bom garantir que o `requirements.txt` esteja atualizado se for implantar em outro lugar)*
4.  **Carregue os Documentos:** Use a interface administrativa (`/admin/documents`) para carregar os arquivos PDF do Regimento Interno e da Convenção Condominial. O sistema os processará automaticamente para fornecer contexto à IA.
5.  **Execute a Aplicação:**
    ```bash
    python app.py
    ```

## Como Usar a Nova Funcionalidade de Sugestões

1.  Acesse a página de registro de nova ocorrência (`/occurrence/new`).
2.  No campo "Descreva a ocorrência ou use palavras-chave...", digite informações sobre a ocorrência (ex: "barulho apto 301", "lixo corredor", "cachorro solto na piscina").
3.  Aguarde alguns instantes. O sistema enviará seu texto para a API Gemini em segundo plano.
4.  Abaixo do campo de texto, aparecerão as sugestões:
    *   **Descrição Sugerida:** Um texto que você pode usar como base para o campo "Descrição Detalhada".
    *   **Artigos Relevantes:** Uma lista de até 3 artigos do Regimento ou Convenção que o Gemini considerou mais relevantes, com o texto completo para consulta.
5.  Utilize as sugestões para preencher os campos "Título da Ocorrência" e "Descrição Detalhada" de forma mais completa e embasada.
6.  Preencha os demais campos e registre a ocorrência normalmente.

## Considerações Importantes

*   **Latência:** A resposta da API Gemini pode levar alguns segundos. A interface exibirá uma mensagem "Buscando sugestões..." durante esse período.
*   **Custos:** O uso da API Gemini pode estar sujeito a custos dependendo do volume de uso e do modelo escolhido. Consulte a tabela de preços do Google AI.
*   **Qualidade das Sugestões:** A qualidade depende da clareza do seu input, da qualidade dos documentos carregados e da capacidade do modelo Gemini. Pode haver casos em que as sugestões não sejam perfeitas.
*   **Erros:** Se houver falha na comunicação com a API ou erro no processamento, uma mensagem de erro será exibida na área de sugestões.
*   **Privacidade:** O texto que você digita no campo `ai_input` é enviado para a API do Google para processamento. Consulte a política de privacidade do Google AI.

## Próximos Passos (Sugestões)

*   Aprimorar os prompts enviados ao Gemini para resultados ainda melhores.
*   Implementar um cache para sugestões comuns.
*   Adicionar mais opções de modelos Gemini.
*   Integrar a IA em outras partes do sistema (ex: análise de relatórios).

