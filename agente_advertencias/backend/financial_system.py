# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from flask import render_template, flash, redirect, url_for, request, jsonify, send_file
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from fpdf2 import FPDF
import enum

Base = declarative_base()

# Enumerações para o sistema financeiro
class FineStatus(enum.Enum):
    PENDING = "pendente"
    NOTIFIED = "notificado"
    PAID = "pago"
    CONTESTED = "contestado"
    CANCELED = "cancelado"
    OVERDUE = "vencido"

class PaymentMethod(enum.Enum):
    BANK_SLIP = "boleto"
    CREDIT_CARD = "cartao_credito"
    BANK_TRANSFER = "transferencia"
    PIX = "pix"
    CASH = "dinheiro"
    OTHER = "outro"

# Modelos para o sistema financeiro de gestão de multas
class FineRule(Base):
    __tablename__ = 'fine_rule'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    article_reference = Column(String(255))  # Referência ao artigo do regimento/convenção
    law_reference = Column(String(255))      # Referência à lei (se aplicável)
    base_value = Column(Float, nullable=False)
    is_progressive = Column(Boolean, default=False)
    progression_type = Column(String(50))    # 'percentage', 'fixed_value'
    progression_value = Column(Float)        # Valor ou percentual de progressão
    max_progression = Column(Integer)        # Número máximo de progressões
    has_early_payment_discount = Column(Boolean, default=False)
    early_payment_discount = Column(Float)   # Percentual de desconto
    early_payment_days = Column(Integer)     # Dias para pagamento com desconto
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    fines = relationship("Fine", back_populates="rule")

class Fine(Base):
    __tablename__ = 'fine'
    
    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey('fine_rule.id'))
    occurrence_id = Column(Integer, ForeignKey('occurrence.id'))
    unit_number = Column(String(50), nullable=False)
    resident_name = Column(String(255))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    base_value = Column(Float, nullable=False)
    applied_value = Column(Float, nullable=False)  # Valor após aplicação de progressões
    discount_value = Column(Float)                 # Valor de desconto (se aplicável)
    final_value = Column(Float, nullable=False)    # Valor final a ser pago
    issue_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    status = Column(Enum(FineStatus), nullable=False, default=FineStatus.PENDING)
    payment_date = Column(DateTime)
    payment_method = Column(Enum(PaymentMethod))
    payment_reference = Column(String(255))        # Referência do pagamento
    payment_proof = Column(String(255))            # Caminho para comprovante
    contest_reason = Column(Text)                  # Motivo da contestação (se houver)
    contest_date = Column(DateTime)
    contest_status = Column(String(50))            # 'pending', 'approved', 'rejected'
    contest_resolution = Column(Text)              # Resolução da contestação
    notes = Column(Text)
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    rule = relationship("FineRule", back_populates="fines")
    notifications = relationship("FineNotification", back_populates="fine", cascade="all, delete-orphan")
    
    # Relacionamento com ocorrência (assumindo que existe um modelo Occurrence)
    # occurrence = relationship("Occurrence", back_populates="fines")

class FineNotification(Base):
    __tablename__ = 'fine_notification'
    
    id = Column(Integer, primary_key=True)
    fine_id = Column(Integer, ForeignKey('fine.id'), nullable=False)
    notification_type = Column(String(50), nullable=False)  # 'email', 'letter', 'app'
    sent_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    recipient = Column(String(255), nullable=False)
    content = Column(Text)
    attachment_path = Column(String(255))
    is_successful = Column(Boolean, default=True)
    error_message = Column(Text)
    created_by = Column(Integer, nullable=False)
    
    # Relacionamentos
    fine = relationship("Fine", back_populates="notifications")

class FinancialReport(Base):
    __tablename__ = 'financial_report'
    
    id = Column(Integer, primary_key=True)
    report_type = Column(String(50), nullable=False)  # 'monthly', 'quarterly', 'custom'
    title = Column(String(255), nullable=False)
    description = Column(Text)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    total_fines = Column(Integer)
    total_value = Column(Float)
    paid_value = Column(Float)
    pending_value = Column(Float)
    overdue_value = Column(Float)
    report_path = Column(String(255))
    created_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Classe para gerenciar o sistema financeiro de multas
class FinancialManager:
    def __init__(self, db_session, upload_folder):
        self.db_session = db_session
        self.upload_folder = upload_folder
        
        # Garantir que a pasta de upload existe
        os.makedirs(upload_folder, exist_ok=True)
    
    def create_fine_rule(self, data):
        """Cria uma nova regra de multa"""
        rule = FineRule(
            title=data.get('title'),
            description=data.get('description'),
            article_reference=data.get('article_reference'),
            law_reference=data.get('law_reference'),
            base_value=float(data.get('base_value')),
            is_progressive=data.get('is_progressive', False),
            progression_type=data.get('progression_type'),
            progression_value=float(data.get('progression_value')) if data.get('progression_value') else None,
            max_progression=int(data.get('max_progression')) if data.get('max_progression') else None,
            has_early_payment_discount=data.get('has_early_payment_discount', False),
            early_payment_discount=float(data.get('early_payment_discount')) if data.get('early_payment_discount') else None,
            early_payment_days=int(data.get('early_payment_days')) if data.get('early_payment_days') else None,
            is_active=data.get('is_active', True),
            created_by=data.get('created_by')
        )
        
        self.db_session.add(rule)
        self.db_session.commit()
        
        return rule
    
    def update_fine_rule(self, rule_id, data):
        """Atualiza uma regra de multa existente"""
        rule = self.db_session.query(FineRule).filter_by(id=rule_id).first()
        if not rule:
            return None
        
        # Atualizar campos
        if 'title' in data:
            rule.title = data['title']
        if 'description' in data:
            rule.description = data['description']
        if 'article_reference' in data:
            rule.article_reference = data['article_reference']
        if 'law_reference' in data:
            rule.law_reference = data['law_reference']
        if 'base_value' in data:
            rule.base_value = float(data['base_value'])
        if 'is_progressive' in data:
            rule.is_progressive = data['is_progressive']
        if 'progression_type' in data:
            rule.progression_type = data['progression_type']
        if 'progression_value' in data:
            rule.progression_value = float(data['progression_value']) if data['progression_value'] else None
        if 'max_progression' in data:
            rule.max_progression = int(data['max_progression']) if data['max_progression'] else None
        if 'has_early_payment_discount' in data:
            rule.has_early_payment_discount = data['has_early_payment_discount']
        if 'early_payment_discount' in data:
            rule.early_payment_discount = float(data['early_payment_discount']) if data['early_payment_discount'] else None
        if 'early_payment_days' in data:
            rule.early_payment_days = int(data['early_payment_days']) if data['early_payment_days'] else None
        if 'is_active' in data:
            rule.is_active = data['is_active']
        
        rule.updated_at = datetime.utcnow()
        
        self.db_session.commit()
        return rule
    
    def delete_fine_rule(self, rule_id):
        """Exclui uma regra de multa"""
        rule = self.db_session.query(FineRule).filter_by(id=rule_id).first()
        if not rule:
            return False
        
        # Verificar se existem multas associadas a esta regra
        fines_count = self.db_session.query(Fine).filter_by(rule_id=rule_id).count()
        if fines_count > 0:
            # Não permitir exclusão se houver multas associadas
            return False
        
        self.db_session.delete(rule)
        self.db_session.commit()
        
        return True
    
    def create_fine(self, data):
        """Cria uma nova multa"""
        # Buscar a regra para obter valores base
        rule = self.db_session.query(FineRule).filter_by(id=data.get('rule_id')).first()
        if not rule:
            return None
        
        # Calcular valores
        base_value = rule.base_value
        applied_value = base_value
        
        # Aplicar progressão, se aplicável
        if rule.is_progressive and data.get('progression_level'):
            progression_level = int(data.get('progression_level'))
            if progression_level > 0:
                if rule.progression_type == 'percentage':
                    for i in range(progression_level):
                        applied_value += applied_value * (rule.progression_value / 100)
                elif rule.progression_type == 'fixed_value':
                    applied_value += rule.progression_value * progression_level
        
        # Calcular desconto, se aplicável
        discount_value = None
        final_value = applied_value
        
        if rule.has_early_payment_discount:
            discount_value = applied_value * (rule.early_payment_discount / 100)
            # O desconto só será aplicado se o pagamento for feito dentro do prazo
        
        # Definir data de vencimento
        due_date = datetime.utcnow() + timedelta(days=30)  # Padrão: 30 dias
        if data.get('due_date'):
            due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d')
        
        fine = Fine(
            rule_id=data.get('rule_id'),
            occurrence_id=data.get('occurrence_id'),
            unit_number=data.get('unit_number'),
            resident_name=data.get('resident_name'),
            title=data.get('title') or rule.title,
            description=data.get('description'),
            base_value=base_value,
            applied_value=applied_value,
            discount_value=discount_value,
            final_value=final_value,
            issue_date=datetime.utcnow(),
            due_date=due_date,
            status=FineStatus.PENDING,
            notes=data.get('notes'),
            created_by=data.get('created_by')
        )
        
        self.db_session.add(fine)
        self.db_session.commit()
        
        return fine
    
    def update_fine(self, fine_id, data):
        """Atualiza uma multa existente"""
        fine = self.db_session.query(Fine).filter_by(id=fine_id).first()
        if not fine:
            return None
        
        # Atualizar campos básicos
        if 'unit_number' in data:
            fine.unit_number = data['unit_number']
        if 'resident_name' in data:
            fine.resident_name = data['resident_name']
        if 'title' in data:
            fine.title = data['title']
        if 'description' in data:
            fine.description = data['description']
        if 'due_date' in data:
            fine.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d')
        if 'notes' in data:
            fine.notes = data['notes']
        
        # Atualizar status
        if 'status' in data:
            new_status = data['status']
            if new_status == 'paid' and fine.status != FineStatus.PAID:
                fine.status = FineStatus.PAID
                fine.payment_date = datetime.utcnow()
                if 'payment_method' in data:
                    fine.payment_method = PaymentMethod(data['payment_method'])
                if 'payment_reference' in data:
                    fine.payment_reference = data['payment_reference']
                
                # Aplicar desconto se estiver dentro do prazo
                if fine.rule.has_early_payment_discount and fine.payment_date <= fine.due_date:
                    fine.final_value = fine.applied_value - fine.discount_value
            
            elif new_status == 'contested' and fine.status != FineStatus.CONTESTED:
                fine.status = FineStatus.CONTESTED
                fine.contest_date = datetime.utcnow()
                if 'contest_reason' in data:
                    fine.contest_reason = data['contest_reason']
                fine.contest_status = 'pending'
            
            elif new_status == 'canceled':
                fine.status = FineStatus.CANCELED
            
            elif new_status == 'notified':
                fine.status = FineStatus.NOTIFIED
        
        # Atualizar contestação
        if 'contest_status' in data and fine.status == FineStatus.CONTESTED:
            fine.contest_status = data['contest_status']
            if 'contest_resolution' in data:
                fine.contest_resolution = data['contest_resolution']
            
            # Se a contestação for aprovada, cancelar a multa
            if data['contest_status'] == 'approved':
                fine.status = FineStatus.CANCELED
        
        fine.updated_at = datetime.utcnow()
        
        self.db_session.commit()
        return fine
    
    def delete_fine(self, fine_id):
        """Exclui uma multa"""
        fine = self.db_session.query(Fine).filter_by(id=fine_id).first()
        if not fine:
            return False
        
        # Não permitir exclusão de multas pagas
        if fine.status == FineStatus.PAID:
            return False
        
        self.db_session.delete(fine)
        self.db_session.commit()
        
        return True
    
    def add_payment_proof(self, fine_id, file):
        """Adiciona comprovante de pagamento a uma multa"""
        fine = self.db_session.query(Fine).filter_by(id=fine_id).first()
        if not fine:
            return None
        
        # Salvar o arquivo
        filename = secure_filename(file.filename)
        file_path = f"payment_proof_{fine_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
        full_path = os.path.join(self.upload_folder, file_path)
        file.save(full_path)
        
        # Atualizar a multa
        fine.payment_proof = file_path
        self.db_session.commit()
        
        return file_path
    
    def send_notification(self, fine_id, data):
        """Envia uma notificação sobre a multa"""
        fine = self.db_session.query(Fine).filter_by(id=fine_id).first()
        if not fine:
            return None
        
        notification = FineNotification(
            fine_id=fine_id,
            notification_type=data.get('notification_type'),
            recipient=data.get('recipient'),
            content=data.get('content'),
            created_by=data.get('created_by')
        )
        
        # Se for uma notificação por e-mail com anexo
        if data.get('notification_type') == 'email' and data.get('attach_pdf'):
            # Gerar PDF da multa
            pdf_path = self.generate_fine_pdf(fine_id)
            if pdf_path:
                notification.attachment_path = pdf_path
        
        self.db_session.add(notification)
        
        # Atualizar status da multa para notificado
        if fine.status == FineStatus.PENDING:
            fine.status = FineStatus.NOTIFIED
        
        self.db_session.commit()
        
        return notification
    
    def generate_fine_pdf(self, fine_id):
        """Gera um PDF da multa"""
        fine = self.db_session.query(Fine).filter_by(id=fine_id).first()
        if not fine:
            return None
        
        # Buscar a regra associada
        rule = self.db_session.query(FineRule).filter_by(id=fine.rule_id).first()
        
        # Criar PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Configurar fonte
        pdf.add_font("NotoSans", fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
        pdf.set_font("NotoSans", size=12)
        
        # Título
        pdf.set_font("NotoSans", size=16)
        pdf.cell(0, 10, "NOTIFICAÇÃO DE MULTA", ln=True, align='C')
        pdf.ln(5)
        
        # Informações básicas
        pdf.set_font("NotoSans", size=12)
        pdf.cell(0, 10, f"Multa Nº: {fine.id}", ln=True)
        pdf.cell(0, 10, f"Data de Emissão: {fine.issue_date.strftime('%d/%m/%Y')}", ln=True)
        pdf.cell(0, 10, f"Unidade: {fine.unit_number}", ln=True)
        if fine.resident_name:
            pdf.cell(0, 10, f"Residente: {fine.resident_name}", ln=True)
        pdf.ln(5)
        
        # Detalhes da multa
        pdf.set_font("NotoSans", size=14)
        pdf.cell(0, 10, "DETALHES DA INFRAÇÃO", ln=True)
        pdf.set_font("NotoSans", size=12)
        pdf.cell(0, 10, f"Título: {fine.title}", ln=True)
        
        # Descrição
        pdf.multi_cell(0, 10, f"Descrição: {fine.description}")
        pdf.ln(5)
        
        # Referências
        if rule:
            if rule.article_reference:
                pdf.cell(0, 10, f"Referência ao Regimento/Convenção: {rule.article_reference}", ln=True)
            if rule.law_reference:
                pdf.cell(0, 10, f"Referência Legal: {rule.law_reference}", ln=True)
        pdf.ln(5)
        
        # Valores
        pdf.set_font("NotoSans", size=14)
        pdf.cell(0, 10, "VALORES", ln=True)
        pdf.set_font("NotoSans", size=12)
        pdf.cell(0, 10, f"Valor Base: R$ {fine.base_value:.2f}", ln=True)
        
        if fine.applied_value != fine.base_value:
            pdf.cell(0, 10, f"Valor Aplicado: R$ {fine.applied_value:.2f}", ln=True)
        
        if fine.discount_value:
            pdf.cell(0, 10, f"Desconto para Pagamento Antecipado: R$ {fine.discount_value:.2f}", ln=True)
            pdf.cell(0, 10, f"Valor com Desconto (até {fine.due_date.strftime('%d/%m/%Y')}): R$ {(fine.applied_value - fine.discount_value):.2f}", ln=True)
        
        pdf.set_font("NotoSans", size=14)
        pdf.cell(0, 10, f"Valor Total: R$ {fine.final_value:.2f}", ln=True)
        pdf.ln(5)
        
        # Prazo e instruções
        pdf.set_font("NotoSans", size=14)
        pdf.cell(0, 10, "PRAZO E INSTRUÇÕES", ln=True)
        pdf.set_font("NotoSans", size=12)
        pdf.cell(0, 10, f"Data de Vencimento: {fine.due_date.strftime('%d/%m/%Y')}", ln=True)
        
        # Instruções de pagamento
        pdf.multi_cell(0, 10, """
        Instruções de Pagamento:
        1. O pagamento deve ser realizado até a data de vencimento.
        2. Após o vencimento, serão aplicados juros e correção monetária.
        3. O comprovante de pagamento deve ser enviado à administração.
        """)
        
        # Instruções para contestação
        pdf.multi_cell(0, 10, """
        Instruções para Contestação:
        1. A contestação deve ser apresentada por escrito à administração no prazo de 10 dias.
        2. A contestação deve conter justificativa e documentos comprobatórios, se houver.
        """)
        
        # Gerar o arquivo
        pdf_filename = f"multa_{fine_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        pdf_path = os.path.join(self.upload_folder, pdf_filename)
        pdf.output(pdf_path)
        
        return pdf_path
    
    def generate_financial_report(self, data):
        """Gera um relatório financeiro"""
        # Definir período
        start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d')
        
        # Buscar multas no período
        fines = self.db_session.query(Fine).filter(
            Fine.issue_date >= start_date,
            Fine.issue_date <= end_date
        ).all()
        
        # Calcular totais
        total_fines = len(fines)
        total_value = sum(fine.applied_value for fine in fines)
        paid_value = sum(fine.final_value for fine in fines if fine.status == FineStatus.PAID)
        pending_value = sum(fine.applied_value for fine in fines if fine.status in [FineStatus.PENDING, FineStatus.NOTIFIED])
        overdue_value = sum(fine.applied_value for fine in fines if fine.status in [FineStatus.PENDING, FineStatus.NOTIFIED] and fine.due_date < datetime.utcnow())
        
        # Criar relatório
        report = FinancialReport(
            report_type=data.get('report_type', 'custom'),
            title=data.get('title', f"Relatório Financeiro - {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"),
            description=data.get('description'),
            start_date=start_date,
            end_date=end_date,
            total_fines=total_fines,
            total_value=total_value,
            paid_value=paid_value,
            pending_value=pending_value,
            overdue_value=overdue_value,
            created_by=data.get('created_by')
        )
        
        self.db_session.add(report)
        self.db_session.flush()  # Para obter o ID
        
        # Gerar PDF do relatório
        pdf_path = self.generate_report_pdf(report.id, fines)
        if pdf_path:
            report.report_path = pdf_path
        
        self.db_session.commit()
        
        return report
    
    def generate_report_pdf(self, report_id, fines=None):
        """Gera um PDF do relatório financeiro"""
        report = self.db_session.query(FinancialReport).filter_by(id=report_id).first()
        if not report:
            return None
        
        # Se não foram fornecidas multas, buscar do banco
        if fines is None:
            fines = self.db_session.query(Fine).filter(
                Fine.issue_date >= report.start_date,
                Fine.issue_date <= report.end_date
            ).all()
        
        # Criar PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Configurar fonte
        pdf.add_font("NotoSans", fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
        pdf.set_font("NotoSans", size=12)
        
        # Título
        pdf.set_font("NotoSans", size=16)
        pdf.cell(0, 10, report.title, ln=True, align='C')
        pdf.ln(5)
        
        # Informações básicas
        pdf.set_font("NotoSans", size=12)
        pdf.cell(0, 10, f"Período: {report.start_date.strftime('%d/%m/%Y')} a {report.end_date.strftime('%d/%m/%Y')}", ln=True)
        if report.description:
            pdf.multi_cell(0, 10, f"Descrição: {report.description}")
        pdf.ln(5)
        
        # Resumo
        pdf.set_font("NotoSans", size=14)
        pdf.cell(0, 10, "RESUMO", ln=True)
        pdf.set_font("NotoSans", size=12)
        pdf.cell(0, 10, f"Total de Multas: {report.total_fines}", ln=True)
        pdf.cell(0, 10, f"Valor Total: R$ {report.total_value:.2f}", ln=True)
        pdf.cell(0, 10, f"Valor Pago: R$ {report.paid_value:.2f}", ln=True)
        pdf.cell(0, 10, f"Valor Pendente: R$ {report.pending_value:.2f}", ln=True)
        pdf.cell(0, 10, f"Valor Vencido: R$ {report.overdue_value:.2f}", ln=True)
        pdf.ln(10)
        
        # Detalhamento das multas
        pdf.set_font("NotoSans", size=14)
        pdf.cell(0, 10, "DETALHAMENTO DAS MULTAS", ln=True)
        pdf.set_font("NotoSans", size=10)
        
        # Cabeçalho da tabela
        pdf.cell(15, 10, "ID", border=1)
        pdf.cell(25, 10, "Unidade", border=1)
        pdf.cell(40, 10, "Data Emissão", border=1)
        pdf.cell(40, 10, "Vencimento", border=1)
        pdf.cell(30, 10, "Valor", border=1)
        pdf.cell(30, 10, "Status", border=1, ln=True)
        
        # Linhas da tabela
        for fine in fines:
            pdf.cell(15, 10, str(fine.id), border=1)
            pdf.cell(25, 10, fine.unit_number, border=1)
            pdf.cell(40, 10, fine.issue_date.strftime('%d/%m/%Y'), border=1)
            pdf.cell(40, 10, fine.due_date.strftime('%d/%m/%Y'), border=1)
            pdf.cell(30, 10, f"R$ {fine.applied_value:.2f}", border=1)
            pdf.cell(30, 10, fine.status.value, border=1, ln=True)
        
        # Gerar o arquivo
        pdf_filename = f"relatorio_{report_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        pdf_path = os.path.join(self.upload_folder, pdf_filename)
        pdf.output(pdf_path)
        
        return pdf_filename
    
    def get_financial_dashboard_data(self):
        """Obtém dados para o dashboard financeiro"""
        # Total de multas
        total_fines = self.db_session.query(Fine).count()
        
        # Contagem por status
        status_counts = {}
        statuses = self.db_session.query(Fine.status, 
                                        self.db_session.func.count(Fine.id))\
                                 .group_by(Fine.status).all()
        for status, count in statuses:
            status_counts[status.value] = count
        
        # Valores totais
        total_value = self.db_session.query(self.db_session.func.sum(Fine.applied_value)).scalar() or 0
        paid_value = self.db_session.query(self.db_session.func.sum(Fine.final_value))\
                                  .filter(Fine.status == FineStatus.PAID).scalar() or 0
        pending_value = self.db_session.query(self.db_session.func.sum(Fine.applied_value))\
                                     .filter(Fine.status.in_([FineStatus.PENDING, FineStatus.NOTIFIED])).scalar() or 0
        
        # Multas por mês (últimos 6 meses)
        today = datetime.utcnow()
        six_months_ago = today - timedelta(days=180)
        
        monthly_data = []
        for i in range(6):
            month_start = today.replace(day=1) - timedelta(days=30*i)
            month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            
            month_count = self.db_session.query(Fine)\
                                       .filter(Fine.issue_date >= month_start, 
                                              Fine.issue_date <= month_end).count()
            
            month_value = self.db_session.query(self.db_session.func.sum(Fine.applied_value))\
                                       .filter(Fine.issue_date >= month_start, 
                                              Fine.issue_date <= month_end).scalar() or 0
            
            monthly_data.append({
                'month': month_start.strftime('%m/%Y'),
                'count': month_count,
                'value': month_value
            })
        
        # Multas recentes
        recent_fines = self.db_session.query(Fine)\
                                    .order_by(Fine.issue_date.desc())\
                                    .limit(5).all()
        
        return {
            'total_fines': total_fines,
            'status_counts': status_counts,
            'total_value': total_value,
            'paid_value': paid_value,
            'pending_value': pending_value,
            'monthly_data': monthly_data,
            'recent_fines': [
                {
                    'id': fine.id,
                    'unit_number': fine.unit_number,
                    'title': fine.title,
                    'value': fine.applied_value,
                    'due_date': fine.due_date.strftime('%d/%m/%Y'),
                    'status': fine.status.value
                } for fine in recent_fines
            ]
        }
    
    def search_fines(self, query, filters=None):
        """Pesquisa multas com base em critérios"""
        base_query = self.db_session.query(Fine)
        
        # Aplicar filtros de texto
        if query:
            base_query = base_query.filter(
                Fine.unit_number.ilike(f"%{query}%") |
                Fine.resident_name.ilike(f"%{query}%") |
                Fine.title.ilike(f"%{query}%")
            )
        
        # Aplicar filtros adicionais
        if filters:
            if 'status' in filters:
                base_query = base_query.filter(Fine.status == FineStatus(filters['status']))
            
            if 'start_date' in filters:
                start_date = datetime.strptime(filters['start_date'], '%Y-%m-%d')
                base_query = base_query.filter(Fine.issue_date >= start_date)
            
            if 'end_date' in filters:
                end_date = datetime.strptime(filters['end_date'], '%Y-%m-%d')
                base_query = base_query.filter(Fine.issue_date <= end_date)
            
            if 'min_value' in filters:
                base_query = base_query.filter(Fine.applied_value >= float(filters['min_value']))
            
            if 'max_value' in filters:
                base_query = base_query.filter(Fine.applied_value <= float(filters['max_value']))
        
        # Ordenar por data de emissão (mais recente primeiro)
        base_query = base_query.order_by(Fine.issue_date.desc())
        
        return base_query.all()
    
    def get_fine_with_details(self, fine_id):
        """Obtém uma multa com todos os detalhes"""
        fine = self.db_session.query(Fine).filter_by(id=fine_id).first()
        if not fine:
            return None
        
        # Buscar regra e notificações
        rule = self.db_session.query(FineRule).filter_by(id=fine.rule_id).first()
        notifications = self.db_session.query(FineNotification).filter_by(fine_id=fine_id).all()
        
        # Construir resposta detalhada
        result = {
            'id': fine.id,
            'rule_id': fine.rule_id,
            'occurrence_id': fine.occurrence_id,
            'unit_number': fine.unit_number,
            'resident_name': fine.resident_name,
            'title': fine.title,
            'description': fine.description,
            'base_value': fine.base_value,
            'applied_value': fine.applied_value,
            'discount_value': fine.discount_value,
            'final_value': fine.final_value,
            'issue_date': fine.issue_date.strftime('%Y-%m-%d'),
            'due_date': fine.due_date.strftime('%Y-%m-%d'),
            'status': fine.status.value,
            'payment_date': fine.payment_date.strftime('%Y-%m-%d') if fine.payment_date else None,
            'payment_method': fine.payment_method.value if fine.payment_method else None,
            'payment_reference': fine.payment_reference,
            'payment_proof': fine.payment_proof,
            'contest_reason': fine.contest_reason,
            'contest_date': fine.contest_date.strftime('%Y-%m-%d') if fine.contest_date else None,
            'contest_status': fine.contest_status,
            'contest_resolution': fine.contest_resolution,
            'notes': fine.notes,
            'created_at': fine.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'rule': {
                'id': rule.id,
                'title': rule.title,
                'article_reference': rule.article_reference,
                'law_reference': rule.law_reference,
                'is_progressive': rule.is_progressive,
                'has_early_payment_discount': rule.has_early_payment_discount,
                'early_payment_discount': rule.early_payment_discount,
                'early_payment_days': rule.early_payment_days
            } if rule else None,
            'notifications': [
                {
                    'id': notification.id,
                    'notification_type': notification.notification_type,
                    'sent_date': notification.sent_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'recipient': notification.recipient,
                    'is_successful': notification.is_successful,
                    'has_attachment': bool(notification.attachment_path)
                } for notification in notifications
            ]
        }
        
        return result
    
    def generate_automated_fines_from_occurrences(self, days=30):
        """Gera multas automatizadas com base em ocorrências recentes"""
        # Esta função seria integrada com o sistema de ocorrências
        # Para o protótipo, vamos simular com dados fictícios
        
        # Buscar regras ativas
        rules = self.db_session.query(FineRule).filter_by(is_active=True).all()
        if not rules:
            return []
        
        # Simular ocorrências recentes
        # Na implementação real, buscaria do banco de dados
        recent_occurrences = [
            {
                'id': 1001,
                'unit_number': '101',
                'resident_name': 'João Silva',
                'title': 'Barulho excessivo após 22h',
                'description': 'Vizinhos relataram música alta e barulho de festa após as 22h, perturbando o sossego.',
                'created_by': 1
            },
            {
                'id': 1002,
                'unit_number': '203',
                'resident_name': 'Maria Souza',
                'title': 'Uso indevido de área comum',
                'description': 'Morador utilizou a área de lazer fora do horário permitido e deixou lixo no local.',
                'created_by': 1
            },
            {
                'id': 1003,
                'unit_number': '305',
                'resident_name': 'Carlos Oliveira',
                'title': 'Estacionamento em vaga de terceiros',
                'description': 'Veículo estacionado em vaga pertencente a outro condômino sem autorização.',
                'created_by': 1
            }
        ]
        
        # Palavras-chave para associar ocorrências a regras
        keywords = {
            'barulho': [rule for rule in rules if 'barulho' in rule.title.lower() or 'sossego' in rule.title.lower()],
            'área comum': [rule for rule in rules if 'área comum' in rule.title.lower() or 'lazer' in rule.title.lower()],
            'estacionamento': [rule for rule in rules if 'estacionamento' in rule.title.lower() or 'vaga' in rule.title.lower()],
            'lixo': [rule for rule in rules if 'lixo' in rule.title.lower() or 'resíduo' in rule.title.lower()]
        }
        
        # Gerar multas automatizadas
        generated_fines = []
        
        for occurrence in recent_occurrences:
            # Encontrar regra aplicável
            applicable_rules = []
            
            for keyword, keyword_rules in keywords.items():
                if (keyword in occurrence['title'].lower() or 
                    keyword in occurrence['description'].lower()) and keyword_rules:
                    applicable_rules.extend(keyword_rules)
            
            # Se encontrou regras aplicáveis, usar a primeira
            if applicable_rules:
                rule = applicable_rules[0]
                
                # Criar multa
                fine_data = {
                    'rule_id': rule.id,
                    'occurrence_id': occurrence['id'],
                    'unit_number': occurrence['unit_number'],
                    'resident_name': occurrence['resident_name'],
                    'title': f"Multa: {occurrence['title']}",
                    'description': f"Multa gerada automaticamente com base na ocorrência: {occurrence['description']}",
                    'created_by': occurrence['created_by']
                }
                
                fine = self.create_fine(fine_data)
                if fine:
                    generated_fines.append(fine)
        
        return generated_fines

# Função para criar tabelas no banco de dados
def create_financial_tables(engine):
    """Cria as tabelas necessárias para o sistema financeiro de gestão de multas"""
    Base.metadata.create_all(engine)

# Rotas Flask para o sistema financeiro (a serem integradas ao app.py)
def register_financial_routes(app, db):
    """Registra as rotas para o sistema financeiro de gestão de multas"""
    # Configurar o gerenciador financeiro
    upload_folder = os.path.join(app.root_path, 'uploads', 'financial')
    financial_manager = FinancialManager(db.session, upload_folder)
    
    @app.route('/financial/dashboard')
    @login_required
    def financial_dashboard():
        """Dashboard financeiro"""
        dashboard_data = financial_manager.get_financial_dashboard_data()
        return render_template('financial_dashboard.html', title='Dashboard Financeiro', data=dashboard_data)
    
    @app.route('/financial/rules')
    @login_required
    def fine_rules_list():
        """Lista de regras de multa"""
        rules = db.session.query(FineRule).all()
        return render_template('fine_rules_list.html', title='Regras de Multa', rules=rules)
    
    @app.route('/financial/rules/new', methods=['GET', 'POST'])
    @login_required
    def new_fine_rule():
        """Página para criar nova regra de multa"""
        if request.method == 'POST':
            data = {
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'article_reference': request.form.get('article_reference'),
                'law_reference': request.form.get('law_reference'),
                'base_value': request.form.get('base_value'),
                'is_progressive': request.form.get('is_progressive') == 'true',
                'progression_type': request.form.get('progression_type'),
                'progression_value': request.form.get('progression_value'),
                'max_progression': request.form.get('max_progression'),
                'has_early_payment_discount': request.form.get('has_early_payment_discount') == 'true',
                'early_payment_discount': request.form.get('early_payment_discount'),
                'early_payment_days': request.form.get('early_payment_days'),
                'is_active': request.form.get('is_active') == 'true',
                'created_by': current_user.id
            }
            
            rule = financial_manager.create_fine_rule(data)
            
            flash('Regra de multa criada com sucesso!', 'success')
            return redirect(url_for('fine_rules_list'))
        
        return render_template('fine_rule_form.html', title='Nova Regra de Multa')
    
    @app.route('/financial/rules/<int:rule_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_fine_rule(rule_id):
        """Página para editar regra de multa"""
        rule = db.session.query(FineRule).filter_by(id=rule_id).first()
        if not rule:
            flash('Regra de multa não encontrada', 'danger')
            return redirect(url_for('fine_rules_list'))
        
        if request.method == 'POST':
            data = {
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'article_reference': request.form.get('article_reference'),
                'law_reference': request.form.get('law_reference'),
                'base_value': request.form.get('base_value'),
                'is_progressive': request.form.get('is_progressive') == 'true',
                'progression_type': request.form.get('progression_type'),
                'progression_value': request.form.get('progression_value'),
                'max_progression': request.form.get('max_progression'),
                'has_early_payment_discount': request.form.get('has_early_payment_discount') == 'true',
                'early_payment_discount': request.form.get('early_payment_discount'),
                'early_payment_days': request.form.get('early_payment_days'),
                'is_active': request.form.get('is_active') == 'true'
            }
            
            financial_manager.update_fine_rule(rule_id, data)
            
            flash('Regra de multa atualizada com sucesso!', 'success')
            return redirect(url_for('fine_rules_list'))
        
        return render_template('fine_rule_form.html', title='Editar Regra de Multa', rule=rule)
    
    @app.route('/financial/rules/<int:rule_id>/delete', methods=['POST'])
    @login_required
    def delete_fine_rule(rule_id):
        """Rota para excluir regra de multa"""
        success = financial_manager.delete_fine_rule(rule_id)
        
        if success:
            flash('Regra de multa excluída com sucesso!', 'success')
        else:
            flash('Erro ao excluir regra de multa. Verifique se não existem multas associadas.', 'danger')
        
        return redirect(url_for('fine_rules_list'))
    
    @app.route('/financial/fines')
    @login_required
    def fines_list():
        """Lista de multas"""
        query = request.args.get('query', '')
        status = request.args.get('status', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        filters = {}
        if status:
            filters['status'] = status
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        
        fines = financial_manager.search_fines(query, filters)
        
        return render_template('fines_list.html', title='Multas', fines=fines, 
                              query=query, status=status, start_date=start_date, end_date=end_date)
    
    @app.route('/financial/fines/new', methods=['GET', 'POST'])
    @login_required
    def new_fine():
        """Página para criar nova multa"""
        if request.method == 'POST':
            data = {
                'rule_id': request.form.get('rule_id'),
                'occurrence_id': request.form.get('occurrence_id'),
                'unit_number': request.form.get('unit_number'),
                'resident_name': request.form.get('resident_name'),
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'progression_level': request.form.get('progression_level'),
                'due_date': request.form.get('due_date'),
                'notes': request.form.get('notes'),
                'created_by': current_user.id
            }
            
            fine = financial_manager.create_fine(data)
            
            flash('Multa criada com sucesso!', 'success')
            return redirect(url_for('view_fine', fine_id=fine.id))
        
        # Buscar regras disponíveis
        rules = db.session.query(FineRule).filter_by(is_active=True).all()
        
        return render_template('fine_form.html', title='Nova Multa', rules=rules)
    
    @app.route('/financial/fines/<int:fine_id>')
    @login_required
    def view_fine(fine_id):
        """Página para visualizar uma multa"""
        fine_data = financial_manager.get_fine_with_details(fine_id)
        if not fine_data:
            flash('Multa não encontrada', 'danger')
            return redirect(url_for('fines_list'))
        
        return render_template('fine_view.html', title=f"Multa #{fine_id}", fine=fine_data)
    
    @app.route('/financial/fines/<int:fine_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_fine(fine_id):
        """Página para editar uma multa"""
        fine_data = financial_manager.get_fine_with_details(fine_id)
        if not fine_data:
            flash('Multa não encontrada', 'danger')
            return redirect(url_for('fines_list'))
        
        if request.method == 'POST':
            data = {
                'unit_number': request.form.get('unit_number'),
                'resident_name': request.form.get('resident_name'),
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'due_date': request.form.get('due_date'),
                'notes': request.form.get('notes')
            }
            
            financial_manager.update_fine(fine_id, data)
            
            flash('Multa atualizada com sucesso!', 'success')
            return redirect(url_for('view_fine', fine_id=fine_id))
        
        return render_template('fine_edit.html', title=f"Editar Multa #{fine_id}", fine=fine_data)
    
    @app.route('/financial/fines/<int:fine_id>/status', methods=['POST'])
    @login_required
    def update_fine_status(fine_id):
        """Rota para atualizar status de uma multa"""
        data = {
            'status': request.form.get('status')
        }
        
        # Campos adicionais dependendo do status
        if request.form.get('status') == 'paid':
            data['payment_method'] = request.form.get('payment_method')
            data['payment_reference'] = request.form.get('payment_reference')
        
        elif request.form.get('status') == 'contested':
            data['contest_reason'] = request.form.get('contest_reason')
        
        financial_manager.update_fine(fine_id, data)
        
        flash('Status da multa atualizado com sucesso!', 'success')
        return redirect(url_for('view_fine', fine_id=fine_id))
    
    @app.route('/financial/fines/<int:fine_id>/contest', methods=['POST'])
    @login_required
    def resolve_contest(fine_id):
        """Rota para resolver contestação de multa"""
        data = {
            'contest_status': request.form.get('contest_status'),
            'contest_resolution': request.form.get('contest_resolution')
        }
        
        financial_manager.update_fine(fine_id, data)
        
        flash('Contestação resolvida com sucesso!', 'success')
        return redirect(url_for('view_fine', fine_id=fine_id))
    
    @app.route('/financial/fines/<int:fine_id>/payment-proof', methods=['POST'])
    @login_required
    def add_payment_proof(fine_id):
        """Rota para adicionar comprovante de pagamento"""
        if 'file' not in request.files:
            flash('Nenhum arquivo selecionado', 'danger')
            return redirect(url_for('view_fine', fine_id=fine_id))
        
        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado', 'danger')
            return redirect(url_for('view_fine', fine_id=fine_id))
        
        file_path = financial_manager.add_payment_proof(fine_id, file)
        
        if file_path:
            flash('Comprovante de pagamento adicionado com sucesso!', 'success')
        else:
            flash('Erro ao adicionar comprovante de pagamento', 'danger')
        
        return redirect(url_for('view_fine', fine_id=fine_id))
    
    @app.route('/financial/fines/<int:fine_id>/pdf')
    @login_required
    def generate_fine_pdf(fine_id):
        """Rota para gerar PDF da multa"""
        pdf_path = financial_manager.generate_fine_pdf(fine_id)
        
        if not pdf_path:
            flash('Erro ao gerar PDF', 'danger')
            return redirect(url_for('view_fine', fine_id=fine_id))
        
        # Retornar o arquivo para download
        return send_file(os.path.join(upload_folder, pdf_path), as_attachment=True)
    
    @app.route('/financial/fines/<int:fine_id>/notify', methods=['POST'])
    @login_required
    def send_fine_notification(fine_id):
        """Rota para enviar notificação sobre multa"""
        data = {
            'notification_type': request.form.get('notification_type'),
            'recipient': request.form.get('recipient'),
            'content': request.form.get('content'),
            'attach_pdf': request.form.get('attach_pdf') == 'true',
            'created_by': current_user.id
        }
        
        notification = financial_manager.send_notification(fine_id, data)
        
        if notification:
            flash('Notificação enviada com sucesso!', 'success')
        else:
            flash('Erro ao enviar notificação', 'danger')
        
        return redirect(url_for('view_fine', fine_id=fine_id))
    
    @app.route('/financial/fines/<int:fine_id>/delete', methods=['POST'])
    @login_required
    def delete_fine(fine_id):
        """Rota para excluir multa"""
        success = financial_manager.delete_fine(fine_id)
        
        if success:
            flash('Multa excluída com sucesso!', 'success')
            return redirect(url_for('fines_list'))
        else:
            flash('Erro ao excluir multa. Multas pagas não podem ser excluídas.', 'danger')
            return redirect(url_for('view_fine', fine_id=fine_id))
    
    @app.route('/financial/reports')
    @login_required
    def financial_reports_list():
        """Lista de relatórios financeiros"""
        reports = db.session.query(FinancialReport).order_by(FinancialReport.created_at.desc()).all()
        return render_template('financial_reports_list.html', title='Relatórios Financeiros', reports=reports)
    
    @app.route('/financial/reports/new', methods=['GET', 'POST'])
    @login_required
    def new_financial_report():
        """Página para criar novo relatório financeiro"""
        if request.method == 'POST':
            data = {
                'report_type': request.form.get('report_type'),
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'start_date': request.form.get('start_date'),
                'end_date': request.form.get('end_date'),
                'created_by': current_user.id
            }
            
            report = financial_manager.generate_financial_report(data)
            
            flash('Relatório financeiro gerado com sucesso!', 'success')
            return redirect(url_for('financial_reports_list'))
        
        return render_template('financial_report_form.html', title='Novo Relatório Financeiro')
    
    @app.route('/financial/reports/<int:report_id>/pdf')
    @login_required
    def download_report_pdf(report_id):
        """Rota para baixar PDF do relatório"""
        report = db.session.query(FinancialReport).filter_by(id=report_id).first()
        if not report or not report.report_path:
            flash('Relatório não encontrado ou PDF não disponível', 'danger')
            return redirect(url_for('financial_reports_list'))
        
        # Retornar o arquivo para download
        return send_file(os.path.join(upload_folder, report.report_path), as_attachment=True)
    
    @app.route('/financial/generate-automated-fines', methods=['POST'])
    @login_required
    def generate_automated_fines():
        """Rota para gerar multas automatizadas"""
        days = int(request.form.get('days', 30))
        
        fines = financial_manager.generate_automated_fines_from_occurrences(days)
        
        if fines:
            flash(f'{len(fines)} multas geradas automaticamente!', 'success')
        else:
            flash('Nenhuma multa gerada. Verifique se existem ocorrências recentes e regras ativas.', 'info')
        
        return redirect(url_for('fines_list'))
