# -*- coding: utf-8 -*-
import os
import re
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

# Modelos para a integração com leis vigentes
class Law(Base):
    __tablename__ = 'law'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    number = Column(String(50), nullable=False)
    jurisdiction = Column(String(20), nullable=False)  # municipal, estadual, federal
    category = Column(String(50), nullable=False)
    summary = Column(Text, nullable=False)
    full_text = Column(Text, nullable=False)
    official_link = Column(String(255))
    effective_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    articles = relationship("LawArticle", back_populates="law", cascade="all, delete-orphan")

class LawArticle(Base):
    __tablename__ = 'law_article'
    
    id = Column(Integer, primary_key=True)
    law_id = Column(Integer, ForeignKey('law.id'), nullable=False)
    article_number = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    
    # Relacionamentos
    law = relationship("Law", back_populates="articles")
    mappings = relationship("RegulationLawMapping", back_populates="law_article")

class RegulationLawMapping(Base):
    __tablename__ = 'regulation_law_mapping'
    
    id = Column(Integer, primary_key=True)
    document_type = Column(String(50), nullable=False)  # regimento_interno, convencao_condominial
    article_reference = Column(String(50), nullable=False)
    law_article_id = Column(Integer, ForeignKey('law_article.id'), nullable=False)
    relevance_score = Column(Integer, default=0)
    notes = Column(Text)
    
    # Relacionamentos
    law_article = relationship("LawArticle", back_populates="mappings")

# Classe para gerenciar a integração com leis vigentes
class LawIntegrationManager:
    def __init__(self, db_session, processed_docs_folder):
        self.db_session = db_session
        self.processed_docs_folder = processed_docs_folder
    
    def get_laws_by_category(self, category=None):
        """Obtém leis por categoria"""
        query = self.db_session.query(Law).filter(Law.is_active == True)
        if category:
            query = query.filter(Law.category == category)
        return query.order_by(Law.jurisdiction, Law.title).all()
    
    def get_law_by_id(self, law_id):
        """Obtém uma lei específica pelo ID"""
        return self.db_session.query(Law).filter_by(id=law_id).first()
    
    def get_law_article_by_id(self, article_id):
        """Obtém um artigo de lei específico pelo ID"""
        return self.db_session.query(LawArticle).filter_by(id=article_id).first()
    
    def search_laws(self, search_term):
        """Pesquisa leis por termo"""
        search_pattern = f"%{search_term}%"
        return self.db_session.query(Law).filter(
            (Law.title.ilike(search_pattern)) |
            (Law.summary.ilike(search_pattern)) |
            (Law.full_text.ilike(search_pattern))
        ).filter(Law.is_active == True).all()
    
    def get_relevant_laws_for_occurrence(self, keywords):
        """Obtém leis relevantes para uma ocorrência com base em palavras-chave"""
        # Identificar categorias relevantes com base nas palavras-chave
        categories = self._identify_categories_from_keywords(keywords)
        
        # Buscar leis nas categorias identificadas
        laws = []
        for category in categories:
            category_laws = self.get_laws_by_category(category)
            laws.extend(category_laws)
        
        # Se não encontrou leis por categoria, tenta busca direta
        if not laws:
            for keyword in keywords.split():
                keyword_laws = self.search_laws(keyword)
                for law in keyword_laws:
                    if law not in laws:
                        laws.append(law)
        
        return laws
    
    def _identify_categories_from_keywords(self, keywords):
        """Identifica categorias de leis com base em palavras-chave"""
        keywords_lower = keywords.lower()
        categories = []
        
        # Mapeamento de palavras-chave para categorias
        category_keywords = {
            'barulho': ['barulho', 'som', 'ruído', 'música', 'festa'],
            'obras': ['obra', 'reforma', 'construção', 'manutenção'],
            'animais': ['animal', 'cachorro', 'gato', 'pet', 'latido'],
            'estacionamento': ['estacionamento', 'vaga', 'garagem', 'veículo', 'carro'],
            'áreas_comuns': ['área comum', 'piscina', 'salão', 'playground', 'academia'],
            'segurança': ['segurança', 'incêndio', 'emergência', 'acidente'],
            'lixo': ['lixo', 'resíduo', 'descarte', 'sujeira']
        }
        
        for category, terms in category_keywords.items():
            if any(term in keywords_lower for term in terms):
                categories.append(category)
        
        return categories
    
    def get_mappings_for_regulation_article(self, document_type, article_reference):
        """Obtém mapeamentos de leis para um artigo específico do regimento/convenção"""
        return self.db_session.query(RegulationLawMapping).filter_by(
            document_type=document_type,
            article_reference=article_reference
        ).order_by(RegulationLawMapping.relevance_score.desc()).all()
    
    def create_or_update_mapping(self, document_type, article_reference, law_article_id, relevance_score=0, notes=None):
        """Cria ou atualiza um mapeamento entre regimento/convenção e lei"""
        mapping = self.db_session.query(RegulationLawMapping).filter_by(
            document_type=document_type,
            article_reference=article_reference,
            law_article_id=law_article_id
        ).first()
        
        if mapping:
            mapping.relevance_score = relevance_score
            mapping.notes = notes
        else:
            mapping = RegulationLawMapping(
                document_type=document_type,
                article_reference=article_reference,
                law_article_id=law_article_id,
                relevance_score=relevance_score,
                notes=notes
            )
            self.db_session.add(mapping)
        
        self.db_session.commit()
        return mapping
    
    def analyze_regulation_for_law_references(self):
        """Analisa o regimento/convenção para identificar referências a leis"""
        # Obter todas as leis ativas
        laws = self.db_session.query(Law).filter_by(is_active=True).all()
        if not laws:
            return False
        
        # Para cada tipo de documento
        for document_type in ['regimento_interno', 'convencao_condominial']:
            json_path = os.path.join(self.processed_docs_folder, f"{document_type}_artigos.json")
            if not os.path.exists(json_path):
                continue
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
                
                # Para cada artigo no documento
                for article in articles:
                    title = article.get('title', '')
                    text = article.get('text', '')
                    
                    # Para cada lei
                    for law in laws:
                        # Verificar se há menção à lei no texto do artigo
                        if law.number.lower() in text.lower() or law.title.lower() in text.lower():
                            # Criar mapeamento para o primeiro artigo da lei (simplificado)
                            if law.articles:
                                first_article = law.articles[0]
                                self.create_or_update_mapping(
                                    document_type=document_type,
                                    article_reference=title,
                                    law_article_id=first_article.id,
                                    relevance_score=10,  # Alta relevância por menção direta
                                    notes=f"Menção direta à {law.title} encontrada no texto do artigo."
                                )
            except Exception as e:
                print(f"Erro ao analisar {document_type} para referências a leis: {e}")
        
        return True
    
    def get_law_references_for_occurrence(self, occurrence):
        """Obtém referências a leis para uma ocorrência específica"""
        # Extrair palavras-chave da ocorrência
        keywords = f"{occurrence.title} {occurrence.description}"
        
        # Obter leis relevantes
        relevant_laws = self.get_relevant_laws_for_occurrence(keywords)
        
        # Formatar resultados
        results = []
        for law in relevant_laws:
            results.append({
                'id': law.id,
                'title': law.title,
                'number': law.number,
                'jurisdiction': law.jurisdiction,
                'summary': law.summary,
                'official_link': law.official_link
            })
        
        return results

# Função para criar tabelas no banco de dados
def create_law_integration_tables(engine):
    """Cria as tabelas necessárias para a integração com leis vigentes"""
    Base.metadata.create_all(engine)

# Função para popular o banco de dados com leis de exemplo
def populate_sample_laws(db_session):
    """Popula o banco de dados com algumas leis de exemplo"""
    # Verificar se já existem leis cadastradas
    if db_session.query(Law).count() > 0:
        return
    
    # Lei do Silêncio (Municipal)
    lei_silencio = Law(
        title="Lei do Silêncio Municipal",
        number="Lei Municipal nº 1234/2020",
        jurisdiction="municipal",
        category="barulho",
        summary="Estabelece limites de ruídos e horários para atividades em áreas residenciais",
        full_text="Art. 1º - É proibida a produção de ruídos excessivos em áreas residenciais entre 22h e 8h. Art. 2º - Considera-se ruído excessivo aquele que ultrapassa 50 decibéis no período noturno e 70 decibéis no período diurno.",
        official_link="https://www.municipio.gov.br/leis/1234",
        effective_date=datetime(2020, 1, 1),
        is_active=True
    )
    db_session.add(lei_silencio)
    
    # Artigos da Lei do Silêncio
    art1_silencio = LawArticle(
        law=lei_silencio,
        article_number="Art. 1º",
        content="É proibida a produção de ruídos excessivos em áreas residenciais entre 22h e 8h.",
        summary="Proibição de ruídos noturnos"
    )
    db_session.add(art1_silencio)
    
    art2_silencio = LawArticle(
        law=lei_silencio,
        article_number="Art. 2º",
        content="Considera-se ruído excessivo aquele que ultrapassa 50 decibéis no período noturno e 70 decibéis no período diurno.",
        summary="Definição de ruído excessivo"
    )
    db_session.add(art2_silencio)
    
    # Lei de Obras em Condomínios (Municipal)
    lei_obras = Law(
        title="Lei de Obras em Condomínios",
        number="Lei Municipal nº 5678/2021",
        jurisdiction="municipal",
        category="obras",
        summary="Regulamenta horários e condições para realização de obras em condomínios residenciais",
        full_text="Art. 1º - As obras em condomínios residenciais só podem ser realizadas de segunda a sexta-feira, das 8h às 18h, e aos sábados das 9h às 13h. Art. 2º - É proibida a realização de obras aos domingos e feriados.",
        official_link="https://www.municipio.gov.br/leis/5678",
        effective_date=datetime(2021, 3, 15),
        is_active=True
    )
    db_session.add(lei_obras)
    
    # Artigos da Lei de Obras
    art1_obras = LawArticle(
        law=lei_obras,
        article_number="Art. 1º",
        content="As obras em condomínios residenciais só podem ser realizadas de segunda a sexta-feira, das 8h às 18h, e aos sábados das 9h às 13h.",
        summary="Horários permitidos para obras"
    )
    db_session.add(art1_obras)
    
    art2_obras = LawArticle(
        law=lei_obras,
        article_number="Art. 2º",
        content="É proibida a realização de obras aos domingos e feriados.",
        summary="Proibição de obras em domingos e feriados"
    )
    db_session.add(art2_obras)
    
    # Lei de Animais em Condomínios (Estadual)
    lei_animais = Law(
        title="Lei de Animais em Condomínios",
        number="Lei Estadual nº 9876/2019",
        jurisdiction="estadual",
        category="animais",
        summary="Estabelece normas para a criação e manutenção de animais domésticos em condomínios",
        full_text="Art. 1º - É permitida a criação de animais domésticos em condomínios, desde que não causem incômodo aos demais moradores. Art. 2º - Os proprietários são responsáveis por manter a higiene e segurança relacionadas aos seus animais.",
        official_link="https://www.estado.gov.br/leis/9876",
        effective_date=datetime(2019, 6, 10),
        is_active=True
    )
    db_session.add(lei_animais)
    
    # Artigos da Lei de Animais
    art1_animais = LawArticle(
        law=lei_animais,
        article_number="Art. 1º",
        content="É permitida a criação de animais domésticos em condomínios, desde que não causem incômodo aos demais moradores.",
        summary="Permissão condicionada para animais"
    )
    db_session.add(art1_animais)
    
    art2_animais = LawArticle(
        law=lei_animais,
        article_number="Art. 2º",
        content="Os proprietários são responsáveis por manter a higiene e segurança relacionadas aos seus animais.",
        summary="Responsabilidade dos proprietários"
    )
    db_session.add(art2_animais)
    
    # Código Civil - Artigos sobre Condomínio (Federal)
    codigo_civil = Law(
        title="Código Civil - Disposições sobre Condomínio",
        number="Lei Federal nº 10.406/2002",
        jurisdiction="federal",
        category="geral",
        summary="Artigos do Código Civil que regulamentam condomínios edilícios",
        full_text="Art. 1.331 - Pode haver, em edificações, partes que são propriedade exclusiva, e partes que são propriedade comum dos condôminos. Art. 1.332 - Institui-se o condomínio edilício por ato entre vivos ou testamento, registrado no Cartório de Registro de Imóveis.",
        official_link="http://www.planalto.gov.br/ccivil_03/leis/2002/l10406.htm",
        effective_date=datetime(2003, 1, 11),
        is_active=True
    )
    db_session.add(codigo_civil)
    
    # Artigos do Código Civil
    art1331_cc = LawArticle(
        law=codigo_civil,
        article_number="Art. 1.331",
        content="Pode haver, em edificações, partes que são propriedade exclusiva, e partes que são propriedade comum dos condôminos.",
        summary="Definição de propriedade exclusiva e comum"
    )
    db_session.add(art1331_cc)
    
    art1332_cc = LawArticle(
        law=codigo_civil,
        article_number="Art. 1.332",
        content="Institui-se o condomínio edilício por ato entre vivos ou testamento, registrado no Cartório de Registro de Imóveis.",
        summary="Instituição do condomínio edilício"
    )
    db_session.add(art1332_cc)
    
    db_session.commit()

# Rotas Flask para a integração com leis vigentes (a serem integradas ao app.py)
def register_law_integration_routes(app, db):
    """Registra as rotas para a integração com leis vigentes"""
    law_manager = LawIntegrationManager(db.session, app.config['PROCESSED_DOCS_FOLDER'])
    
    @app.route('/leis')
    @login_required
    def law_list():
        """Página de listagem de leis"""
        category = request.args.get('category')
        laws = law_manager.get_laws_by_category(category)
        return render_template('law_list.html', title='Leis Vigentes', laws=laws, category=category)
    
    @app.route('/lei/<int:law_id>')
    @login_required
    def law_detail(law_id):
        """Página de detalhes de uma lei"""
        law = law_manager.get_law_by_id(law_id)
        if not law:
            flash('Lei não encontrada', 'danger')
            return redirect(url_for('law_list'))
        return render_template('law_detail.html', title=law.title, law=law)
    
    @app.route('/api/laws/search')
    @login_required
    def api_law_search():
        """API para pesquisa de leis"""
        search_term = request.args.get('q', '')
        
        if not search_term:
            return jsonify({'error': 'Termo de busca não fornecido'}), 400
        
        laws = law_manager.search_laws(search_term)
        
        return jsonify({
            'laws': [
                {
                    'id': law.id,
                    'title': law.title,
                    'number': law.number,
                    'jurisdiction': law.jurisdiction,
                    'category': law.category,
                    'summary': law.summary
                } for law in laws
            ],
            'count': len(laws)
        })
    
    @app.route('/api/laws/for-occurrence/<int:occurrence_id>')
    @login_required
    def api_laws_for_occurrence(occurrence_id):
        """API para obter leis relevantes para uma ocorrência"""
        from models import Occurrence  # Importar aqui para evitar circular import
        
        occurrence = db.session.query(Occurrence).filter_by(id=occurrence_id).first()
        if not occurrence:
            return jsonify({'error': 'Ocorrência não encontrada'}), 404
        
        law_references = law_manager.get_law_references_for_occurrence(occurrence)
        
        return jsonify({
            'occurrence_id': occurrence_id,
            'law_references': law_references
        })
    
    @app.route('/api/laws/analyze-regulations', methods=['POST'])
    @login_required
    def api_analyze_regulations():
        """API para analisar regimento/convenção em busca de referências a leis"""
        # Verificar permissões (idealmente apenas admin)
        # if current_user.role != 'admin':
        #     return jsonify({'error': 'Acesso não autorizado'}), 403
        
        success = law_manager.analyze_regulation_for_law_references()
        
        if success:
            return jsonify({'message': 'Análise concluída com sucesso'})
        else:
            return jsonify({'error': 'Erro ao analisar documentos'}), 500
