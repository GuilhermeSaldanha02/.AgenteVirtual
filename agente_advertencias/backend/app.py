# -*- coding: utf-8 -*-
import os
import io
import json
import subprocess
import logging # Adicionado para log
from flask import Flask, render_template, redirect, url_for, flash, request, send_file, send_from_directory, jsonify # Adicionado jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, MultipleFileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from fpdf import FPDF

# Importar a nova classe de sugestões
from smart_suggestions import SmartSuggestions

# --- Protótipo de Parse do Regimento (mantido por enquanto para processamento inicial) ---
import re
def parse_document_text(text_content):
    # ... (código da função parse_document_text mantido como antes)
    """Lê o conteúdo de texto de um documento e extrai os artigos."""
    articles = []
    current_article_text = []
    current_article_title = None

    for line in text_content.splitlines():
        line = line.strip()
        if not line:
            continue

        # Tenta identificar "Artigo X:" ou "Artigo X." ou "Art. X"
        match = re.match(r"^(Art(?:igo|\.)?\s*\d+[:\.\s])(.*)", line, re.IGNORECASE)
        if match:
            if current_article_title and current_article_text:
                articles.append({
                    "title": current_article_title.strip(),
                    "text": " ".join(current_article_text).strip()
                })
                current_article_text = []
            
            # Extrai apenas o "Artigo X" ou "Art. X"
            title_match = re.match(r"^(Art(?:igo|\.)?\s*\d+)", match.group(1).strip(), re.IGNORECASE)
            current_article_title = title_match.group(1) if title_match else match.group(1).strip()
            initial_text = match.group(2).strip()
            if initial_text:
                current_article_text.append(initial_text)
        elif current_article_title:
            # Evita adicionar linhas que parecem ser títulos de seções/capítulos
            if not re.match(r"^(Capítulo \d+[:\s])", line, re.IGNORECASE) and \
               not re.match(r"^(Título \w+)", line, re.IGNORECASE) and \
               not re.match(r"^(Seção \w+)", line, re.IGNORECASE):
                current_article_text.append(line)
            
    if current_article_title and current_article_text:
        articles.append({
            "title": current_article_title.strip(),
            "text": " ".join(current_article_text).strip()
        })
    
    # Criar um dicionário {numero_artigo: texto}
    articles_dict = {}
    for article in articles:
        num_match = re.search(r"\d+", article["title"])
        if num_match:
            articles_dict[num_match.group(0)] = article["text"]
            
    return articles_dict # Retorna dicionário
# --- Fim do Protótipo de Parse ---

# App Configuration
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "uma_chave_secreta_muito_forte_padrao")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "uploads" # Para imagens de ocorrências
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"} # Para imagens de ocorrências
app.config["DOCUMENTS_FOLDER"] = "documentos_condominio" # Para PDFs de Regimento/Convenção
app.config["PROCESSED_DOCS_FOLDER"] = "documentos_processados" # Para JSONs de artigos
app.config["ALLOWED_DOCUMENT_EXTENSIONS"] = {"pdf"}

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create folders if they don't exist
for folder_key in ["UPLOAD_FOLDER", "DOCUMENTS_FOLDER", "PROCESSED_DOCS_FOLDER"]:
    folder_path = app.config[folder_key]
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

# Instanciar a classe de sugestões (passando o diretório de documentos processados)
smart_suggestions = SmartSuggestions(app.config["PROCESSED_DOCS_FOLDER"])

# Helper functions for file extensions (mantidas como antes)
def allowed_image_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

def allowed_document_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_DOCUMENT_EXTENSIONS"]

# Database Models (User, Image, Occurrence - sem alterações)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    occurrences = db.relationship("Occurrence", backref="author", lazy=True)

    def __repr__(self):
        return f"User(\"{self.username}\", \"{self.email}\")"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    occurrence_id = db.Column(db.Integer, db.ForeignKey("occurrence.id"), nullable=False)

    def __repr__(self):
        return f"Image(\"{self.filename}\")"

class Occurrence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    unit_number = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Registrada") # Aumentado tamanho do status
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    images = db.relationship("Image", backref="occurrence", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"Occurrence(\"{self.title}\", \"{self.date_posted}\")"

# Forms (atualizar OccurrenceForm)
class RegistrationForm(FlaskForm):
    # ... (mantido como antes)
    username = StringField("Nome de Usuário", validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("Confirmar Senha", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Registrar")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Este nome de usuário já existe. Por favor, escolha outro.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Este email já está cadastrado. Por favor, escolha outro.")

class LoginForm(FlaskForm):
    # ... (mantido como antes)
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Senha", validators=[DataRequired()])
    submit = SubmitField("Login")

class OccurrenceForm(FlaskForm):
    # Campo para input do usuário para a IA
    ai_input = TextAreaField("Descreva a ocorrência ou use palavras-chave para obter sugestões da IA", validators=[Length(max=500)])
    # Campos padrão
    title = StringField("Título da Ocorrência", validators=[DataRequired(), Length(min=5, max=100)])
    description = TextAreaField("Descrição Detalhada", validators=[DataRequired()])
    unit_number = StringField("Número da Unidade/Apartamento", validators=[DataRequired(), Length(min=1, max=20)])
    images = MultipleFileField("Anexar Imagens (Opcional)", validators=[
        FileAllowed(app.config["ALLOWED_EXTENSIONS"], "Apenas imagens são permitidas!")
    ])
    submit = SubmitField("Registrar Ocorrência")

class DocumentUploadForm(FlaskForm):
    # ... (mantido como antes)
    document_file = FileField("Arquivo PDF do Documento", validators=[
        FileRequired(),
        FileAllowed(app.config["ALLOWED_DOCUMENT_EXTENSIONS"], "Apenas arquivos PDF são permitidos!")
    ])
    submit = SubmitField("Carregar Documento")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class PDF(FPDF): # ... (mantido como antes)
    def header(self):
        try:
            # Tentar usar a fonte NotoSansCJK
            self.add_font("NotoSansCJK", fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
            self.set_font("NotoSansCJK", size=12)
        except RuntimeError:
            # Fallback para Arial se a fonte não estiver disponível
            logger.warning("Fonte NotoSansCJK não encontrada, usando Arial.")
            self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Advertência Condominial", 0, 1, "C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        try:
            self.set_font("NotoSansCJK", size=8)
        except RuntimeError:
            self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

    def chapter_title(self, title):
        try:
            self.set_font("NotoSansCJK", size=12)
        except RuntimeError:
            self.set_font("Arial", "B", 12)
        # Usar encode/decode para tentar lidar com caracteres especiais
        try:
            title_encoded = title.encode("latin-1", "replace").decode("latin-1")
        except Exception:
             title_encoded = "Erro ao decodificar título"
        self.cell(0, 10, title_encoded, 0, 1, "L")
        self.ln(5)

    def chapter_body(self, body):
        try:
            self.set_font("NotoSansCJK", size=10)
        except RuntimeError:
            self.set_font("Arial", "", 10)
        # Usar encode/decode para tentar lidar com caracteres especiais
        try:
            body_encoded = body.encode("latin-1", "replace").decode("latin-1")
        except Exception:
            body_encoded = "Erro ao decodificar texto."
        self.multi_cell(0, 5, body_encoded) # Reduzido espaçamento entre linhas
        self.ln()

    def add_image_to_pdf(self, image_path):
        try:
            page_width = self.w - 2 * self.l_margin
            # Reduzir um pouco a largura da imagem para garantir que caiba
            max_img_width = page_width * 0.8 
            self.image(image_path, x=None, y=None, w=max_img_width)
            self.ln(5)
        except Exception as e:
            logger.error(f"Erro ao adicionar imagem {os.path.basename(image_path)} ao PDF: {e}")
            self.chapter_body(f"[Erro ao adicionar imagem {os.path.basename(image_path)} ao PDF]")

# Routes (rotas existentes mantidas, adicionada rota para API de sugestões)
@app.route("/")
@app.route("/home")
def home():
    # ... (mantido como antes)
    if current_user.is_authenticated:
        return redirect(url_for("list_occurrences"))
    return render_template("index.html", title="Página Inicial")

@app.route("/register", methods=["GET", "POST"])
def register():
    # ... (mantido como antes)
    if current_user.is_authenticated: return redirect(url_for("home"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f"Conta criada para {form.username.data}! Você já pode fazer login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", title="Registro", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    # ... (mantido como antes)
    if current_user.is_authenticated: return redirect(url_for("home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get("next")
            flash("Login bem-sucedido!", "success")
            return redirect(next_page) if next_page else redirect(url_for("home"))
        else:
            flash("Login falhou. Verifique o email e a senha.", "danger")
    return render_template("login.html", title="Login", form=form)

@app.route("/logout")
@login_required
def logout():
    # ... (mantido como antes)
    logout_user()
    flash("Você foi desconectado.", "info")
    return redirect(url_for("home"))

@app.route("/occurrence/new", methods=["GET", "POST"])
@login_required
def new_occurrence():
    form = OccurrenceForm()
    if form.validate_on_submit():
        # A lógica de sugestão agora é chamada via API separadamente
        occurrence = Occurrence(
            title=form.title.data,
            description=form.description.data, # Descrição preenchida pelo usuário
            unit_number=form.unit_number.data,
            author=current_user
        )
        db.session.add(occurrence)
        db.session.flush() # Obter o ID da ocorrência antes de salvar imagens
        
        # Salvar imagens
        image_filenames = []
        for image_file in form.images.data:
            if image_file and allowed_image_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                # Criar nome único para evitar colisões
                unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename}"
                image_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
                try:
                    image_file.save(image_path)
                    img = Image(filename=unique_filename, occurrence_id=occurrence.id)
                    db.session.add(img)
                    image_filenames.append(unique_filename)
                except Exception as e:
                    logger.error(f"Erro ao salvar imagem {filename}: {e}")
                    flash(f"Erro ao salvar a imagem {filename}.", "danger")

        try:
            db.session.commit()
            flash("Ocorrência registrada com sucesso!", "success")
            return redirect(url_for("list_occurrences"))
        except Exception as e:
            db.session.rollback() # Desfazer alterações no banco em caso de erro
            logger.error(f"Erro ao commitar ocorrência no banco: {e}")
            flash("Erro ao salvar a ocorrência no banco de dados.", "danger")
            # Remover imagens que possam ter sido salvas se o commit falhou
            for fname in image_filenames:
                 try:
                      os.remove(os.path.join(app.config["UPLOAD_FOLDER"], fname))
                 except OSError as rm_err:
                      logger.error(f"Erro ao remover imagem órfã {fname}: {rm_err}")

    # Se GET ou falha na validação, renderiza o formulário
    return render_template("add_occurrence.html", title="Nova Ocorrência", form=form, legend="Nova Ocorrência")

# --- NOVA ROTA PARA SUGESTÕES DA IA ---
@app.route("/api/suggestions", methods=["POST"])
@login_required
def api_get_suggestions():
    """Endpoint da API para obter sugestões da IA Gemini."""
    data = request.get_json()
    if not data or "user_input" not in data:
        return jsonify({"error": "Input do usuário não fornecido"}), 400
    
    user_input = data["user_input"]
    logger.info(f"Recebida requisição para sugestões com input: {user_input[:50]}...")
    
    # Chamar a classe SmartSuggestions (que usa Gemini)
    suggestions = smart_suggestions.get_suggestions(user_input)
    
    if suggestions:
        logger.info("Sugestões geradas com sucesso.")
        return jsonify(suggestions)
    else:
        logger.error("Falha ao gerar sugestões.")
        # Retornar um erro genérico ou o erro específico se disponível e seguro
        return jsonify({"error": "Falha ao obter sugestões da IA."}), 500
# --- FIM DA NOVA ROTA ---

@app.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    # ... (mantido como antes)
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/occurrences")
@login_required
def list_occurrences():
    # ... (mantido como antes)
    page = request.args.get("page", 1, type=int)
    occurrences = Occurrence.query.filter_by(user_id=current_user.id).order_by(Occurrence.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template("occurrences.html", title="Minhas Ocorrências", occurrences=occurrences)

@app.route("/occurrence/<int:occurrence_id>")
@login_required
def view_occurrence(occurrence_id):
    # ... (mantido como antes)
    occurrence = Occurrence.query.get_or_404(occurrence_id)
    if occurrence.author != current_user: # Basic authorization
        flash("Você não tem permissão para ver esta ocorrência.", "danger")
        return redirect(url_for("list_occurrences"))
    return render_template("view_occurrence.html", title=occurrence.title, occurrence=occurrence)

@app.route("/occurrence/<int:occurrence_id>/generate_pdf")
@login_required
def generate_warning_pdf(occurrence_id):
    # ... (lógica de geração de PDF mantida, pode ser melhorada depois)
    occurrence = Occurrence.query.get_or_404(occurrence_id)
    if occurrence.author != current_user:
        flash("Você não tem permissão para gerar PDF para esta ocorrência.", "danger")
        return redirect(url_for("list_occurrences"))
    pdf = PDF()
    pdf.add_page()
    pdf.chapter_title(f"Advertência Referente à Ocorrência: {occurrence.title}")
    pdf.chapter_body(f"Data da Ocorrência: {occurrence.date_posted.strftime('%d/%m/%Y %H:%M:%S')}")
    pdf.chapter_body(f"Unidade Envolvida: {occurrence.unit_number}")
    pdf.chapter_body(f"Registrado por: {occurrence.author.username}")
    pdf.ln(10)
    pdf.chapter_title("Descrição da Ocorrência:")
    pdf.chapter_body(occurrence.description)
    pdf.ln(5)
    if occurrence.images:
        pdf.chapter_title("Imagens Anexadas:")
        for image in occurrence.images:
            image_full_path = os.path.join(app.config["UPLOAD_FOLDER"], image.filename)
            if os.path.exists(image_full_path):
                pdf.add_image_to_pdf(image_full_path)
            else:
                 logger.warning(f"Imagem {image.filename} referenciada mas não encontrada em {image_full_path}")
                 pdf.chapter_body(f"[Imagem {image.filename} não encontrada no servidor]")
        pdf.ln(5)
    pdf.chapter_body("Esta é uma notificação formal de advertência. Solicitamos a devida atenção para que a situação não se repita, sob pena de aplicação das sanções previstas no regulamento interno e/ou convenção condominial.")
    pdf.ln(20)
    pdf.chapter_body("Atenciosamente,")
    pdf.chapter_body("A Administração do Condomínio")
    buffer = io.BytesIO()
    try:
        # Tentar gerar o PDF
        pdf_output = pdf.output(dest="S").encode("latin-1")
        buffer.write(pdf_output)
        buffer.seek(0)
        # Atualizar status apenas se o PDF foi gerado com sucesso
        occurrence.status = "Notificado (PDF Gerado)"
        db.session.commit()
        flash("PDF de advertência gerado com sucesso!", "success")
        return send_file(buffer, as_attachment=True, download_name=f"advertencia_{occurrence.id}.pdf", mimetype="application/pdf")
    except Exception as e:
        logger.error(f"Erro ao gerar PDF para ocorrência {occurrence_id}: {e}")
        flash("Erro ao gerar o PDF de advertência.", "danger")
        return redirect(url_for("view_occurrence", occurrence_id=occurrence_id))

# --- Rotas para Gerenciamento de Documentos (atualizadas) ---
@app.route("/admin/documents", methods=["GET", "POST"])
@login_required # Idealmente, adicionar verificação de role de admin aqui
def manage_documents():
    # if current_user.role != "admin": # Exemplo
    #     flash("Acesso não autorizado.", "danger")
    #     return redirect(url_for("home"))

    form_regimento = DocumentUploadForm(prefix="regimento")
    form_convencao = DocumentUploadForm(prefix="convencao")
    
    # Status dos documentos atuais
    regimento_status = "Não carregado" 
    convencao_status = "Não carregado"
    if os.path.exists(os.path.join(app.config["DOCUMENTS_FOLDER"], "regimento_interno.pdf")):
        regimento_status = "Carregado"
    if os.path.exists(os.path.join(app.config["DOCUMENTS_FOLDER"], "convencao_condominial.pdf")):
        convencao_status = "Carregado"

    if request.method == "POST":
        doc_type = None
        form = None
        if form_regimento.validate_on_submit() and form_regimento.submit.data:
             doc_type = "regimento_interno"
             form = form_regimento
             file_key = form_regimento.document_file.name
        elif form_convencao.validate_on_submit() and form_convencao.submit.data:
             doc_type = "convencao_condominial"
             form = form_convencao
             file_key = form_convencao.document_file.name
        
        if doc_type and form and request.files.get(file_key):
            doc_file = request.files.get(file_key)
            if doc_file and allowed_document_file(doc_file.filename):
                filename = f"{doc_type}.pdf" # Nome fixo
                save_path = os.path.join(app.config["DOCUMENTS_FOLDER"], filename)
                processed_text_path = os.path.join(app.config["PROCESSED_DOCS_FOLDER"], f"{doc_type}_texto.txt")
                processed_json_path = os.path.join(app.config["PROCESSED_DOCS_FOLDER"], f"{doc_type}_processado.json")
                
                try:
                    # Remover arquivos antigos processados se existirem
                    if os.path.exists(processed_text_path): os.remove(processed_text_path)
                    if os.path.exists(processed_json_path): os.remove(processed_json_path)
                    
                    # Salvar o novo PDF
                    doc_file.save(save_path)
                    flash(f"{doc_type.replace('_', ' ').title()} carregado com sucesso! Iniciando processamento...", "info")
                    
                    # Chamar pdftotext para extrair texto
                    result = subprocess.run(["pdftotext", save_path, processed_text_path], capture_output=True, text=True, check=False)
                    if result.returncode != 0:
                         raise RuntimeError(f"Erro ao executar pdftotext: {result.stderr}")
                    
                    # Ler o texto extraído
                    with open(processed_text_path, "r", encoding="utf-8") as f_text:
                        text_content = f_text.read()
                        
                    # Parsear o texto para extrair artigos
                    articles_dict = parse_document_text(text_content)
                    
                    # Salvar os artigos em JSON
                    output_data = {
                        "source": doc_type.replace("_", " ").title(),
                        "processed_at": datetime.utcnow().isoformat(),
                        "articles": articles_dict
                    }
                    with open(processed_json_path, "w", encoding="utf-8") as f_json:
                        json.dump(output_data, f_json, ensure_ascii=False, indent=4)
                        
                    flash(f"{doc_type.replace('_', ' ').title()} processado com sucesso! {len(articles_dict)} artigos extraídos.", "success")
                    # Atualizar status para exibição
                    if doc_type == "regimento_interno": regimento_status = "Carregado e Processado"
                    if doc_type == "convencao_condominial": convencao_status = "Carregado e Processado"

                except Exception as e:
                    logger.error(f"Erro ao processar o documento {doc_type}: {e}")
                    flash(f"Erro ao processar o {doc_type.replace('_', ' ')}. Verifique o arquivo e tente novamente. Detalhes: {e}", "danger")
                    # Remover arquivos parcialmente processados em caso de erro
                    if os.path.exists(save_path): os.remove(save_path)
                    if os.path.exists(processed_text_path): os.remove(processed_text_path)
                    if os.path.exists(processed_json_path): os.remove(processed_json_path)
                    if doc_type == "regimento_interno": regimento_status = "Erro no processamento"
                    if doc_type == "convencao_condominial": convencao_status = "Erro no processamento"
            else:
                 flash("Tipo de arquivo inválido. Apenas PDF é permitido.", "warning")
        else:
            # Tratar caso onde a validação falhou ou nenhum arquivo foi enviado
            if form and form.errors:
                 for field, errors in form.errors.items():
                      for error in errors:
                           flash(f"Erro no campo ", "danger") # Melhorar mensagem de erro
            # else: # Não fazer nada se for um POST inválido sem erros de formulário
            #     flash("Erro no envio do formulário.", "danger")
            pass # Evita flash desnecessário se for só um GET

    # Se for GET, apenas renderiza a página
    return render_template("admin_docs.html", title="Gerenciar Documentos", 
                           form_regimento=form_regimento, form_convencao=form_convencao,
                           regimento_status=regimento_status, convencao_status=convencao_status)
# --- Fim das Rotas de Documentos ---

# Inicialização do Banco de Dados (se necessário)
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    # Rodar em 0.0.0.0 para ser acessível externamente se necessário (e.g., via expose_port)
    # Usar debug=True apenas em desenvolvimento
    app.run(host="0.0.0.0", port=5000, debug=False) 

