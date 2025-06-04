# Design do Sistema de Envio de E-mails para Advertências

## Visão Geral

O sistema de envio de e-mails para advertências será responsável por enviar automaticamente as advertências geradas em PDF para os destinatários configurados. O sistema permitirá personalização do conteúdo do e-mail e configuração de destinatários específicos.

## Requisitos Funcionais

1. **Envio Automático**
   - Enviar e-mail automaticamente após a geração da advertência em PDF
   - Anexar o arquivo PDF da advertência ao e-mail
   - Registrar o status de envio no sistema

2. **Personalização de Conteúdo**
   - Permitir personalização do assunto do e-mail
   - Permitir personalização do corpo do e-mail
   - Suportar templates de e-mail com variáveis dinâmicas (ex: nome do condômino, número da unidade, data da ocorrência)

3. **Configuração de Destinatários**
   - Permitir configuração de destinatários principais (TO)
   - Permitir configuração de destinatários em cópia (CC)
   - Permitir configuração de destinatários em cópia oculta (BCC)
   - Associar e-mails a unidades/apartamentos específicos

4. **Gestão de Configurações**
   - Interface para configuração do servidor SMTP
   - Interface para gestão de templates de e-mail
   - Interface para gestão de destinatários

## Arquitetura Técnica

### Componentes Principais

1. **Módulo de Configuração de E-mail**
   - Armazenamento de configurações SMTP
   - Gestão de credenciais de e-mail
   - Validação de configurações

2. **Módulo de Templates**
   - Armazenamento de templates de e-mail
   - Sistema de substituição de variáveis
   - Validação de templates

3. **Módulo de Destinatários**
   - Banco de dados de destinatários
   - Associação entre unidades e e-mails
   - Validação de endereços de e-mail

4. **Serviço de Envio**
   - Integração com servidor SMTP
   - Tratamento de erros de envio
   - Registro de logs de envio

5. **Interface de Usuário**
   - Formulários de configuração
   - Visualização de histórico de envios
   - Testes de configuração

### Fluxo de Dados

1. Usuário gera uma advertência em PDF
2. Sistema identifica a unidade associada à advertência
3. Sistema busca os destinatários configurados para aquela unidade
4. Sistema carrega o template de e-mail configurado
5. Sistema substitui as variáveis do template com dados da advertência
6. Sistema anexa o PDF da advertência
7. Sistema envia o e-mail através do servidor SMTP configurado
8. Sistema registra o resultado do envio no banco de dados

## Modelo de Dados

### Tabela EmailConfig
- id (PK)
- smtp_server
- smtp_port
- smtp_username
- smtp_password (criptografado)
- use_tls
- default_sender
- created_at
- updated_at

### Tabela EmailTemplate
- id (PK)
- name
- subject
- body_html
- body_text
- is_default
- created_at
- updated_at

### Tabela UnitEmail
- id (PK)
- unit_number
- email
- recipient_name
- recipient_type (TO, CC, BCC)
- is_active
- created_at
- updated_at

### Tabela EmailLog
- id (PK)
- occurrence_id (FK)
- template_id (FK)
- sent_at
- status
- error_message
- recipient_list
- subject
- body_preview

## Interface de Usuário

### Telas Principais

1. **Configuração de SMTP**
   - Formulário para configuração do servidor SMTP
   - Botão para testar conexão
   - Indicador de status da configuração

2. **Gestão de Templates**
   - Lista de templates disponíveis
   - Editor de templates com suporte a HTML
   - Visualização prévia do template
   - Lista de variáveis disponíveis

3. **Gestão de Destinatários**
   - Formulário para adicionar/editar destinatários
   - Associação de e-mails a unidades
   - Importação em massa de e-mails (CSV)

4. **Histórico de Envios**
   - Lista de e-mails enviados
   - Filtros por data, status, unidade
   - Detalhes do envio (destinatários, assunto, corpo)
   - Opção para reenvio manual

## Implementação Técnica

### Tecnologias

- Flask-Mail para integração com SMTP
- SQLAlchemy para modelo de dados
- Jinja2 para templates de e-mail
- Bootstrap para interface de usuário

### Segurança

- Criptografia de credenciais SMTP
- Validação de endereços de e-mail
- Proteção contra injeção de código em templates
- Limitação de taxa de envio para evitar spam

## Plano de Implementação

1. **Fase 1: Configuração Básica**
   - Implementar modelo de dados
   - Criar interface de configuração SMTP
   - Implementar teste de conexão

2. **Fase 2: Templates e Destinatários**
   - Implementar gestão de templates
   - Implementar gestão de destinatários
   - Criar associação entre unidades e e-mails

3. **Fase 3: Integração com Advertências**
   - Conectar geração de advertência com envio de e-mail
   - Implementar substituição de variáveis
   - Criar logs de envio

4. **Fase 4: Testes e Refinamentos**
   - Testar fluxo completo
   - Implementar tratamento de erros
   - Refinar interface de usuário

## Considerações Futuras

- Agendamento de envios (envio em horários específicos)
- Relatórios de entrega e abertura de e-mails
- Integração com serviços de e-mail transacional (SendGrid, Mailgun)
- Automação de follow-up para advertências não respondidas
