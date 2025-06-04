# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime, timedelta
from flask import render_template, flash, redirect, url_for, request, jsonify, send_file
from flask_login import current_user, login_required
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('system_improvements')

class SystemImprovements:
    """
    Classe responsável por implementar melhorias nas funcionalidades existentes
    do Agente de Advertências Condominial.
    """
    
    def __init__(self, app, db):
        """
        Inicializa o módulo de melhorias do sistema.
        
        Args:
            app: A aplicação Flask
            db: O objeto de banco de dados SQLAlchemy
        """
        self.app = app
        self.db = db
        self.config_path = os.path.join(app.root_path, 'config', 'system_config.json')
        
        # Garantir que a pasta de configuração existe
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Carregar ou criar configuração
        self.config = self._load_config()
        
        # Registrar rotas
        self._register_routes()
        
        # Aplicar melhorias
        self._apply_improvements()
        
        logger.info("Módulo de melhorias do sistema inicializado")
    
    def _load_config(self):
        """Carrega a configuração do sistema ou cria uma padrão se não existir"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar configuração: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()
    
    def _create_default_config(self):
        """Cria uma configuração padrão para o sistema"""
        default_config = {
            "version": "1.0.0",
            "last_updated": datetime.utcnow().isoformat(),
            "features": {
                "dark_mode": True,
                "notifications": True,
                "auto_refresh": False,
                "refresh_interval": 60,  # segundos
                "items_per_page": 10,
                "default_sort": "date_desc"
            },
            "performance": {
                "cache_enabled": True,
                "cache_timeout": 300,  # segundos
                "lazy_loading": True,
                "compress_responses": True
            },
            "ui": {
                "sidebar_collapsed": False,
                "show_tooltips": True,
                "compact_tables": False,
                "animation_speed": "normal"  # slow, normal, fast
            },
            "workflow": {
                "confirm_actions": True,
                "auto_save_drafts": True,
                "draft_save_interval": 60,  # segundos
                "show_recent_items": True,
                "recent_items_count": 5
            }
        }
        
        # Salvar configuração padrão
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            logger.info("Configuração padrão criada")
        except Exception as e:
            logger.error(f"Erro ao salvar configuração padrão: {e}")
        
        return default_config
    
    def _save_config(self):
        """Salva a configuração atual no arquivo"""
        try:
            self.config["last_updated"] = datetime.utcnow().isoformat()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Configuração salva com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configuração: {e}")
            return False
    
    def _register_routes(self):
        """Registra as rotas para as funcionalidades de melhoria do sistema"""
        app = self.app
        
        @app.route('/system/settings', methods=['GET', 'POST'])
        @login_required
        def system_settings():
            """Página de configurações do sistema"""
            if request.method == 'POST':
                # Atualizar configurações
                try:
                    # Features
                    self.config["features"]["dark_mode"] = request.form.get('dark_mode') == 'on'
                    self.config["features"]["notifications"] = request.form.get('notifications') == 'on'
                    self.config["features"]["auto_refresh"] = request.form.get('auto_refresh') == 'on'
                    self.config["features"]["refresh_interval"] = int(request.form.get('refresh_interval', 60))
                    self.config["features"]["items_per_page"] = int(request.form.get('items_per_page', 10))
                    self.config["features"]["default_sort"] = request.form.get('default_sort', 'date_desc')
                    
                    # Performance
                    self.config["performance"]["cache_enabled"] = request.form.get('cache_enabled') == 'on'
                    self.config["performance"]["cache_timeout"] = int(request.form.get('cache_timeout', 300))
                    self.config["performance"]["lazy_loading"] = request.form.get('lazy_loading') == 'on'
                    self.config["performance"]["compress_responses"] = request.form.get('compress_responses') == 'on'
                    
                    # UI
                    self.config["ui"]["sidebar_collapsed"] = request.form.get('sidebar_collapsed') == 'on'
                    self.config["ui"]["show_tooltips"] = request.form.get('show_tooltips') == 'on'
                    self.config["ui"]["compact_tables"] = request.form.get('compact_tables') == 'on'
                    self.config["ui"]["animation_speed"] = request.form.get('animation_speed', 'normal')
                    
                    # Workflow
                    self.config["workflow"]["confirm_actions"] = request.form.get('confirm_actions') == 'on'
                    self.config["workflow"]["auto_save_drafts"] = request.form.get('auto_save_drafts') == 'on'
                    self.config["workflow"]["draft_save_interval"] = int(request.form.get('draft_save_interval', 60))
                    self.config["workflow"]["show_recent_items"] = request.form.get('show_recent_items') == 'on'
                    self.config["workflow"]["recent_items_count"] = int(request.form.get('recent_items_count', 5))
                    
                    # Salvar configurações
                    if self._save_config():
                        flash('Configurações salvas com sucesso!', 'success')
                    else:
                        flash('Erro ao salvar configurações', 'danger')
                    
                    # Aplicar melhorias
                    self._apply_improvements()
                    
                except Exception as e:
                    logger.error(f"Erro ao atualizar configurações: {e}")
                    flash(f'Erro ao atualizar configurações: {str(e)}', 'danger')
                
                return redirect(url_for('system_settings'))
            
            return render_template('system_settings.html', title='Configurações do Sistema', config=self.config)
        
        @app.route('/system/dashboard')
        @login_required
        def system_dashboard():
            """Dashboard do sistema com estatísticas e informações de uso"""
            # Coletar estatísticas do sistema
            stats = self._collect_system_stats()
            return render_template('system_dashboard.html', title='Dashboard do Sistema', stats=stats)
        
        @app.route('/api/system/config')
        @login_required
        def api_system_config():
            """API para obter configuração do sistema (para uso em JavaScript)"""
            return jsonify(self.config)
        
        @app.route('/api/system/stats')
        @login_required
        def api_system_stats():
            """API para obter estatísticas do sistema (para uso em JavaScript)"""
            stats = self._collect_system_stats()
            return jsonify(stats)
        
        @app.route('/system/optimize-database', methods=['POST'])
        @login_required
        def optimize_database():
            """Rota para otimizar o banco de dados"""
            try:
                # Executar otimização do banco de dados
                self._optimize_database()
                flash('Banco de dados otimizado com sucesso!', 'success')
            except Exception as e:
                logger.error(f"Erro ao otimizar banco de dados: {e}")
                flash(f'Erro ao otimizar banco de dados: {str(e)}', 'danger')
            
            return redirect(url_for('system_dashboard'))
        
        @app.route('/system/clear-cache', methods=['POST'])
        @login_required
        def clear_cache():
            """Rota para limpar o cache do sistema"""
            try:
                # Limpar cache
                self._clear_cache()
                flash('Cache limpo com sucesso!', 'success')
            except Exception as e:
                logger.error(f"Erro ao limpar cache: {e}")
                flash(f'Erro ao limpar cache: {str(e)}', 'danger')
            
            return redirect(url_for('system_dashboard'))
        
        @app.route('/system/export-data')
        @login_required
        def export_system_data():
            """Rota para exportar dados do sistema"""
            try:
                # Exportar dados
                export_file = self._export_system_data()
                if export_file:
                    return send_file(export_file, as_attachment=True)
                else:
                    flash('Erro ao exportar dados', 'danger')
                    return redirect(url_for('system_dashboard'))
            except Exception as e:
                logger.error(f"Erro ao exportar dados: {e}")
                flash(f'Erro ao exportar dados: {str(e)}', 'danger')
                return redirect(url_for('system_dashboard'))
        
        logger.info("Rotas de melhoria do sistema registradas")
    
    def _apply_improvements(self):
        """Aplica as melhorias nas funcionalidades existentes com base na configuração"""
        # Aplicar melhorias de UI
        self._apply_ui_improvements()
        
        # Aplicar melhorias de performance
        self._apply_performance_improvements()
        
        # Aplicar melhorias de workflow
        self._apply_workflow_improvements()
        
        logger.info("Melhorias aplicadas com sucesso")
    
    def _apply_ui_improvements(self):
        """Aplica melhorias na interface do usuário"""
        app = self.app
        
        # Adicionar variáveis globais para templates
        @app.context_processor
        def inject_ui_config():
            return {
                'ui_config': self.config["ui"],
                'features_config': self.config["features"],
                'workflow_config': self.config["workflow"],
                'system_version': self.config["version"]
            }
        
        # Adicionar filtros personalizados para templates
        @app.template_filter('format_date')
        def format_date_filter(date, format='%d/%m/%Y'):
            if isinstance(date, str):
                try:
                    date = datetime.fromisoformat(date)
                except ValueError:
                    return date
            return date.strftime(format) if date else ''
        
        @app.template_filter('format_currency')
        def format_currency_filter(value):
            return f"R$ {float(value):.2f}" if value is not None else ''
        
        logger.info("Melhorias de UI aplicadas")
    
    def _apply_performance_improvements(self):
        """Aplica melhorias de performance"""
        app = self.app
        
        # Configurar compressão de respostas
        if self.config["performance"]["compress_responses"]:
            try:
                from flask_compress import Compress
                compress = Compress()
                compress.init_app(app)
                logger.info("Compressão de respostas ativada")
            except ImportError:
                logger.warning("flask_compress não está instalado. Compressão de respostas não será ativada.")
        
        # Configurar cache
        if self.config["performance"]["cache_enabled"]:
            try:
                from flask_caching import Cache
                cache_config = {
                    'CACHE_TYPE': 'SimpleCache',
                    'CACHE_DEFAULT_TIMEOUT': self.config["performance"]["cache_timeout"]
                }
                cache = Cache(config=cache_config)
                cache.init_app(app)
                app.config['CACHE'] = cache
                logger.info("Cache ativado")
            except ImportError:
                logger.warning("flask_caching não está instalado. Cache não será ativado.")
        
        logger.info("Melhorias de performance aplicadas")
    
    def _apply_workflow_improvements(self):
        """Aplica melhorias nos fluxos de trabalho"""
        app = self.app
        
        # Adicionar middleware para rastrear ações do usuário
        @app.before_request
        def track_user_actions():
            if current_user.is_authenticated and request.endpoint:
                # Aqui poderíamos registrar ações do usuário para análise
                pass
        
        # Adicionar middleware para auto-salvar rascunhos
        if self.config["workflow"]["auto_save_drafts"]:
            @app.before_request
            def setup_draft_autosave():
                if current_user.is_authenticated and request.method == 'GET':
                    # Aqui poderíamos configurar o auto-save de rascunhos
                    pass
        
        logger.info("Melhorias de workflow aplicadas")
    
    def _collect_system_stats(self):
        """Coleta estatísticas do sistema para o dashboard"""
        db = self.db
        
        try:
            # Estatísticas de usuários
            user_count = db.session.execute(db.select(db.func.count()).select_from(db.User)).scalar() or 0
            active_users = db.session.execute(db.select(db.func.count()).select_from(db.User).where(db.User.is_active == True)).scalar() or 0
            
            # Estatísticas de ocorrências
            occurrence_count = db.session.execute(db.select(db.func.count()).select_from(db.Occurrence)).scalar() or 0
            
            # Estatísticas de advertências
            warning_count = 0  # Implementar quando o modelo estiver disponível
            
            # Estatísticas de multas
            fine_count = 0  # Implementar quando o modelo estiver disponível
            
            # Estatísticas de atas
            minute_count = 0  # Implementar quando o modelo estiver disponível
            
            # Estatísticas de sistema
            system_uptime = self._get_system_uptime()
            database_size = self._get_database_size()
            
            return {
                "users": {
                    "total": user_count,
                    "active": active_users
                },
                "content": {
                    "occurrences": occurrence_count,
                    "warnings": warning_count,
                    "fines": fine_count,
                    "minutes": minute_count
                },
                "system": {
                    "uptime": system_uptime,
                    "database_size": database_size,
                    "version": self.config["version"],
                    "last_updated": self.config["last_updated"]
                }
            }
        except Exception as e:
            logger.error(f"Erro ao coletar estatísticas: {e}")
            return {
                "error": str(e)
            }
    
    def _get_system_uptime(self):
        """Obtém o tempo de atividade do sistema"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return str(timedelta(seconds=uptime_seconds))
        except Exception:
            return "Desconhecido"
    
    def _get_database_size(self):
        """Obtém o tamanho do banco de dados"""
        try:
            # Para SQLite
            db_path = self.app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if os.path.exists(db_path):
                size_bytes = os.path.getsize(db_path)
                if size_bytes < 1024:
                    return f"{size_bytes} bytes"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.2f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.2f} MB"
            return "Desconhecido"
        except Exception:
            return "Desconhecido"
    
    def _optimize_database(self):
        """Otimiza o banco de dados"""
        try:
            # Para SQLite
            db_path = self.app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if os.path.exists(db_path):
                import sqlite3
                conn = sqlite3.connect(db_path)
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
                conn.close()
                logger.info("Banco de dados otimizado")
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao otimizar banco de dados: {e}")
            raise
    
    def _clear_cache(self):
        """Limpa o cache do sistema"""
        try:
            if 'CACHE' in self.app.config:
                self.app.config['CACHE'].clear()
                logger.info("Cache limpo")
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            raise
    
    def _export_system_data(self):
        """Exporta dados do sistema para um arquivo JSON"""
        try:
            export_data = {
                "metadata": {
                    "version": self.config["version"],
                    "exported_at": datetime.utcnow().isoformat(),
                    "exported_by": current_user.id if current_user.is_authenticated else None
                },
                "config": self.config,
                "statistics": self._collect_system_stats()
            }
            
            # Criar arquivo de exportação
            export_dir = os.path.join(self.app.root_path, 'exports')
            os.makedirs(export_dir, exist_ok=True)
            
            export_file = os.path.join(export_dir, f"system_export_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json")
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4)
            
            logger.info(f"Dados exportados para {export_file}")
            return export_file
        except Exception as e:
            logger.error(f"Erro ao exportar dados: {e}")
            raise

# Função para registrar o módulo de melhorias no aplicativo Flask
def register_system_improvements(app, db):
    """Registra o módulo de melhorias do sistema na aplicação Flask"""
    improvements = SystemImprovements(app, db)
    return improvements
