# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime
from flask import current_app
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Modelos de dados para o sistema de e-mail
class EmailConfig(Base):
    __tablename__ = 'email_config'
    
    id = Column(Integer, primary_key=True)
    smtp_server = Column(String(100), nullable=False)
    smtp_port = Column(Integer, nullable=False)
    smtp_username = Column(String(100), nullable=False)
    smtp_password = Column(String(255), nullable=False)  # Armazenado criptografado
    use_tls = Column(Boolean, default=True)
    default_sender = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.smtp_password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.smtp_password, password)

class EmailTemplate(Base):
    __tablename__ = 'email_template'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UnitEmail(Base):
    __tablename__ = 'unit_email'
    
    id = Column(Integer, primary_key=True)
    unit_number = Column(String(20), nullable=False)
    email = Column(String(100), nullable=False)
    recipient_name = Column(String(100))
    recipient_type = Column(String(10), default='TO')  # TO, CC, BCC
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EmailLog(Base):
    __tablename__ = 'email_log'
    
    id = Column(Integer, primary_key=True)
    occurrence_id = Column(Integer, ForeignKey('occurrence.id'))
    template_id = Column(Integer, ForeignKey('email_template.id'))
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='pending')  # pending, sent, failed
    error_message = Column(Text)
    recipient_list = Column(Text)  # JSON string of recipients
    subject = Column(String(255))
    body_preview = Column(Text)
    
    # Relacionamentos
    template = relationship("EmailTemplate")

# Classe principal para gerenciar o envio de e-mails
class EmailManager:
    def __init__(self, db_session):
        self.db_session = db_session
        self.mail = None
        self._initialize_mail()
    
    def _initialize_mail(self):
        """Inicializa o objeto Flask-Mail com as configurações do banco de dados"""
        config = self.db_session.query(EmailConfig).first()
        if not config:
            return False
        
        app = current_app._get_current_object()
        app.config['MAIL_SERVER'] = config.smtp_server
        app.config['MAIL_PORT'] = config.smtp_port
        app.config['MAIL_USERNAME'] = config.smtp_username
        app.config['MAIL_PASSWORD'] = config.smtp_password  # Idealmente, descriptografar aqui
        app.config['MAIL_USE_TLS'] = config.use_tls
        app.config['MAIL_DEFAULT_SENDER'] = config.default_sender
        
        self.mail = Mail(app)
        return True
    
    def test_connection(self):
        """Testa a conexão com o servidor SMTP"""
        if not self.mail:
            if not self._initialize_mail():
                return False, "Configuração de e-mail não encontrada"
        
        try:
            with self.mail.connect() as conn:
                return True, "Conexão estabelecida com sucesso"
        except Exception as e:
            return False, f"Erro ao conectar: {str(e)}"
    
    def get_unit_emails(self, unit_number):
        """Obtém todos os e-mails associados a uma unidade"""
        return self.db_session.query(UnitEmail).filter_by(
            unit_number=unit_number, 
            is_active=True
        ).all()
    
    def get_default_template(self):
        """Obtém o template padrão para e-mails de advertência"""
        return self.db_session.query(EmailTemplate).filter_by(
            is_default=True
        ).first()
    
    def replace_template_variables(self, template_text, occurrence):
        """Substitui variáveis no template com dados da ocorrência"""
        replacements = {
            '{{occurrence_title}}': occurrence.title,
            '{{occurrence_description}}': occurrence.description,
            '{{occurrence_date}}': occurrence.date_posted.strftime('%d/%m/%Y %H:%M:%S'),
            '{{unit_number}}': occurrence.unit_number,
            '{{author_name}}': occurrence.author.username,
            '{{current_date}}': datetime.utcnow().strftime('%d/%m/%Y'),
        }
        
        result = template_text
        for key, value in replacements.items():
            result = result.replace(key, value)
        
        return result
    
    def send_warning_email(self, occurrence, pdf_attachment=None):
        """Envia e-mail de advertência para os destinatários da unidade"""
        if not self.mail:
            if not self._initialize_mail():
                return False, "Configuração de e-mail não encontrada"
        
        # Obter e-mails da unidade
        unit_emails = self.get_unit_emails(occurrence.unit_number)
        if not unit_emails:
            return False, f"Nenhum e-mail cadastrado para a unidade {occurrence.unit_number}"
        
        # Obter template
        template = self.get_default_template()
        if not template:
            return False, "Nenhum template padrão encontrado"
        
        # Preparar destinatários
        recipients = {'to': [], 'cc': [], 'bcc': []}
        for unit_email in unit_emails:
            recipients[unit_email.recipient_type.lower()].append(unit_email.email)
        
        # Substituir variáveis no template
        subject = self.replace_template_variables(template.subject, occurrence)
        body_html = self.replace_template_variables(template.body_html, occurrence)
        body_text = self.replace_template_variables(template.body_text, occurrence)
        
        # Criar mensagem
        msg = Message(
            subject=subject,
            recipients=recipients['to'],
            cc=recipients['cc'],
            bcc=recipients['bcc'],
            body=body_text,
            html=body_html
        )
        
        # Anexar PDF se fornecido
        if pdf_attachment:
            msg.attach(
                filename=f"advertencia_{occurrence.id}.pdf",
                content_type="application/pdf",
                data=pdf_attachment
            )
        
        # Registrar no log
        log_entry = EmailLog(
            occurrence_id=occurrence.id,
            template_id=template.id,
            status='pending',
            recipient_list=json.dumps({
                'to': recipients['to'],
                'cc': recipients['cc'],
                'bcc': recipients['bcc']
            }),
            subject=subject,
            body_preview=body_text[:200] + ('...' if len(body_text) > 200 else '')
        )
        self.db_session.add(log_entry)
        self.db_session.flush()
        
        # Enviar e-mail
        try:
            self.mail.send(msg)
            log_entry.status = 'sent'
            self.db_session.commit()
            return True, f"E-mail enviado com sucesso para {len(recipients['to'])} destinatários"
        except Exception as e:
            log_entry.status = 'failed'
            log_entry.error_message = str(e)
            self.db_session.commit()
            return False, f"Erro ao enviar e-mail: {str(e)}"

# Funções para criar templates padrão
def create_default_templates(db_session):
    """Cria templates padrão se não existirem"""
    default_template = db_session.query(EmailTemplate).filter_by(is_default=True).first()
    if default_template:
        return
    
    # Template padrão para advertências
    warning_template = EmailTemplate(
        name="Template Padrão de Advertência",
        subject="Advertência Condominial - Unidade {{unit_number}}",
        body_html="""
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; }
                .header { background-color: #f0f0f0; padding: 20px; text-align: center; }
                .content { padding: 20px; }
                .footer { background-color: #f0f0f0; padding: 10px; text-align: center; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Advertência Condominial</h2>
            </div>
            <div class="content">
                <p>Prezado(a) Condômino da Unidade <strong>{{unit_number}}</strong>,</p>
                
                <p>Vimos por meio deste comunicar que foi registrada a seguinte ocorrência:</p>
                
                <p><strong>Título:</strong> {{occurrence_title}}</p>
                <p><strong>Data:</strong> {{occurrence_date}}</p>
                <p><strong>Descrição:</strong></p>
                <p>{{occurrence_description}}</p>
                
                <p>Esta é uma notificação formal de advertência. Solicitamos a devida atenção para que a situação não se repita, sob pena de aplicação das sanções previstas no regulamento interno do condomínio.</p>
                
                <p>Em anexo, segue o documento oficial da advertência em formato PDF.</p>
                
                <p>Caso tenha qualquer dúvida ou deseje contestar esta advertência, por favor entre em contato com a administração do condomínio.</p>
                
                <p>Atenciosamente,<br>
                A Administração do Condomínio</p>
            </div>
            <div class="footer">
                <p>Este é um e-mail automático. Por favor, não responda diretamente a esta mensagem.</p>
                <p>Data de envio: {{current_date}}</p>
            </div>
        </body>
        </html>
        """,
        body_text="""
        ADVERTÊNCIA CONDOMINIAL
        
        Prezado(a) Condômino da Unidade {{unit_number}},
        
        Vimos por meio deste comunicar que foi registrada a seguinte ocorrência:
        
        Título: {{occurrence_title}}
        Data: {{occurrence_date}}
        Descrição:
        {{occurrence_description}}
        
        Esta é uma notificação formal de advertência. Solicitamos a devida atenção para que a situação não se repita, sob pena de aplicação das sanções previstas no regulamento interno do condomínio.
        
        Em anexo, segue o documento oficial da advertência em formato PDF.
        
        Caso tenha qualquer dúvida ou deseje contestar esta advertência, por favor entre em contato com a administração do condomínio.
        
        Atenciosamente,
        A Administração do Condomínio
        
        ---
        Este é um e-mail automático. Por favor, não responda diretamente a esta mensagem.
        Data de envio: {{current_date}}
        """,
        is_default=True
    )
    
    db_session.add(warning_template)
    db_session.commit()

# Função para criar tabelas no banco de dados
def create_email_tables(engine):
    """Cria as tabelas necessárias para o sistema de e-mail"""
    Base.metadata.create_all(engine)
