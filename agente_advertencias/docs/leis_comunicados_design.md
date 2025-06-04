# Design da Integração com Leis Vigentes e Sistema de Comunicados

## Parte 1: Integração com Leis Vigentes

### Visão Geral

A integração com leis vigentes ampliará o algoritmo de inteligência do Agente de Advertências para incluir referências a legislações aplicáveis, complementando as regras internas do condomínio (regimento e convenção). Isso proporcionará maior embasamento legal para as advertências e auxiliará na compreensão das implicações legais das infrações.

### Requisitos Funcionais

1. **Base de Dados de Legislação**
   - Cadastro e manutenção de leis relevantes para condomínios
   - Categorização por tema (barulho, obras, animais, etc.)
   - Versionamento para acompanhar atualizações legislativas

2. **Correlação com Regimento/Convenção**
   - Mapeamento entre artigos do regimento/convenção e leis aplicáveis
   - Identificação automática de leis relevantes para uma infração
   - Sugestão de referências legais ao registrar ocorrências

3. **Consulta e Visualização**
   - Busca específica de leis por tema ou palavra-chave
   - Exibição contextualizada da legislação
   - Links para fontes oficiais das leis

4. **Integração com Advertências**
   - Inclusão automática de referências legais nas advertências
   - Explicação simplificada das implicações legais
   - Diferenciação visual entre regras internas e legislação

### Arquitetura da Solução

#### Modelo de Dados

**Tabela Law**
- id (PK)
- title (título da lei)
- number (número/identificador da lei)
- jurisdiction (municipal, estadual, federal)
- category (categoria temática)
- summary (resumo em linguagem simples)
- full_text (texto completo ou trecho relevante)
- official_link (link para fonte oficial)
- effective_date (data de vigência)
- is_active (status de vigência)
- created_at
- updated_at

**Tabela LawArticle**
- id (PK)
- law_id (FK para Law)
- article_number
- content (texto do artigo)
- summary (resumo simplificado)

**Tabela RegulationLawMapping**
- id (PK)
- document_type (regimento ou convenção)
- article_reference (referência ao artigo do documento)
- law_article_id (FK para LawArticle)
- relevance_score (pontuação de relevância)
- notes (observações sobre a correlação)

#### Algoritmo de Correlação

1. **Análise Textual**
   - Processamento de linguagem natural para identificar temas
   - Extração de entidades e conceitos-chave
   - Correspondência semântica entre infrações e legislação

2. **Sistema de Pontuação**
   - Cálculo de relevância baseado em similaridade textual
   - Ponderação por jurisdição e especificidade
   - Ajuste baseado em feedback de uso

3. **Aprendizado Incremental**
   - Refinamento das correlações com base em seleções anteriores
   - Adaptação a novas leis ou atualizações
   - Sugestões personalizadas por tipo de condomínio

### Interface de Usuário

1. **Cadastro e Gestão de Leis**
   - Formulário para adição manual de leis
   - Opção para importação em lote (CSV/JSON)
   - Interface de edição e atualização

2. **Visualização de Correlações**
   - Matriz de mapeamento entre regimento/convenção e leis
   - Visualização gráfica de relações
   - Ferramentas de filtro e ordenação

3. **Integração no Fluxo de Ocorrências**
   - Exibição de leis sugeridas durante registro de ocorrências
   - Opção para incluir/excluir referências legais
   - Prévia da advertência com referências legais

## Parte 2: Sistema de Elaboração de Comunicados

### Visão Geral

O sistema de elaboração de comunicados permitirá a criação, gestão e distribuição de comunicados oficiais do condomínio para os condôminos. Esta funcionalidade complementará o sistema de advertências, oferecendo um canal formal para informações gerais, avisos e notificações não punitivas.

### Requisitos Funcionais

1. **Criação de Comunicados**
   - Editor de texto rico para formatação
   - Suporte a modelos pré-definidos
   - Inclusão de imagens e anexos
   - Agendamento de publicação

2. **Categorização e Organização**
   - Classificação por tipo (aviso, informativo, convocação)
   - Definição de prioridade e visibilidade
   - Organização por data e tema
   - Tags para facilitar busca

3. **Distribuição Multicanal**
   - Envio por e-mail (individual ou em massa)
   - Geração de versão para impressão/mural
   - Armazenamento em repositório digital acessível
   - Confirmação de recebimento (opcional)

4. **Gestão e Histórico**
   - Registro completo de comunicados enviados
   - Estatísticas de visualização/confirmação
   - Versionamento de comunicados
   - Arquivamento automático

### Arquitetura da Solução

#### Modelo de Dados

**Tabela Announcement**
- id (PK)
- title
- content_html
- content_text
- category
- priority (baixa, média, alta)
- status (rascunho, agendado, publicado, arquivado)
- created_by (FK para User)
- created_at
- published_at
- expires_at

**Tabela AnnouncementAttachment**
- id (PK)
- announcement_id (FK para Announcement)
- file_name
- file_path
- file_type
- file_size
- created_at

**Tabela AnnouncementDistribution**
- id (PK)
- announcement_id (FK para Announcement)
- distribution_type (todos, unidades específicas, grupos)
- target_units (lista de unidades, se aplicável)
- target_group (grupo alvo, se aplicável)
- email_sent (boolean)
- email_sent_at
- print_generated (boolean)
- print_generated_at

**Tabela AnnouncementReceipt**
- id (PK)
- announcement_id (FK para Announcement)
- unit_number
- email (se enviado por e-mail)
- viewed (boolean)
- viewed_at
- confirmed (boolean)
- confirmed_at

#### Fluxo de Trabalho

1. **Criação e Edição**
   - Iniciar novo comunicado (do zero ou de modelo)
   - Editar conteúdo com formatação
   - Adicionar anexos se necessário
   - Salvar como rascunho ou agendar publicação

2. **Revisão e Aprovação**
   - Visualização prévia do comunicado
   - Opção para revisão por outros usuários
   - Processo de aprovação (opcional)
   - Finalização para distribuição

3. **Distribuição**
   - Seleção de canais de distribuição
   - Definição de destinatários
   - Execução da distribuição (imediata ou agendada)
   - Confirmação de envio

4. **Acompanhamento**
   - Monitoramento de visualizações/confirmações
   - Reenvio para não visualizados (opcional)
   - Geração de relatórios de efetividade
   - Arquivamento após expiração

### Interface de Usuário

1. **Dashboard de Comunicados**
   - Visão geral de comunicados ativos
   - Indicadores de status e prioridade
   - Filtros por categoria, data, status
   - Ações rápidas (criar, editar, arquivar)

2. **Editor de Comunicados**
   - Interface WYSIWYG para edição
   - Biblioteca de modelos acessível
   - Ferramentas de formatação e mídia
   - Opções de salvamento e publicação

3. **Gestão de Distribuição**
   - Seleção de destinatários (individual, grupos, todos)
   - Configuração de canais (e-mail, impressão)
   - Agendamento de envio
   - Opções de notificação e lembretes

4. **Relatórios e Histórico**
   - Visualização cronológica de comunicados
   - Estatísticas de engajamento
   - Filtros avançados para busca
   - Exportação de dados e relatórios

## Implementação Técnica

### Tecnologias Recomendadas

- **Backend**: Flask (já utilizado no projeto)
- **Banco de Dados**: SQLite/PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript (Bootstrap, CKEditor para edição de texto)
- **Processamento de Texto**: Python-Markdown, BeautifulSoup
- **E-mail**: Flask-Mail
- **PDF**: WeasyPrint/FPDF2 (já utilizado)

### Segurança e Conformidade

- Validação de entrada para prevenir injeção
- Sanitização de HTML em comunicados
- Controle de acesso baseado em perfil
- Conformidade com LGPD para dados pessoais
- Registro de auditoria para ações críticas

## Plano de Implementação

### Fase 1: Estrutura Básica
- Implementar modelos de dados para leis e comunicados
- Criar interfaces administrativas básicas
- Desenvolver funcionalidades core sem integração

### Fase 2: Algoritmos e Inteligência
- Implementar correlação entre regimento e leis
- Desenvolver sistema de sugestão de leis
- Criar templates inteligentes para comunicados

### Fase 3: Integração e Distribuição
- Integrar leis no fluxo de advertências
- Implementar sistema de distribuição de comunicados
- Conectar com sistema de e-mail existente

### Fase 4: Refinamento e Testes
- Otimizar algoritmos de correlação
- Melhorar interface de usuário
- Realizar testes de usabilidade e ajustes

## Considerações Futuras

- Integração com sistemas jurídicos para atualizações automáticas de legislação
- Análise preditiva de conformidade legal
- Sistema de votação/feedback em comunicados
- Aplicativo móvel para notificações push de comunicados importantes
