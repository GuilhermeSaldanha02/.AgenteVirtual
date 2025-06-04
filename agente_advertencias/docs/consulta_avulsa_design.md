# Design da Interface de Consulta Avulsa ao Regimento e Convenção

## Visão Geral

A interface de consulta avulsa ao regimento e convenção permitirá aos usuários pesquisar e visualizar artigos específicos dos documentos do condomínio, independentemente do processo de registro de ocorrências. O foco será em proporcionar buscas rápidas e eficientes, com uma visualização organizada dos resultados.

## Requisitos Funcionais

1. **Pesquisa Avançada**
   - Busca por palavras-chave em todo o conteúdo dos documentos
   - Filtro por tipo de documento (Regimento Interno, Convenção Condominial)
   - Busca específica por número de artigo
   - Histórico de pesquisas recentes

2. **Visualização de Resultados**
   - Exibição organizada dos artigos encontrados
   - Destaque (highlight) dos termos pesquisados nos resultados
   - Agrupamento por documento e relevância
   - Visualização do contexto do artigo (artigos anteriores/posteriores)

3. **Navegação nos Documentos**
   - Visualização da estrutura completa dos documentos (índice)
   - Navegação por capítulos/seções
   - Opção para visualizar o documento completo em formato original

4. **Funcionalidades Adicionais**
   - Favoritar artigos para acesso rápido
   - Compartilhar artigos específicos (via link ou e-mail)
   - Exportar seleção de artigos para PDF

## Arquitetura da Interface

### Componentes Principais

1. **Barra de Pesquisa**
   - Campo de entrada de texto para palavras-chave
   - Filtros dropdown para tipo de documento
   - Botões para opções avançadas de pesquisa
   - Sugestões automáticas durante a digitação

2. **Painel de Resultados**
   - Lista paginada de artigos encontrados
   - Indicadores visuais de relevância
   - Opções de ordenação (relevância, número do artigo)
   - Visualização compacta e expandida

3. **Visualizador de Artigos**
   - Exibição do texto completo do artigo selecionado
   - Navegação para artigos relacionados
   - Ferramentas de interação (favoritar, compartilhar)
   - Referências cruzadas a outros artigos ou leis

4. **Navegador de Estrutura**
   - Árvore de navegação por capítulos/seções
   - Indicadores visuais de localização atual
   - Opção para expandir/colapsar seções

## Layout da Interface

### Tela Principal

```
+-----------------------------------------------------------------------+
| AGENTE DE ADVERTÊNCIAS                                      [Usuário] |
+-----------------------------------------------------------------------+
| [Home] [Ocorrências] [Consulta de Documentos] [Admin]                 |
+-----------------------------------------------------------------------+
|                                                                       |
|  CONSULTA DE DOCUMENTOS                                               |
|                                                                       |
|  +-------------------------------------------------------------------+|
|  | Pesquisar:  [                                    ] [Buscar]      ||
|  | Filtros:    [Todos os documentos ▼] [Opções avançadas ▼]         ||
|  +-------------------------------------------------------------------+|
|                                                                       |
|  +------------------------+  +--------------------------------------+ |
|  | ESTRUTURA              |  | RESULTADOS                           | |
|  |                        |  |                                      | |
|  | ▶ Regimento Interno    |  | "barulho" - 5 resultados encontrados | |
|  |   ▶ Capítulo I         |  |                                      | |
|  |   ▶ Capítulo II        |  | [Regimento Interno] Artigo 15        | |
|  |   ▶ Capítulo III       |  | É proibido produzir ruídos e         | |
|  |                        |  | barulhos excessivos entre 22h e 8h.  | |
|  | ▶ Convenção            |  | [Ver completo]                       | |
|  |   ▶ Título I           |  |                                      | |
|  |   ▶ Título II          |  | [Convenção] Artigo 7                 | |
|  |                        |  | Os condôminos devem respeitar o      | |
|  |                        |  | sossego, evitando barulho...         | |
|  |                        |  | [Ver completo]                       | |
|  |                        |  |                                      | |
|  |                        |  | ...                                  | |
|  +------------------------+  +--------------------------------------+ |
|                                                                       |
+-----------------------------------------------------------------------+
```

### Visualização de Artigo

```
+-----------------------------------------------------------------------+
| AGENTE DE ADVERTÊNCIAS                                      [Usuário] |
+-----------------------------------------------------------------------+
| [Home] [Ocorrências] [Consulta de Documentos] [Admin]                 |
+-----------------------------------------------------------------------+
|                                                                       |
|  CONSULTA DE DOCUMENTOS > Regimento Interno > Artigo 15               |
|                                                                       |
|  +-------------------------------------------------------------------+|
|  | Pesquisar:  [barulho                           ] [Buscar]        ||
|  +-------------------------------------------------------------------+|
|                                                                       |
|  +------------------------+  +--------------------------------------+ |
|  | ESTRUTURA              |  | ARTIGO 15                            | |
|  |                        |  |                                      | |
|  | ▶ Regimento Interno    |  | É proibido produzir ruídos e         | |
|  |   ▶ Capítulo I         |  | barulhos excessivos entre 22h e 8h,  | |
|  |   ▶ Capítulo II        |  | bem como em qualquer horário que     | |
|  |     ▶ Artigo 14        |  | perturbe o sossego dos demais        | |
|  |     ▷ Artigo 15        |  | condôminos. Incluem-se nesta         | |
|  |     ▶ Artigo 16        |  | proibição sons de instrumentos       | |
|  |   ▶ Capítulo III       |  | musicais, aparelhos de som,          | |
|  |                        |  | televisores, festas e obras.         | |
|  | ▶ Convenção            |  |                                      | |
|  |                        |  | Referências:                         | |
|  |                        |  | - Lei do Silêncio Municipal nº 1234  | |
|  |                        |  | - Artigo 7 da Convenção Condominial  | |
|  |                        |  |                                      | |
|  |                        |  | [Favoritar] [Compartilhar] [PDF]     | |
|  +------------------------+  +--------------------------------------+ |
|                                                                       |
+-----------------------------------------------------------------------+
```

## Funcionalidades Detalhadas

### Algoritmo de Busca

1. **Indexação de Conteúdo**
   - Pré-processamento dos documentos para indexação
   - Tokenização e normalização de texto
   - Criação de índice invertido para busca rápida

2. **Relevância e Ranking**
   - Pontuação baseada em frequência de termos
   - Peso maior para correspondências em títulos de artigos
   - Consideração de proximidade entre múltiplos termos de busca

3. **Filtros Contextuais**
   - Filtro por tipo de documento
   - Filtro por capítulo/seção
   - Filtro por intervalo de artigos

### Visualização Contextual

1. **Navegação Hierárquica**
   - Exibição da estrutura completa do documento
   - Indicação visual da localização atual
   - Links rápidos para níveis superiores/inferiores

2. **Referências Cruzadas**
   - Identificação automática de referências a outros artigos
   - Links clicáveis para artigos referenciados
   - Exibição de tooltip com prévia do artigo referenciado

3. **Histórico e Favoritos**
   - Armazenamento local de histórico de pesquisas
   - Sistema de favoritos persistente por usuário
   - Sugestões baseadas em pesquisas frequentes

## Implementação Técnica

### Tecnologias

- Frontend: HTML5, CSS3, JavaScript (com possível uso de Vue.js ou React)
- Backend: Flask (já utilizado no projeto)
- Busca: Implementação de algoritmo de busca textual ou integração com Elasticsearch
- Armazenamento: SQLite (já utilizado) para metadados e favoritos

### Segurança

- Validação de entrada de pesquisa para prevenir injeção
- Controle de acesso baseado em perfil de usuário
- Sanitização de saída para exibição segura de conteúdo

## Plano de Implementação

1. **Fase 1: Estrutura Básica**
   - Criar modelo de dados para indexação de artigos
   - Implementar interface básica de pesquisa
   - Desenvolver visualização de resultados simples

2. **Fase 2: Algoritmo de Busca Avançada**
   - Implementar indexação e busca textual eficiente
   - Adicionar filtros e opções avançadas
   - Desenvolver sistema de ranking e relevância

3. **Fase 3: Visualização e Navegação**
   - Implementar visualizador de artigos completo
   - Desenvolver navegador de estrutura hierárquica
   - Adicionar referências cruzadas e contextualização

4. **Fase 4: Funcionalidades Adicionais**
   - Implementar sistema de favoritos
   - Adicionar compartilhamento de artigos
   - Desenvolver exportação para PDF

## Considerações Futuras

- Integração com sistema de notificações para atualizações em artigos favoritos
- Adição de anotações pessoais em artigos específicos
- Implementação de histórico de versões dos documentos
- Estatísticas de uso para identificar artigos mais consultados
