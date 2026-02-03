"""
Blueprint routes.
"""
from .main import main_bp
from .auth import auth_bp
from .ci import ci_bp
from .import_routes import import_bp
from .alerts import alerts_bp
from .reports import reports_bp
from .api import api_bp

# Lista de todos os blueprints
__all__ = ['main_bp', 'auth_bp', 'ci_bp', 'import_bp', 'alerts_bp', 'reports_bp', 'api_bp']