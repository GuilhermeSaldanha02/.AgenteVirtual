# Guia de Implementação - Fase 2: Integração de Inteligência no Agente de Advertências

## Introdução

Este guia apresenta o passo a passo detalhado para implementar a Fase 2 do Agente de Advertências Condominial, que consiste na integração das funcionalidades inteligentes (leitura do regimento interno e detalhamento automático de ocorrências) na aplicação principal.

## Pré-requisitos

- Fase 1 (MVP) já implementada e funcionando
- Python 3.8+ instalado
- Flask e dependências instaladas
- Conhecimentos básicos de:
  - Python/Flask
  - HTML/CSS/JavaScript
  - Processamento de texto
  - SQLite (ou outro banco de dados configurado)

## Visão Geral da Implementação

A implementação da Fase 2 está dividida em quatro etapas principais:

1. **Preparação do ambiente**
2. **Upload e processamento automático de documentos**
3. **Integração de sugestões inteligentes no formulário de ocorrências**
4. **Interface para consulta avulsa ao regimento e convenção**

## Etapa 1: Preparação do Ambiente

### 1.1. Criar estrutura de diretórios

```bash
# No diretório raiz do projeto
mkdir -p backend/documentos_condominio
mkdir -p backend/documentos_processados
```

### 1.2. Instalar dependências adicionais

```bash
# Ativar ambiente virtual
source backend/venv/bin/activate

# Instalar dependências para processamento de PDF e análise de texto
pip install PyPDF2 nltk spacy
pip install python-Levenshtein fuzzywuzzy

# Baixar modelos de linguagem para português
python -m spacy download pt_core_news_sm
python -m nltk.downloader punkt stopwords
```

### 1.3. Criar módulos para processamento de documentos

Crie o arquivo `backend/document_processor.py`:

```python
# -*- coding: utf-8 -*-
import os
import re
import json
import PyPDF2
import nltk
import spacy
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from fuzzywuzzy import fuzz

# Carregar modelos de linguagem
nlp = spacy.load('pt_core_news_sm')
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
stop_words = set(stopwords.words('portuguese'))

class DocumentProcessor:
    """Classe para processar documentos do condomínio (regimento e convenção)"""
    
    def __init__(self, upload_dir, processed_dir):
        """
        Inicializa o processador de documentos
        
        Args:
            upload_dir: Diretório onde os documentos são carregados
            processed_dir: Diretório onde os documentos processados são salvos
        """
        self.upload_dir = upload_dir
        self.processed_dir = processed_dir
        
        # Garantir que os diretórios existem
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
    
    def extract_text_from_pdf(self, pdf_path):
        """Extrai texto de um arquivo PDF"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Erro ao extrair texto do PDF: {e}")
            return None
    
    def extract_articles(self, text):
        """Extrai artigos do texto do documento"""
        articles = {}
        
        # Padrões para identificar artigos
        patterns = [
            r'Art(?:igo)?\.?\s*(\d+)[\s\.\-:]+([^A].*?)(?=Art(?:igo)?\.?\s*\d+[\s\.\-:]|$)',
            r'Art(?:igo)?\s*(\d+)º[\s\.\-:]+([^A].*?)(?=Art(?:igo)?\s*\d+º[\s\.\-:]|$)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                article_num = match.group(1)
                article_text = match.group(2).strip()
                
                # Limpar o texto do artigo
                article_text = re.sub(r'\s+', ' ', article_text)
                
                # Armazenar o artigo
                articles[article_num] = article_text
        
        return articles
    
    def extract_chapters(self, text):
        """Extrai capítulos do texto do documento"""
        chapters = {}
        
        # Padrão para identificar capítulos
        pattern = r'CAPÍTULO\s+([IVX]+|[0-9]+)[\s\.\-:]+([^\n]+)'
        
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            chapter_num = match.group(1)
            chapter_title = match.group(2).strip()
            
            # Armazenar o capítulo
            chapters[chapter_num] = chapter_title
        
        return chapters
    
    def process_document(self, file_path, doc_type):
        """
        Processa um documento (regimento ou convenção)
        
        Args:
            file_path: Caminho do arquivo PDF
            doc_type: Tipo de documento ('regimento' ou 'convencao')
        
        Returns:
            Caminho do arquivo JSON processado
        """
        # Extrair texto do PDF
        text = self.extract_text_from_pdf(file_path)
        if not text:
            return None
        
        # Extrair artigos e capítulos
        articles = self.extract_articles(text)
        chapters = self.extract_chapters(text)
        
        # Criar estrutura de dados processada
        processed_data = {
            'type': doc_type,
            'filename': os.path.basename(file_path),
            'original_path': file_path,
            'processed_date': datetime.now().isoformat(),
            'articles': articles,
            'chapters': chapters,
            'full_text': text
        }
        
        # Salvar dados processados
        output_filename = f"{doc_type}_processado.json"
        output_path = os.path.join(self.processed_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=4)
        
        return output_path
    
    def search_in_documents(self, query, threshold=70):
        """
        Busca uma consulta nos documentos processados
        
        Args:
            query: Texto da consulta
            threshold: Limiar de similaridade (0-100)
        
        Returns:
            Lista de resultados relevantes
        """
        results = []
        
        # Processar a consulta
        query = query.lower()
        query_tokens = [token for token in query.split() if token not in stop_words]
        
        # Buscar em cada documento processado
        for doc_type in ['regimento', 'convencao']:
            json_path = os.path.join(self.processed_dir, f"{doc_type}_processado.json")
            if not os.path.exists(json_path):
                continue
            
            with open(json_path, 'r', encoding='utf-8') as f:
                doc_data = json.load(f)
            
            # Buscar em artigos
            for article_num, article_text in doc_data['articles'].items():
                article_text_lower = article_text.lower()
                
                # Verificar similaridade
                similarity = fuzz.partial_ratio(query, article_text_lower)
                
                # Verificar presença de tokens da consulta
                token_matches = sum(1 for token in query_tokens if token in article_text_lower)
                token_score = (token_matches / len(query_tokens)) * 100 if query_tokens else 0
                
                # Calcular pontuação combinada
                combined_score = (similarity + token_score) / 2
                
                if combined_score >= threshold:
                    results.append({
                        'doc_type': doc_type,
                        'article_num': article_num,
                        'text': article_text,
                        'score': combined_score
                    })
        
        # Ordenar resultados por pontuação
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def generate_description_suggestion(self, keywords, max_results=3):
        """
        Gera sugestão de descrição com base em palavras-chave
        
        Args:
            keywords: Lista de palavras-chave ou texto curto
            max_results: Número máximo de resultados a considerar
        
        Returns:
            Sugestão de descrição e artigos relacionados
        """
        # Buscar artigos relevantes
        search_results = self.search_in_documents(keywords)[:max_results]
        
        if not search_results:
            return {
                'suggested_description': None,
                'related_articles': []
            }
        
        # Extrair textos dos artigos encontrados
        article_texts = [result['text'] for result in search_results]
        
        # Gerar descrição sugerida
        suggested_description = f"Com base nas palavras-chave fornecidas, foi identificada uma possível infração relacionada a: {keywords}.\n\n"
        
        # Adicionar referência ao primeiro artigo mais relevante
        if search_results:
            top_result = search_results[0]
            doc_type_name = "Regimento Interno" if top_result['doc_type'] == 'regimento' else "Convenção Condominial"
            suggested_description += f"Esta ocorrência pode estar relacionada ao Artigo {top_result['article_num']} do {doc_type_name}, que estabelece:\n\n"
            suggested_description += f"\"{top_result['text']}\"\n\n"
            suggested_description += "Detalhes adicionais da ocorrência: [Preencher com informações específicas do caso]"
        
        return {
            'suggested_description': suggested_description,
            'related_articles': search_results
        }
```

### 1.4. Atualizar o modelo de dados

Modifique o arquivo `backend/app.py` para adicionar novos modelos:

```python
# Adicionar após os modelos existentes

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # 'regimento' ou 'convencao'
    filename = db.Column(db.String(255), nullable=False)
    original_path = db.Column(db.String(255), nullable=False)
    processed_path = db.Column(db.String(255), nullable=True)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    user = db.relationship('User', backref=db.backref('documents', lazy=True))
```

## Etapa 2: Upload e Processamento Automático de Documentos

### 2.1. Criar interface para upload de documentos

Crie o arquivo `backend/templates/admin_docs.html`:

```html
{% extends "layout.html" %}
{% block content %}
<div class="content-section">
    <h1>Gerenciamento de Documentos</h1>
    
    <div class="row mb-4">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h3>Regimento Interno</h3>
                </div>
                <div class="card-body">
                    {% if regimento %}
                        <p><strong>Arquivo atual:</strong> {{ regimento.filename }}</p>
                        <p><strong>Data de upload:</strong> {{ regimento.upload_date.strftime('%d/%m/%Y %H:%M') }}</p>
                        <p><strong>Status:</strong> 
                            {% if regimento.processed %}
                                <span class="text-success">Processado</span>
                            {% else %}
                                <span class="text-warning">Pendente</span>
                            {% endif %}
                        </p>
                        <form method="POST" action="{{ url_for('delete_document', doc_id=regimento.id) }}" class="mt-2">
                            <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Tem certeza que deseja excluir este documento?')">Excluir</button>
                        </form>
                    {% else %}
                        <p>Nenhum Regimento Interno carregado.</p>
                    {% endif %}
                    
                    <form method="POST" action="{{ url_for('upload_document') }}" enctype="multipart/form-data" class="mt-3">
                        <input type="hidden" name="doc_type" value="regimento">
                        <div class="form-group">
                            <label for="regimento_file">Carregar novo Regimento Interno (PDF)</label>
                            <input type="file" class="form-control-file" id="regimento_file" name="document" accept=".pdf" required>
                        </div>
                        <button type="submit" class="btn btn-primary mt-2">Enviar</button>
                    </form>
                </div>
            </div>
        </div>
        
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h3>Convenção Condominial</h3>
                </div>
                <div class="card-body">
                    {% if convencao %}
                        <p><strong>Arquivo atual:</strong> {{ convencao.filename }}</p>
                        <p><strong>Data de upload:</strong> {{ convencao.upload_date.strftime('%d/%m/%Y %H:%M') }}</p>
                        <p><strong>Status:</strong> 
                            {% if convencao.processed %}
                                <span class="text-success">Processado</span>
                            {% else %}
                                <span class="text-warning">Pendente</span>
                            {% endif %}
                        </p>
                        <form method="POST" action="{{ url_for('delete_document', doc_id=convencao.id) }}" class="mt-2">
                            <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Tem certeza que deseja excluir este documento?')">Excluir</button>
                        </form>
                    {% else %}
                        <p>Nenhuma Convenção Condominial carregada.</p>
                    {% endif %}
                    
                    <form method="POST" action="{{ url_for('upload_document') }}" enctype="multipart/form-data" class="mt-3">
                        <input type="hidden" name="doc_type" value="convencao">
                        <div class="form-group">
                            <label for="convencao_file">Carregar nova Convenção Condominial (PDF)</label>
                            <input type="file" class="form-control-file" id="convencao_file" name="document" accept=".pdf" required>
                        </div>
                        <button type="submit" class="btn btn-primary mt-2">Enviar</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    
    <div class="card mt-4">
        <div class="card-header">
            <h3>Processamento de Documentos</h3>
        </div>
        <div class="card-body">
            <p>O processamento dos documentos é realizado automaticamente após o upload.</p>
            <p>Se necessário, você pode forçar o reprocessamento dos documentos existentes:</p>
            <form method="POST" action="{{ url_for('reprocess_documents') }}">
                <button type="submit" class="btn btn-warning">Reprocessar Documentos</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

### 2.2. Atualizar o menu de navegação

Modifique o arquivo `backend/templates/layout.html` para adicionar o link para a página de documentos:

```html
<!-- No menu de navegação, adicione: -->
{% if current_user.is_authenticated %}
    <li class="nav-item">
        <a class="nav-link" href="{{ url_for('admin_docs') }}">Documentos</a>
    </li>
{% endif %}
```

### 2.3. Implementar rotas para gerenciamento de documentos

Adicione as seguintes rotas ao arquivo `backend/app.py`:

```python
# Importar o processador de documentos
from document_processor import DocumentProcessor

# Configurar diretórios
UPLOAD_FOLDER = os.path.join(app.root_path, 'documentos_condominio')
PROCESSED_FOLDER = os.path.join(app.root_path, 'documentos_processados')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Inicializar processador de documentos
document_processor = DocumentProcessor(UPLOAD_FOLDER, PROCESSED_FOLDER)

# --- Novas Rotas para Gerenciamento de Documentos ---

@app.route("/admin/docs")
@login_required
def admin_docs():
    """Página de gerenciamento de documentos"""
    # Buscar documentos existentes
    regimento = Document.query.filter_by(type='regimento').order_by(Document.upload_date.desc()).first()
    convencao = Document.query.filter_by(type='convencao').order_by(Document.upload_date.desc()).first()
    
    return render_template('admin_docs.html', title='Documentos', 
                          regimento=regimento, convencao=convencao)

@app.route("/admin/docs/upload", methods=['POST'])
@login_required
def upload_document():
    """Rota para upload de documento"""
    if 'document' not in request.files:
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('admin_docs'))
    
    file = request.files['document']
    doc_type = request.form.get('doc_type')
    
    if file.filename == '':
        flash('Nenhum arquivo selecionado', 'danger')
        return redirect(url_for('admin_docs'))
    
    if doc_type not in ['regimento', 'convencao']:
        flash('Tipo de documento inválido', 'danger')
        return redirect(url_for('admin_docs'))
    
    if file and allowed_file(file.filename, ['pdf']):
        # Salvar arquivo
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Remover documento anterior do mesmo tipo
        old_doc = Document.query.filter_by(type=doc_type).first()
        if old_doc:
            # Remover arquivo físico se existir
            if os.path.exists(old_doc.original_path):
                os.remove(old_doc.original_path)
            if old_doc.processed_path and os.path.exists(old_doc.processed_path):
                os.remove(old_doc.processed_path)
            
            # Remover do banco de dados
            db.session.delete(old_doc)
            db.session.commit()
        
        # Criar novo registro no banco de dados
        new_doc = Document(
            type=doc_type,
            filename=filename,
            original_path=file_path,
            user_id=current_user.id
        )
        
        db.session.add(new_doc)
        db.session.commit()
        
        # Processar documento em segundo plano
        processed_path = document_processor.process_document(file_path, doc_type)
        
        if processed_path:
            new_doc.processed_path = processed_path
            new_doc.processed = True
            db.session.commit()
            
            flash(f'{doc_type.capitalize()} carregado e processado com sucesso!', 'success')
        else:
            flash(f'{doc_type.capitalize()} carregado, mas ocorreu um erro no processamento.', 'warning')
        
        return redirect(url_for('admin_docs'))
    
    flash('Tipo de arquivo não permitido. Use apenas PDF.', 'danger')
    return redirect(url_for('admin_docs'))

@app.route("/admin/docs/<int:doc_id>/delete", methods=['POST'])
@login_required
def delete_document(doc_id):
    """Rota para excluir documento"""
    doc = Document.query.get_or_404(doc_id)
    
    # Remover arquivo físico
    if os.path.exists(doc.original_path):
        os.remove(doc.original_path)
    
    # Remover arquivo processado
    if doc.processed_path and os.path.exists(doc.processed_path):
        os.remove(doc.processed_path)
    
    # Remover do banco de dados
    db.session.delete(doc)
    db.session.commit()
    
    flash(f'{doc.type.capitalize()} excluído com sucesso!', 'success')
    return redirect(url_for('admin_docs'))

@app.route("/admin/docs/reprocess", methods=['POST'])
@login_required
def reprocess_documents():
    """Rota para reprocessar documentos existentes"""
    docs = Document.query.all()
    processed_count = 0
    
    for doc in docs:
        if os.path.exists(doc.original_path):
            processed_path = document_processor.process_document(doc.original_path, doc.type)
            
            if processed_path:
                doc.processed_path = processed_path
                doc.processed = True
                processed_count += 1
    
    db.session.commit()
    
    if processed_count > 0:
        flash(f'{processed_count} documento(s) reprocessado(s) com sucesso!', 'success')
    else:
        flash('Nenhum documento foi reprocessado.', 'info')
    
    return redirect(url_for('admin_docs'))

# Função auxiliar para verificar extensões permitidas
def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
```

## Etapa 3: Integração de Sugestões Inteligentes no Formulário de Ocorrências

### 3.1. Criar módulo para sugestões inteligentes

Crie o arquivo `backend/smart_suggestions.py`:

```python
# -*- coding: utf-8 -*-
import os
import json
from document_processor import DocumentProcessor

class SmartSuggestions:
    """Classe para fornecer sugestões inteligentes baseadas nos documentos processados"""
    
    def __init__(self, processed_dir):
        """
        Inicializa o sistema de sugestões
        
        Args:
            processed_dir: Diretório onde os documentos processados estão salvos
        """
        self.processed_dir = processed_dir
        self.document_processor = DocumentProcessor(None, processed_dir)
    
    def get_suggestions_from_keywords(self, keywords):
        """
        Obtém sugestões baseadas em palavras-chave
        
        Args:
            keywords: Texto com palavras-chave
        
        Returns:
            Dicionário com sugestões
        """
        return self.document_processor.generate_description_suggestion(keywords)
    
    def get_suggestions_from_text(self, text):
        """
        Analisa um texto e fornece sugestões
        
        Args:
            text: Texto a ser analisado
        
        Returns:
            Dicionário com sugestões
        """
        # Para textos mais longos, podemos extrair palavras-chave
        # e usar a mesma lógica de sugestão baseada em palavras-chave
        return self.document_processor.generate_description_suggestion(text)
    
    def get_article_details(self, doc_type, article_num):
        """
        Obtém detalhes de um artigo específico
        
        Args:
            doc_type: Tipo de documento ('regimento' ou 'convencao')
            article_num: Número do artigo
        
        Returns:
            Texto do artigo ou None se não encontrado
        """
        json_path = os.path.join(self.processed_dir, f"{doc_type}_processado.json")
        if not os.path.exists(json_path):
            return None
        
        with open(json_path, 'r', encoding='utf-8') as f:
            doc_data = json.load(f)
        
        return doc_data['articles'].get(article_num)
```

### 3.2. Atualizar o formulário de ocorrências

Modifique o arquivo `backend/templates/add_occurrence.html`:

```html
{% extends "layout.html" %}
{% block content %}
<div class="content-section">
    <form method="POST" action="" enctype="multipart/form-data">
        {{ form.hidden_tag() }}
        <fieldset class="form-group">
            <legend class="border-bottom mb-4">Registrar Nova Ocorrência</legend>
            <div class="form-group">
                {{ form.title.label(class="form-control-label") }}
                {% if form.title.errors %}
                    {{ form.title(class="form-control form-control-lg is-invalid") }}
                    <div class="invalid-feedback">
                        {% for error in form.title.errors %}
                            <span>{{ error }}</span>
                        {% endfor %}
                    </div>
                {% else %}
                    {{ form.title(class="form-control form-control-lg") }}
                {% endif %}
            </div>
            <div class="form-group mt-3">
                {{ form.unit_number.label(class="form-control-label") }}
                {% if form.unit_number.errors %}
                    {{ form.unit_number(class="form-control form-control-lg is-invalid") }}
                    <div class="invalid-feedback">
                        {% for error in form.unit_number.errors %}
                            <span>{{ error }}</span>
                        {% endfor %}
                    </div>
                {% else %}
                    {{ form.unit_number(class="form-control form-control-lg") }}
                {% endif %}
            </div>
            
            <!-- Nova seção para palavras-chave -->
            <div class="form-group mt-3">
                <label for="keywords" class="form-control-label">Palavras-chave (opcional)</label>
                <input type="text" id="keywords" name="keywords" class="form-control form-control-lg" placeholder="Ex: barulho festa noite">
                <small class="form-text text-muted">Digite palavras-chave relacionadas à ocorrência para obter sugestões automáticas.</small>
                <button type="button" id="btnGetSuggestions" class="btn btn-info btn-sm mt-2">Obter Sugestões</button>
            </div>
            
            <div class="form-group mt-3">
                {{ form.description.label(class="form-control-label") }}
                {% if form.description.errors %}
                    {{ form.description(class="form-control form-control-lg is-invalid") }}
                    <div class="invalid-feedback">
                        {% for error in form.description.errors %}
                            <span>{{ error }}</span>
                        {% endfor %}
                    </div>
                {% else %}
                    {{ form.description(class="form-control form-control-lg") }}
                {% endif %}
            </div>
            
            <!-- Área para exibir sugestões -->
            <div id="suggestionArea" class="mt-3" style="display: none;">
                <div class="card">
                    <div class="card-header bg-info text-white">
                        <h5 class="mb-0">Sugestões Baseadas no Regimento/Convenção</h5>
                    </div>
                    <div class="card-body">
                        <h6>Descrição Sugerida:</h6>
                        <div id="suggestedDescription" class="p-2 bg-light mb-3" style="border-left: 3px solid #17a2b8;"></div>
                        
                        <h6>Artigos Relacionados:</h6>
                        <div id="relatedArticles"></div>
                        
                        <button type="button" id="btnUseSuggestion" class="btn btn-success mt-2">Usar Sugestão</button>
                    </div>
                </div>
            </div>
            
            <!-- Seção para upload de imagens -->
            <div class="form-group mt-3">
                <label for="images">Imagens (opcional)</label>
                <input type="file" class="form-control-file" id="images" name="images" multiple accept="image/*">
                <small class="form-text text-muted">Você pode selecionar múltiplas imagens.</small>
            </div>
        </fieldset>
        <div class="form-group mt-3">
            {{ form.submit(class="btn btn-outline-info") }}
        </div>
    </form>
</div>

<!-- JavaScript para sugestões inteligentes -->
<script>
    document.addEventListener('DOMContentLoaded', function() {
        const keywordsInput = document.getElementById('keywords');
        const descriptionTextarea = document.getElementById('description');
        const btnGetSuggestions = document.getElementById('btnGetSuggestions');
        const btnUseSuggestion = document.getElementById('btnUseSuggestion');
        const suggestionArea = document.getElementById('suggestionArea');
        const suggestedDescription = document.getElementById('suggestedDescription');
        const relatedArticles = document.getElementById('relatedArticles');
        
        // Função para obter sugestões
        btnGetSuggestions.addEventListener('click', function() {
            const keywords = keywordsInput.value.trim();
            const description = descriptionTextarea.value.trim();
            
            if (!keywords && !description) {
                alert('Por favor, digite palavras-chave ou comece a escrever uma descrição para obter sugestões.');
                return;
            }
            
            // Mostrar indicador de carregamento
            suggestionArea.style.display = 'block';
            suggestedDescription.innerHTML = 'Buscando sugestões...';
            relatedArticles.innerHTML = '';
            
            // Fazer requisição para API de sugestões
            fetch('/api/suggestions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    keywords: keywords,
                    description: description
                }),
            })
            .then(response => response.json())
            .then(data => {
                // Exibir sugestões
                if (data.suggested_description) {
                    suggestedDescription.innerHTML = data.suggested_description.replace(/\n/g, '<br>');
                    
                    // Exibir artigos relacionados
                    if (data.related_articles && data.related_articles.length > 0) {
                        let articlesHtml = '<ul class="list-group">';
                        
                        data.related_articles.forEach(article => {
                            const docTypeName = article.doc_type === 'regimento' ? 'Regimento Interno' : 'Convenção Condominial';
                            
                            articlesHtml += `
                                <li class="list-group-item">
                                    <strong>${docTypeName} - Artigo ${article.article_num}</strong>
                                    <p>${article.text}</p>
                                    <small class="text-muted">Relevância: ${Math.round(article.score)}%</small>
                                </li>
                            `;
                        });
                        
                        articlesHtml += '</ul>';
                        relatedArticles.innerHTML = articlesHtml;
                    } else {
                        relatedArticles.innerHTML = '<p class="text-muted">Nenhum artigo relacionado encontrado.</p>';
                    }
                } else {
                    suggestedDescription.innerHTML = 'Nenhuma sugestão encontrada. Tente outras palavras-chave.';
                    relatedArticles.innerHTML = '';
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                suggestedDescription.innerHTML = 'Erro ao buscar sugestões. Tente novamente.';
            });
        });
        
        // Função para usar a sugestão
        btnUseSuggestion.addEventListener('click', function() {
            const suggestion = suggestedDescription.innerText;
            descriptionTextarea.value = suggestion;
        });
        
        // Também buscar sugestões quando o usuário digita na descrição
        let typingTimer;
        const doneTypingInterval = 1000; // 1 segundo
        
        descriptionTextarea.addEventListener('keyup', function() {
            clearTimeout(typingTimer);
            if (descriptionTextarea.value) {
                typingTimer = setTimeout(function() {
                    // Usar o texto atual como entrada para sugestões
                    keywordsInput.value = ''; // Limpar palavras-chave
                    btnGetSuggestions.click(); // Simular clique no botão
                }, doneTypingInterval);
            }
        });
    });
</script>
{% endblock %}
```

### 3.3. Implementar API para sugestões

Adicione a seguinte rota ao arquivo `backend/app.py`:

```python
# Importar o módulo de sugestões
from smart_suggestions import SmartSuggestions

# Inicializar sistema de sugestões
smart_suggestions = SmartSuggestions(PROCESSED_FOLDER)

@app.route("/api/suggestions", methods=['POST'])
@login_required
def get_suggestions():
    """API para obter sugestões inteligentes"""
    data = request.get_json()
    
    keywords = data.get('keywords', '').strip()
    description = data.get('description', '').strip()
    
    # Priorizar palavras-chave, se fornecidas
    if keywords:
        suggestions = smart_suggestions.get_suggestions_from_keywords(keywords)
    elif description:
        suggestions = smart_suggestions.get_suggestions_from_text(description)
    else:
        return jsonify({
            'suggested_description': None,
            'related_articles': []
        })
    
    return jsonify(suggestions)
```

## Etapa 4: Interface para Consulta Avulsa ao Regimento e Convenção

### 4.1. Criar página de consulta

Crie o arquivo `backend/templates/document_search.html`:

```html
{% extends "layout.html" %}
{% block content %}
<div class="content-section">
    <h1>Consulta ao Regimento e Convenção</h1>
    
    <div class="card mb-4">
        <div class="card-body">
            <form id="searchForm" class="mb-3">
                <div class="input-group">
                    <input type="text" id="searchQuery" class="form-control" placeholder="Digite sua consulta...">
                    <div class="input-group-append">
                        <button class="btn btn-primary" type="submit">Buscar</button>
                    </div>
                </div>
                <div class="form-check mt-2">
                    <input class="form-check-input" type="checkbox" id="searchRegimento" checked>
                    <label class="form-check-label" for="searchRegimento">
                        Regimento Interno
                    </label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="searchConvencao" checked>
                    <label class="form-check-label" for="searchConvencao">
                        Convenção Condominial
                    </label>
                </div>
            </form>
            
            <div id="searchResults"></div>
        </div>
    </div>
    
    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h3>Regimento Interno</h3>
                </div>
                <div class="card-body">
                    <div id="regimentoContent">
                        {% if regimento_processed %}
                            <div class="list-group">
                                {% for num, text in regimento_articles.items() %}
                                    <div class="list-group-item">
                                        <h5 class="mb-1">Artigo {{ num }}</h5>
                                        <p class="mb-1">{{ text }}</p>
                                    </div>
                                {% endfor %}
                            </div>
                        {% else %}
                            <p class="text-muted">Regimento Interno não disponível ou não processado.</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h3>Convenção Condominial</h3>
                </div>
                <div class="card-body">
                    <div id="convencaoContent">
                        {% if convencao_processed %}
                            <div class="list-group">
                                {% for num, text in convencao_articles.items() %}
                                    <div class="list-group-item">
                                        <h5 class="mb-1">Artigo {{ num }}</h5>
                                        <p class="mb-1">{{ text }}</p>
                                    </div>
                                {% endfor %}
                            </div>
                        {% else %}
                            <p class="text-muted">Convenção Condominial não disponível ou não processada.</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', function() {
        const searchForm = document.getElementById('searchForm');
        const searchQuery = document.getElementById('searchQuery');
        const searchRegimento = document.getElementById('searchRegimento');
        const searchConvencao = document.getElementById('searchConvencao');
        const searchResults = document.getElementById('searchResults');
        
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const query = searchQuery.value.trim();
            if (!query) {
                alert('Por favor, digite uma consulta.');
                return;
            }
            
            // Verificar documentos selecionados
            const docTypes = [];
            if (searchRegimento.checked) docTypes.push('regimento');
            if (searchConvencao.checked) docTypes.push('convencao');
            
            if (docTypes.length === 0) {
                alert('Por favor, selecione pelo menos um documento para buscar.');
                return;
            }
            
            // Mostrar indicador de carregamento
            searchResults.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"><span class="sr-only">Buscando...</span></div></div>';
            
            // Fazer requisição para API de busca
            fetch('/api/search_documents', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    doc_types: docTypes
                }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.results && data.results.length > 0) {
                    let resultsHtml = `
                        <div class="alert alert-success">
                            Encontrados ${data.results.length} resultados para "${query}"
                        </div>
                        <div class="list-group">
                    `;
                    
                    data.results.forEach(result => {
                        const docTypeName = result.doc_type === 'regimento' ? 'Regimento Interno' : 'Convenção Condominial';
                        
                        resultsHtml += `
                            <div class="list-group-item">
                                <h5 class="mb-1">${docTypeName} - Artigo ${result.article_num}</h5>
                                <p class="mb-1">${result.text}</p>
                                <small class="text-muted">Relevância: ${Math.round(result.score)}%</small>
                            </div>
                        `;
                    });
                    
                    resultsHtml += '</div>';
                    searchResults.innerHTML = resultsHtml;
                } else {
                    searchResults.innerHTML = `
                        <div class="alert alert-warning">
                            Nenhum resultado encontrado para "${query}". Tente outras palavras-chave.
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                searchResults.innerHTML = `
                    <div class="alert alert-danger">
                        Erro ao realizar a busca. Tente novamente.
                    </div>
                `;
            });
        });
    });
</script>
{% endblock %}
```

### 4.2. Atualizar o menu de navegação

Modifique novamente o arquivo `backend/templates/layout.html` para adicionar o link para a página de consulta:

```html
<!-- No menu de navegação, adicione: -->
{% if current_user.is_authenticated %}
    <li class="nav-item">
        <a class="nav-link" href="{{ url_for('document_search') }}">Consultar Documentos</a>
    </li>
{% endif %}
```

### 4.3. Implementar rotas para consulta de documentos

Adicione as seguintes rotas ao arquivo `backend/app.py`:

```python
@app.route("/documents/search")
@login_required
def document_search():
    """Página de consulta ao regimento e convenção"""
    regimento_articles = {}
    convencao_articles = {}
    regimento_processed = False
    convencao_processed = False
    
    # Verificar se existem documentos processados
    regimento_json = os.path.join(PROCESSED_FOLDER, 'regimento_processado.json')
    convencao_json = os.path.join(PROCESSED_FOLDER, 'convencao_processado.json')
    
    if os.path.exists(regimento_json):
        with open(regimento_json, 'r', encoding='utf-8') as f:
            regimento_data = json.load(f)
            regimento_articles = regimento_data.get('articles', {})
            regimento_processed = True
    
    if os.path.exists(convencao_json):
        with open(convencao_json, 'r', encoding='utf-8') as f:
            convencao_data = json.load(f)
            convencao_articles = convencao_data.get('articles', {})
            convencao_processed = True
    
    return render_template('document_search.html', title='Consultar Documentos',
                          regimento_articles=regimento_articles,
                          convencao_articles=convencao_articles,
                          regimento_processed=regimento_processed,
                          convencao_processed=convencao_processed)

@app.route("/api/search_documents", methods=['POST'])
@login_required
def search_documents():
    """API para buscar nos documentos"""
    data = request.get_json()
    
    query = data.get('query', '').strip()
    doc_types = data.get('doc_types', ['regimento', 'convencao'])
    
    if not query:
        return jsonify({
            'results': []
        })
    
    # Filtrar resultados por tipo de documento
    all_results = smart_suggestions.document_processor.search_in_documents(query)
    filtered_results = [r for r in all_results if r['doc_type'] in doc_types]
    
    return jsonify({
        'results': filtered_results
    })
```

## Etapa 5: Teste e Verificação

### 5.1. Criar banco de dados e tabelas

Execute o seguinte código para criar o banco de dados e as tabelas necessárias:

```python
# No terminal Python
from app import app, db
with app.app_context():
    db.create_all()
```

### 5.2. Executar a aplicação

```bash
# No terminal
cd backend
source venv/bin/activate
python app.py
```

### 5.3. Testar o fluxo completo

1. Acesse a aplicação no navegador (geralmente em http://127.0.0.1:5000/)
2. Faça login com suas credenciais
3. Acesse a página de Documentos e faça upload do Regimento Interno e da Convenção
4. Verifique se os documentos foram processados corretamente
5. Acesse a página de Consultar Documentos e teste a busca
6. Acesse a página de Nova Ocorrência e teste as sugestões inteligentes

## Conclusão

Você concluiu com sucesso a implementação da Fase 2 do Agente de Advertências Condominial! Agora o sistema possui:

1. Upload e processamento automático do Regimento Interno e da Convenção Condominial
2. Sugestões inteligentes no formulário de ocorrências, baseadas em palavras-chave ou no texto digitado
3. Interface dedicada para consulta avulsa ao regimento e convenção

Estas funcionalidades tornam o sistema muito mais inteligente e útil para a administração de condomínios, automatizando parte do trabalho de interpretação do regimento e convenção.

## Próximos Passos

Para continuar evoluindo o sistema, considere:

1. Melhorar os algoritmos de processamento de texto para maior precisão
2. Implementar um sistema de feedback para as sugestões
3. Adicionar suporte para outros tipos de documentos
4. Integrar com sistemas de e-mail para envio automático de advertências

## Solução de Problemas

Se encontrar problemas durante a implementação:

1. **Erro no processamento de PDF**: Verifique se o PDF está em formato texto e não apenas imagens. PDFs escaneados podem precisar de OCR.
2. **Artigos não detectados**: Ajuste as expressões regulares no método `extract_articles` para corresponder ao formato específico do seu regimento.
3. **Sugestões imprecisas**: Aumente o conjunto de dados de treinamento ou ajuste o limiar de similaridade.
4. **Erros de permissão**: Verifique se os diretórios têm permissões de escrita.

Para qualquer outro problema, consulte a documentação das bibliotecas utilizadas ou entre em contato com o suporte técnico.
