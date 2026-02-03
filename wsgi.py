#!/usr/bin/env python3
"""
WSGI Entry Point - VERSÃO OTIMIZADA
====================================

Entry point WSGI para servidores de produção (Gunicorn, uWSGI, etc).

Este arquivo é usado pelos servidores WSGI para carregar a aplicação.
Inclui configurações de logging, monitoramento e tratamento de erros.

Usage:
    gunicorn wsgi:app
    gunicorn -c gunicorn_config.py wsgi:app

Author: Equipe CI Gestão
Version: 2.0.0
"""

import os
import sys
import logging
from typing import Optional

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

# Obter ambiente (production por padrão em WSGI)
ENV = os.environ.get('FLASK_ENV', 'production')

# Configurar logging
logging.basicConfig(
    level=logging.INFO if ENV == 'production' else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CRIAR APLICAÇÃO
# ============================================================================

try:
    logger.info(f'Iniciando aplicação (ambiente: {ENV})')
    
    # Criar aplicação Flask
    app = create_app(config_name=ENV)
    
    logger.info('✓ Aplicação criada com sucesso')
    
    # Validar configuração
    from app.utils.validators import validate_app_config
    
    is_valid, errors = validate_app_config()
    if not is_valid:
        logger.error('✗ Configuração inválida:')
        for error in errors:
            logger.error(f'  - {error}')
        raise ValueError('Configuração da aplicação inválida')
    
    logger.info('✓ Configuração validada')
    
    # Verificar conexão com banco
    with app.app_context():
        try:
            db.session.execute(text('SELECT 1'))
            logger.info('✓ Conexão com banco de dados OK')
        except Exception as e:
            logger.error(f'✗ Erro na conexão com banco: {str(e)}')
            raise
    
    # Log de configurações importantes (sem dados sensíveis)
    logger.info('Configurações da aplicação:')
    logger.info(f'  - Debug: {app.config.get("DEBUG")}')
    logger.info(f'  - Database: {app.config.get("SQLALCHEMY_DATABASE_URI", "").split("@")[-1]}')
    logger.info(f'  - Max Upload Size: {app.config.get("MAX_CONTENT_LENGTH", 0) / (1024*1024):.0f}MB')
    logger.info(f'  - Session Lifetime: {app.config.get("PERMANENT_SESSION_LIFETIME")}')
    
    logger.info('=' * 70)
    logger.info('Aplicação pronta para receber requisições')
    logger.info('=' * 70)

except Exception as e:
    logger.error(f'✗ Erro fatal ao inicializar aplicação: {str(e)}', exc_info=True)
    
    # Em produção, pode querer notificar sobre erro crítico
    # (ex: enviar email, notificação Slack, etc)
    
    # Re-raise para que o servidor WSGI saiba que houve erro
    raise


# ============================================================================
# MIDDLEWARE PARA LOGGING DE REQUISIÇÕES
# ============================================================================

class RequestLoggingMiddleware:
    """
    Middleware para logging detalhado de requisições.
    
    Útil para debug e auditoria em produção.
    """
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('request_logger')
    
    def __call__(self, environ, start_response):
        # Extrair informações da requisição
        method = environ.get('REQUEST_METHOD')
        path = environ.get('PATH_INFO')
        remote_addr = environ.get('REMOTE_ADDR')
        user_agent = environ.get('HTTP_USER_AGENT', '')
        
        # Log da requisição
        self.logger.info(
            f'{method} {path} from {remote_addr}',
            extra={
                'method': method,
                'path': path,
                'remote_addr': remote_addr,
                'user_agent': user_agent
            }
        )
        
        # Passar para a aplicação
        return self.app(environ, start_response)


# Adicionar middleware se em produção
if ENV == 'production' and os.environ.get('ENABLE_REQUEST_LOGGING', 'false').lower() == 'true':
    app = RequestLoggingMiddleware(app)
    logger.info('✓ Middleware de logging de requisições ativado')


# ============================================================================
# HEALTH CHECK (para load balancers)
# ============================================================================

@app.route('/_health')
def health_check():
    """
    Endpoint de health check simplificado.
    
    Usado por load balancers e sistemas de monitoramento.
    Não requer autenticação.
    
    Returns:
        200: Aplicação saudável
        503: Aplicação com problemas
    """
    from flask import jsonify
    from datetime import datetime
    
    try:
        # Verificar banco de dados
        with app.app_context():
            db.session.execute(text('SELECT 1'))
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': app.config.get('APP_VERSION', '2.0.0')
        }), 200
        
    except Exception as e:
        logger.error(f'Health check falhou: {str(e)}')
        
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


# ============================================================================
# TRATAMENTO DE ERROS GLOBAL
# ============================================================================

@app.errorhandler(500)
def internal_error(error):
    """Handler global para erros 500."""
    logger.error(f'Erro interno do servidor: {str(error)}', exc_info=True)
    
    # Rollback da sessão do banco em caso de erro
    db.session.rollback()
    
    from flask import jsonify, render_template, request
    
    # Se for requisição API, retornar JSON
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'Erro interno do servidor',
            'message': 'Ocorreu um erro inesperado. Por favor, tente novamente.'
        }), 500
    
    # Senão, renderizar página de erro
    return render_template('errors/500.html'), 500


@app.errorhandler(404)
def not_found_error(error):
    """Handler global para erros 404."""
    from flask import jsonify, render_template, request
    
    # Se for requisição API, retornar JSON
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'Não encontrado',
            'message': 'O recurso solicitado não foi encontrado'
        }), 404
    
    # Senão, renderizar página de erro
    return render_template('errors/404.html'), 404


# ============================================================================
# SENTRY INTEGRATION (para monitoramento de erros)
# ============================================================================

SENTRY_DSN = os.environ.get('SENTRY_DSN')

if SENTRY_DSN and ENV == 'production':
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FlaskIntegration(),
                SqlalchemyIntegration()
            ],
            traces_sample_rate=0.1,  # 10% de sampling
            environment=ENV,
            release=app.config.get('APP_VERSION', '2.0.0')
        )
        
        logger.info('✓ Sentry integration ativada')
        
    except ImportError:
        logger.warning('⚠️  sentry_sdk não instalado. Instale com: pip install sentry-sdk[flask]')
    except Exception as e:
        logger.error(f'✗ Erro ao configurar Sentry: {str(e)}')


# ============================================================================
# NEW RELIC INTEGRATION (para monitoramento de performance)
# ============================================================================

if os.environ.get('NEW_RELIC_LICENSE_KEY') and ENV == 'production':
    try:
        import newrelic.agent
        newrelic.agent.initialize('newrelic.ini')
        app = newrelic.agent.WSGIApplicationWrapper(app)
        logger.info('✓ New Relic integration ativada')
    except ImportError:
        logger.warning('⚠️  newrelic não instalado')
    except Exception as e:
        logger.error(f'✗ Erro ao configurar New Relic: {str(e)}')


# ============================================================================
# GRACEFUL SHUTDOWN
# ============================================================================

def cleanup():
    """
    Limpeza ao encerrar a aplicação.
    
    Fecha conexões e libera recursos.
    """
    logger.info('Encerrando aplicação...')
    
    try:
        # Fechar conexões do banco
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        
        logger.info('✓ Recursos liberados com sucesso')
        
    except Exception as e:
        logger.error(f'✗ Erro ao liberar recursos: {str(e)}')


import atexit
atexit.register(cleanup)


# ============================================================================
# EXPORTAR APLICAÇÃO
# ============================================================================

# Esta é a variável que o servidor WSGI irá importar
# Exemplo: gunicorn wsgi:app
__all__ = ['app']


if __name__ == '__main__':
    # Se executado diretamente, rodar servidor de desenvolvimento
    logger.warning('⚠️  ATENÇÃO: Executando servidor de desenvolvimento!')
    logger.warning('⚠️  Para produção, use: gunicorn wsgi:app')
    
    app.run(
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 5000),
        debug=app.config.get('DEBUG', False)
    )
