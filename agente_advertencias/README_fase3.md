# Agente de Advertências Condominial - Fase 3 (Inteligência Integrada)

Este documento descreve a implementação da Fase 3 do Agente de Advertências Condominial, que integra funcionalidades inteligentes à aplicação principal.

## Novas Funcionalidades Implementadas

### 1. Gerenciamento de Documentos do Condomínio
- **Upload de Documentos**: Interface administrativa para carregar o Regimento Interno e a Convenção Condominial em formato PDF.
- **Processamento Automático**: Extração automática dos artigos dos documentos carregados.
- **Visualização de Status**: Painel que mostra o status atual dos documentos carregados e processados.

### 2. Consulta Inteligente ao Registrar Ocorrências
- **Campo de Palavras-chave**: Ao registrar uma nova ocorrência, o usuário pode inserir palavras-chave para consultar o regimento/convenção.
- **Exibição de Artigos Relevantes**: O sistema busca e exibe os artigos mais relevantes com base nas palavras-chave.
- **Sugestão de Descrição**: Geração automática de uma descrição detalhada para a ocorrência, baseada nas palavras-chave e nos artigos encontrados.

## Como Utilizar as Novas Funcionalidades

### Gerenciamento de Documentos
1. Faça login no sistema.
2. No menu superior, clique em "Administração" > "Gerenciar Documentos".
3. Na página de gerenciamento, você verá duas seções: uma para o Regimento Interno e outra para a Convenção Condominial.
4. Para cada documento, você pode:
   - Ver o status atual (se está carregado e processado)
   - Carregar um novo arquivo PDF (que substituirá o anterior, se existir)
5. Após o upload, o sistema processará automaticamente o documento para extrair os artigos.

### Registro de Ocorrências com Consulta Inteligente
1. Faça login e clique em "Nova Ocorrência".
2. No formulário, você verá um novo campo "Palavras-chave para Consulta".
3. Digite palavras-chave relacionadas à ocorrência (ex: "barulho festa apartamento 101").
4. Clique no botão "Consultar" ao lado do campo.
5. O sistema exibirá:
   - Artigos relevantes encontrados no regimento/convenção
   - Uma sugestão de descrição detalhada para a ocorrência
6. Você pode clicar em "Usar esta sugestão" para preencher automaticamente os campos de título e descrição com base na sugestão.
7. Complete o restante do formulário normalmente e clique em "Registrar Ocorrência".

## Fluxo Completo de Uso

### Preparação (Administrador)
1. Carregar o Regimento Interno e a Convenção Condominial na área administrativa.
2. Verificar se os documentos foram processados corretamente.

### Registro de Ocorrências (Usuário)
1. Ao identificar uma infração, acessar o formulário de nova ocorrência.
2. Inserir palavras-chave descritivas da situação.
3. Consultar o regimento/convenção através do botão "Consultar".
4. Revisar os artigos encontrados e a sugestão de descrição.
5. Usar a sugestão ou adaptar conforme necessário.
6. Adicionar o número da unidade e anexar imagens, se disponíveis.
7. Registrar a ocorrência.
8. Gerar o PDF de advertência, que agora incluirá referências aos artigos relevantes.

## Detalhes Técnicos

### Processamento de Documentos
- Os documentos PDF são convertidos para texto usando a ferramenta `pdftotext`.
- Um algoritmo de análise de texto identifica os artigos com base em padrões como "Artigo X:".
- Os artigos extraídos são armazenados em formato JSON para consulta rápida.

### Consulta Inteligente
- As palavras-chave são comparadas com o conteúdo dos artigos para determinar relevância.
- Um algoritmo de pontuação classifica os artigos mais relevantes para as palavras-chave fornecidas.
- A sugestão de descrição é gerada combinando:
  - Informações extraídas das palavras-chave (ex: número da unidade, tipo de infração)
  - Referências aos artigos relevantes encontrados
  - Um template estruturado para garantir clareza e completude

## Limitações Atuais e Próximos Passos

### Limitações
- A extração de artigos depende da formatação do PDF; documentos mal formatados podem não ser processados corretamente.
- A consulta inteligente funciona melhor com palavras-chave específicas e diretas.
- A sugestão de descrição é baseada em templates e pode precisar de ajustes manuais para casos específicos.

### Próximos Passos Possíveis
- Melhorar o algoritmo de extração de artigos para lidar com diferentes formatos de documentos.
- Implementar análise de texto mais avançada para entender melhor o contexto das palavras-chave.
- Adicionar funcionalidade de consulta avulsa ao regimento/convenção, independente do registro de ocorrências.
- Integrar envio automático de e-mails com as advertências geradas.

## Conclusão

A integração das funcionalidades inteligentes ao Agente de Advertências Condominial representa um avanço significativo na eficiência e precisão do processo de registro e gestão de ocorrências. Ao automatizar a consulta ao regimento e a geração de descrições detalhadas, o sistema reduz o tempo necessário para registrar ocorrências e aumenta a conformidade com as normas do condomínio.
