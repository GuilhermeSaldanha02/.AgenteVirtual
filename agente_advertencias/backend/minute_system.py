# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from fpdf2 import FPDF

Base = declarative_base()

# Modelos para o sistema de automatização de atas
class MeetingMinute(Base):
    __tablename__ = 'meeting_minute'
    
    id = Column(Integer, primary_key=True)
    meeting_type = Column(String(50), nullable=False)  # ordinária, extraordinária
    meeting_date = Column(DateTime, nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String(20), default='rascunho')  # rascunho, finalizada, publicada
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime)
    
    # Relacionamentos
    sections = relationship("MinuteSection", back_populates="minute", cascade="all, delete-orphan")
    participants = relationship("MinuteParticipant", back_populates="minute", cascade="all, delete-orphan")
    attachments = relationship("MinuteAttachment", back_populates="minute", cascade="all, delete-orphan")

class MinuteSection(Base):
    __tablename__ = 'minute_section'
    
    id = Column(Integer, primary_key=True)
    minute_id = Column(Integer, ForeignKey('meeting_minute.id'), nullable=False)
    section_type = Column(String(50), nullable=False)  # introdução, pauta, deliberações, etc.
    title = Column(String(255), nullable=False)
    content = Column(Text)
    sequence = Column(Integer, default=0)
    
    # Relacionamentos
    minute = relationship("MeetingMinute", back_populates="sections")

class MinuteParticipant(Base):
    __tablename__ = 'minute_participant'
    
    id = Column(Integer, primary_key=True)
    minute_id = Column(Integer, ForeignKey('meeting_minute.id'), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(100))  # síndico, conselheiro, condômino
    unit = Column(String(50))
    attendance_status = Column(String(20), default='presente')  # presente, ausente, justificado
    signature = Column(Text)  # assinatura digital (se aplicável)
    
    # Relacionamentos
    minute = relationship("MeetingMinute", back_populates="participants")

class MinuteTemplate(Base):
    __tablename__ = 'minute_template'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    meeting_type = Column(String(50))  # ordinária, extraordinária
    structure = Column(Text)  # JSON com a estrutura do template
    is_default = Column(Boolean, default=False)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class MinuteAttachment(Base):
    __tablename__ = 'minute_attachment'
    
    id = Column(Integer, primary_key=True)
    minute_id = Column(Integer, ForeignKey('meeting_minute.id'), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_type = Column(String(100))
    description = Column(Text)
    uploaded_by = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    minute = relationship("MeetingMinute", back_populates="attachments")

# Classe para gerenciar o sistema de automatização de atas
class MinuteManager:
    def __init__(self, db_session, upload_folder):
        self.db_session = db_session
        self.upload_folder = upload_folder
        
        # Garantir que a pasta de upload existe
        os.makedirs(upload_folder, exist_ok=True)
    
    def create_default_templates(self):
        """Cria templates padrão para atas se não existirem"""
        # Verificar se já existem templates
        existing_templates = self.db_session.query(MinuteTemplate).count()
        if existing_templates > 0:
            return
        
        # Template para assembleia ordinária
        ordinary_template = {
            'sections': [
                {
                    'section_type': 'introdução',
                    'title': 'Introdução',
                    'content': 'Aos {data} dias do mês de {mês} de {ano}, às {hora}, reuniram-se em {local}, os condôminos do Condomínio {nome_condominio}, em Assembleia Geral Ordinária, conforme convocação prévia.'
                },
                {
                    'section_type': 'verificação_quorum',
                    'title': 'Verificação de Quórum',
                    'content': 'Foi verificada a presença de {numero_presentes} condôminos, representando {percentual_presentes}% das unidades, conforme lista de presença anexa.'
                },
                {
                    'section_type': 'pauta',
                    'title': 'Pauta',
                    'content': '1. Aprovação das contas do exercício anterior\n2. Previsão orçamentária\n3. Eleição de síndico e conselho\n4. Assuntos gerais'
                },
                {
                    'section_type': 'deliberações',
                    'title': 'Deliberações',
                    'content': 'Após discussão, foram tomadas as seguintes deliberações:'
                },
                {
                    'section_type': 'encerramento',
                    'title': 'Encerramento',
                    'content': 'Nada mais havendo a tratar, o(a) Sr(a). {nome_presidente} deu por encerrada a assembleia às {hora_encerramento}, da qual eu, {nome_secretario}, lavrei a presente ata que, após lida e aprovada, vai assinada por mim e pelo(a) presidente da assembleia.'
                }
            ]
        }
        
        # Template para assembleia extraordinária
        extraordinary_template = {
            'sections': [
                {
                    'section_type': 'introdução',
                    'title': 'Introdução',
                    'content': 'Aos {data} dias do mês de {mês} de {ano}, às {hora}, reuniram-se em {local}, os condôminos do Condomínio {nome_condominio}, em Assembleia Geral Extraordinária, conforme convocação prévia.'
                },
                {
                    'section_type': 'verificação_quorum',
                    'title': 'Verificação de Quórum',
                    'content': 'Foi verificada a presença de {numero_presentes} condôminos, representando {percentual_presentes}% das unidades, conforme lista de presença anexa.'
                },
                {
                    'section_type': 'pauta',
                    'title': 'Pauta',
                    'content': '{itens_pauta}'
                },
                {
                    'section_type': 'deliberações',
                    'title': 'Deliberações',
                    'content': 'Após discussão, foram tomadas as seguintes deliberações:'
                },
                {
                    'section_type': 'encerramento',
                    'title': 'Encerramento',
                    'content': 'Nada mais havendo a tratar, o(a) Sr(a). {nome_presidente} deu por encerrada a assembleia às {hora_encerramento}, da qual eu, {nome_secretario}, lavrei a presente ata que, após lida e aprovada, vai assinada por mim e pelo(a) presidente da assembleia.'
                }
            ]
        }
        
        # Template para reunião de conselho
        council_template = {
            'sections': [
                {
                    'section_type': 'introdução',
                    'title': 'Introdução',
                    'content': 'Aos {data} dias do mês de {mês} de {ano}, às {hora}, reuniram-se em {local}, os membros do Conselho Consultivo do Condomínio {nome_condominio}, conforme convocação prévia.'
                },
                {
                    'section_type': 'presentes',
                    'title': 'Presentes',
                    'content': 'Estiveram presentes os seguintes conselheiros: {nomes_conselheiros}'
                },
                {
                    'section_type': 'pauta',
                    'title': 'Pauta',
                    'content': '{itens_pauta}'
                },
                {
                    'section_type': 'discussões',
                    'title': 'Discussões e Recomendações',
                    'content': 'Foram discutidos os seguintes assuntos:'
                },
                {
                    'section_type': 'encerramento',
                    'title': 'Encerramento',
                    'content': 'Nada mais havendo a tratar, o(a) Sr(a). {nome_presidente} deu por encerrada a reunião às {hora_encerramento}, da qual eu, {nome_secretario}, lavrei a presente ata.'
                }
            ]
        }
        
        # Criar os templates no banco de dados
        templates = [
            {
                'name': 'Assembleia Geral Ordinária',
                'description': 'Template padrão para atas de Assembleia Geral Ordinária',
                'meeting_type': 'ordinária',
                'structure': json.dumps(ordinary_template),
                'is_default': True
            },
            {
                'name': 'Assembleia Geral Extraordinária',
                'description': 'Template padrão para atas de Assembleia Geral Extraordinária',
                'meeting_type': 'extraordinária',
                'structure': json.dumps(extraordinary_template),
                'is_default': True
            },
            {
                'name': 'Reunião de Conselho',
                'description': 'Template padrão para atas de Reunião de Conselho',
                'meeting_type': 'conselho',
                'structure': json.dumps(council_template),
                'is_default': True
            }
        ]
        
        for template_data in templates:
            template = MinuteTemplate(**template_data)
            self.db_session.add(template)
        
        self.db_session.commit()
    
    def create_minute(self, data):
        """Cria uma nova ata com base nos dados fornecidos"""
        # Criar a ata
        minute = MeetingMinute(
            meeting_type=data.get('meeting_type'),
            meeting_date=datetime.strptime(data.get('meeting_date'), '%Y-%m-%d'),
            title=data.get('title'),
            location=data.get('location'),
            start_time=datetime.strptime(data.get('start_time'), '%H:%M') if data.get('start_time') else None,
            created_by=data.get('created_by')
        )
        
        self.db_session.add(minute)
        self.db_session.flush()  # Para obter o ID
        
        # Adicionar seções com base no template
        template_id = data.get('template_id')
        if template_id:
            template = self.db_session.query(MinuteTemplate).filter_by(id=template_id).first()
            if template:
                structure = json.loads(template.structure)
                for i, section_data in enumerate(structure.get('sections', [])):
                    section = MinuteSection(
                        minute_id=minute.id,
                        section_type=section_data.get('section_type'),
                        title=section_data.get('title'),
                        content=section_data.get('content'),
                        sequence=i
                    )
                    self.db_session.add(section)
        
        # Adicionar participantes iniciais
        participants_data = data.get('participants', [])
        for participant_data in participants_data:
            participant = MinuteParticipant(
                minute_id=minute.id,
                name=participant_data.get('name'),
                role=participant_data.get('role'),
                unit=participant_data.get('unit'),
                attendance_status=participant_data.get('attendance_status', 'presente')
            )
            self.db_session.add(participant)
        
        self.db_session.commit()
        return minute
    
    def update_minute(self, minute_id, data):
        """Atualiza uma ata existente"""
        minute = self.db_session.query(MeetingMinute).filter_by(id=minute_id).first()
        if not minute:
            return None
        
        # Atualizar campos básicos
        if 'meeting_type' in data:
            minute.meeting_type = data['meeting_type']
        if 'meeting_date' in data:
            minute.meeting_date = datetime.strptime(data['meeting_date'], '%Y-%m-%d')
        if 'title' in data:
            minute.title = data['title']
        if 'location' in data:
            minute.location = data['location']
        if 'start_time' in data:
            minute.start_time = datetime.strptime(data['start_time'], '%H:%M') if data['start_time'] else None
        if 'end_time' in data:
            minute.end_time = datetime.strptime(data['end_time'], '%H:%M') if data['end_time'] else None
        if 'status' in data:
            minute.status = data['status']
            if data['status'] == 'publicada' and not minute.published_at:
                minute.published_at = datetime.utcnow()
        
        # Atualizar seções
        if 'sections' in data:
            # Remover seções existentes
            self.db_session.query(MinuteSection).filter_by(minute_id=minute_id).delete()
            
            # Adicionar novas seções
            for i, section_data in enumerate(data['sections']):
                section = MinuteSection(
                    minute_id=minute_id,
                    section_type=section_data.get('section_type'),
                    title=section_data.get('title'),
                    content=section_data.get('content'),
                    sequence=i
                )
                self.db_session.add(section)
        
        # Atualizar participantes
        if 'participants' in data:
            # Remover participantes existentes
            self.db_session.query(MinuteParticipant).filter_by(minute_id=minute_id).delete()
            
            # Adicionar novos participantes
            for participant_data in data['participants']:
                participant = MinuteParticipant(
                    minute_id=minute_id,
                    name=participant_data.get('name'),
                    role=participant_data.get('role'),
                    unit=participant_data.get('unit'),
                    attendance_status=participant_data.get('attendance_status', 'presente'),
                    signature=participant_data.get('signature')
                )
                self.db_session.add(participant)
        
        self.db_session.commit()
        return minute
    
    def delete_minute(self, minute_id):
        """Exclui uma ata"""
        minute = self.db_session.query(MeetingMinute).filter_by(id=minute_id).first()
        if not minute:
            return False
        
        # Excluir anexos físicos
        attachments = self.db_session.query(MinuteAttachment).filter_by(minute_id=minute_id).all()
        for attachment in attachments:
            file_path = os.path.join(self.upload_folder, attachment.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # A exclusão em cascata cuidará das seções, participantes e anexos
        self.db_session.delete(minute)
        self.db_session.commit()
        
        return True
    
    def add_attachment(self, minute_id, file, description, user_id):
        """Adiciona um anexo a uma ata"""
        minute = self.db_session.query(MeetingMinute).filter_by(id=minute_id).first()
        if not minute:
            return None
        
        # Salvar o arquivo
        filename = secure_filename(file.filename)
        file_path = f"minute_{minute_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
        full_path = os.path.join(self.upload_folder, file_path)
        file.save(full_path)
        
        # Determinar o tipo de arquivo
        file_type = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
        
        # Criar o registro de anexo
        attachment = MinuteAttachment(
            minute_id=minute_id,
            file_name=filename,
            file_path=file_path,
            file_type=file_type,
            description=description,
            uploaded_by=user_id
        )
        
        self.db_session.add(attachment)
        self.db_session.commit()
        
        return attachment
    
    def delete_attachment(self, attachment_id):
        """Exclui um anexo"""
        attachment = self.db_session.query(MinuteAttachment).filter_by(id=attachment_id).first()
        if not attachment:
            return False
        
        # Excluir o arquivo físico
        file_path = os.path.join(self.upload_folder, attachment.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Excluir o registro
        self.db_session.delete(attachment)
        self.db_session.commit()
        
        return True
    
    def create_template(self, data):
        """Cria um novo template de ata"""
        template = MinuteTemplate(
            name=data.get('name'),
            description=data.get('description'),
            meeting_type=data.get('meeting_type'),
            structure=json.dumps(data.get('structure')),
            is_default=data.get('is_default', False),
            created_by=data.get('created_by')
        )
        
        # Se este for o template padrão, desmarcar outros do mesmo tipo
        if template.is_default:
            self.db_session.query(MinuteTemplate).filter_by(
                meeting_type=template.meeting_type,
                is_default=True
            ).update({'is_default': False})
        
        self.db_session.add(template)
        self.db_session.commit()
        
        return template
    
    def update_template(self, template_id, data):
        """Atualiza um template existente"""
        template = self.db_session.query(MinuteTemplate).filter_by(id=template_id).first()
        if not template:
            return None
        
        if 'name' in data:
            template.name = data['name']
        if 'description' in data:
            template.description = data['description']
        if 'meeting_type' in data:
            template.meeting_type = data['meeting_type']
        if 'structure' in data:
            template.structure = json.dumps(data['structure'])
        if 'is_default' in data:
            template.is_default = data['is_default']
            
            # Se este for o template padrão, desmarcar outros do mesmo tipo
            if template.is_default:
                self.db_session.query(MinuteTemplate).filter(
                    MinuteTemplate.meeting_type == template.meeting_type,
                    MinuteTemplate.id != template_id,
                    MinuteTemplate.is_default == True
                ).update({'is_default': False})
        
        self.db_session.commit()
        return template
    
    def delete_template(self, template_id):
        """Exclui um template"""
        template = self.db_session.query(MinuteTemplate).filter_by(id=template_id).first()
        if not template:
            return False
        
        # Não permitir exclusão de templates padrão
        if template.is_default:
            return False
        
        self.db_session.delete(template)
        self.db_session.commit()
        
        return True
    
    def generate_pdf(self, minute_id):
        """Gera um PDF da ata"""
        minute = self.db_session.query(MeetingMinute).filter_by(id=minute_id).first()
        if not minute:
            return None
        
        # Buscar seções e participantes
        sections = self.db_session.query(MinuteSection).filter_by(minute_id=minute_id).order_by(MinuteSection.sequence).all()
        participants = self.db_session.query(MinuteParticipant).filter_by(minute_id=minute_id).all()
        
        # Criar PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Configurar fonte
        pdf.add_font("NotoSans", fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
        pdf.set_font("NotoSans", size=12)
        
        # Título
        pdf.set_font("NotoSans", size=16)
        pdf.cell(0, 10, minute.title, ln=True, align='C')
        pdf.ln(5)
        
        # Informações básicas
        pdf.set_font("NotoSans", size=12)
        pdf.cell(0, 10, f"Data: {minute.meeting_date.strftime('%d/%m/%Y')}", ln=True)
        if minute.location:
            pdf.cell(0, 10, f"Local: {minute.location}", ln=True)
        if minute.start_time:
            pdf.cell(0, 10, f"Horário de início: {minute.start_time.strftime('%H:%M')}", ln=True)
        if minute.end_time:
            pdf.cell(0, 10, f"Horário de término: {minute.end_time.strftime('%H:%M')}", ln=True)
        pdf.ln(5)
        
        # Conteúdo das seções
        for section in sections:
            pdf.set_font("NotoSans", size=14)
            pdf.cell(0, 10, section.title, ln=True)
            pdf.set_font("NotoSans", size=12)
            
            # Quebrar o conteúdo em linhas
            content_lines = section.content.split('\n')
            for line in content_lines:
                pdf.multi_cell(0, 10, line)
            
            pdf.ln(5)
        
        # Lista de participantes
        if participants:
            pdf.set_font("NotoSans", size=14)
            pdf.cell(0, 10, "Lista de Presença", ln=True)
            pdf.set_font("NotoSans", size=12)
            
            for participant in participants:
                status = "Presente" if participant.attendance_status == "presente" else "Ausente" if participant.attendance_status == "ausente" else "Justificado"
                unit_text = f" (Unidade {participant.unit})" if participant.unit else ""
                role_text = f" - {participant.role}" if participant.role else ""
                
                pdf.cell(0, 10, f"{participant.name}{unit_text}{role_text}: {status}", ln=True)
        
        # Gerar o arquivo
        pdf_filename = f"ata_{minute_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        pdf_path = os.path.join(self.upload_folder, pdf_filename)
        pdf.output(pdf_path)
        
        return pdf_path
    
    def generate_attendance_list(self, minute_id):
        """Gera uma lista de presença em PDF"""
        minute = self.db_session.query(MeetingMinute).filter_by(id=minute_id).first()
        if not minute:
            return None
        
        # Buscar participantes
        participants = self.db_session.query(MinuteParticipant).filter_by(minute_id=minute_id).all()
        
        # Criar PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Configurar fonte
        pdf.add_font("NotoSans", fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
        pdf.set_font("NotoSans", size=12)
        
        # Título
        pdf.set_font("NotoSans", size=16)
        pdf.cell(0, 10, f"Lista de Presença - {minute.title}", ln=True, align='C')
        pdf.ln(5)
        
        # Informações básicas
        pdf.set_font("NotoSans", size=12)
        pdf.cell(0, 10, f"Data: {minute.meeting_date.strftime('%d/%m/%Y')}", ln=True)
        if minute.location:
            pdf.cell(0, 10, f"Local: {minute.location}", ln=True)
        pdf.ln(10)
        
        # Cabeçalho da tabela
        pdf.set_font("NotoSans", size=12, style='B')
        pdf.cell(60, 10, "Nome", border=1)
        pdf.cell(30, 10, "Unidade", border=1)
        pdf.cell(40, 10, "Função", border=1)
        pdf.cell(60, 10, "Assinatura", border=1, ln=True)
        
        # Linhas da tabela
        pdf.set_font("NotoSans", size=12)
        for participant in participants:
            pdf.cell(60, 10, participant.name, border=1)
            pdf.cell(30, 10, participant.unit or "", border=1)
            pdf.cell(40, 10, participant.role or "", border=1)
            pdf.cell(60, 10, "", border=1, ln=True)  # Espaço para assinatura
        
        # Adicionar linhas extras para participantes não previstos
        for _ in range(5):
            pdf.cell(60, 10, "", border=1)
            pdf.cell(30, 10, "", border=1)
            pdf.cell(40, 10, "", border=1)
            pdf.cell(60, 10, "", border=1, ln=True)
        
        # Gerar o arquivo
        pdf_filename = f"lista_presenca_{minute_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        pdf_path = os.path.join(self.upload_folder, pdf_filename)
        pdf.output(pdf_path)
        
        return pdf_path
    
    def send_minute_email(self, minute_id, recipients, subject=None, message=None):
        """Envia a ata por e-mail"""
        minute = self.db_session.query(MeetingMinute).filter_by(id=minute_id).first()
        if not minute:
            return False
        
        # Gerar o PDF da ata
        pdf_path = self.generate_pdf(minute_id)
        if not pdf_path:
            return False
        
        # Preparar assunto e mensagem
        if not subject:
            subject = f"Ata: {minute.title}"
        
        if not message:
            message = f"""
            Prezado(a) Condômino(a),
            
            Segue em anexo a ata da reunião "{minute.title}" realizada em {minute.meeting_date.strftime('%d/%m/%Y')}.
            
            Atenciosamente,
            Administração do Condomínio
            """
        
        # Lógica de envio de e-mail (simplificada)
        # Na prática, integraria com o sistema de e-mail existente
        
        # Simular envio bem-sucedido
        return True
    
    def get_minute_statistics(self):
        """Obtém estatísticas sobre as atas"""
        total_minutes = self.db_session.query(MeetingMinute).count()
        
        # Contagem por tipo
        type_counts = {}
        types = self.db_session.query(MeetingMinute.meeting_type, 
                                     self.db_session.func.count(MeetingMinute.id))\
                              .group_by(MeetingMinute.meeting_type).all()
        for meeting_type, count in types:
            type_counts[meeting_type] = count
        
        # Contagem por status
        status_counts = {}
        statuses = self.db_session.query(MeetingMinute.status, 
                                        self.db_session.func.count(MeetingMinute.id))\
                                 .group_by(MeetingMinute.status).all()
        for status, count in statuses:
            status_counts[status] = count
        
        # Atas recentes
        recent_minutes = self.db_session.query(MeetingMinute)\
                                      .order_by(MeetingMinute.created_at.desc())\
                                      .limit(5).all()
        
        return {
            'total_minutes': total_minutes,
            'type_counts': type_counts,
            'status_counts': status_counts,
            'recent_minutes': [
                {
                    'id': minute.id,
                    'title': minute.title,
                    'meeting_date': minute.meeting_date.strftime('%d/%m/%Y'),
                    'status': minute.status
                } for minute in recent_minutes
            ]
        }
    
    def search_minutes(self, query, filters=None):
        """Pesquisa atas com base em critérios"""
        base_query = self.db_session.query(MeetingMinute)
        
        # Aplicar filtros de texto
        if query:
            base_query = base_query.filter(
                MeetingMinute.title.ilike(f"%{query}%") |
                MeetingMinute.location.ilike(f"%{query}%")
            )
        
        # Aplicar filtros adicionais
        if filters:
            if 'meeting_type' in filters:
                base_query = base_query.filter(MeetingMinute.meeting_type == filters['meeting_type'])
            
            if 'status' in filters:
                base_query = base_query.filter(MeetingMinute.status == filters['status'])
            
            if 'start_date' in filters:
                start_date = datetime.strptime(filters['start_date'], '%Y-%m-%d')
                base_query = base_query.filter(MeetingMinute.meeting_date >= start_date)
            
            if 'end_date' in filters:
                end_date = datetime.strptime(filters['end_date'], '%Y-%m-%d')
                base_query = base_query.filter(MeetingMinute.meeting_date <= end_date)
        
        # Ordenar por data de reunião (mais recente primeiro)
        base_query = base_query.order_by(MeetingMinute.meeting_date.desc())
        
        return base_query.all()
    
    def get_minute_with_details(self, minute_id):
        """Obtém uma ata com todos os detalhes"""
        minute = self.db_session.query(MeetingMinute).filter_by(id=minute_id).first()
        if not minute:
            return None
        
        # Buscar seções, participantes e anexos
        sections = self.db_session.query(MinuteSection).filter_by(minute_id=minute_id).order_by(MinuteSection.sequence).all()
        participants = self.db_session.query(MinuteParticipant).filter_by(minute_id=minute_id).all()
        attachments = self.db_session.query(MinuteAttachment).filter_by(minute_id=minute_id).all()
        
        # Construir resposta detalhada
        result = {
            'id': minute.id,
            'meeting_type': minute.meeting_type,
            'meeting_date': minute.meeting_date.strftime('%Y-%m-%d'),
            'title': minute.title,
            'location': minute.location,
            'start_time': minute.start_time.strftime('%H:%M') if minute.start_time else None,
            'end_time': minute.end_time.strftime('%H:%M') if minute.end_time else None,
            'status': minute.status,
            'created_at': minute.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'published_at': minute.published_at.strftime('%Y-%m-%d %H:%M:%S') if minute.published_at else None,
            'sections': [
                {
                    'id': section.id,
                    'section_type': section.section_type,
                    'title': section.title,
                    'content': section.content,
                    'sequence': section.sequence
                } for section in sections
            ],
            'participants': [
                {
                    'id': participant.id,
                    'name': participant.name,
                    'role': participant.role,
                    'unit': participant.unit,
                    'attendance_status': participant.attendance_status,
                    'has_signature': bool(participant.signature)
                } for participant in participants
            ],
            'attachments': [
                {
                    'id': attachment.id,
                    'file_name': attachment.file_name,
                    'file_path': attachment.file_path,
                    'file_type': attachment.file_type,
                    'description': attachment.description,
                    'uploaded_at': attachment.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
                } for attachment in attachments
            ]
        }
        
        return result
    
    def generate_automated_warnings_from_minute(self, minute_id):
        """Gera advertências automatizadas com base nas deliberações de uma ata"""
        minute = self.db_session.query(MeetingMinute).filter_by(id=minute_id).first()
        if not minute or minute.status != 'publicada':
            return []
        
        # Buscar seções de deliberações
        deliberation_sections = self.db_session.query(MinuteSection).filter_by(
            minute_id=minute_id,
            section_type='deliberações'
        ).all()
        
        if not deliberation_sections:
            return []
        
        # Analisar o conteúdo das deliberações para identificar possíveis advertências
        warnings = []
        
        # Simplificado - na prática, usaria NLP ou regras mais sofisticadas
        for section in deliberation_sections:
            content = section.content.lower()
            
            # Palavras-chave que podem indicar necessidade de advertência
            keywords = {
                'proibido': 'Proibição estabelecida em assembleia',
                'multa': 'Aplicação de multa aprovada em assembleia',
                'advertência': 'Advertência aprovada em assembleia',
                'infração': 'Infração identificada em assembleia',
                'penalidade': 'Penalidade aprovada em assembleia',
                'notificação': 'Notificação aprovada em assembleia'
            }
            
            for keyword, title in keywords.items():
                if keyword in content:
                    # Encontrar o parágrafo relevante
                    paragraphs = content.split('\n')
                    relevant_paragraphs = [p for p in paragraphs if keyword in p.lower()]
                    
                    for paragraph in relevant_paragraphs:
                        # Simplificado - na prática, faria uma análise mais sofisticada
                        warning = {
                            'title': title,
                            'content': paragraph,
                            'source': f"Ata: {minute.title} ({minute.meeting_date.strftime('%d/%m/%Y')})",
                            'minute_id': minute.id
                        }
                        warnings.append(warning)
        
        return warnings

# Função para criar tabelas no banco de dados
def create_minute_tables(engine):
    """Cria as tabelas necessárias para o sistema de automatização de atas"""
    Base.metadata.create_all(engine)

# Rotas Flask para o sistema de automatização de atas (a serem integradas ao app.py)
def register_minute_routes(app, db):
    """Registra as rotas para o sistema de automatização de atas"""
    # Configurar o gerenciador de atas
    upload_folder = os.path.join(app.root_path, 'uploads', 'minutes')
    minute_manager = MinuteManager(db.session, upload_folder)
    
    # Criar templates padrão se não existirem
    minute_manager.create_default_templates()
    
    @app.route('/minutes')
    @login_required
    def minutes_list():
        """Lista de atas"""
        query = request.args.get('query', '')
        meeting_type = request.args.get('meeting_type', '')
        status = request.args.get('status', '')
        
        filters = {}
        if meeting_type:
            filters['meeting_type'] = meeting_type
        if status:
            filters['status'] = status
        
        minutes = minute_manager.search_minutes(query, filters)
        
        return render_template('minutes_list.html', title='Atas', minutes=minutes, 
                              query=query, meeting_type=meeting_type, status=status)
    
    @app.route('/minutes/dashboard')
    @login_required
    def minutes_dashboard():
        """Dashboard de atas"""
        statistics = minute_manager.get_minute_statistics()
        return render_template('minutes_dashboard.html', title='Dashboard de Atas', statistics=statistics)
    
    @app.route('/minutes/new', methods=['GET', 'POST'])
    @login_required
    def new_minute():
        """Página para criar nova ata"""
        if request.method == 'POST':
            data = {
                'meeting_type': request.form.get('meeting_type'),
                'meeting_date': request.form.get('meeting_date'),
                'title': request.form.get('title'),
                'location': request.form.get('location'),
                'start_time': request.form.get('start_time'),
                'template_id': request.form.get('template_id'),
                'created_by': current_user.id
            }
            
            minute = minute_manager.create_minute(data)
            
            flash('Ata criada com sucesso!', 'success')
            return redirect(url_for('edit_minute', minute_id=minute.id))
        
        # Buscar templates disponíveis
        templates = db.session.query(MinuteTemplate).all()
        
        return render_template('minute_new.html', title='Nova Ata', templates=templates)
    
    @app.route('/minutes/<int:minute_id>')
    @login_required
    def view_minute(minute_id):
        """Página para visualizar uma ata"""
        minute_data = minute_manager.get_minute_with_details(minute_id)
        if not minute_data:
            flash('Ata não encontrada', 'danger')
            return redirect(url_for('minutes_list'))
        
        return render_template('minute_view.html', title=minute_data['title'], minute=minute_data)
    
    @app.route('/minutes/<int:minute_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_minute(minute_id):
        """Página para editar uma ata"""
        minute_data = minute_manager.get_minute_with_details(minute_id)
        if not minute_data:
            flash('Ata não encontrada', 'danger')
            return redirect(url_for('minutes_list'))
        
        if request.method == 'POST':
            data = {
                'meeting_type': request.form.get('meeting_type'),
                'meeting_date': request.form.get('meeting_date'),
                'title': request.form.get('title'),
                'location': request.form.get('location'),
                'start_time': request.form.get('start_time'),
                'end_time': request.form.get('end_time'),
                'status': request.form.get('status')
            }
            
            # Processar seções
            sections = []
            section_ids = request.form.getlist('section_id[]')
            section_types = request.form.getlist('section_type[]')
            section_titles = request.form.getlist('section_title[]')
            section_contents = request.form.getlist('section_content[]')
            
            for i in range(len(section_ids)):
                sections.append({
                    'id': section_ids[i],
                    'section_type': section_types[i],
                    'title': section_titles[i],
                    'content': section_contents[i]
                })
            
            data['sections'] = sections
            
            # Processar participantes
            participants = []
            participant_ids = request.form.getlist('participant_id[]')
            participant_names = request.form.getlist('participant_name[]')
            participant_roles = request.form.getlist('participant_role[]')
            participant_units = request.form.getlist('participant_unit[]')
            participant_statuses = request.form.getlist('participant_status[]')
            
            for i in range(len(participant_ids)):
                participants.append({
                    'id': participant_ids[i],
                    'name': participant_names[i],
                    'role': participant_roles[i],
                    'unit': participant_units[i],
                    'attendance_status': participant_statuses[i]
                })
            
            data['participants'] = participants
            
            minute_manager.update_minute(minute_id, data)
            
            flash('Ata atualizada com sucesso!', 'success')
            return redirect(url_for('view_minute', minute_id=minute_id))
        
        return render_template('minute_edit.html', title=f'Editar: {minute_data["title"]}', minute=minute_data)
    
    @app.route('/minutes/<int:minute_id>/delete', methods=['POST'])
    @login_required
    def delete_minute(minute_id):
        """Rota para excluir uma ata"""
        success = minute_manager.delete_minute(minute_id)
        
        if success:
            flash('Ata excluída com sucesso!', 'success')
        else:
            flash('Erro ao excluir ata', 'danger')
        
        return redirect(url_for('minutes_list'))
    
    @app.route('/minutes/<int:minute_id>/pdf')
    @login_required
    def generate_minute_pdf(minute_id):
        """Rota para gerar PDF da ata"""
        pdf_path = minute_manager.generate_pdf(minute_id)
        
        if not pdf_path:
            flash('Erro ao gerar PDF', 'danger')
            return redirect(url_for('view_minute', minute_id=minute_id))
        
        # Retornar o arquivo para download
        return send_file(pdf_path, as_attachment=True)
    
    @app.route('/minutes/<int:minute_id>/attendance-list')
    @login_required
    def generate_attendance_list(minute_id):
        """Rota para gerar lista de presença"""
        pdf_path = minute_manager.generate_attendance_list(minute_id)
        
        if not pdf_path:
            flash('Erro ao gerar lista de presença', 'danger')
            return redirect(url_for('view_minute', minute_id=minute_id))
        
        # Retornar o arquivo para download
        return send_file(pdf_path, as_attachment=True)
    
    @app.route('/minutes/<int:minute_id>/send', methods=['POST'])
    @login_required
    def send_minute(minute_id):
        """Rota para enviar ata por e-mail"""
        recipients = request.form.get('recipients')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        success = minute_manager.send_minute_email(minute_id, recipients, subject, message)
        
        if success:
            flash('Ata enviada com sucesso!', 'success')
        else:
            flash('Erro ao enviar ata', 'danger')
        
        return redirect(url_for('view_minute', minute_id=minute_id))
    
    @app.route('/minutes/<int:minute_id>/attachment', methods=['POST'])
    @login_required
    def add_minute_attachment(minute_id):
        """Rota para adicionar anexo a uma ata"""
        if 'file' not in request.files:
            flash('Nenhum arquivo selecionado', 'danger')
            return redirect(url_for('edit_minute', minute_id=minute_id))
        
        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado', 'danger')
            return redirect(url_for('edit_minute', minute_id=minute_id))
        
        description = request.form.get('description', '')
        
        attachment = minute_manager.add_attachment(minute_id, file, description, current_user.id)
        
        if attachment:
            flash('Anexo adicionado com sucesso!', 'success')
        else:
            flash('Erro ao adicionar anexo', 'danger')
        
        return redirect(url_for('edit_minute', minute_id=minute_id))
    
    @app.route('/minutes/attachment/<int:attachment_id>/delete', methods=['POST'])
    @login_required
    def delete_minute_attachment(attachment_id):
        """Rota para excluir anexo"""
        attachment = db.session.query(MinuteAttachment).filter_by(id=attachment_id).first()
        if not attachment:
            flash('Anexo não encontrado', 'danger')
            return redirect(url_for('minutes_list'))
        
        minute_id = attachment.minute_id
        
        success = minute_manager.delete_attachment(attachment_id)
        
        if success:
            flash('Anexo excluído com sucesso!', 'success')
        else:
            flash('Erro ao excluir anexo', 'danger')
        
        return redirect(url_for('edit_minute', minute_id=minute_id))
    
    @app.route('/minutes/templates')
    @login_required
    def minute_templates():
        """Lista de templates de ata"""
        templates = db.session.query(MinuteTemplate).all()
        return render_template('minute_templates.html', title='Templates de Ata', templates=templates)
    
    @app.route('/minutes/templates/new', methods=['GET', 'POST'])
    @login_required
    def new_minute_template():
        """Página para criar novo template de ata"""
        if request.method == 'POST':
            # Processar seções do template
            sections = []
            section_types = request.form.getlist('section_type[]')
            section_titles = request.form.getlist('section_title[]')
            section_contents = request.form.getlist('section_content[]')
            
            for i in range(len(section_types)):
                sections.append({
                    'section_type': section_types[i],
                    'title': section_titles[i],
                    'content': section_contents[i]
                })
            
            data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'meeting_type': request.form.get('meeting_type'),
                'structure': {'sections': sections},
                'is_default': request.form.get('is_default') == 'true',
                'created_by': current_user.id
            }
            
            template = minute_manager.create_template(data)
            
            flash('Template criado com sucesso!', 'success')
            return redirect(url_for('minute_templates'))
        
        return render_template('minute_template_form.html', title='Novo Template')
    
    @app.route('/minutes/templates/<int:template_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_minute_template(template_id):
        """Página para editar template de ata"""
        template = db.session.query(MinuteTemplate).filter_by(id=template_id).first()
        if not template:
            flash('Template não encontrado', 'danger')
            return redirect(url_for('minute_templates'))
        
        if request.method == 'POST':
            # Processar seções do template
            sections = []
            section_types = request.form.getlist('section_type[]')
            section_titles = request.form.getlist('section_title[]')
            section_contents = request.form.getlist('section_content[]')
            
            for i in range(len(section_types)):
                sections.append({
                    'section_type': section_types[i],
                    'title': section_titles[i],
                    'content': section_contents[i]
                })
            
            data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'meeting_type': request.form.get('meeting_type'),
                'structure': {'sections': sections},
                'is_default': request.form.get('is_default') == 'true'
            }
            
            minute_manager.update_template(template_id, data)
            
            flash('Template atualizado com sucesso!', 'success')
            return redirect(url_for('minute_templates'))
        
        # Preparar dados para o formulário
        structure = json.loads(template.structure)
        
        return render_template('minute_template_form.html', title='Editar Template', 
                              template=template, structure=structure)
    
    @app.route('/minutes/templates/<int:template_id>/delete', methods=['POST'])
    @login_required
    def delete_minute_template(template_id):
        """Rota para excluir template de ata"""
        success = minute_manager.delete_template(template_id)
        
        if success:
            flash('Template excluído com sucesso!', 'success')
        else:
            flash('Erro ao excluir template. Templates padrão não podem ser excluídos.', 'danger')
        
        return redirect(url_for('minute_templates'))
    
    @app.route('/minutes/<int:minute_id>/generate-warnings', methods=['POST'])
    @login_required
    def generate_warnings_from_minute(minute_id):
        """Rota para gerar advertências a partir de uma ata"""
        warnings = minute_manager.generate_automated_warnings_from_minute(minute_id)
        
        if warnings:
            # Na prática, integraria com o sistema de advertências automatizadas
            flash(f'{len(warnings)} possíveis advertências identificadas!', 'success')
        else:
            flash('Nenhuma advertência identificada nesta ata', 'info')
        
        return redirect(url_for('view_minute', minute_id=minute_id))
    
    @app.route('/api/minutes/templates/<int:template_id>')
    @login_required
    def api_get_template(template_id):
        """API para obter detalhes de um template"""
        template = db.session.query(MinuteTemplate).filter_by(id=template_id).first()
        if not template:
            return jsonify({'error': 'Template não encontrado'}), 404
        
        structure = json.loads(template.structure)
        
        return jsonify({
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'meeting_type': template.meeting_type,
            'structure': structure,
            'is_default': template.is_default
        })
