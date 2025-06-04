# Integração das Funcionalidades Avançadas - Passo 4

Este arquivo contém as instruções para integrar os novos módulos desenvolvidos para o Passo 4 ao sistema principal do Agente de Advertências Condominial.

## Arquivos Implementados

1. **email_system.py** - Sistema de envio automático de e-mails com advertências em PDF
2. **document_consult.py** - Interface de consulta avulsa ao regimento e convenção
3. **law_integration.py** - Integração com leis vigentes
4. **announcement_system.py** - Sistema de elaboração de comunicados

## Passos para Integração

### 1. Atualizar o arquivo app.py

Abra o arquivo `app.py` e adicione as seguintes importações no início do arquivo:

```python
# Importar novos módulos
from email_system import create_email_tables, create_default_templates, EmailManager
from document_consult import create_document_consult_tables, register_document_consult_routes
from law_integration import create_law_integration_tables, populate_sample_laws, register_law_integration_routes
from announcement_system import create_announcement_tables, register_announcement_routes
from flask_mail import Mail
```

### 2. Configurar Flask-Mail

Adicione a configuração do Flask-Mail após a configuração do app:

```python
# Configuração do Flask-Mail
mail = Mail(app)
```

### 3. Criar tabelas no banco de dados

Adicione o seguinte código após a inicialização do banco de dados:

```python
# Criar tabelas para os novos módulos
with app.app_context():
    db.create_all()  # Cria tabelas existentes
    
    # Criar tabelas para os novos módulos
    engine = db.engine
    create_email_tables(engine)
    create_document_consult_tables(engine)
    create_law_integration_tables(engine)
    create_announcement_tables(engine)
    
    # Criar templates padrão de e-mail
    create_default_templates(db.session)
    
    # Povoar banco de dados com leis de exemplo
    populate_sample_laws(db.session)
```

### 4. Registrar rotas para os novos módulos

Adicione o seguinte código antes da linha `if __name__ == "__main__":`:

```python
# Registrar rotas para os novos módulos
register_document_consult_routes(app, db)
register_law_integration_routes(app, db)
register_announcement_routes(app, db, mail)
```

### 5. Modificar a rota de geração de PDF para incluir envio de e-mail

Modifique a rota `generate_warning_pdf` para incluir o envio de e-mail:

```python
@app.route("/occurrence/<int:occurrence_id>/generate_pdf")
@login_required
def generate_warning_pdf(occurrence_id):
    occurrence = Occurrence.query.get_or_404(occurrence_id)
    if occurrence.author != current_user:
        flash("Você não tem permissão para gerar PDF para esta ocorrência.", "danger")
        return redirect(url_for("list_occurrences"))
    
    # Código existente para gerar PDF
    pdf = PDF()
    pdf.add_page()
    # ... (resto do código existente)
    
    buffer = io.BytesIO()
    pdf_output = pdf.output(dest="S").encode("latin-1")
    buffer.write(pdf_output)
    buffer.seek(0)
    
    # Atualizar status da ocorrência
    occurrence.status = "Notificado (PDF Gerado)"
    db.session.commit()
    
    # Enviar e-mail com o PDF anexado
    email_manager = EmailManager(db.session)
    success, message = email_manager.send_warning_email(occurrence, pdf_attachment=pdf_output)
    
    if success:
        flash("PDF de advertência gerado e enviado por e-mail com sucesso!", "success")
    else:
        flash(f"PDF de advertência gerado com sucesso, mas não foi possível enviar por e-mail: {message}", "warning")
    
    return send_file(buffer, as_attachment=True, download_name=f"advertencia_{occurrence.id}.pdf", mimetype="application/pdf")
```

## Criação de Templates HTML

### 1. Template para Consulta Avulsa (document_consult.html)

Crie o arquivo `templates/document_consult.html`:

```html
{% extends "layout.html" %}
{% block content %}
    <div class="content-section">
        <h2>Consulta de Documentos</h2>
        
        <div class="row mb-4">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Pesquisar nos Documentos</h5>
                    </div>
                    <div class="card-body">
                        <form id="searchForm">
                            <div class="form-group">
                                <div class="input-group">
                                    <input type="text" id="searchQuery" class="form-control" placeholder="Digite palavras-chave para pesquisar...">
                                    <div class="input-group-append">
                                        <select id="documentType" class="form-control">
                                            <option value="">Todos os documentos</option>
                                            <option value="regimento_interno">Regimento Interno</option>
                                            <option value="convencao_condominial">Convenção Condominial</option>
                                        </select>
                                        <button type="submit" class="btn btn-primary">Pesquisar</button>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Histórico de Pesquisas</h5>
                    </div>
                    <div class="card-body">
                        <ul id="searchHistory" class="list-group">
                            <!-- Histórico de pesquisas será carregado via JavaScript -->
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Estrutura dos Documentos</h5>
                    </div>
                    <div class="card-body">
                        <ul class="nav nav-tabs" id="documentTabs" role="tablist">
                            <li class="nav-item">
                                <a class="nav-link active" id="regimento-tab" data-toggle="tab" href="#regimento" role="tab">Regimento</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" id="convencao-tab" data-toggle="tab" href="#convencao" role="tab">Convenção</a>
                            </li>
                        </ul>
                        <div class="tab-content mt-3" id="documentTabsContent">
                            <div class="tab-pane fade show active" id="regimento" role="tabpanel">
                                <div id="regimentoStructure">
                                    <!-- Estrutura do regimento será carregada via JavaScript -->
                                </div>
                            </div>
                            <div class="tab-pane fade" id="convencao" role="tabpanel">
                                <div id="convencaoStructure">
                                    <!-- Estrutura da convenção será carregada via JavaScript -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0" id="resultsTitle">Resultados da Pesquisa</h5>
                    </div>
                    <div class="card-body">
                        <div id="searchResults">
                            <!-- Resultados da pesquisa serão exibidos aqui -->
                            <p class="text-muted">Digite palavras-chave na caixa de pesquisa para buscar nos documentos.</p>
                        </div>
                        <div id="articleView" style="display: none;">
                            <!-- Visualização de artigo específico -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Carregar estrutura dos documentos
            loadDocumentStructure('regimento_interno', 'regimentoStructure');
            loadDocumentStructure('convencao_condominial', 'convencaoStructure');
            
            // Carregar histórico de pesquisas
            loadSearchHistory();
            
            // Configurar formulário de pesquisa
            document.getElementById('searchForm').addEventListener('submit', function(e) {
                e.preventDefault();
                const query = document.getElementById('searchQuery').value.trim();
                const type = document.getElementById('documentType').value;
                
                if (query) {
                    searchDocuments(query, type);
                }
            });
        });
        
        function loadDocumentStructure(documentType, targetElementId) {
            fetch(`/api/document/structure?type=${documentType}`)
                .then(response => response.json())
                .then(data => {
                    const targetElement = document.getElementById(targetElementId);
                    
                    if (Object.keys(data).length === 0) {
                        targetElement.innerHTML = '<p class="text-muted">Documento não encontrado ou não processado.</p>';
                        return;
                    }
                    
                    let html = '<ul class="list-group">';
                    
                    for (const chapterNum in data) {
                        const chapter = data[chapterNum];
                        html += `
                            <li class="list-group-item">
                                <div class="d-flex justify-content-between align-items-center">
                                    <span>${chapter.title}</span>
                                    <button class="btn btn-sm btn-link" onclick="toggleChapter(this)">+</button>
                                </div>
                                <ul class="list-group mt-2" style="display: none;">
                        `;
                        
                        for (const article of chapter.articles) {
                            html += `
                                <li class="list-group-item">
                                    <a href="#" onclick="viewArticle('${documentType}', 'Artigo ${article.number}'); return false;">
                                        Artigo ${article.number}
                                    </a>
                                </li>
                            `;
                        }
                        
                        html += `
                                </ul>
                            </li>
                        `;
                    }
                    
                    html += '</ul>';
                    targetElement.innerHTML = html;
                })
                .catch(error => {
                    console.error('Erro ao carregar estrutura do documento:', error);
                    document.getElementById(targetElementId).innerHTML = '<p class="text-danger">Erro ao carregar estrutura do documento.</p>';
                });
        }
        
        function toggleChapter(button) {
            const chapterContent = button.parentElement.nextElementSibling;
            const isHidden = chapterContent.style.display === 'none';
            
            chapterContent.style.display = isHidden ? 'block' : 'none';
            button.textContent = isHidden ? '-' : '+';
        }
        
        function loadSearchHistory() {
            fetch('/api/document/history')
                .then(response => response.json())
                .then(data => {
                    const historyElement = document.getElementById('searchHistory');
                    
                    if (data.history.length === 0) {
                        historyElement.innerHTML = '<li class="list-group-item text-muted">Nenhuma pesquisa recente.</li>';
                        return;
                    }
                    
                    let html = '';
                    for (const item of data.history) {
                        const docType = item.document_type ? `(${item.document_type})` : '';
                        html += `
                            <li class="list-group-item">
                                <a href="#" onclick="searchDocuments('${item.search_term}', '${item.document_type || ''}'); return false;">
                                    ${item.search_term} ${docType}
                                </a>
                            </li>
                        `;
                    }
                    
                    historyElement.innerHTML = html;
                })
                .catch(error => {
                    console.error('Erro ao carregar histórico de pesquisas:', error);
                });
        }
        
        function searchDocuments(query, type) {
            document.getElementById('searchQuery').value = query;
            if (type) {
                document.getElementById('documentType').value = type;
            }
            
            document.getElementById('resultsTitle').textContent = `Resultados para: "${query}"`;
            document.getElementById('searchResults').innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><p>Pesquisando...</p></div>';
            document.getElementById('searchResults').style.display = 'block';
            document.getElementById('articleView').style.display = 'none';
            
            const typeParam = type ? `&type=${type}` : '';
            fetch(`/api/document/search?q=${encodeURIComponent(query)}${typeParam}`)
                .then(response => response.json())
                .then(data => {
                    if (data.count === 0) {
                        document.getElementById('searchResults').innerHTML = '<p class="text-muted">Nenhum resultado encontrado.</p>';
                        return;
                    }
                    
                    let html = `<p>Encontrados ${data.count} resultados:</p><div class="list-group">`;
                    
                    for (const result of data.results) {
                        html += `
                            <div class="list-group-item">
                                <div class="d-flex justify-content-between align-items-center">
                                    <h5 class="mb-1">${result.title}</h5>
                                    <span class="badge badge-primary badge-pill">${result.source}</span>
                                </div>
                                <p class="mb-1">${result.highlighted_text}</p>
                                <small>
                                    <a href="#" onclick="viewArticle('${result.source === 'Regimento Interno' ? 'regimento_interno' : 'convencao_condominial'}', '${result.title}'); return false;">
                                        Ver artigo completo
                                    </a>
                                </small>
                            </div>
                        `;
                    }
                    
                    html += '</div>';
                    document.getElementById('searchResults').innerHTML = html;
                    
                    // Atualizar histórico de pesquisas
                    loadSearchHistory();
                })
                .catch(error => {
                    console.error('Erro na pesquisa:', error);
                    document.getElementById('searchResults').innerHTML = '<p class="text-danger">Erro ao realizar a pesquisa.</p>';
                });
        }
        
        function viewArticle(documentType, articleReference) {
            document.getElementById('searchResults').style.display = 'none';
            document.getElementById('articleView').style.display = 'block';
            document.getElementById('articleView').innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><p>Carregando artigo...</p></div>';
            
            fetch(`/api/document/article?type=${documentType}&ref=${encodeURIComponent(articleReference)}`)
                .then(response => response.json())
                .then(data => {
                    const article = data.article;
                    const related = data.related;
                    
                    let html = `
                        <h4>${article.title}</h4>
                        <div class="card mb-3">
                            <div class="card-body">
                                <p>${article.text}</p>
                            </div>
                        </div>
                    `;
                    
                    // Navegação entre artigos
                    html += '<div class="d-flex justify-content-between">';
                    
                    if (related.previous) {
                        html += `
                            <a href="#" onclick="viewArticle('${documentType}', '${related.previous.title}'); return false;" class="btn btn-outline-primary">
                                &laquo; ${related.previous.title}
                            </a>
                        `;
                    } else {
                        html += '<div></div>';
                    }
                    
                    if (related.next) {
                        html += `
                            <a href="#" onclick="viewArticle('${documentType}', '${related.next.title}'); return false;" class="btn btn-outline-primary">
                                ${related.next.title} &raquo;
                            </a>
                        `;
                    } else {
                        html += '<div></div>';
                    }
                    
                    html += '</div>';
                    
                    // Botão para voltar aos resultados
                    html += `
                        <div class="text-center mt-3">
                            <button onclick="document.getElementById('searchResults').style.display = 'block'; document.getElementById('articleView').style.display = 'none';" class="btn btn-secondary">
                                Voltar aos resultados
                            </button>
                        </div>
                    `;
                    
                    document.getElementById('articleView').innerHTML = html;
                    document.getElementById('resultsTitle').textContent = article.title;
                })
                .catch(error => {
                    console.error('Erro ao carregar artigo:', error);
                    document.getElementById('articleView').innerHTML = '<p class="text-danger">Erro ao carregar o artigo.</p>';
                });
        }
    </script>
{% endblock content %}
```

### 2. Template para Leis Vigentes (law_list.html)

Crie o arquivo `templates/law_list.html`:

```html
{% extends "layout.html" %}
{% block content %}
    <div class="content-section">
        <h2>Leis Vigentes</h2>
        
        <div class="row mb-4">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Pesquisar Leis</h5>
                    </div>
                    <div class="card-body">
                        <form id="lawSearchForm">
                            <div class="form-group">
                                <div class="input-group">
                                    <input type="text" id="lawSearchQuery" class="form-control" placeholder="Digite palavras-chave para pesquisar leis...">
                                    <div class="input-group-append">
                                        <button type="submit" class="btn btn-primary">Pesquisar</button>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Filtrar por Categoria</h5>
                    </div>
                    <div class="card-body">
                        <div class="list-group">
                            <a href="{{ url_for('law_list') }}" class="list-group-item list-group-item-action {% if not category %}active{% endif %}">
                                Todas as Categorias
                            </a>
                            <a href="{{ url_for('law_list', category='barulho') }}" class="list-group-item list-group-item-action {% if category == 'barulho' %}active{% endif %}">
                                Barulho
                            </a>
                            <a href="{{ url_for('law_list', category='obras') }}" class="list-group-item list-group-item-action {% if category == 'obras' %}active{% endif %}">
                                Obras
                            </a>
                            <a href="{{ url_for('law_list', category='animais') }}" class="list-group-item list-group-item-action {% if category == 'animais' %}active{% endif %}">
                                Animais
                            </a>
                            <a href="{{ url_for('law_list', category='geral') }}" class="list-group-item list-group-item-action {% if category == 'geral' %}active{% endif %}">
                                Geral
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Leis Disponíveis</h5>
                    </div>
                    <div class="card-body">
                        {% if laws %}
                            <div class="list-group">
                                {% for law in laws %}
                                    <div class="list-group-item">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <h5 class="mb-1">{{ law.title }}</h5>
                                            <span class="badge badge-{% if law.jurisdiction == 'municipal' %}primary{% elif law.jurisdiction == 'estadual' %}success{% else %}danger{% endif %} badge-pill">
                                                {{ law.jurisdiction|capitalize }}
                                            </span>
                                        </div>
                                        <p class="mb-1">{{ law.number }}</p>
                                        <p class="mb-1">{{ law.summary }}</p>
                                        <small>
                                            <a href="{{ url_for('law_detail', law_id=law.id) }}" class="btn btn-sm btn-outline-info">Ver Detalhes</a>
                                            {% if law.official_link %}
                                                <a href="{{ law.official_link }}" target="_blank" class="btn btn-sm btn-outline-secondary">Link Oficial</a>
                                            {% endif %}
                                        </small>
                                    </div>
                                {% endfor %}
                            </div>
                        {% else %}
                            <p class="text-muted">Nenhuma lei encontrada.</p>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Configurar formulário de pesquisa
            document.getElementById('lawSearchForm').addEventListener('submit', function(e) {
                e.preventDefault();
                const query = document.getElementById('lawSearchQuery').value.trim();
                
                if (query) {
                    window.location.href = `/api/laws/search?q=${encodeURIComponent(query)}`;
                }
            });
        });
    </script>
{% endblock content %}
```

### 3. Template para Comunicados (announcement_list.html)

Crie o arquivo `templates/announcement_list.html`:

```html
{% extends "layout.html" %}
{% block content %}
    <div class="content-section">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2>Comunicados</h2>
            <a href="{{ url_for('announcement_new') }}" class="btn btn-success">Novo Comunicado</a>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <ul class="nav nav-tabs card-header-tabs" id="announcementTabs" role="tablist">
                            <li class="nav-item">
                                <a class="nav-link active" id="published-tab" data-toggle="tab" href="#published" role="tab">Publicados</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" id="drafts-tab" data-toggle="tab" href="#drafts" role="tab">Rascunhos</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" id="archived-tab" data-toggle="tab" href="#archived" role="tab">Arquivados</a>
                            </li>
                        </ul>
                    </div>
                    <div class="card-body">
                        <div class="tab-content" id="announcementTabsContent">
                            <div class="tab-pane fade show active" id="published" role="tabpanel">
                                {% set published_announcements = announcements|selectattr('status', 'equalto', 'publicado')|list %}
                                {% if published_announcements %}
                                    <div class="list-group">
                                        {% for announcement in published_announcements %}
                                            <div class="list-group-item">
                                                <div class="d-flex justify-content-between align-items-center">
                                                    <h5 class="mb-1">{{ announcement.title }}</h5>
                                                    <span class="badge badge-{% if announcement.priority == 'alta' %}danger{% elif announcement.priority == 'média' %}warning{% else %}info{% endif %} badge-pill">
                                                        {{ announcement.priority|capitalize }}
                                                    </span>
                                                </div>
                                                <p class="mb-1">Categoria: {{ announcement.category }}</p>
                                                <p class="mb-1">Publicado em: {{ announcement.published_at.strftime('%d/%m/%Y %H:%M') if announcement.published_at else 'N/A' }}</p>
                                                <small>
                                                    <a href="{{ url_for('announcement_detail', announcement_id=announcement.id) }}" class="btn btn-sm btn-outline-info">Ver Detalhes</a>
                                                    <a href="{{ url_for('announcement_print', announcement_id=announcement.id) }}" class="btn btn-sm btn-outline-secondary">Versão para Impressão</a>
                                                </small>
                                            </div>
                                        {% endfor %}
                                    </div>
                                {% else %}
                                    <p class="text-muted">Nenhum comunicado publicado.</p>
                                {% endif %}
                            </div>
                            <div class="tab-pane fade" id="drafts" role="tabpanel">
                                {% set draft_announcements = announcements|selectattr('status', 'equalto', 'rascunho')|list %}
                                {% if draft_announcements %}
                                    <div class="list-group">
                                        {% for announcement in draft_announcements %}
                                            <div class="list-group-item">
                                                <div class="d-flex justify-content-between align-items-center">
                                                    <h5 class="mb-1">{{ announcement.title }}</h5>
                                                    <span class="badge badge-secondary badge-pill">Rascunho</span>
                                                </div>
                                                <p class="mb-1">Categoria: {{ announcement.category }}</p>
                                                <p class="mb-1">Criado em: {{ announcement.created_at.strftime('%d/%m/%Y %H:%M') }}</p>
                                                <small>
                                                    <a href="{{ url_for('announcement_edit', announcement_id=announcement.id) }}" class="btn btn-sm btn-outline-primary">Editar</a>
                                                    <a href="{{ url_for('announcement_distribution', announcement_id=announcement.id) }}" class="btn btn-sm btn-outline-info">Configurar Distribuição</a>
                                                </small>
                                            </div>
                                        {% endfor %}
                                    </div>
                                {% else %}
                                    <p class="text-muted">Nenhum rascunho de comunicado.</p>
                                {% endif %}
                            </div>
                            <div class="tab-pane fade" id="archived" role="tabpanel">
                                {% set archived_announcements = announcements|selectattr('status', 'equalto', 'arquivado')|list %}
                                {% if archived_announcements %}
                                    <div class="list-group">
                                        {% for announcement in archived_announcements %}
                                            <div class="list-group-item">
                                                <div class="d-flex justify-content-between align-items-center">
                                                    <h5 class="mb-1">{{ announcement.title }}</h5>
                                                    <span class="badge badge-dark badge-pill">Arquivado</span>
                                                </div>
                                                <p class="mb-1">Categoria: {{ announcement.category }}</p>
                                                <p class="mb-1">Arquivado em: {{ announcement.updated_at.strftime('%d/%m/%Y %H:%M') }}</p>
                                                <small>
                                                    <a href="{{ url_for('announcement_detail', announcement_id=announcement.id) }}" class="btn btn-sm btn-outline-info">Ver Detalhes</a>
                                                </small>
                                            </div>
                                        {% endfor %}
                                    </div>
                                {% else %}
                                    <p class="text-muted">Nenhum comunicado arquivado.</p>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
{% endblock content %}
```

## Testes a Serem Realizados

Após a integração, os seguintes testes devem ser realizados:

1. **Sistema de E-mail**
   - Configuração de SMTP
   - Cadastro de e-mails por unidade
   - Geração de PDF e envio automático
   - Verificação de logs de envio

2. **Consulta Avulsa**
   - Carregamento da estrutura dos documentos
   - Pesquisa por palavras-chave
   - Visualização de artigos específicos
   - Histórico de pesquisas

3. **Integração com Leis**
   - Listagem de leis por categoria
   - Pesquisa de leis
   - Visualização de detalhes de leis
   - Correlação com artigos do regimento/convenção

4. **Sistema de Comunicados**
   - Criação de comunicados
   - Configuração de distribuição
   - Publicação e envio por e-mail
   - Geração de versão para impressão

## Considerações Finais

Esta integração completa o Passo 4 do desenvolvimento do Agente de Advertências Condominial, adicionando funcionalidades avançadas que tornam o sistema mais completo e útil para a administração de condomínios.

Após a conclusão dos testes, será necessário atualizar a documentação do sistema e apresentar os resultados ao usuário, destacando as novas capacidades e como utilizá-las de forma eficiente.
