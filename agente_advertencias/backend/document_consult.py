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

# Modelos para a interface de consulta avulsa
class DocumentSearch(Base):
    __tablename__ = 'document_search'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    search_term = Column(String(255), nullable=False)
    document_type = Column(String(50))  # regimento_interno, convencao_condominial, all
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamento com o usuário (se implementado)
    # user = relationship("User", back_populates="searches")

class DocumentFavorite(Base):
    __tablename__ = 'document_favorite'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    document_type = Column(String(50), nullable=False)  # regimento_interno, convencao_condominial
    article_reference = Column(String(50), nullable=False)  # ex: "Artigo 15"
    article_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamento com o usuário (se implementado)
    # user = relationship("User", back_populates="favorites")

# Classe para gerenciar a consulta de documentos
class DocumentConsultManager:
    def __init__(self, app_config):
        self.processed_docs_folder = app_config['PROCESSED_DOCS_FOLDER']
    
    def get_document_structure(self, document_type):
        """Obtém a estrutura hierárquica do documento (capítulos, seções, artigos)"""
        json_path = os.path.join(self.processed_docs_folder, f"{document_type}_artigos.json")
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            # Analisar a estrutura do documento
            structure = {}
            for article in articles:
                title = article.get('title', '')
                # Extrair número do artigo
                article_match = re.match(r'Artigo (\d+)', title)
                if article_match:
                    article_num = int(article_match.group(1))
                    
                    # Determinar capítulo/seção (simplificado)
                    chapter = 1
                    if article_num <= 10:
                        chapter = 1
                    elif article_num <= 20:
                        chapter = 2
                    else:
                        chapter = 3
                    
                    if chapter not in structure:
                        structure[chapter] = {
                            'title': f'Capítulo {chapter}',
                            'articles': []
                        }
                    
                    structure[chapter]['articles'].append({
                        'number': article_num,
                        'title': title,
                        'text': article.get('text', '')
                    })
            
            return structure
        except Exception as e:
            print(f"Erro ao processar estrutura do documento: {e}")
            return None
    
    def search_documents(self, search_term, document_type=None):
        """Pesquisa nos documentos por termo específico"""
        results = []
        
        # Determinar quais arquivos JSON pesquisar
        json_files = []
        if document_type == "regimento_interno" or document_type is None:
            json_files.append(("regimento_interno_artigos.json", "Regimento Interno"))
        if document_type == "convencao_condominial" or document_type is None:
            json_files.append(("convencao_condominial_artigos.json", "Convenção Condominial"))
        
        # Preparar termos de busca
        search_terms = search_term.lower().split()
        
        # Buscar em cada arquivo JSON
        for json_file, source_name in json_files:
            file_path = os.path.join(self.processed_docs_folder, json_file)
            if not os.path.exists(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
                
                for article in articles:
                    # Verificar se algum termo de busca está presente no título ou texto do artigo
                    article_text = (article.get('title', '') + ' ' + article.get('text', '')).lower()
                    
                    # Calcular relevância (número de termos encontrados)
                    relevance = sum(1 for term in search_terms if term in article_text)
                    
                    if relevance > 0:
                        # Destacar os termos de busca no texto
                        highlighted_text = article.get('text', '')
                        for term in search_terms:
                            pattern = re.compile(re.escape(term), re.IGNORECASE)
                            highlighted_text = pattern.sub(f'<mark>{term}</mark>', highlighted_text)
                        
                        results.append({
                            'title': article.get('title', ''),
                            'text': article.get('text', ''),
                            'highlighted_text': highlighted_text,
                            'source': source_name,
                            'relevance': relevance
                        })
            except Exception as e:
                print(f"Erro ao processar {json_file}: {e}")
        
        # Ordenar resultados por relevância (mais relevantes primeiro)
        results.sort(key=lambda x: x['relevance'], reverse=True)
        
        return results
    
    def get_article_by_reference(self, document_type, article_reference):
        """Obtém um artigo específico pelo seu número/referência"""
        json_path = os.path.join(self.processed_docs_folder, f"{document_type}_artigos.json")
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            for article in articles:
                if article.get('title', '').startswith(article_reference):
                    return article
            
            return None
        except Exception as e:
            print(f"Erro ao buscar artigo: {e}")
            return None
    
    def get_related_articles(self, document_type, article_reference):
        """Obtém artigos relacionados (anterior e posterior)"""
        json_path = os.path.join(self.processed_docs_folder, f"{document_type}_artigos.json")
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            # Extrair número do artigo de referência
            ref_match = re.match(r'Artigo (\d+)', article_reference)
            if not ref_match:
                return None
            
            ref_num = int(ref_match.group(1))
            related = {'previous': None, 'next': None}
            
            # Encontrar artigos anterior e posterior
            for article in articles:
                title = article.get('title', '')
                article_match = re.match(r'Artigo (\d+)', title)
                if article_match:
                    article_num = int(article_match.group(1))
                    
                    if article_num == ref_num - 1:
                        related['previous'] = article
                    elif article_num == ref_num + 1:
                        related['next'] = article
            
            return related
        except Exception as e:
            print(f"Erro ao buscar artigos relacionados: {e}")
            return None
    
    def save_search_history(self, db_session, user_id, search_term, document_type=None):
        """Salva histórico de pesquisa do usuário"""
        search = DocumentSearch(
            user_id=user_id,
            search_term=search_term,
            document_type=document_type
        )
        db_session.add(search)
        db_session.commit()
    
    def get_search_history(self, db_session, user_id, limit=10):
        """Obtém histórico de pesquisas do usuário"""
        return db_session.query(DocumentSearch).filter_by(
            user_id=user_id
        ).order_by(DocumentSearch.created_at.desc()).limit(limit).all()
    
    def toggle_favorite(self, db_session, user_id, document_type, article_reference, article_text):
        """Adiciona ou remove um artigo dos favoritos"""
        favorite = db_session.query(DocumentFavorite).filter_by(
            user_id=user_id,
            document_type=document_type,
            article_reference=article_reference
        ).first()
        
        if favorite:
            db_session.delete(favorite)
            db_session.commit()
            return False  # Removido dos favoritos
        else:
            favorite = DocumentFavorite(
                user_id=user_id,
                document_type=document_type,
                article_reference=article_reference,
                article_text=article_text
            )
            db_session.add(favorite)
            db_session.commit()
            return True  # Adicionado aos favoritos
    
    def get_favorites(self, db_session, user_id):
        """Obtém artigos favoritos do usuário"""
        return db_session.query(DocumentFavorite).filter_by(
            user_id=user_id
        ).order_by(DocumentFavorite.created_at.desc()).all()

# Função para criar tabelas no banco de dados
def create_document_consult_tables(engine):
    """Cria as tabelas necessárias para a interface de consulta avulsa"""
    Base.metadata.create_all(engine)

# Rotas Flask para a interface de consulta avulsa (a serem integradas ao app.py)
def register_document_consult_routes(app, db):
    """Registra as rotas para a interface de consulta avulsa"""
    document_manager = DocumentConsultManager(app.config)
    
    @app.route('/consulta')
    @login_required
    def document_consult():
        """Página principal da interface de consulta"""
        return render_template('document_consult.html', title='Consulta de Documentos')
    
    @app.route('/api/document/search')
    @login_required
    def api_document_search():
        """API para pesquisa de documentos"""
        search_term = request.args.get('q', '')
        document_type = request.args.get('type')
        
        if not search_term:
            return jsonify({'error': 'Termo de busca não fornecido'}), 400
        
        results = document_manager.search_documents(search_term, document_type)
        
        # Salvar histórico de pesquisa
        document_manager.save_search_history(db.session, current_user.id, search_term, document_type)
        
        return jsonify({
            'results': results,
            'count': len(results)
        })
    
    @app.route('/api/document/structure')
    @login_required
    def api_document_structure():
        """API para obter estrutura do documento"""
        document_type = request.args.get('type', 'regimento_interno')
        
        structure = document_manager.get_document_structure(document_type)
        if not structure:
            return jsonify({'error': 'Documento não encontrado ou não processado'}), 404
        
        return jsonify(structure)
    
    @app.route('/api/document/article')
    @login_required
    def api_document_article():
        """API para obter um artigo específico"""
        document_type = request.args.get('type', 'regimento_interno')
        article_reference = request.args.get('ref', '')
        
        if not article_reference:
            return jsonify({'error': 'Referência de artigo não fornecida'}), 400
        
        article = document_manager.get_article_by_reference(document_type, article_reference)
        if not article:
            return jsonify({'error': 'Artigo não encontrado'}), 404
        
        related = document_manager.get_related_articles(document_type, article_reference)
        
        return jsonify({
            'article': article,
            'related': related
        })
    
    @app.route('/api/document/favorite', methods=['POST'])
    @login_required
    def api_document_favorite():
        """API para adicionar/remover favorito"""
        data = request.json
        document_type = data.get('type')
        article_reference = data.get('ref')
        article_text = data.get('text', '')
        
        if not document_type or not article_reference:
            return jsonify({'error': 'Dados incompletos'}), 400
        
        is_favorite = document_manager.toggle_favorite(
            db.session, 
            current_user.id, 
            document_type, 
            article_reference, 
            article_text
        )
        
        return jsonify({
            'is_favorite': is_favorite,
            'message': 'Artigo adicionado aos favoritos' if is_favorite else 'Artigo removido dos favoritos'
        })
    
    @app.route('/api/document/favorites')
    @login_required
    def api_document_favorites():
        """API para obter favoritos do usuário"""
        favorites = document_manager.get_favorites(db.session, current_user.id)
        
        return jsonify({
            'favorites': [
                {
                    'document_type': f.document_type,
                    'article_reference': f.article_reference,
                    'article_text': f.article_text,
                    'created_at': f.created_at.isoformat()
                } for f in favorites
            ]
        })
    
    @app.route('/api/document/history')
    @login_required
    def api_document_history():
        """API para obter histórico de pesquisas do usuário"""
        history = document_manager.get_search_history(db.session, current_user.id)
        
        return jsonify({
            'history': [
                {
                    'search_term': h.search_term,
                    'document_type': h.document_type,
                    'created_at': h.created_at.isoformat()
                } for h in history
            ]
        })
