"""
Configurações da Aplicação - VERSÃO OTIMIZADA
==============================================

Sistema de configuração hierárquico com validações e segurança aprimorada.

Melhorias implementadas:
- ✅ Validação de variáveis de ambiente
- ✅ Configurações específicas por ambiente
- ✅ Segurança aprimorada
- ✅ Type hints
- ✅ Documentação completa
- ✅ Rate limiting
- ✅ CORS configurável

Author: Equipe CI Gestão
Version: 2.0.0
"""

import os
import secrets
from datetime import timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()


# ============================================================================
# CONFIGURAÇÃO BASE
# ============================================================================

class Config:
    """
    Configuração base da aplicação.
    
    Todas as outras configurações herdam desta classe.
    Contém configurações comuns a todos os ambientes.
    """
    
    # ========================================================================
    # INFORMAÇÕES DO SISTEMA
    # ========================================================================
    
    APP_NAME: str = 'Sistema de Gestão CI'
    APP_VERSION: str = '2.0.0'
    APP_DESCRIPTION: str = 'Sistema de Gestão de Colaboradores Internos'
    
    # ========================================================================
    # SEGURANÇA
    # ========================================================================
    
    # Chave secreta (DEVE ser alterada em produção!)
    SECRET_KEY: str = os.environ.get(
        'SECRET_KEY',
        secrets.token_urlsafe(32)  # Gera chave aleatória se não definida
    )
    
    # Proteção CSRF
    WTF_CSRF_ENABLED: bool = True
    WTF_CSRF_TIME_LIMIT: Optional[int] = None  # Sem limite de tempo
    
    # Segurança de cookies
    SESSION_COOKIE_SECURE: bool = os.environ.get(
        'SESSION_COOKIE_SECURE', 
        'False'
    ).lower() == 'true'
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'
    
    # Headers de segurança
    SECURITY_HEADERS: Dict[str, str] = {
        'X-Frame-Options': 'SAMEORIGIN',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
    }
    
    # ========================================================================
    # BANCO DE DADOS
    # ========================================================================
    
    # URI de conexão
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        'DATABASE_URL',
        'sqlite:///database.db'
    )
    
    # Configurações do SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ECHO: bool = False  # Log de queries SQL
    SQLALCHEMY_RECORD_QUERIES: bool = True  # Habilita query profiling
    
    # Pool de conexões
    SQLALCHEMY_ENGINE_OPTIONS: Dict[str, Any] = {
        'pool_size': 10,            # Número de conexões no pool
        'pool_recycle': 3600,       # Reciclar conexões após 1h
        'pool_pre_ping': True,      # Testar conexão antes de usar
        'max_overflow': 20,         # Conexões extras quando pool cheio
        'pool_timeout': 30,         # Timeout para obter conexão
        'echo': False,              # Não logar queries
        'echo_pool': False,         # Não logar pool events
    }
    
    # ========================================================================
    # SESSÃO
    # ========================================================================
    
    # Duração da sessão
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(
        hours=int(os.environ.get('SESSION_LIFETIME_HOURS', 8))
    )
    
    # Tipo de sessão
    SESSION_TYPE: str = 'filesystem'  # Pode ser 'redis' em produção
    
    # ========================================================================
    # UPLOAD DE ARQUIVOS
    # ========================================================================
    
    # Diretório de uploads
    UPLOAD_FOLDER: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'uploads'
    )
    
    # Tamanho máximo de arquivo (100MB)
    MAX_CONTENT_LENGTH: int = 100 * 1024 * 1024
    
    # Extensões permitidas
    ALLOWED_EXTENSIONS: set = {'xlsx', 'xls', 'csv', 'pdf', 'txt'}
    
    # ========================================================================
    # PAGINAÇÃO
    # ========================================================================
    
    ITEMS_PER_PAGE: int = 50
    MAX_ITEMS_PER_PAGE: int = 100
    
    # ========================================================================
    # LOGGING
    # ========================================================================
    
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE: str = 'logs/app.log'
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 10
    
    # ========================================================================
    # CACHE
    # ========================================================================
    
    CACHE_TYPE: str = 'simple'  # Pode ser 'redis' em produção
    CACHE_DEFAULT_TIMEOUT: int = 300  # 5 minutos
    
    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    
    RATELIMIT_ENABLED: bool = True
    RATELIMIT_STORAGE_URL: str = 'memory://'  # Pode ser redis:// em produção
    RATELIMIT_DEFAULT: str = '200 per hour'  # Limite padrão
    
    # Limites específicos por tipo de requisição
    RATELIMIT_LOGIN: str = '5 per minute'
    RATELIMIT_API: str = '100 per hour'
    RATELIMIT_UPLOAD: str = '10 per hour'
    
    # ========================================================================
    # CORS (Cross-Origin Resource Sharing)
    # ========================================================================
    
    CORS_ENABLED: bool = os.environ.get('CORS_ENABLED', 'False').lower() == 'true'
    CORS_ORIGINS: List[str] = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # ========================================================================
    # EMPRESAS E CÓDIGOS
    # ========================================================================
    
    # Códigos de empresa válidos
    VALID_COMPANY_CODES: Dict[str, str] = {
        '106': 'PSF',
        '110': 'PASCC',
        '170': 'NPAA'
    }
    
    # Contratos UNIMED por empresa
    UNIMED_CONTRACTS: Dict[str, Dict[str, str]] = {
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
    
    # ========================================================================
    # IMPORTAÇÃO
    # ========================================================================
    
    # Tamanho do lote para processamento de importações
    IMPORT_BATCH_SIZE: int = 1000
    
    # Timeout para processamento de importações (segundos)
    IMPORT_TIMEOUT: int = 300
    
    # ========================================================================
    # EMAIL (para futuras notificações)
    # ========================================================================
    
    MAIL_ENABLED: bool = os.environ.get('MAIL_ENABLED', 'False').lower() == 'true'
    MAIL_SERVER: Optional[str] = os.environ.get('MAIL_SERVER')
    MAIL_PORT: int = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS: bool = True
    MAIL_USERNAME: Optional[str] = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD: Optional[str] = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER: str = os.environ.get(
        'MAIL_DEFAULT_SENDER',
        'noreply@ci-gestao.com.br'
    )
    
    # ========================================================================
    # MÉTODOS DE CLASSE
    # ========================================================================
    
    @classmethod
    def validate(cls) -> tuple[bool, List[str]]:
        """
        Valida a configuração.
        
        Returns:
            Tupla (válido, lista_de_erros)
        """
        errors: List[str] = []
        
        # Validar SECRET_KEY
        if not cls.SECRET_KEY or len(cls.SECRET_KEY) < 32:
            errors.append('SECRET_KEY deve ter pelo menos 32 caracteres')
        
        # Validar DATABASE_URI
        if not cls.SQLALCHEMY_DATABASE_URI:
            errors.append('SQLALCHEMY_DATABASE_URI não pode estar vazio')
        
        # Validar UPLOAD_FOLDER
        if not cls.UPLOAD_FOLDER:
            errors.append('UPLOAD_FOLDER não pode estar vazio')
        
        # Validar códigos de empresa
        if not cls.VALID_COMPANY_CODES:
            errors.append('VALID_COMPANY_CODES não pode estar vazio')
        
        return len(errors) == 0, errors
    
    @classmethod
    def init_app(cls, app) -> None:
        """
        Inicializa configurações específicas da aplicação.
        
        Args:
            app: Instância da aplicação Flask
        """
        # Validar configuração
        is_valid, errors = cls.validate()
        if not is_valid:
            for error in errors:
                app.logger.error(f'Erro de configuração: {error}')
            raise ValueError('Configuração inválida')


# ============================================================================
# CONFIGURAÇÃO DE DESENVOLVIMENTO
# ============================================================================

class DevelopmentConfig(Config):
    """
    Configuração para ambiente de desenvolvimento.
    
    Características:
    - Debug ativado
    - SQLite local
    - Logging verbose
    - Sem HTTPS
    """
    
    DEBUG: bool = True
    TESTING: bool = False
    
    # Servidor
    HOST: str = '0.0.0.0'
    PORT: int = 5000
    
    # Banco de dados local
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        'DATABASE_URL',
        'sqlite:///database_dev.db'
    )
    
    # Logging mais verbose
    SQLALCHEMY_ECHO: bool = True
    LOG_LEVEL: str = 'DEBUG'
    
    # Desabilitar HTTPS em desenvolvimento
    SESSION_COOKIE_SECURE: bool = False
    
    # Habilitar profiler
    PROFILE: bool = True


# ============================================================================
# CONFIGURAÇÃO DE TESTE
# ============================================================================

class TestingConfig(Config):
    """
    Configuração para ambiente de testes.
    
    Características:
    - Banco em memória
    - CSRF desabilitado
    - Sem rate limiting
    """
    
    TESTING: bool = True
    DEBUG: bool = True
    
    # Banco de dados em memória
    SQLALCHEMY_DATABASE_URI: str = 'sqlite:///:memory:'
    
    # Desabilitar CSRF em testes
    WTF_CSRF_ENABLED: bool = False
    
    # Desabilitar rate limiting
    RATELIMIT_ENABLED: bool = False
    
    # Não salvar arquivos em testes
    UPLOAD_FOLDER: str = '/tmp/ci_gestao_test_uploads'


# ============================================================================
# CONFIGURAÇÃO DE PRODUÇÃO
# ============================================================================

class ProductionConfig(Config):
    """
    Configuração para ambiente de produção.
    
    Características:
    - Debug desabilitado
    - PostgreSQL/MySQL
    - HTTPS obrigatório
    - Rate limiting ativo
    - Cache com Redis
    """
    
    DEBUG: bool = False
    TESTING: bool = False
    
    # Servidor
    HOST: str = '0.0.0.0'
    PORT: int = int(os.environ.get('PORT', 8000))
    
    # Segurança HTTPS obrigatória
    SESSION_COOKIE_SECURE: bool = True
    
    # Banco de dados (PostgreSQL ou MySQL)
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        'DATABASE_URL',
        'postgresql://user:pass@localhost/ci_gestao'
    )
    
    # Cache com Redis
    CACHE_TYPE: str = 'redis'
    CACHE_REDIS_URL: str = os.environ.get(
        'REDIS_URL',
        'redis://localhost:6379/0'
    )
    
    # Rate limiting com Redis
    RATELIMIT_STORAGE_URL: str = os.environ.get(
        'REDIS_URL',
        'redis://localhost:6379/1'
    )
    
    # Logging menos verbose
    LOG_LEVEL: str = 'WARNING'
    SQLALCHEMY_ECHO: bool = False
    
    @classmethod
    def init_app(cls, app) -> None:
        """Inicializa configurações de produção."""
        super().init_app(app)
        
        # Configurar logging para syslog ou serviço de log
        import logging
        from logging.handlers import SysLogHandler
        
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)


# ============================================================================
# MAPEAMENTO DE CONFIGURAÇÕES
# ============================================================================

config_by_name: Dict[str, type] = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: Optional[str] = None) -> type:
    """
    Obtém classe de configuração por nome.
    
    Args:
        config_name: Nome da configuração ('development', 'testing', 'production')
    
    Returns:
        Classe de configuração
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config_by_name.get(config_name, DevelopmentConfig)
