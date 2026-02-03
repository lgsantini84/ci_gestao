"""
Configurações da aplicação.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

class Config:
    """Configurações base."""
    
    # Segurança
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sistema-ci-gestao-2025')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///database.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # Upload
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'pdf', 'txt'}
    
    # Sessão
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Paginação
    ITEMS_PER_PAGE = 50
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Empresas
    VALID_COMPANY_CODES = {
        '106': 'PSF',
        '110': 'PASCC', 
        '170': 'NPAA'
    }
    
    # Contratos UNIMED
    UNIMED_CONTRACTS = {
        '106': {
            '2441000001': 'GERENTE TITULAR',
            '2441000002': 'GERENTE DEPENDENTE',
            '2441000003': 'GERAL CLT',
            '2441000004': 'LIDERES TITULAR',
            '2441000005': 'LIDERES DEPENDENTE'
        },
        '110': {
            '5249000001': 'GERAL CLT',
            '5249000002': 'LIDERES TITULAR',
            '5249000003': 'LIDERES DEPENDENTE',
            '5249000004': 'GERENTE TITULAR',
            '5249000005': 'GERENTE DEPENDENTE'
        },
        '170': {
            '2896000001': 'GERENTE TITULAR',
            '2896000002': 'GERENTE DEPENDENTE',
            '2896000003': 'FILIAL',
            '2896000004': 'GERAL CLT',
            '2896000005': 'LIDERES TITULAR',
            '2896000006': 'LIDERES DEPENDENTE'
        }
    }


class DevelopmentConfig(Config):
    """Configurações para desenvolvimento."""
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000


class TestingConfig(Config):
    """Configurações para testes."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_database.db'


class ProductionConfig(Config):
    """Configurações para produção."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    # Em produção, usar PostgreSQL ou MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


# Configuração por ambiente
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}