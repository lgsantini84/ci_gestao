"""
Pacote de serviços do sistema.

Este pacote contém serviços de negócio que encapsulam a lógica de aplicação,
separando-a das rotas e modelos.
"""

# Serviços disponíveis
from app.services.ci_service import CIService, ci_service
from app.services.alert_service import AlertService, alert_service
from app.services.import_service import ImportService, import_service
from app.services.report_service import ReportService, report_service

# Versão do pacote
__version__ = '1.0.0'
__author__ = 'Sistema de Gestão de CI'

# Lista de serviços exportados
__all__ = [
    # Classes
    'CIService',
    'AlertService', 
    'ImportService',
    'ReportService',
    
    # Instâncias singleton
    'ci_service',
    'alert_service',
    'import_service', 
    'report_service'
]


class ServiceFactory:
    """
    Fábrica para criar instâncias de serviços.
    
    Útil para injeção de dependências e testes.
    """
    
    @staticmethod
    def create_ci_service():
        """Cria uma instância do serviço de CI."""
        return CIService()
    
    @staticmethod
    def create_alert_service():
        """Cria uma instância do serviço de alertas."""
        return AlertService()
    
    @staticmethod
    def create_import_service():
        """Cria uma instância do serviço de importação."""
        return ImportService()
    
    @staticmethod
    def create_report_service():
        """Cria uma instância do serviço de relatórios."""
        return ReportService()
    
    @staticmethod
    def create_all_services():
        """Cria instâncias de todos os serviços."""
        return {
            'ci_service': CIService(),
            'alert_service': AlertService(),
            'import_service': ImportService(),
            'report_service': ReportService()
        }


def init_services(app):
    """
    Inicializa os serviços com o contexto da aplicação.
    
    Args:
        app: Aplicação Flask
    """
    # Esta função pode ser usada para configurar serviços
    # com parâmetros específicos da aplicação
    pass


# Documentação dos serviços
SERVICES_DOCS = {
    'CIService': {
        'description': 'Serviço para operações de negócio relacionadas a Colaboradores Internos',
        'responsibilities': [
            'CRUD de colaboradores',
            'Gerenciamento de NCs',
            'Gerenciamento de dependentes',
            'Exportação de dados',
            'Estatísticas'
        ]
    },
    'AlertService': {
        'description': 'Serviço para gerenciamento de alertas do sistema',
        'responsibilities': [
            'Criação de alertas',
            'Verificação automática de problemas',
            'Scan de inconsistências',
            'Estatísticas de alertas'
        ]
    },
    'ImportService': {
        'description': 'Serviço para importação de arquivos',
        'responsibilities': [
            'Processamento de arquivos (Excel, CSV, PDF)',
            'Validação de dados',
            'Importação de diferentes operadoras',
            'Log de importações'
        ]
    },
    'ReportService': {
        'description': 'Serviço para geração de relatórios',
        'responsibilities': [
            'Exportação para diferentes formatos',
            'Geração de relatórios estatísticos',
            'Dashboard e métricas'
        ]
    }
}


def get_service_documentation(service_name=None):
    """
    Retorna documentação dos serviços.
    
    Args:
        service_name: Nome do serviço (opcional)
    
    Returns:
        Dict com documentação
    """
    if service_name:
        return SERVICES_DOCS.get(service_name, {})
    return SERVICES_DOCS


# Atalhos para serviços comuns (para facilitar o uso)
def get_ci_service():
    """Retorna o serviço de CI (singleton)."""
    return ci_service


def get_alert_service():
    """Retorna o serviço de alertas (singleton)."""
    return alert_service


def get_import_service():
    """Retorna o serviço de importação (singleton)."""
    return import_service


def get_report_service():
    """Retorna o serviço de relatórios (singleton)."""
    return report_service