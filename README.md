Comando para Extensões:

pip install -r agente_advertencias/backend/requirements.txt

Caso necessario atualizar pip:
python.exe -m pip install --upgrade pip

Funcionalidades

Autenticação de Usuários:
Registro de usuários com nome de usuário, e-mail e senha.
Criptografia segura de senhas.
Funcionalidade de login e logout de usuários.
Gerenciamento de sessão para usuários autenticados.

Gerenciamento de Ocorrências:
Registro de novas ocorrências com título, descrição detalhada e número da unidade.
Visualização de uma lista de todas as ocorrências registradas, paginada para fácil navegação.
Visualização dos detalhes de ocorrências individuais.
As ocorrências incluem acompanhamento de status (por exemplo, "Registrada", "Em Análise", "Notificado", "Multado", "Resolvido").

Geração de PDF:
Geração de avisos formais de advertência em formato PDF para ocorrências específicas.
Os PDFs incluem detalhes da ocorrência, data, unidade envolvida e uma mensagem formal de advertência.

Integração com Banco de Dados:
Utiliza SQLite como banco de dados para armazenar dados de usuários e ocorrências.
Utiliza Flask-SQLAlchemy para ORM (Mapeamento Objeto-Relacional).

Tecnologias Utilizadas
Backend: Python, Flask
Banco de Dados: SQLite
Geração de PDF: FPDF
Formulários: Flask-WTF, WTForms
Gerenciamento de Usuários: Flask-Login
Frontend: HTML, Bootstrap

Instalação e Configuração
Pré-requisitos
Python 3.x
pip (gerenciador de pacotes Python)
