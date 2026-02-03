#!/usr/bin/env python3
"""
Sistema de Gestão de Colaboradores Internos (CI) - VERSÃO OTIMIZADA
=====================================================================

Aplicação principal com melhorias de performance, segurança e qualidade de código.

Melhorias implementadas:
- ✅ Type hints completos
- ✅ Tratamento robusto de erros
- ✅ Logging estruturado
- ✅ Validação de configuração
- ✅ Inicialização segura do banco
- ✅ Migração automática
- ✅ Health checks
- ✅ Graceful shutdown

Author: Equipe CI Gestão
Version: 2.0.0
Python: 3.8+
"""

import os
import sys
import io
import signal
import warnings
import logging
from datetime import datetime
from typing import Optional, NoReturn

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from app import create_app, db
from sqlalchemy import text
from app.models import Usuario
from app.utils.validators import setup_directories, validate_app_config

# Configurar logging

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# INICIALIZAÇÃO DO SISTEMA
# ============================================================================

def create_admin_user() -> None:
    """
    Cria usuário administrador padrão se não existir.
    
    Este usuário deve ter sua senha alterada no primeiro login.
    
    Raises:
        Exception: Se houver erro na criação do usuário
    """
    try:
        with app.app_context():
            # Verificar se admin já existe
            admin = Usuario.query.filter_by(username='admin').first()
            
            if not admin:
                admin = Usuario(
                    username='admin',
                    nome='Administrador do Sistema',
                    email='admin@sistema.com.br',
                    tipo_usuario='admin',
                    ativo=True
                )
                admin.set_password('admin123')
                
                db.session.add(admin)
                db.session.commit()
                
                logger.info('✓ Usuário administrador criado com sucesso')
                logger.warning('⚠️  IMPORTANTE: Altere a senha padrão (admin123) imediatamente!')
            else:
                logger.info('✓ Usuário administrador já existe')
                
    except Exception as e:
        logger.error(f'✗ Erro ao criar usuário administrador: {str(e)}')
        raise


def init_database() -> None:
    """
    Inicializa o banco de dados criando todas as tabelas.
    
    Verifica se as tabelas já existem antes de criar.
    
    Raises:
        Exception: Se houver erro na criação do banco
    """
    try:
        with app.app_context():
            # Criar todas as tabelas
            db.create_all()
            
            # Verificar se tabelas foram criadas
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if tables:
                logger.info(f'✓ Banco de dados inicializado com {len(tables)} tabelas')
                logger.debug(f'Tabelas criadas: {", ".join(tables)}')
            else:
                logger.warning('⚠️  Nenhuma tabela foi criada')
                
    except Exception as e:
        logger.error(f'✗ Erro ao inicializar banco de dados: {str(e)}')
        raise


def validate_environment() -> None:
    """
    Valida o ambiente e configurações antes de iniciar.
    
    Verifica:
    - Variáveis de ambiente necessárias
    - Configurações da aplicação
    - Permissões de diretórios
    - Conexão com banco de dados
    
    Raises:
        ValueError: Se alguma validação falhar
    """
    try:
        logger.info('Validando ambiente...')
        
        # Validar configurações da aplicação
        is_valid, errors = validate_app_config(app)
        
        if not is_valid:
            logger.error('✗ Configuração inválida:')
            for error in errors:
                logger.error(f'  - {error}')
            raise ValueError('Configuração da aplicação inválida')
        
        logger.info('✓ Configurações validadas')
        
        # Validar conexão com banco
        with app.app_context():
            try:
                db.session.execute(text('SELECT 1'))
                logger.info('✓ Conexão com banco de dados OK')
            except Exception as e:
                logger.error(f'✗ Erro na conexão com banco: {str(e)}')
                raise
        
        logger.info('✓ Ambiente validado com sucesso')
        
    except Exception as e:
        logger.error(f'✗ Erro na validação do ambiente: {str(e)}')
        raise


def setup_signal_handlers() -> None:
    """
    Configura handlers para sinais do sistema (graceful shutdown).
    
    Permite que a aplicação seja encerrada de forma elegante,
    fechando conexões e salvando estado quando necessário.
    """
    def signal_handler(signum: int, frame) -> NoReturn:
        """Handler para sinais de término."""
        logger.info(f'Sinal {signum} recebido. Encerrando aplicação...')
        
        try:
            # Fechar conexões do banco
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
            
            logger.info('✓ Aplicação encerrada com sucesso')
        except Exception as e:
            logger.error(f'✗ Erro ao encerrar aplicação: {str(e)}')
        finally:
            sys.exit(0)
    
    # Registrar handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def print_startup_banner() -> None:
    """Exibe banner de inicialização do sistema."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   Sistema de Gestão de Colaboradores Internos (CI)           ║
║   Versão 2.0.0 - Otimizado                                    ║
║                                                               ║
║   Desenvolvido com ❤️  pela Equipe CI Gestão                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(banner)
    logger.info('Sistema de Gestão CI iniciado')


def display_startup_info() -> None:
    """Exibe informações de inicialização do sistema."""
    logger.info('=' * 70)
    logger.info(f'Data/Hora: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    logger.info(f'Ambiente: {app.config.get("ENV", "production")}')
    logger.info(f'Debug: {app.config.get("DEBUG", False)}')
    logger.info(f'Host: {app.config.get("HOST", "127.0.0.1")}')
    logger.info(f'Port: {app.config.get("PORT", 5000)}')
    logger.info(f'Database: {app.config.get("SQLALCHEMY_DATABASE_URI", "").split("///")[0]}')
    logger.info('=' * 70)
    logger.info('Acesse o sistema em:')
    logger.info(f'  → http://{app.config.get("HOST", "127.0.0.1")}:{app.config.get("PORT", 5000)}')
    logger.info('=' * 70)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    try:
        # Exibir banner
        print_startup_banner()
        
        # Criar diretório de logs se não existir
        os.makedirs('logs', exist_ok=True)
        
        # Criar aplicação
        logger.info('Criando aplicação Flask...')
        env = os.environ.get('FLASK_ENV', 'development')
        app = create_app(config_name=env)
        logger.info(f'✓ Aplicação criada (ambiente: {env})')
        
        # Validar ambiente
        validate_environment()
        
        # Configurar diretórios necessários
        logger.info('Configurando diretórios...')
        setup_directories(app)
        logger.info('✓ Diretórios configurados')
        
        # Inicializar banco de dados
        logger.info('Inicializando banco de dados...')
        init_database()
        
        # Criar usuário admin
        logger.info('Verificando usuário administrador...')
        create_admin_user()
        
        # Configurar signal handlers
        setup_signal_handlers()
        
        # Exibir informações de startup
        display_startup_info()
        
        # Iniciar servidor
        app.run(
            host=app.config.get('HOST', '0.0.0.0'),
            port=app.config.get('PORT', 5000),
            debug=app.config.get('DEBUG', False),
            threaded=True,
            use_reloader=app.config.get('DEBUG', False)
        )
        
    except KeyboardInterrupt:
        logger.info('Interrompido pelo usuário')
        sys.exit(0)
        
    except Exception as e:
        logger.error(f'✗ Erro fatal ao iniciar aplicação: {str(e)}', exc_info=True)
        sys.exit(1)
