# Agente de Advertências Condominial - Fase 2 (MVP + Imagens)

Este documento descreve o estado atual do Agente de Advertências Condominial, que agora inclui as funcionalidades do MVP e a capacidade de anexar e visualizar imagens nas ocorrências.

## Funcionalidades Implementadas:

### Funcionalidades do MVP (Já Entregues):

1.  **Autenticação de Usuários:**
    *   Registro de novos usuários (síndicos/administração).
    *   Login e Logout de usuários.
2.  **Gestão de Ocorrências (Texto):**
    *   Cadastro de novas ocorrências (título, descrição, número da unidade).
    *   Listagem das ocorrências registradas pelo usuário logado (com paginação).
    *   Visualização detalhada de uma ocorrência específica.
3.  **Geração de Advertência em PDF (Texto):**
    *   Geração de um documento PDF formal de advertência para uma ocorrência selecionada.
    *   O PDF inclui detalhes da ocorrência (título, data, unidade, descrição) e um texto padrão de advertência.
    *   O PDF pode ser baixado pelo usuário.

### Novas Funcionalidades (Fase 2 - Parcialmente Implementadas):

1.  **Upload e Visualização de Imagens em Ocorrências:**
    *   **Upload:** Ao registrar uma nova ocorrência, o usuário pode anexar múltiplos arquivos de imagem (formatos permitidos: png, jpg, jpeg, gif).
    *   **Armazenamento:** As imagens são salvas em uma pasta `uploads` no servidor.
    *   **Visualização:** As imagens anexadas são exibidas na página de visualização detalhada da ocorrência.
    *   **Inclusão no PDF:** As imagens anexadas à ocorrência agora são incluídas no final do documento PDF de advertência gerado.

2.  **Protótipos para Inteligência (Desenvolvidos Separadamente - Não Integrados à Interface Principal Ainda):**
    *   **Leitura e Estruturação de Regimento Interno:** Foi desenvolvido um script (`parse_regimento.py`) capaz de ler um arquivo de texto (convertido de PDF) de um regimento e extrair seus artigos.
    *   **Detalhamento Automático de Ocorrências:** Foi criado um protótipo (`detalhamento_automatico_prototipo.py`) que, com base em palavras-chave e nos artigos extraídos do regimento, sugere um título, uma descrição mais detalhada para a ocorrência e o artigo do regimento potencialmente infringido.
    *   *Observação: Estas funcionalidades de inteligência são protótipos e ainda precisam ser integradas à aplicação Flask principal e à interface do usuário.*

## Configuração e Execução

O projeto foi desenvolvido utilizando Flask (Python).

### Pré-requisitos:

*   Python 3.11
*   Ambiente virtual (venv)
*   Utilitário `pdftotext` (parte do `poppler-utils`) se for testar a extração de texto de PDFs para os protótipos de inteligência.

### Passos para Execução da Aplicação Principal (com Upload de Imagens):

1.  **Clonar o repositório (ou descompactar os arquivos em um diretório, por exemplo, `/home/ubuntu/agente_advertencias`).**

2.  **Navegar até o diretório backend:**
    ```bash
    cd /home/ubuntu/agente_advertencias/backend
    ```

3.  **Criar e ativar o ambiente virtual (se ainda não foi feito):
    ```bash
    python3.11 -m venv venv
    source venv/bin/activate
    ```

4.  **Instalar as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
    O arquivo `requirements.txt` contém:
    ```
    Flask
    Flask-SQLAlchemy
    Flask-Login
    Flask-WTF
    email-validator
    fpdf2
    ```

5.  **Executar a aplicação Flask:**
    ```bash
    python app.py
    ```
    A aplicação estará rodando em `http://0.0.0.0:5000/`. Você pode acessá-la através do seu navegador.
    A pasta `uploads` será criada automaticamente dentro de `backend` se não existir.

6.  **Acesso e Teste:**
    *   Acesse `http://localhost:5000/` no seu navegador.
    *   **Registro/Login:** Crie uma conta ou faça login.
    *   **Nova Ocorrência:** Ao registrar uma nova ocorrência, você verá um campo para anexar imagens.
    *   **Minhas Ocorrências/Ver Ocorrência:** As imagens anexadas serão exibidas nos detalhes da ocorrência.
    *   **Gerar PDF:** O PDF de advertência agora incluirá as imagens anexadas.

## Estrutura do Projeto (Backend):

```
/home/ubuntu/agente_advertencias/
├── backend/
│   ├── app.py             # Arquivo principal da aplicação Flask
│   ├── requirements.txt   # Dependências Python
│   ├── site.db            # Banco de dados SQLite
│   ├── static/            # Arquivos estáticos (CSS, JS)
│   ├── templates/         # Templates HTML
│   │   ├── ... (arquivos html)
│   └── uploads/           # Pasta para armazenar imagens de ocorrências
│   └── venv/                # Ambiente virtual Python
├── parse_regimento.py     # Protótipo: Script para extrair artigos do regimento
├── detalhamento_automatico_prototipo.py # Protótipo: Script para sugerir detalhamento
├── regimento_exemplo.md   # Exemplo de regimento em Markdown
└── regimento_exemplo.pdf  # Exemplo de regimento em PDF (gerado do .md)
└── regimento_exemplo.txt  # Exemplo de regimento em TXT (extraído do .pdf)
```

## Observações sobre esta Fase:

*   **Protótipos de Inteligência:** As funcionalidades de leitura de regimento e detalhamento automático são protótipos funcionais, mas ainda não estão integradas na interface web do `app.py`. A integração será um próximo passo.
*   **Envio de E-mail:** Continua não implementado.
*   **Segurança e Validações:** Para um ambiente de produção, seriam necessárias mais validações de segurança no upload de arquivos e outras áreas.

Este documento serve como um guia para testar as funcionalidades implementadas até o momento.
