# Lista de Tarefas: Agente de Advertências para Condomínio

## Fase 1: MVP (Produto Mínimo Viável) - Concluído

- [X] **Planejar MVP do agente de advertências.**
- [X] **Configurar ambiente de desenvolvimento.**
- [X] **Desenvolver backend inicial: autenticação e cadastro de ocorrências.**
- [X] **Desenvolver frontend básico para registro e visualização.**
- [X] **Implementar geração de PDF para advertências.**
- [X] **Testar fluxo básico e documentar.**
- [X] **Reportar progresso e entregar versão MVP ao usuário.**

## Fase 2: Inteligência e Multimídia - Funcionalidades de Base Concluídas

- [X] **001: Analisar requisitos para inteligência e multimídia.**
    - [X] Interpretação do Regimento Interno:
        - [X] Formato de entrada: PDF.
        - [X] Extensão: 12-51 páginas.
        - [X] Saída esperada: Número do artigo e detalhamento do texto do artigo.
    - [X] Detalhamento Automático de Ocorrências:
        - [X] Input básico: Palavras-chave.
        - [X] Detalhamento esperado: O mais completo possível (descrição, classificação, data/hora).
    - [X] Suporte a Imagens:
        - [X] Limite: Sem limite.
        - [X] Inclusão no PDF de advertência: Sim.
- [X] **002: Pesquisar e estruturar leitura do regimento e classificação de infrações.**
    - [X] Pesquisar e testar ferramentas para extração de texto de PDF (priorizar `poppler-utils`).
    - [X] Definir estratégia para identificar e estruturar artigos e seus conteúdos a partir do texto extraído.
    - [X] Projetar um mecanismo para que o sistema possa "consultar" o regimento processado para encontrar artigos relevantes com base em palavras-chave ou descrição da infração.
    - [X] Criar um protótipo para extrair e consultar o regimento.
- [X] **003: Projetar detalhamento automático de ocorrências.**
    - [X] Pesquisar técnicas para expandir palavras-chave em descrições mais completas (ex: templates, IA generativa simples).
    - [X] Definir como o sistema classificará o tipo de infração com base nas palavras-chave e/ou consulta ao regimento.
    - [X] Explorar como o sistema poderia inferir data/hora (se não fornecida explicitamente).
    - [X] Desenvolver um protótipo para o detalhamento automático.
    - [X] Corrigir e validar protótipo de detalhamento automático.
- [X] **004: Adicionar funcionalidade de upload e visualização de imagens.**
    - [X] Modificar o modelo de dados `Occurrence` para armazenar referências a imagens.
    - [X] Implementar o upload de múltiplas imagens no formulário de ocorrência.
    - [X] Desenvolver a lógica para salvar as imagens no servidor (ou serviço de armazenamento).
    - [X] Exibir as imagens na página de visualização da ocorrência.
    - [X] Modificar a geração de PDF para incluir as imagens anexadas.
- [X] **005: Integrar novas funcionalidades de imagem ao fluxo existente.** (Considerado parte da etapa 004 e 006 da Fase 2)
- [X] **006: Ajustar templates para exibir imagens em ocorrências.** (Considerado parte da etapa 004 e 005 da Fase 2)
- [X] **007: Testar e documentar novas capacidades (imagens e protótipos de IA).**
- [X] **008: Apresentar resultados e próximos passos ao usuário.**

## Fase 3: Integração de Inteligência na Aplicação Principal

- [X] **001: Analisar requisitos detalhados para integração das funcionalidades inteligentes.**
    - [X] Definir como o regimento interno (PDF) e convenção (PDF) serão carregados e gerenciados no sistema (área administrativa, upload único/substituível para cada tipo).
    - [X] Especificar como o processamento do PDF (extração de artigos) será disparado (automaticamente no upload).
    - [X] Detalhar a interação do usuário com a consulta ao regimento e detalhamento automático no formulário de nova ocorrência (campo de palavras-chave e, futuramente, análise de texto; sugestões para basear-se, não preenchimento automático).
    - [X] Avaliar a necessidade de uma interface para consulta/pesquisa avulsa do regimento/convenção carregados (confirmado como útil).
- [ ] **002: Implementar interface para upload e gerenciamento do regimento interno.**
    - [ ] Criar rota e template para upload do arquivo PDF do regimento.
    - [ ] Implementar lógica para salvar o arquivo PDF no servidor.
    - [ ] Implementar lógica para processar o PDF (usando `pdftotext` e o script `parse_regimento.py` adaptado) e armazenar os artigos de forma estruturada (ex: em um arquivo JSON ou no banco de dados).
- [ ] **003: Integrar consulta automática ao regimento no formulário de ocorrência.**
    - [ ] Modificar o formulário de nova ocorrência para incluir campos ou gatilhos para a consulta inteligente.
    - [ ] Implementar a lógica no backend para receber as palavras-chave (ou texto) e usar o script `detalhamento_automatico_prototipo.py` (adaptado) para buscar no regimento processado.
- [ ] **004: Integrar sugestão automática de descrição e artigo no registro de ocorrência.**
    - [ ] Apresentar as sugestões (descrição, artigo infringido) de forma clara na interface do formulário.
    - [ ] Permitir que o usuário aceite, edite ou ignore as sugestões antes de salvar a ocorrência.
- [ ] **005: Testar e documentar fluxo com inteligência integrada.**
    - [ ] Realizar testes completos do novo fluxo: upload do regimento, registro de ocorrência com consulta inteligente, visualização das sugestões.
    - [ ] Atualizar o `README.md` e a documentação interna.
- [ ] **006: Apresentar resultados e coletar feedback do usuário.**
    - [ ] Demonstrar a aplicação com as funcionalidades de inteligência integradas.
    - [ ] Coletar feedback para ajustes e próximos passos.
