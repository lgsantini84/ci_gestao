"""
Factory da aplicação Flask.
"""

from flask import Flask, render_template  # ADICIONE render_template AQUI
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import logging
from logging.handlers import RotatingFileHandler
import os

# Extensões
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_name='development'):
    """
    Factory para criar a aplicação Flask.
    
    Args:
        config_name: Nome da configuração ('development', 'testing', 'production')
    
    Returns:
        Flask app configurada
    """
    app = Flask(__name__)
    
    # Carregar configurações
    from config import config_by_name
    app.config.from_object(config_by_name[config_name])
    
    # Inicializar extensões
    db.init_app(app)
    
    # Configurar Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import Usuario
        return Usuario.query.get(int(user_id))
    migrate.init_app(app, db)
    
    # Configurar logging
    setup_logging(app)
    
    # Registrar blueprints
    register_blueprints(app)
    
    # Registrar filtros de template
    register_template_filters(app)
    
    # Registrar error handlers
    register_error_handlers(app)
    
    return app


def setup_logging(app):
    """Configurar sistema de logging."""
    if not app.debug:
        # Criar diretório de logs
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Handler para arquivo
        file_handler = RotatingFileHandler(
            f'{log_dir}/app.log',
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Sistema CI iniciado')


def register_blueprints(app):
    """Registrar todos os blueprints."""
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.ci import ci_bp
    from app.routes.import_routes import import_bp
    from app.routes.alerts import alerts_bp
    from app.routes.reports import reports_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ci_bp)
    app.register_blueprint(import_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp, url_prefix='/api')


def register_template_filters(app):
    """Registrar filtros de template."""
    from datetime import datetime
    from app.utils.data_utils import to_brasilia, from_json, strftime
    from app.services.alert_service import AlertService

    app.jinja_env.filters['to_brasilia'] = to_brasilia
    app.jinja_env.filters['from_json'] = from_json
    app.jinja_env.filters['strftime'] = strftime
    app.jinja_env.globals['now'] = datetime.utcnow
    app.jinja_env.globals['get_alert_service'] = lambda: AlertService()


def register_error_handlers(app):
    """Registrar handlers de erro."""
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500