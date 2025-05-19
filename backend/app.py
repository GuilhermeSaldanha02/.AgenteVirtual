# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, redirect, url_for, flash, request, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from fpdf import FPDF
import io

# App Configuration
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "uma_chave_secreta_muito_forte_padrao")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Email Configuration (for later use with Flask-Mail)
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.googlemail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "true").lower() in ["true", "on", "1"]
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME") # Configure this via environment variable
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD") # Configure this via environment variable
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER") # Configure this via environment variable


db = SQLAlchemy(app)
# mail = Mail(app) # Initialize Flask-Mail later if used

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

# Database Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    occurrences = db.relationship("Occurrence", backref="author", lazy=True)

    def __repr__(self):
        return f"User(\'{self.username}\', \'{self.email}\')"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Occurrence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    unit_number = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Registrada") # Registrada, Em Análise, Notificado, Multado, Resolvido
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        return f"Occurrence(\'{self.title}\', \'{self.date_posted}\')"

# Forms
class RegistrationForm(FlaskForm):
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
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Senha", validators=[DataRequired()])
    submit = SubmitField("Login")

class OccurrenceForm(FlaskForm):
    title = StringField("Título da Ocorrência", validators=[DataRequired(), Length(min=5, max=100)])
    description = TextAreaField("Descrição Detalhada", validators=[DataRequired()])
    unit_number = StringField("Número da Unidade/Apartamento", validators=[DataRequired(), Length(min=1, max=20)])
    submit = SubmitField("Registrar Ocorrência")

# Flask-Login User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# PDF Generation Helper
class PDF(FPDF):
    def header(self):
        # Use a CJK font if available, otherwise default
        try:
            self.add_font("NotoSansCJK", fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
            self.set_font("NotoSansCJK", size=12)
        except RuntimeError:
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
        self.cell(0, 10, title, 0, 1, "L")
        self.ln(5)

    def chapter_body(self, body):
        try:
            self.set_font("NotoSansCJK", size=10)
        except RuntimeError:
            self.set_font("Arial", "", 10)
        self.multi_cell(0, 10, body)
        self.ln()

# Routes
@app.route("/")
@app.route("/home")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("list_occurrences"))
    return render_template("index.html", title="Página Inicial")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
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
    if current_user.is_authenticated:
        return redirect(url_for("home"))
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
    logout_user()
    flash("Você foi desconectado.", "info")
    return redirect(url_for("home"))

@app.route("/occurrence/new", methods=["GET", "POST"])
@login_required
def new_occurrence():
    form = OccurrenceForm()
    if form.validate_on_submit():
        occurrence = Occurrence(
            title=form.title.data,
            description=form.description.data,
            unit_number=form.unit_number.data,
            author=current_user
        )
        db.session.add(occurrence)
        db.session.commit()
        flash("Ocorrência registrada com sucesso!", "success")
        return redirect(url_for("list_occurrences"))
    return render_template("add_occurrence.html", title="Nova Ocorrência", form=form, legend="Nova Ocorrência")

@app.route("/occurrences")
@login_required
def list_occurrences():
    page = request.args.get("page", 1, type=int)
    occurrences = Occurrence.query.filter_by(user_id=current_user.id).order_by(Occurrence.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template("occurrences.html", title="Minhas Ocorrências", occurrences=occurrences)

@app.route("/occurrence/<int:occurrence_id>")
@login_required
def view_occurrence(occurrence_id):
    occurrence = Occurrence.query.get_or_404(occurrence_id)
    if occurrence.author != current_user:
        flash("Você não tem permissão para ver esta ocorrência.", "danger")
        return redirect(url_for("list_occurrences"))
    return render_template("view_occurrence.html", title=occurrence.title, occurrence=occurrence)

@app.route("/occurrence/<int:occurrence_id>/generate_pdf")
@login_required
def generate_warning_pdf(occurrence_id):
    occurrence = Occurrence.query.get_or_404(occurrence_id)
    if occurrence.author != current_user:
        flash("Você não tem permissão para gerar PDF para esta ocorrência.", "danger")
        return redirect(url_for("list_occurrences"))

    pdf = PDF()
    pdf.add_page()
    pdf.chapter_title(f"Advertência Referente à Ocorrência: {occurrence.title}")
    pdf.chapter_body(f"Data da Ocorrência: {occurrence.date_posted.strftime("%d/%m/%Y %H:%M:%S")}")
    pdf.chapter_body(f"Unidade Envolvida: {occurrence.unit_number}")
    pdf.chapter_body(f"Registrado por: {occurrence.author.username}")
    pdf.ln(10)
    pdf.chapter_title("Descrição da Ocorrência:")
    # Ensure description is encoded correctly for FPDF
    try:
        description_cleaned = occurrence.description.encode("latin-1", "replace").decode("latin-1")
    except Exception:
        description_cleaned = "Erro ao decodificar a descrição."
    pdf.chapter_body(description_cleaned)
    pdf.ln(10)
    pdf.chapter_body("Esta é uma notificação formal de advertência. Solicitamos a devida atenção para que a situação não se repita, sob pena de aplicação das sanções previstas no regulamento interno do condomínio.")
    pdf.ln(20)
    pdf.chapter_body("Atenciosamente,")
    pdf.chapter_body("A Administração do Condomínio")

    # Create a BytesIO buffer for the PDF
    buffer = io.BytesIO()
    pdf_output = pdf.output(dest="S").encode("latin-1") # Output as string, then encode to latin-1 for BytesIO
    buffer.write(pdf_output)
    buffer.seek(0)

    # Update occurrence status (example)
    occurrence.status = "Notificado (PDF Gerado)"
    db.session.commit()

    flash("PDF de advertência gerado com sucesso!", "success")
    return send_file(buffer, as_attachment=True, download_name=f"advertencia_{occurrence.id}.pdf", mimetype="application/pdf")

# Placeholder for email sending function (to be implemented with Flask-Mail)
# def send_warning_email(user_email, occurrence, pdf_attachment):
#     msg = Message("Advertência Condominial", recipients=[user_email])
#     msg.body = f"""
#     Prezado(a) condômino(a) da unidade {occurrence.unit_number},

#     Segue em anexo a advertência referente à ocorrência: {occurrence.title}.

#     Detalhes:
#     Descrição: {occurrence.description}
#     Data: {occurrence.date_posted.strftime("%d/%m/%Y %H:%M:%S")}

#     Atenciosamente,
#     A Administração do Condomínio
#     """
#     msg.attach(f"advertencia_{occurrence.id}.pdf", "application/pdf", pdf_attachment)
#     try:
#         mail.send(msg)
#         return True
#     except Exception as e:
#         app.logger.error(f"Erro ao enviar email: {e}")
#         return False

if __name__ == "__main__":
    with app.app_context():
        db.create_all() # Create database tables if they don_t exist
    app.run(debug=True, host="0.0.0.0", port=5000)

