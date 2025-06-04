# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from flask_mail import Message

Base = declarative_base()

# Modelos para o sistema de comunicados
class Announcement(Base):
    __tablename__ = 'announcement'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    content_html = Column(Text, nullable=False)
    content_text = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    priority = Column(String(10), default='média')  # baixa, média, alta
    status = Column(String(20), default='rascunho')  # rascunho, agendado, publicado, arquivado
    created_by = Column(Integer, ForeignKey('user.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime)
    expires_at = Column(DateTime)
    
    # Relacionamentos
    attachments = relationship("AnnouncementAttachment", back_populates="announcement", cascade="all, delete-orphan")
    distributions = relationship("AnnouncementDistribution", back_populates="announcement", cascade="all, delete-orphan")
    receipts = relationship("AnnouncementReceipt", back_populates="announcement", cascade="all, delete-orphan")
    creator = relationship("User")

class AnnouncementAttachment(Base):
    __tablename__ = 'announcement_attachment'
    
    id = Column(Integer, primary_key=True)
    announcement_id = Column(Integer, ForeignKey('announcement.id'), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_type = Column(String(50))
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    announcement = relationship("Announcement", back_populates="attachments")

class AnnouncementDistribution(Base):
    __tablename__ = 'announcement_distribution'
    
    id = Column(Integer, primary_key=True)
    announcement_id = Column(Integer, ForeignKey('announcement.id'), nullable=False)
    distribution_type = Column(String(20), nullable=False)  # todos, unidades_especificas, grupos
    target_units = Column(Text)  # JSON string de unidades
    target_group = Column(String(50))
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)
    print_generated = Column(Boolean, default=False)
    print_generated_at = Column(DateTime)
    
    # Relacionamentos
    announcement = relationship("Announcement", back_populates="distributions")

class AnnouncementReceipt(Base):
    __tablename__ = 'announcement_receipt'
    
    id = Column(Integer, primary_key=True)
    announcement_id = Column(Integer, ForeignKey('announcement.id'), nullable=False)
    unit_number = Column(String(20))
    email = Column(String(100))
    viewed = Column(Boolean, default=False)
    viewed_at = Column(DateTime)
    confirmed = Column(Boolean, default=False)
    confirmed_at = Column(DateTime)
    
    # Relacionamentos
    announcement = relationship("Announcement", back_populates="receipts")

# Classe para gerenciar o sistema de comunicados
class AnnouncementManager:
    def __init__(self, db_session, app_config, mail=None):
        self.db_session = db_session
        self.app_config = app_config
        self.mail = mail
        self.attachments_folder = os.path.join(app_config['UPLOAD_FOLDER'], 'comunicados')
        
        # Criar pasta de anexos se não existir
        if not os.path.exists(self.attachments_folder):
            os.makedirs(self.attachments_folder)
    
    def create_announcement(self, title, content_html, content_text, category, priority, created_by, status='rascunho', published_at=None, expires_at=None):
        """Cria um novo comunicado"""
        announcement = Announcement(
            title=title,
            content_html=content_html,
            content_text=content_text,
            category=category,
            priority=priority,
            status=status,
            created_by=created_by,
            published_at=published_at,
            expires_at=expires_at
        )
        
        self.db_session.add(announcement)
        self.db_session.commit()
        return announcement
    
    def update_announcement(self, announcement_id, **kwargs):
        """Atualiza um comunicado existente"""
        announcement = self.db_session.query(Announcement).filter_by(id=announcement_id).first()
        if not announcement:
            return None
        
        for key, value in kwargs.items():
            if hasattr(announcement, key):
                setattr(announcement, key, value)
        
        self.db_session.commit()
        return announcement
    
    def delete_announcement(self, announcement_id):
        """Exclui um comunicado"""
        announcement = self.db_session.query(Announcement).filter_by(id=announcement_id).first()
        if not announcement:
            return False
        
        self.db_session.delete(announcement)
        self.db_session.commit()
        return True
    
    def get_announcement_by_id(self, announcement_id):
        """Obtém um comunicado pelo ID"""
        return self.db_session.query(Announcement).filter_by(id=announcement_id).first()
    
    def get_announcements(self, status=None, category=None, priority=None, created_by=None, limit=None):
        """Obtém comunicados com filtros opcionais"""
        query = self.db_session.query(Announcement)
        
        if status:
            query = query.filter(Announcement.status == status)
        
        if category:
            query = query.filter(Announcement.category == category)
        
        if priority:
            query = query.filter(Announcement.priority == priority)
        
        if created_by:
            query = query.filter(Announcement.created_by == created_by)
        
        query = query.order_by(Announcement.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def add_attachment(self, announcement_id, file_obj):
        """Adiciona um anexo ao comunicado"""
        announcement = self.get_announcement_by_id(announcement_id)
        if not announcement:
            return None
        
        # Salvar arquivo
        filename = file_obj.filename
        file_path = os.path.join(self.attachments_folder, f"{announcement_id}_{filename}")
        file_obj.save(file_path)
        
        # Criar registro de anexo
        attachment = AnnouncementAttachment(
            announcement_id=announcement_id,
            file_name=filename,
            file_path=file_path,
            file_type=file_obj.content_type if hasattr(file_obj, 'content_type') else None,
            file_size=os.path.getsize(file_path)
        )
        
        self.db_session.add(attachment)
        self.db_session.commit()
        return attachment
    
    def remove_attachment(self, attachment_id):
        """Remove um anexo do comunicado"""
        attachment = self.db_session.query(AnnouncementAttachment).filter_by(id=attachment_id).first()
        if not attachment:
            return False
        
        # Remover arquivo físico
        if os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)
        
        # Remover registro
        self.db_session.delete(attachment)
        self.db_session.commit()
        return True
    
    def set_distribution(self, announcement_id, distribution_type, target_units=None, target_group=None):
        """Define a distribuição do comunicado"""
        announcement = self.get_announcement_by_id(announcement_id)
        if not announcement:
            return None
        
        # Remover distribuições existentes
        self.db_session.query(AnnouncementDistribution).filter_by(announcement_id=announcement_id).delete()
        
        # Criar nova distribuição
        distribution = AnnouncementDistribution(
            announcement_id=announcement_id,
            distribution_type=distribution_type,
            target_units=json.dumps(target_units) if target_units else None,
            target_group=target_group
        )
        
        self.db_session.add(distribution)
        self.db_session.commit()
        return distribution
    
    def publish_announcement(self, announcement_id, send_email=True):
        """Publica um comunicado e opcionalmente envia por e-mail"""
        announcement = self.get_announcement_by_id(announcement_id)
        if not announcement or announcement.status == 'publicado':
            return False
        
        # Atualizar status e data de publicação
        announcement.status = 'publicado'
        announcement.published_at = datetime.utcnow()
        self.db_session.commit()
        
        # Enviar e-mails se solicitado
        if send_email and self.mail:
            self._send_announcement_emails(announcement)
        
        return True
    
    def _send_announcement_emails(self, announcement):
        """Envia e-mails do comunicado para os destinatários"""
        # Obter distribuição
        distribution = self.db_session.query(AnnouncementDistribution).filter_by(announcement_id=announcement.id).first()
        if not distribution:
            return False
        
        # Determinar destinatários
        recipients = []
        
        if distribution.distribution_type == 'todos':
            # Obter todos os e-mails de unidades
            from email_system import UnitEmail
            unit_emails = self.db_session.query(UnitEmail).filter_by(is_active=True).all()
            recipients = [ue.email for ue in unit_emails]
        
        elif distribution.distribution_type == 'unidades_especificas' and distribution.target_units:
            # Obter e-mails das unidades específicas
            from email_system import UnitEmail
            target_units = json.loads(distribution.target_units)
            unit_emails = self.db_session.query(UnitEmail).filter(
                UnitEmail.unit_number.in_(target_units),
                UnitEmail.is_active == True
            ).all()
            recipients = [ue.email for ue in unit_emails]
        
        elif distribution.distribution_type == 'grupos' and distribution.target_group:
            # Implementação de grupos (simplificada)
            # Na prática, seria necessário um modelo de dados para grupos
            pass
        
        if not recipients:
            return False
        
        # Preparar e enviar e-mail
        try:
            msg = Message(
                subject=f"Comunicado: {announcement.title}",
                recipients=recipients,
                body=announcement.content_text,
                html=announcement.content_html
            )
            
            # Adicionar anexos
            for attachment in announcement.attachments:
                with open(attachment.file_path, 'rb') as f:
                    msg.attach(
                        filename=attachment.file_name,
                        content_type=attachment.file_type,
                        data=f.read()
                    )
            
            self.mail.send(msg)
            
            # Atualizar status de envio
            distribution.email_sent = True
            distribution.email_sent_at = datetime.utcnow()
            
            # Registrar recibos
            for email in recipients:
                receipt = AnnouncementReceipt(
                    announcement_id=announcement.id,
                    email=email
                )
                self.db_session.add(receipt)
            
            self.db_session.commit()
            return True
        
        except Exception as e:
            print(f"Erro ao enviar e-mails do comunicado: {e}")
            return False
    
    def generate_print_version(self, announcement_id):
        """Gera versão para impressão do comunicado"""
        announcement = self.get_announcement_by_id(announcement_id)
        if not announcement:
            return None
        
        # Implementação da geração de PDF para impressão
        # Semelhante à geração de PDF de advertência
        from fpdf import FPDF
        
        class PDF(FPDF):
            def header(self):
                try:
                    self.add_font("NotoSansCJK", fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
                    self.set_font("NotoSansCJK", size=12)
                except RuntimeError:
                    self.set_font("Arial", "B", 12)
                self.cell(0, 10, "Comunicado Condominial", 0, 1, "C")
                self.ln(10)
            
            def footer(self):
                self.set_y(-15)
                try:
                    self.set_font("NotoSansCJK", size=8)
                except RuntimeError:
                    self.set_font("Arial", "I", 8)
                self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")
        
        pdf = PDF()
        pdf.add_page()
        
        # Título
        try:
            pdf.set_font("NotoSansCJK", size=16)
        except RuntimeError:
            pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, announcement.title, 0, 1, "C")
        pdf.ln(5)
        
        # Data
        try:
            pdf.set_font("NotoSansCJK", size=10)
        except RuntimeError:
            pdf.set_font("Arial", "I", 10)
        published_date = announcement.published_at or datetime.utcnow()
        pdf.cell(0, 10, f"Data: {published_date.strftime('%d/%m/%Y')}", 0, 1, "R")
        pdf.ln(5)
        
        # Conteúdo
        try:
            pdf.set_font("NotoSansCJK", size=12)
        except RuntimeError:
            pdf.set_font("Arial", "", 12)
        
        # Simplificar HTML para texto
        import re
        content_text = re.sub(r'<[^>]*>', '', announcement.content_html)
        
        pdf.multi_cell(0, 10, content_text)
        pdf.ln(10)
        
        # Assinatura
        pdf.cell(0, 10, "Atenciosamente,", 0, 1, "L")
        pdf.cell(0, 10, "A Administração do Condomínio", 0, 1, "L")
        
        # Salvar PDF
        pdf_filename = f"comunicado_{announcement.id}.pdf"
        pdf_path = os.path.join(self.attachments_folder, pdf_filename)
        pdf.output(pdf_path)
        
        # Atualizar status de impressão
        distribution = self.db_session.query(AnnouncementDistribution).filter_by(announcement_id=announcement.id).first()
        if distribution:
            distribution.print_generated = True
            distribution.print_generated_at = datetime.utcnow()
            self.db_session.commit()
        
        return pdf_path
    
    def mark_as_viewed(self, announcement_id, email=None, unit_number=None):
        """Marca um comunicado como visualizado por um destinatário"""
        query = self.db_session.query(AnnouncementReceipt).filter_by(announcement_id=announcement_id)
        
        if email:
            query = query.filter_by(email=email)
        
        if unit_number:
            query = query.filter_by(unit_number=unit_number)
        
        receipt = query.first()
        if not receipt:
            return False
        
        receipt.viewed = True
        receipt.viewed_at = datetime.utcnow()
        self.db_session.commit()
        return True
    
    def mark_as_confirmed(self, announcement_id, email=None, unit_number=None):
        """Marca um comunicado como confirmado por um destinatário"""
        query = self.db_session.query(AnnouncementReceipt).filter_by(announcement_id=announcement_id)
        
        if email:
            query = query.filter_by(email=email)
        
        if unit_number:
            query = query.filter_by(unit_number=unit_number)
        
        receipt = query.first()
        if not receipt:
            return False
        
        receipt.confirmed = True
        receipt.confirmed_at = datetime.utcnow()
        self.db_session.commit()
        return True
    
    def get_view_statistics(self, announcement_id):
        """Obtém estatísticas de visualização de um comunicado"""
        announcement = self.get_announcement_by_id(announcement_id)
        if not announcement:
            return None
        
        total_receipts = self.db_session.query(AnnouncementReceipt).filter_by(announcement_id=announcement_id).count()
        viewed_receipts = self.db_session.query(AnnouncementReceipt).filter_by(announcement_id=announcement_id, viewed=True).count()
        confirmed_receipts = self.db_session.query(AnnouncementReceipt).filter_by(announcement_id=announcement_id, confirmed=True).count()
        
        return {
            'total': total_receipts,
            'viewed': viewed_receipts,
            'confirmed': confirmed_receipts,
            'viewed_percentage': (viewed_receipts / total_receipts * 100) if total_receipts > 0 else 0,
            'confirmed_percentage': (confirmed_receipts / total_receipts * 100) if total_receipts > 0 else 0
        }

# Função para criar tabelas no banco de dados
def create_announcement_tables(engine):
    """Cria as tabelas necessárias para o sistema de comunicados"""
    Base.metadata.create_all(engine)

# Rotas Flask para o sistema de comunicados (a serem integradas ao app.py)
def register_announcement_routes(app, db, mail):
    """Registra as rotas para o sistema de comunicados"""
    announcement_manager = AnnouncementManager(db.session, app.config, mail)
    
    @app.route('/comunicados')
    @login_required
    def announcement_list():
        """Página de listagem de comunicados"""
        status = request.args.get('status')
        category = request.args.get('category')
        announcements = announcement_manager.get_announcements(status=status, category=category)
        return render_template('announcement_list.html', title='Comunicados', announcements=announcements)
    
    @app.route('/comunicado/<int:announcement_id>')
    @login_required
    def announcement_detail(announcement_id):
        """Página de detalhes de um comunicado"""
        announcement = announcement_manager.get_announcement_by_id(announcement_id)
        if not announcement:
            flash('Comunicado não encontrado', 'danger')
            return redirect(url_for('announcement_list'))
        
        # Marcar como visualizado
        if current_user.email:
            announcement_manager.mark_as_viewed(announcement_id, email=current_user.email)
        
        return render_template('announcement_detail.html', title=announcement.title, announcement=announcement)
    
    @app.route('/comunicado/novo', methods=['GET', 'POST'])
    @login_required
    def announcement_new():
        """Página de criação de novo comunicado"""
        # Verificar permissões (idealmente apenas admin)
        # if current_user.role != 'admin':
        #     flash('Acesso não autorizado', 'danger')
        #     return redirect(url_for('announcement_list'))
        
        if request.method == 'POST':
            title = request.form.get('title')
            content_html = request.form.get('content_html')
            content_text = request.form.get('content_text')
            category = request.form.get('category')
            priority = request.form.get('priority')
            
            if not title or not content_html:
                flash('Título e conteúdo são obrigatórios', 'danger')
                return render_template('announcement_form.html', title='Novo Comunicado')
            
            # Criar comunicado
            announcement = announcement_manager.create_announcement(
                title=title,
                content_html=content_html,
                content_text=content_text or content_html,
                category=category,
                priority=priority,
                created_by=current_user.id
            )
            
            # Processar anexos
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    announcement_manager.add_attachment(announcement.id, file)
            
            flash('Comunicado criado com sucesso', 'success')
            return redirect(url_for('announcement_detail', announcement_id=announcement.id))
        
        return render_template('announcement_form.html', title='Novo Comunicado')
    
    @app.route('/comunicado/<int:announcement_id>/editar', methods=['GET', 'POST'])
    @login_required
    def announcement_edit(announcement_id):
        """Página de edição de comunicado"""
        announcement = announcement_manager.get_announcement_by_id(announcement_id)
        if not announcement:
            flash('Comunicado não encontrado', 'danger')
            return redirect(url_for('announcement_list'))
        
        # Verificar permissões
        if announcement.created_by != current_user.id:  # Simplificado, idealmente verificar role também
            flash('Você não tem permissão para editar este comunicado', 'danger')
            return redirect(url_for('announcement_detail', announcement_id=announcement_id))
        
        if request.method == 'POST':
            title = request.form.get('title')
            content_html = request.form.get('content_html')
            content_text = request.form.get('content_text')
            category = request.form.get('category')
            priority = request.form.get('priority')
            
            if not title or not content_html:
                flash('Título e conteúdo são obrigatórios', 'danger')
                return render_template('announcement_form.html', title='Editar Comunicado', announcement=announcement)
            
            # Atualizar comunicado
            announcement_manager.update_announcement(
                announcement_id=announcement_id,
                title=title,
                content_html=content_html,
                content_text=content_text or content_html,
                category=category,
                priority=priority
            )
            
            # Processar anexos
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    announcement_manager.add_attachment(announcement_id, file)
            
            flash('Comunicado atualizado com sucesso', 'success')
            return redirect(url_for('announcement_detail', announcement_id=announcement_id))
        
        return render_template('announcement_form.html', title='Editar Comunicado', announcement=announcement)
    
    @app.route('/comunicado/<int:announcement_id>/distribuicao', methods=['GET', 'POST'])
    @login_required
    def announcement_distribution(announcement_id):
        """Página de configuração de distribuição do comunicado"""
        announcement = announcement_manager.get_announcement_by_id(announcement_id)
        if not announcement:
            flash('Comunicado não encontrado', 'danger')
            return redirect(url_for('announcement_list'))
        
        if request.method == 'POST':
            distribution_type = request.form.get('distribution_type')
            target_units = request.form.getlist('target_units')
            target_group = request.form.get('target_group')
            
            # Configurar distribuição
            announcement_manager.set_distribution(
                announcement_id=announcement_id,
                distribution_type=distribution_type,
                target_units=target_units if target_units else None,
                target_group=target_group
            )
            
            flash('Distribuição configurada com sucesso', 'success')
            return redirect(url_for('announcement_detail', announcement_id=announcement_id))
        
        # Obter unidades para seleção
        from email_system import UnitEmail
        units = db.session.query(UnitEmail.unit_number).distinct().all()
        units = [u[0] for u in units]
        
        return render_template('announcement_distribution.html', title='Configurar Distribuição', announcement=announcement, units=units)
    
    @app.route('/comunicado/<int:announcement_id>/publicar', methods=['POST'])
    @login_required
    def announcement_publish(announcement_id):
        """Rota para publicar um comunicado"""
        announcement = announcement_manager.get_announcement_by_id(announcement_id)
        if not announcement:
            flash('Comunicado não encontrado', 'danger')
            return redirect(url_for('announcement_list'))
        
        send_email = request.form.get('send_email') == 'true'
        
        # Publicar comunicado
        success = announcement_manager.publish_announcement(announcement_id, send_email=send_email)
        
        if success:
            flash('Comunicado publicado com sucesso', 'success')
        else:
            flash('Erro ao publicar comunicado', 'danger')
        
        return redirect(url_for('announcement_detail', announcement_id=announcement_id))
    
    @app.route('/comunicado/<int:announcement_id>/imprimir')
    @login_required
    def announcement_print(announcement_id):
        """Rota para gerar versão para impressão de um comunicado"""
        announcement = announcement_manager.get_announcement_by_id(announcement_id)
        if not announcement:
            flash('Comunicado não encontrado', 'danger')
            return redirect(url_for('announcement_list'))
        
        # Gerar PDF
        pdf_path = announcement_manager.generate_print_version(announcement_id)
        
        if not pdf_path or not os.path.exists(pdf_path):
            flash('Erro ao gerar versão para impressão', 'danger')
            return redirect(url_for('announcement_detail', announcement_id=announcement_id))
        
        # Enviar arquivo
        return send_file(pdf_path, as_attachment=True, download_name=f"comunicado_{announcement_id}.pdf", mimetype="application/pdf")
    
    @app.route('/api/comunicado/<int:announcement_id>/confirmar', methods=['POST'])
    @login_required
    def api_announcement_confirm(announcement_id):
        """API para confirmar recebimento de um comunicado"""
        announcement = announcement_manager.get_announcement_by_id(announcement_id)
        if not announcement:
            return jsonify({'error': 'Comunicado não encontrado'}), 404
        
        # Confirmar recebimento
        if current_user.email:
            success = announcement_manager.mark_as_confirmed(announcement_id, email=current_user.email)
            
            if success:
                return jsonify({'message': 'Recebimento confirmado com sucesso'})
            else:
                return jsonify({'error': 'Erro ao confirmar recebimento'}), 500
        else:
            return jsonify({'error': 'E-mail do usuário não disponível'}), 400
    
    @app.route('/api/comunicado/<int:announcement_id>/estatisticas')
    @login_required
    def api_announcement_statistics(announcement_id):
        """API para obter estatísticas de um comunicado"""
        announcement = announcement_manager.get_announcement_by_id(announcement_id)
        if not announcement:
            return jsonify({'error': 'Comunicado não encontrado'}), 404
        
        # Obter estatísticas
        statistics = announcement_manager.get_view_statistics(announcement_id)
        
        return jsonify(statistics)
