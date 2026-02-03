"""
Utilitários para validação e limpeza de dados.
"""

import re
import os
from datetime import datetime, date
from typing import Optional, Tuple, Dict, Any, Union, List
import pandas as pd
from werkzeug.utils import secure_filename
from flask import current_app
import unicodedata


# ============================================================================
# CONSTANTES DE VALIDAÇÃO
# ============================================================================

# Formatos de data suportados
_DATE_FORMATS = [
    '%d/%m/%Y',    # 31/12/2023
    '%d/%m/%y',    # 31/12/23
    '%d-%m-%Y',    # 31-12-2023
    '%d-%m-%y',    # 31-12-23
    '%Y/%m/%d',    # 2023/12/31
    '%Y-%m-%d',    # 2023-12-31
    '%d.%m.%Y',    # 31.12.2023
    '%d.%m.%y',    # 31.12.23
]

# Base para conversão de datas Excel
_EXCEL_BASE = date(1899, 12, 30)

# Padrões regex
CPF_REGEX = r'^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$'
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
TELEFONE_REGEX = r'^(\+\d{1,3})?[\s-]?\(?\d{2,3}\)?[\s-]?\d{4,5}[\s-]?\d{4}$'
NUMERO_REGEX = r'^[0-9]+$'
NC_REGEX = r'^[0-9]{1,20}$'  # NC pode ter até 20 dígitos


# ============================================================================
# VALIDAÇÃO DE TIPOS BÁSICOS
# ============================================================================

def is_valid_cpf(cpf: str) -> bool:
    """
    Valida um CPF brasileiro.
    
    Args:
        cpf: String contendo o CPF
    
    Returns:
        True se o CPF for válido, False caso contrário
    
    Examples:
        >>> is_valid_cpf('123.456.789-09')
        True
        >>> is_valid_cpf('11111111111')
        False
    """
    if not cpf:
        return False
    
    # Remover caracteres não numéricos
    cpf = ''.join(filter(str.isdigit, str(cpf)))
    
    # CPF deve ter 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verificar se todos os dígitos são iguais (CPF inválido)
    if cpf == cpf[0] * 11:
        return False
    
    # Calcular primeiro dígito verificador
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    # Calcular segundo dígito verificador
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    # Verificar dígitos calculados
    return int(cpf[9]) == digito1 and int(cpf[10]) == digito2


def is_valid_email(email: str) -> bool:
    """
    Valida formato de email.
    
    Args:
        email: String contendo o email
    
    Returns:
        True se o email for válido, False caso contrário
    """
    if not email:
        return False
    
    email = str(email).strip()
    return bool(re.match(EMAIL_REGEX, email, re.IGNORECASE))


def is_valid_telefone(telefone: str) -> bool:
    """
    Valida formato de telefone brasileiro.
    
    Args:
        telefone: String contendo o telefone
    
    Returns:
        True se o telefone for válido, False caso contrário
    """
    if not telefone:
        return False
    
    telefone = str(telefone).strip()
    
    # Remover caracteres não numéricos
    numeros = ''.join(filter(str.isdigit, telefone))
    
    # Telefone deve ter 10 ou 11 dígitos (com DDD)
    if len(numeros) not in (10, 11):
        return False
    
    # Validar DDD (11 a 99)
    ddd = int(numeros[:2])
    if ddd < 11 or ddd > 99:
        return False
    
    return True


def is_valid_nc(nc: str) -> bool:
    """
    Valida formato de Número de Cadastro (NC).
    
    Args:
        nc: String contendo o NC
    
    Returns:
        True se o NC for válido, False caso contrário
    """
    if not nc:
        return False
    
    nc = str(nc).strip()
    
    # Verificar se contém apenas dígitos
    if not re.match(NUMERO_REGEX, nc):
        return False
    
    # NC deve ter entre 1 e 20 dígitos
    if len(nc) < 1 or len(nc) > 20:
        return False
    
    return True


def is_valid_empresa(codigo: str) -> bool:
    """
    Valida código de empresa.
    
    Args:
        codigo: Código da empresa
    
    Returns:
        True se a empresa for válida, False caso contrário
    """
    if not codigo:
        return False
    
    codigo = str(codigo).strip()
    
    # Verificar se está na lista de empresas válidas
    if hasattr(current_app, 'config'):
        valid_codes = current_app.config.get('VALID_COMPANY_CODES', {})
        return codigo in valid_codes
    
    return False


# ============================================================================
# LIMPEZA DE DADOS
# ============================================================================

def clean_cpf(cpf: str) -> Optional[str]:
    """
    Limpa e valida um CPF.
    
    Args:
        cpf: String contendo o CPF
    
    Returns:
        CPF limpo (apenas dígitos) ou None se inválido
    
    Examples:
        >>> clean_cpf('123.456.789-09')
        '12345678909'
        >>> clean_cpf('123')
        None
    """
    if not cpf:
        return None
    
    # Converter para string e remover espaços
    cpf_str = str(cpf).strip()
    
    # Remover caracteres não numéricos
    cpf_limpo = ''.join(filter(str.isdigit, cpf_str))
    
    # Verificar se tem 11 dígitos
    if len(cpf_limpo) != 11:
        return None
    
    # Validar CPF
    if not is_valid_cpf(cpf_limpo):
        return None
    
    return cpf_limpo


def clean_nc(nc: str) -> Optional[str]:
    """
    Limpa e valida um Número de Cadastro (NC).
    
    Args:
        nc: String contendo o NC
    
    Returns:
        NC limpo (apenas dígitos, sem zeros à esquerda) ou None se inválido
    """
    if not nc:
        return None
    
    # Converter para string e remover espaços
    nc_str = str(nc).strip()
    
    # Remover caracteres não numéricos
    nc_limpo = ''.join(filter(str.isdigit, nc_str))
    
    # Verificar se é válido
    if not nc_limpo or not is_valid_nc(nc_limpo):
        return None
    
    # Remover zeros à esquerda, mas manter pelo menos um dígito
    return nc_limpo.lstrip('0') or '0'


def clean_empresa(codigo: str) -> Optional[str]:
    """
    Limpa código de empresa.
    
    Args:
        codigo: Código da empresa
    
    Returns:
        Código limpo ou None se inválido
    """
    if not codigo:
        return None
    
    # Converter para string e remover espaços
    codigo_str = str(codigo).strip()
    
    # Remover caracteres não numéricos
    codigo_limpo = ''.join(filter(str.isdigit, codigo_str))
    
    # Verificar se é válido
    if not codigo_limpo or not is_valid_empresa(codigo_limpo):
        return None
    
    return codigo_limpo


def clean_nome(nome: str) -> str:
    """
    Limpa e normaliza um nome.
    
    Args:
        nome: String contendo o nome
    
    Returns:
        Nome limpo e normalizado
    
    Examples:
        >>> clean_nome('  João   DA  silva  ')
        'João da Silva'
    """
    if not nome:
        return ''
    
    # Converter para string
    nome_str = str(nome)
    
    # Remover espaços extras
    nome_limpo = ' '.join(nome_str.split())
    
    # Normalizar caracteres Unicode
    nome_limpo = unicodedata.normalize('NFKC', nome_limpo)
    
    # Capitalizar nome (tratando casos especiais)
    palavras = nome_limpo.split()
    palavras_capitalizadas = []
    
    for palavra in palavras:
        palavra_lower = palavra.lower()
        
        # Tratar preposições e artigos
        if palavra_lower in ('da', 'de', 'do', 'das', 'dos', 'e'):
            palavras_capitalizadas.append(palavra_lower)
        else:
            palavras_capitalizadas.append(palavra.capitalize())
    
    return ' '.join(palavras_capitalizadas)


def clean_email(email: str) -> Optional[str]:
    """
    Limpa e valida um email.
    
    Args:
        email: String contendo o email
    
    Returns:
        Email limpo em minúsculas ou None se inválido
    """
    if not email:
        return None
    
    # Converter para string e remover espaços
    email_str = str(email).strip().lower()
    
    # Validar email
    if not is_valid_email(email_str):
        return None
    
    return email_str


def clean_telefone(telefone: str) -> Optional[str]:
    """
    Limpa e formata um telefone brasileiro.
    
    Args:
        telefone: String contendo o telefone
    
    Returns:
        Telefone formatado ou None se inválido
    """
    if not telefone:
        return None
    
    # Converter para string e remover espaços
    telefone_str = str(telefone).strip()
    
    # Remover caracteres não numéricos
    numeros = ''.join(filter(str.isdigit, telefone_str))
    
    # Validar telefone
    if not is_valid_telefone(numeros):
        return None
    
    # Formatar: (XX) XXXXX-XXXX ou (XX) XXXX-XXXX
    if len(numeros) == 11:  # Celular
        return f'({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}'
    else:  # Telefone fixo
        return f'({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}'


def clean_valor_monetario(valor: str) -> Optional[float]:
    """
    Converte string de valor monetário brasileiro para float.
    
    Args:
        valor: String contendo o valor monetário
    
    Returns:
        Valor como float ou None se inválido
    
    Examples:
        >>> clean_valor_monetario('R$ 1.234,56')
        1234.56
        >>> clean_valor_monetario('5622')
        56.22
    """
    if not valor:
        return 0.0
    
    try:
        # Converter para string e limpar
        valor_str = str(valor).strip()
        
        # Remover R$ e espaços
        valor_str = valor_str.replace('R$', '').replace('$', '').strip()
        
        # Se começa com =", remove aspas (ex: ="5622")
        if valor_str.startswith('="') and valor_str.endswith('"'):
            valor_str = valor_str[2:-1]
        
        # Verificar se tem vírgula ou ponto
        tem_virgula = ',' in valor_str
        tem_ponto = '.' in valor_str
        
        # Se não tem nenhum separador decimal
        if not tem_virgula and not tem_ponto:
            try:
                valor_int = int(valor_str)
                # Para valores como 5622 são 56,22 (dividir por 100)
                # Mas também pode ser valor pequeno como 5 (que seria 5,00)
                if abs(valor_int) >= 100:  # Se for >= 100, assume centavos
                    return valor_int / 100.0
                else:
                    return float(valor_int)
            except ValueError:
                return 0.0
        
        # Se tem vírgula e ponto, é formato brasileiro (1.234,56)
        if tem_virgula and tem_ponto:
            # Remove pontos de milhar
            valor_str = valor_str.replace('.', '')
            # Substitui vírgula por ponto
            valor_str = valor_str.replace(',', '.')
        
        # Se só tem vírgula, é decimal brasileiro (1234,56)
        elif tem_virgula:
            valor_str = valor_str.replace(',', '.')
        
        # Se só tem ponto, pode ser decimal internacional (1234.56) ou milhar (1.234)
        elif tem_ponto:
            # Verificar se é milhar ou decimal
            parts = valor_str.split('.')
            if len(parts) == 2:
                # Tem uma parte decimal
                if len(parts[1]) <= 2:  # Máximo 2 casas decimais
                    # É decimal: 1234.56
                    pass
                else:
                    # Pode ser milhar com erro: 1.234
                    valor_str = valor_str.replace('.', '')
            else:
                # Mais de um ponto: 1.234.567 -> é milhar
                valor_str = valor_str.replace('.', '')
        
        return float(valor_str) if valor_str else 0.0
        
    except (ValueError, TypeError):
        return 0.0


# ============================================================================
# VALIDAÇÃO DE DATAS
# ============================================================================

def parse_date(value: Any) -> Optional[date]:
    """
    Tenta converter um valor para data.
    
    Args:
        value: Valor a ser convertido (string, int, float, date, datetime)
    
    Returns:
        Objeto date ou None se não conseguir converter
    
    Examples:
        >>> parse_date('31/12/2023')
        datetime.date(2023, 12, 31)
        >>> parse_date(45000)  # Data Excel
        datetime.date(2023, 3, 15)
    """
    if not value:
        return None
    
    # Se já é date, retorna
    if isinstance(value, date):
        return value
    
    # Se é datetime, extrai date
    if isinstance(value, datetime):
        return value.date()
    
    # Se é número (data Excel)
    if isinstance(value, (int, float)):
        return convert_excel_date(value)
    
    # Se é string, tenta vários formatos
    if isinstance(value, str):
        value_str = value.strip()
        
        # Tentar formatos conhecidos
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue
        
        # Tentar converter com pandas (mais flexível)
        try:
            dt = pd.to_datetime(value_str, dayfirst=True, errors='coerce')
            if pd.notna(dt):
                return dt.date()
        except Exception:
            pass
        
        # Tentar como data Excel
        try:
            # Verificar se parece número
            if value_str.replace('.', '', 1).replace(',', '', 1).isdigit():
                num_val = float(value_str.replace(',', '.'))
                return convert_excel_date(num_val)
        except Exception:
            pass
    
    return None


def convert_excel_date(excel_date: Union[int, float]) -> Optional[date]:
    """
    Converte data Excel serial para datetime.date.
    
    Args:
        excel_date: Número serial da data Excel
    
    Returns:
        Objeto date ou None se inválido
    """
    try:
        if not isinstance(excel_date, (int, float)):
            return None
        
        # Valores típicos do Excel (de 1 a ~50.000)
        if not (1 <= excel_date <= 50000):
            return None
        
        # Converter
        result = _EXCEL_BASE + date.fromordinal(int(excel_date))
        
        # Verificar se o ano é razoável
        if 1900 <= result.year <= 2100:
            return result
        else:
            return None
            
    except Exception:
        return None


def validate_date(value: Any, default: Optional[date] = None) -> Optional[date]:
    """
    Valida e converte uma data.
    
    Args:
        value: Valor a ser validado
        default: Valor padrão se a validação falhar
    
    Returns:
        Data validada ou default
    """
    date_obj = parse_date(value)
    return date_obj if date_obj is not None else default


def is_valid_date(value: Any) -> bool:
    """
    Verifica se um valor pode ser convertido para data válida.
    
    Args:
        value: Valor a ser verificado
    
    Returns:
        True se for uma data válida, False caso contrário
    """
    return parse_date(value) is not None


def format_date_brasil(data: Optional[date]) -> str:
    """
    Formata data no padrão brasileiro (DD/MM/YYYY).
    
    Args:
        data: Objeto date
    
    Returns:
        String formatada ou string vazia se data for None
    """
    if not data:
        return ''
    
    return data.strftime('%d/%m/%Y')


def format_datetime_brasil(dt: Optional[datetime]) -> str:
    """
    Formata datetime no padrão brasileiro (DD/MM/YYYY HH:MM).
    
    Args:
        dt: Objeto datetime
    
    Returns:
        String formatada ou string vazia se datetime for None
    """
    if not dt:
        return ''
    
    return dt.strftime('%d/%m/%Y %H:%M')


# ============================================================================
# VALIDAÇÃO DE ARQUIVOS
# ============================================================================

def allowed_file(filename: str, allowed_extensions: Optional[set] = None) -> bool:
    """
    Verifica se a extensão do arquivo é permitida.
    
    Args:
        filename: Nome do arquivo
        allowed_extensions: Conjunto de extensões permitidas
    
    Returns:
        True se a extensão for permitida, False caso contrário
    """
    if not filename:
        return False
    
    if allowed_extensions is None:
        if hasattr(current_app, 'config'):
            allowed_extensions = set(current_app.config.get('ALLOWED_EXTENSIONS', set()))
        else:
            allowed_extensions = {'xlsx', 'xls', 'csv', 'pdf', 'txt'}
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def secure_upload_file(file, upload_folder: str, allowed_extensions: Optional[set] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Processa upload de arquivo de forma segura.
    
    Args:
        file: Objeto de arquivo do Flask
        upload_folder: Pasta de upload
        allowed_extensions: Extensões permitidas
    
    Returns:
        Tuple (caminho_do_arquivo, mensagem_de_erro)
    """
    if not file or file.filename == '':
        return None, 'Nenhum arquivo selecionado'
    
    if not allowed_file(file.filename, allowed_extensions):
        return None, 'Tipo de arquivo não permitido'
    
    # Gerar nome seguro para o arquivo
    filename = secure_filename(file.filename)
    
    # Criar diretório se não existir
    os.makedirs(upload_folder, exist_ok=True)
    
    # Caminho completo do arquivo
    filepath = os.path.join(upload_folder, filename)
    
    # Verificar se arquivo já existe e adicionar sufixo se necessário
    counter = 1
    while os.path.exists(filepath):
        name, ext = os.path.splitext(filename)
        new_filename = f"{name}_{counter}{ext}"
        filepath = os.path.join(upload_folder, new_filename)
        counter += 1
    
    try:
        # Salvar arquivo
        file.save(filepath)
        return filepath, None
    except Exception as e:
        return None, f"Erro ao salvar arquivo: {str(e)}"


def validate_file_size(file, max_size_mb: int = 100) -> Tuple[bool, Optional[str]]:
    """
    Valida tamanho do arquivo.
    
    Args:
        file: Objeto de arquivo
        max_size_mb: Tamanho máximo em MB
    
    Returns:
        Tuple (valido, mensagem_de_erro)
    """
    if not hasattr(file, 'content_length'):
        return True, None
    
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file.content_length > max_size_bytes:
        return False, f'Arquivo muito grande. Tamanho máximo: {max_size_mb}MB'
    
    return True, None


# ============================================================================
# VALIDAÇÃO DE FORMULÁRIOS
# ============================================================================

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Valida campos obrigatórios em um dicionário de dados.
    
    Args:
        data: Dicionário com dados
        required_fields: Lista de campos obrigatórios
    
    Returns:
        Tuple (valido, mensagem_de_erro)
    """
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f'Campo obrigatório ausente: {field}'
    
    return True, None


def validate_field_types(data: Dict[str, Any], field_types: Dict[str, type]) -> Tuple[bool, Optional[str]]:
    """
    Valida tipos de campos em um dicionário de dados.
    
    Args:
        data: Dicionário com dados
        field_types: Dicionário campo -> tipo esperado
    
    Returns:
        Tuple (valido, mensagem_de_erro)
    """
    for field, expected_type in field_types.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], expected_type):
                return False, f'Campo {field} deve ser do tipo {expected_type.__name__}'
    
    return True, None


def sanitize_input(value: Any) -> Any:
    """
    Sanitiza entrada de dados para prevenir XSS.
    
    Args:
        value: Valor a ser sanitizado
    
    Returns:
        Valor sanitizado
    """
    if not isinstance(value, str):
        return value
    
    # Remover tags HTML/XML
    value = re.sub(r'<[^>]*>', '', value)
    
    # Escapar caracteres especiais
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;'
    }
    
    for char, replacement in replacements.items():
        value = value.replace(char, replacement)
    
    return value


# ============================================================================
# VALIDAÇÃO ESPECÍFICA DO SISTEMA
# ============================================================================

def extract_nc_from_matricula(matricula: str) -> Optional[str]:
    """
    Extrai NC (6 dígitos) de uma matrícula do Hapvida.
    
    Args:
        matricula: Número de matrícula
    
    Returns:
        NC extraído ou None se inválido
    """
    if not matricula:
        return None
    
    # Extrair apenas dígitos
    digits = ''.join(filter(str.isdigit, str(matricula)))
    
    # Se tiver 10+ dígitos, pegar os últimos 6
    if len(digits) >= 6:
        nc = digits[-6:].lstrip('0') or '000001'
        return clean_nc(nc)
    
    # Se não, completar com zeros à esquerda
    return clean_nc(digits.zfill(6))


def extrair_codigo_beneficiario(beneficiario_field: str) -> Optional[str]:
    """
    Extrai código beneficiário do campo 'BENEFICIARIO' no formato '0AFP5000442003-LUIZ GUSTAVO SANTINI'.
    
    Args:
        beneficiario_field: Campo do beneficiário
    
    Returns:
        Código beneficiário ou None
    """
    if not beneficiario_field:
        return None
    
    parts = str(beneficiario_field).split('-', 1)
    if len(parts) > 0:
        # Remover qualquer ponto, espaço ou hífen do código
        codigo = ''.join(filter(lambda c: c.isalnum(), parts[0]))
        return codigo if codigo else None
    
    return None


def determinar_parentesco_por_idade(
    data_nascimento_dep: Optional[date],
    data_nascimento_titular: Optional[date]
) -> str:
    """
    Determina parentesco baseado na diferença de idade.
    
    Args:
        data_nascimento_dep: Data de nascimento do dependente
        data_nascimento_titular: Data de nascimento do titular
    
    Returns:
        Parentesco estimado
    """
    if not data_nascimento_dep or not data_nascimento_titular:
        return 'DEPENDENTE'
    
    # Calcular idades
    hoje = date.today()
    
    idade_dep = hoje.year - data_nascimento_dep.year - (
        (hoje.month, hoje.day) < (data_nascimento_dep.month, data_nascimento_dep.day)
    )
    
    idade_titular = hoje.year - data_nascimento_titular.year - (
        (hoje.month, hoje.day) < (data_nascimento_titular.month, data_nascimento_titular.day)
    )
    
    # Calcular diferença de idade
    diferenca_idade = idade_titular - idade_dep
    
    # Lógica de parentesco
    if abs(diferenca_idade) <= 5:
        # Diferença pequena (até 5 anos) - provavelmente CONJUGE
        return 'CONJUGE'
    elif diferenca_idade >= 15:
        # Titular é pelo menos 15 anos mais velho - FILHO
        return 'FILHO(A)'
    elif diferenca_idade <= -15:
        # Titular é pelo menos 15 anos mais novo - PAIS
        return 'PAIS'
    else:
        # Outra relação familiar
        return 'OUTROS'


# ============================================================================
# VALIDAÇÃO DE CONFIGURAÇÃO
# ============================================================================

def validate_app_config() -> Tuple[bool, List[str]]:
    """
    Valida configuração da aplicação.
    
    Returns:
        Tuple (valido, lista_de_erros)
    """
    errors = []
    
    if not hasattr(current_app, 'config'):
        errors.append("Configuração da aplicação não encontrada")
        return False, errors
    
    config = current_app.config
    
    # Verificar configurações obrigatórias
    required_configs = [
        'SECRET_KEY',
        'SQLALCHEMY_DATABASE_URI',
        'UPLOAD_FOLDER',
        'VALID_COMPANY_CODES'
    ]
    
    for config_key in required_configs:
        if config_key not in config or not config[config_key]:
            errors.append(f"Configuração obrigatória ausente: {config_key}")
    
    # Verificar VALID_COMPANY_CODES
    if 'VALID_COMPANY_CODES' in config:
        if not isinstance(config['VALID_COMPANY_CODES'], dict):
            errors.append("VALID_COMPANY_CODES deve ser um dicionário")
        elif len(config['VALID_COMPANY_CODES']) == 0:
            errors.append("VALID_COMPANY_CODES não pode estar vazio")
    
    # Verificar UPLOAD_FOLDER
    if 'UPLOAD_FOLDER' in config:
        upload_folder = config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            try:
                os.makedirs(upload_folder, exist_ok=True)
            except Exception as e:
                errors.append(f"Não foi possível criar pasta de upload: {str(e)}")
    
    return len(errors) == 0, errors


def setup_directories(app) -> None:
    """
    Configura diretórios necessários para a aplicação.
    
    Args:
        app: Aplicação Flask
    """
    directories = [
        app.config.get('UPLOAD_FOLDER', 'uploads'),
        'uploads/backups',
        'static/charts',
        'logs'
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            app.logger.warning(f"Não foi possível criar diretório {directory}: {str(e)}")


# ============================================================================
# VALIDAÇÃO DE BANCO DE DADOS
# ============================================================================

def validate_database_connection() -> Tuple[bool, Optional[str]]:
    """
    Valida conexão com o banco de dados.
    
    Returns:
        Tuple (conectado, mensagem_de_erro)
    """
    try:
        from app import db
        # Tentar executar uma query simples
        db.session.execute('SELECT 1')
        return True, None
    except Exception as e:
        return False, f"Erro na conexão com o banco de dados: {str(e)}"


# ============================================================================
# UTILITÁRIOS DE FORMATAÇÃO
# ============================================================================

def format_cpf(cpf: str) -> str:
    """
    Formata CPF para exibição (XXX.XXX.XXX-XX).
    
    Args:
        cpf: CPF sem formatação
    
    Returns:
        CPF formatado ou string vazia se inválido
    """
    cpf_limpo = clean_cpf(cpf)
    if not cpf_limpo:
        return ''
    
    return f'{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}'


def format_currency(value: float) -> str:
    """
    Formata valor monetário no padrão brasileiro (R$ X.XXX,XX).
    
    Args:
        value: Valor a ser formatado
    
    Returns:
        Valor formatado
    """
    try:
        return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return 'R$ 0,00'


def truncate_string(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Trunca string para um comprimento máximo.
    
    Args:
        text: Texto a ser truncado
        max_length: Comprimento máximo
        suffix: Sufixo a ser adicionado se truncado
    
    Returns:
        String truncada
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


# ============================================================================
# DECORATORS DE VALIDAÇÃO
# ============================================================================

def validate_args(*validators):
    """
    Decorator para validar argumentos de função.
    
    Args:
        *validators: Funções validadoras
    
    Returns:
        Função decorada
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            for validator in validators:
                result, error = validator(*args, **kwargs)
                if not result:
                    raise ValueError(f"Validação falhou: {error}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_return(*validators):
    """
    Decorator para validar retorno de função.
    
    Args:
        *validators: Funções validadoras
    
    Returns:
        Função decorada
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            for validator in validators:
                validation_result = validator(result)
                if not validation_result:
                    raise ValueError(f"Validação de retorno falhou")
            return result
        return wrapper
    return decorator


# ============================================================================
# TESTES UNITÁRIOS (se executado diretamente)
# ============================================================================

if __name__ == '__main__':
    # Testes básicos
    print("Testando validadores...")
    
    # Teste CPF
    assert is_valid_cpf('123.456.789-09') == True
    assert is_valid_cpf('111.111.111-11') == False
    assert clean_cpf('123.456.789-09') == '12345678909'
    assert clean_cpf('123') == None
    print("✓ Testes CPF passaram")
    
    # Teste NC
    assert is_valid_nc('123456') == True
    assert is_valid_nc('abc') == False
    assert clean_nc('00123456') == '123456'
    print("✓ Testes NC passaram")
    
    # Teste datas
    test_date = parse_date('31/12/2023')
    assert test_date == date(2023, 12, 31)
    assert is_valid_date('31/12/2023') == True
    assert is_valid_date('data inválida') == False
    print("✓ Testes datas passaram")
    
    # Teste valores monetários
    assert clean_valor_monetario('R$ 1.234,56') == 1234.56
    assert clean_valor_monetario('5622') == 56.22
    print("✓ Testes valores monetários passaram")
    
    print("\nTodos os testes passaram!")