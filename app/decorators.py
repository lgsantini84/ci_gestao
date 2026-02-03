"""
Decorators personalizados para controle de acesso, validação e utilitários.
"""

from functools import wraps
from flask import session, flash, redirect, url_for, request, abort, jsonify, current_app
from flask_login import current_user
import logging
from datetime import datetime, timedelta
import time
from typing import Callable, Any, Optional, Tuple, Dict
import json


# ============================================================================
# DECORATORS DE CONTROLE DE ACESSO
# ============================================================================

def login_required(f: Callable) -> Callable:
    """
    Decorator para verificar se o usuário está autenticado.
    
    Redireciona para página de login se não estiver autenticado.
    Mantém a URL original no parâmetro 'next'.
    
    Args:
        f: Função a ser decorada
    
    Returns:
        Função decorada
    
    Example:
        @login_required
        def minha_rota():
            return 'Acesso permitido'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            
            # Registrar tentativa de acesso não autorizado
            log_acesso_nao_autorizado(request)
            
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f: Callable) -> Callable:
    """
    Decorator para verificar se o usuário é administrador.
    
    Requer que o usuário esteja autenticado e seja administrador.
    
    Args:
        f: Função a ser decorada
    
    Returns:
        Função decorada
    
    Example:
        @admin_required
        def rota_admin():
            return 'Acesso administrativo'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if not current_user.tipo_usuario == 'admin':
            flash('Acesso negado. Permissão de administrador necessária.', 'error')
            
            # Registrar tentativa de acesso não autorizado
            log_acesso_nao_autorizado(request, 'admin_required')
            
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission: str) -> Callable:
    """
    Decorator para verificar permissão específica.
    
    Args:
        permission: Nome da permissão requerida
    
    Returns:
        Decorator
    
    Example:
        @permission_required('importar_dados')
        def importar():
            return 'Importação permitida'
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Por favor, faça login para acessar esta página.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            # Verificar permissão (implementação básica)
            # Em produção, implementar sistema de permissões mais robusto
            user_permissions = session.get('permissions', [])
            
            if permission not in user_permissions and not current_user.is_admin:
                flash(f'Acesso negado. Permissão "{permission}" necessária.', 'error')
                
                # Registrar tentativa de acesso não autorizado
                log_acesso_nao_autorizado(request, f'permission_required:{permission}')
                
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def api_key_required(f: Callable) -> Callable:
    """
    Decorator para verificar API key em requisições de API.
    
    Args:
        f: Função a ser decorada
    
    Returns:
        Função decorada
    
    Example:
        @api_key_required
        def api_endpoint():
            return jsonify({'status': 'ok'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'API key requerida'}), 401
        
        # Verificar API key (em produção, verificar no banco de dados)
        valid_keys = current_app.config.get('API_KEYS', [])
        
        if api_key not in valid_keys:
            log_acesso_api_nao_autorizado(request)
            return jsonify({'error': 'API key inválida'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# DECORATORS DE VALIDAÇÃO
# ============================================================================

def validate_json(schema: Optional[Dict] = None) -> Callable:
    """
    Decorator para validar JSON de entrada.
    
    Args:
        schema: Esquema de validação (opcional)
    
    Returns:
        Decorator
    
    Example:
        @validate_json({
            'nome': {'type': 'string', 'required': True},
            'idade': {'type': 'integer', 'min': 0}
        })
        def criar_usuario():
            return 'Usuário criado'
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type deve ser application/json'}), 400
            
            try:
                data = request.get_json()
            except Exception as e:
                return jsonify({'error': f'JSON inválido: {str(e)}'}), 400
            
            # Validar com schema se fornecido
            if schema:
                errors = validate_against_schema(data, schema)
                if errors:
                    return jsonify({
                        'error': 'Validação falhou',
                        'details': errors
                    }), 400
            
            # Adicionar dados validados ao request para uso na função
            request.validated_data = data
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_form(fields: Dict[str, Callable]) -> Callable:
    """
    Decorator para validar formulário.
    
    Args:
        fields: Dicionário campo -> função validadora
    
    Returns:
        Decorator
    
    Example:
        @validate_form({
            'email': lambda x: '@' in x,
            'idade': lambda x: x.isdigit() and int(x) >= 0
        })
        def processar_form():
            return 'Formulário válido'
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            errors = {}
            
            for field_name, validator in fields.items():
                field_value = request.form.get(field_name)
                
                try:
                    if not validator(field_value):
                        errors[field_name] = f'Valor inválido para {field_name}'
                except Exception as e:
                    errors[field_name] = f'Erro ao validar {field_name}: {str(e)}'
            
            if errors:
                for field, error in errors.items():
                    flash(f'{field}: {error}', 'error')
                return redirect(request.url)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def required_params(*params: str) -> Callable:
    """
    Decorator para verificar parâmetros obrigatórios.
    
    Args:
        *params: Nomes dos parâmetros obrigatórios
    
    Returns:
        Decorator
    
    Example:
        @required_params('nome', 'email')
        def minha_rota():
            return 'Parâmetros presentes'
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            missing = []
            
            for param in params:
                if param not in request.values:
                    missing.append(param)
            
            if missing:
                error_msg = f'Parâmetros obrigatórios ausentes: {", ".join(missing)}'
                
                if request.is_json:
                    return jsonify({'error': error_msg}), 400
                else:
                    flash(error_msg, 'error')
                    return redirect(request.url)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================================
# DECORATORS DE CACHE
# ============================================================================

def cache_response(seconds: int = 300, key_prefix: str = 'cache') -> Callable:
    """
    Decorator para cache de resposta HTTP.
    
    Args:
        seconds: Tempo de cache em segundos
        key_prefix: Prefixo para chave de cache
    
    Returns:
        Decorator
    
    Example:
        @cache_response(seconds=60)
        def dados_frequentes():
            return 'Dados cacheados por 60 segundos'
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Gerar chave de cache baseada na função e argumentos
            cache_key = f"{key_prefix}:{f.__name__}:{str(args)}:{str(kwargs)}"
            
            # Verificar se está em cache
            cached = get_cached_response(cache_key)
            if cached is not None:
                return cached
            
            # Executar função e cachear resultado
            response = f(*args, **kwargs)
            cache_response_data(cache_key, response, seconds)
            
            return response
        return decorated_function
    return decorator


def memoize(ttl: int = 300) -> Callable:
    """
    Decorator para memoização de funções (cache em memória).
    
    Args:
        ttl: Time to live em segundos
    
    Returns:
        Decorator
    
    Example:
        @memoize(ttl=60)
        def calculo_pesado(x):
            time.sleep(2)
            return x * 2
    """
    cache = {}
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Gerar chave baseada nos argumentos
            key = (f.__name__, args, frozenset(kwargs.items()))
            
            # Verificar se está no cache e ainda é válido
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl:
                    return result
            
            # Executar função e cachear resultado
            result = f(*args, **kwargs)
            cache[key] = (result, time.time())
            
            # Limpar cache expirado periodicamente
            if len(cache) > 100:  # Limite arbitrário
                cleanup_expired_cache(cache, ttl)
            
            return result
        return decorated_function
    return decorator


# ============================================================================
# DECORATORS DE LOGGING E AUDITORIA
# ============================================================================

def log_access(f: Callable) -> Callable:
    """
    Decorator para registrar acesso a rotas.
    
    Args:
        f: Função a ser decorada
    
    Returns:
        Função decorada
    
    Example:
        @log_access
        def rota_sensivel():
            return 'Acesso registrado'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Registrar antes da execução
        log_acesso_rota(request, f.__name__, 'INICIADO')
        
        try:
            result = f(*args, **kwargs)
            
            # Registrar sucesso
            log_acesso_rota(request, f.__name__, 'CONCLUIDO')
            
            return result
            
        except Exception as e:
            # Registrar erro
            log_acesso_rota(request, f.__name__, 'ERRO', str(e))
            raise
    
    return decorated_function


def audit_action(action: str) -> Callable:
    """
    Decorator para auditoria de ações específicas.
    
    Args:
        action: Nome da ação sendo auditada
    
    Returns:
        Decorator
    
    Example:
        @audit_action('excluir_usuario')
        def excluir_usuario(id):
            return 'Usuário excluído'
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Informações para auditoria
            audit_data = {
                'action': action,
                'user_id': current_user.id if current_user.is_authenticated else None,
                'user_name': current_user.nome if current_user.is_authenticated else None,
                'timestamp': datetime.utcnow().isoformat(),
                'ip_address': request.remote_addr,
                'user_agent': request.user_agent.string,
                'request_method': request.method,
                'request_path': request.path,
                'request_args': dict(request.args),
                'function_name': f.__name__,
                'function_args': str(args),
                'function_kwargs': str(kwargs)
            }
            
            try:
                result = f(*args, **kwargs)
                
                # Adicionar resultado à auditoria
                audit_data['status'] = 'SUCCESS'
                audit_data['result'] = str(result)[:500]  # Limitar tamanho
                
                # Registrar auditoria
                log_audit(audit_data)
                
                return result
                
            except Exception as e:
                # Adicionar erro à auditoria
                audit_data['status'] = 'ERROR'
                audit_data['error'] = str(e)
                
                # Registrar auditoria
                log_audit(audit_data)
                
                raise
        
        return decorated_function
    return decorator


# ============================================================================
# DECORATORS DE PERFORMANCE
# ============================================================================

def time_execution(f: Callable) -> Callable:
    """
    Decorator para medir tempo de execução de funções.
    
    Args:
        f: Função a ser decorada
    
    Returns:
        Função decorada
    
    Example:
        @time_execution
        def funcao_lenta():
            time.sleep(2)
            return 'Concluído'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = f(*args, **kwargs)
            elapsed_time = time.time() - start_time
            
            # Log do tempo de execução
            log_performance(f.__name__, elapsed_time, 'SUCCESS')
            
            return result
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            
            # Log do tempo de execução com erro
            log_performance(f.__name__, elapsed_time, 'ERROR', str(e))
            
            raise
    
    return decorated_function


def rate_limit(requests_per_minute: int = 60) -> Callable:
    """
    Decorator para rate limiting (limitação de requisições).
    
    Args:
        requests_per_minute: Máximo de requisições por minuto
    
    Returns:
        Decorator
    
    Example:
        @rate_limit(requests_per_minute=30)
        def api_endpoint():
            return 'Requisição limitada'
    """
    def decorator(f: Callable) -> Callable:
        request_times = {}
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Identificar cliente (IP ou user_id)
            client_id = request.remote_addr
            if current_user.is_authenticated:
                client_id = str(current_user.id)
            
            now = time.time()
            
            # Inicializar histórico para este cliente
            if client_id not in request_times:
                request_times[client_id] = []
            
            # Remover requisições antigas (mais de 1 minuto)
            request_times[client_id] = [
                t for t in request_times[client_id] 
                if now - t < 60
            ]
            
            # Verificar se excedeu o limite
            if len(request_times[client_id]) >= requests_per_minute:
                log_rate_limit_exceeded(client_id, f.__name__)
                
                if request.is_json:
                    return jsonify({
                        'error': 'Rate limit excedido',
                        'retry_after': 60
                    }), 429
                else:
                    flash('Muitas requisições. Tente novamente em alguns instantes.', 'error')
                    return redirect(request.url)
            
            # Adicionar requisição atual
            request_times[client_id].append(now)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


# ============================================================================
# DECORATORS DE TRANSFORMAÇÃO
# ============================================================================

def json_response(f: Callable) -> Callable:
    """
    Decorator para converter retorno em JSON response.
    
    Args:
        f: Função a ser decorada
    
    Returns:
        Função decorada
    
    Example:
        @json_response
        def api_endpoint():
            return {'status': 'ok', 'data': [...]}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            
            # Se já é uma resposta Flask, retornar como está
            if hasattr(result, 'headers'):
                return result
            
            # Converter para JSON response
            return jsonify(result)
            
        except Exception as e:
            current_app.logger.error(f"Erro em {f.__name__}: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    return decorated_function


def template_response(template: str) -> Callable:
    """
    Decorator para renderizar template com dados da função.
    
    Args:
        template: Nome do template
    
    Returns:
        Decorator
    
    Example:
        @template_response('usuarios/list.html')
        def listar_usuarios():
            return {'usuarios': [...]}
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Executar função para obter dados
                data = f(*args, **kwargs)
                
                # Se já é uma resposta Flask, retornar como está
                if hasattr(data, 'headers'):
                    return data
                
                # Renderizar template com dados
                from flask import render_template
                return render_template(template, **data)
                
            except Exception as e:
                current_app.logger.error(f"Erro em {f.__name__}: {str(e)}")
                raise
        
        return decorated_function
    return decorator


def paginate(default_per_page: int = 50) -> Callable:
    """
    Decorator para adicionar paginação a resultados.
    
    Args:
        default_per_page: Itens por página padrão
    
    Returns:
        Decorator
    
    Example:
        @paginate(default_per_page=20)
        def listar_itens():
            return Item.query.all()  # Retorna lista completa
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Obter parâmetros de paginação
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', default_per_page, type=int)
            
            # Executar função para obter query ou lista
            result = f(*args, **kwargs)
            
            # Se for query do SQLAlchemy, paginar
            if hasattr(result, 'paginate'):
                paginated = result.paginate(page=page, per_page=per_page, error_out=False)
                
                # Retornar dados paginados
                return {
                    'items': paginated.items,
                    'pagination': {
                        'page': paginated.page,
                        'per_page': paginated.per_page,
                        'total': paginated.total,
                        'pages': paginated.pages,
                        'has_next': paginated.has_next,
                        'has_prev': paginated.has_prev,
                        'next_num': paginated.next_num,
                        'prev_num': paginated.prev_num
                    }
                }
            
            # Se for lista, paginar manualmente
            elif isinstance(result, list):
                start = (page - 1) * per_page
                end = start + per_page
                items = result[start:end]
                total = len(result)
                pages = (total + per_page - 1) // per_page
                
                return {
                    'items': items,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': pages,
                        'has_next': page < pages,
                        'has_prev': page > 1,
                        'next_num': page + 1 if page < pages else None,
                        'prev_num': page - 1 if page > 1 else None
                    }
                }
            
            # Se não for paginável, retornar como está
            return result
        
        return decorated_function
    return decorator


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def validate_against_schema(data: Dict, schema: Dict) -> Dict[str, str]:
    """
    Valida dados contra um schema.
    
    Args:
        data: Dados a validar
        schema: Schema de validação
    
    Returns:
        Dicionário de erros
    """
    errors = {}
    
    for field, rules in schema.items():
        value = data.get(field)
        
        # Verificar se é obrigatório
        if rules.get('required', False) and value is None:
            errors[field] = 'Campo obrigatório'
            continue
        
        # Se não é obrigatório e está vazio, pular outras validações
        if value is None:
            continue
        
        # Validar tipo
        expected_type = rules.get('type')
        if expected_type:
            type_map = {
                'string': str,
                'integer': int,
                'float': float,
                'boolean': bool,
                'array': list,
                'object': dict
            }
            
            if expected_type in type_map:
                expected_class = type_map[expected_type]
                if not isinstance(value, expected_class):
                    try:
                        # Tentar conversão
                        if expected_type == 'integer':
                            value = int(value)
                        elif expected_type == 'float':
                            value = float(value)
                        elif expected_type == 'boolean':
                            value = str(value).lower() in ('true', '1', 'yes')
                        else:
                            raise ValueError(f"Não pode converter para {expected_type}")
                        
                        # Atualizar valor convertido
                        data[field] = value
                    except ValueError:
                        errors[field] = f'Deve ser do tipo {expected_type}'
        
        # Validar valores mínimos/máximos
        if isinstance(value, (int, float)):
            if 'min' in rules and value < rules['min']:
                errors[field] = f'Valor mínimo: {rules["min"]}'
            
            if 'max' in rules and value > rules['max']:
                errors[field] = f'Valor máximo: {rules["max"]}'
        
        # Validar comprimento para strings
        if isinstance(value, str):
            if 'min_length' in rules and len(value) < rules['min_length']:
                errors[field] = f'Comprimento mínimo: {rules["min_length"]} caracteres'
            
            if 'max_length' in rules and len(value) > rules['max_length']:
                errors[field] = f'Comprimento máximo: {rules["max_length"]} caracteres'
            
            # Validar padrão regex
            if 'pattern' in rules:
                import re
                if not re.match(rules['pattern'], value):
                    errors[field] = f'Não corresponde ao padrão esperado'
    
    return errors


def get_cached_response(cache_key: str) -> Any:
    """
    Obtém resposta do cache.
    
    Args:
        cache_key: Chave do cache
    
    Returns:
        Resposta cacheadas ou None
    """
    # Implementação básica usando session
    # Em produção, usar Redis ou outro sistema de cache
    cached = session.get(f'cache_{cache_key}')
    
    if cached:
        data, timestamp = cached
        if time.time() - timestamp < 300:  # 5 minutos
            return data
    
    return None


def cache_response_data(cache_key: str, response: Any, seconds: int) -> None:
    """
    Armazena resposta no cache.
    
    Args:
        cache_key: Chave do cache
        response: Resposta a cachear
        seconds: Tempo de cache em segundos
    """
    # Implementação básica usando session
    # Nota: Session não é ideal para cache, usar Redis em produção
    session[f'cache_{cache_key}'] = (response, time.time())
    session.modified = True


def cleanup_expired_cache(cache: Dict, ttl: int) -> None:
    """
    Limpa cache expirado.
    
    Args:
        cache: Dicionário de cache
        ttl: Time to live em segundos
    """
    current_time = time.time()
    expired_keys = [
        key for key, (_, timestamp) in cache.items()
        if current_time - timestamp > ttl
    ]
    
    for key in expired_keys:
        cache.pop(key, None)


def log_acesso_nao_autorizado(request, requirement: str = 'login_required') -> None:
    """
    Registra tentativa de acesso não autorizado.
    
    Args:
        request: Objeto request
        requirement: Requisito que falhou
    """
    logger = logging.getLogger('security')
    logger.warning(
        f"Acesso não autorizado - "
        f"IP: {request.remote_addr}, "
        f"Path: {request.path}, "
        f"Method: {request.method}, "
        f"User: {current_user.id if current_user.is_authenticated else 'Anonymous'}, "
        f"Requirement: {requirement}"
    )


def log_acesso_api_nao_autorizado(request) -> None:
    """
    Registra tentativa de acesso à API não autorizada.
    
    Args:
        request: Objeto request
    """
    logger = logging.getLogger('api')
    logger.warning(
        f"API access denied - "
        f"IP: {request.remote_addr}, "
        f"Path: {request.path}, "
        f"Method: {request.method}, "
        f"API-Key: {request.headers.get('X-API-Key', 'None')}"
    )


def log_acesso_rota(request, route_name: str, status: str, error: str = None) -> None:
    """
    Registra acesso a rota.
    
    Args:
        request: Objeto request
        route_name: Nome da rota/função
        status: Status do acesso
        error: Mensagem de erro (opcional)
    """
    logger = logging.getLogger('access')
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'ip': request.remote_addr,
        'method': request.method,
        'path': request.path,
        'route': route_name,
        'user_id': current_user.id if current_user.is_authenticated else None,
        'user_agent': request.user_agent.string[:200] if request.user_agent else None,
        'status': status
    }
    
    if error:
        log_data['error'] = error
    
    logger.info(json.dumps(log_data))


def log_audit(audit_data: Dict) -> None:
    """
    Registra evento de auditoria.
    
    Args:
        audit_data: Dados de auditoria
    """
    logger = logging.getLogger('audit')
    logger.info(json.dumps(audit_data))


def log_performance(function_name: str, elapsed_time: float, status: str, error: str = None) -> None:
    """
    Registra métrica de performance.
    
    Args:
        function_name: Nome da função
        elapsed_time: Tempo de execução em segundos
        status: Status da execução
        error: Mensagem de erro (opcional)
    """
    logger = logging.getLogger('performance')
    
    log_entry = {
        'function': function_name,
        'elapsed_time': round(elapsed_time, 4),
        'status': status,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if error:
        log_entry['error'] = error
    
    # Apenas logar se for lento (> 1 segundo) ou erro
    if elapsed_time > 1.0 or status == 'ERROR':
        logger.warning(json.dumps(log_entry))
    elif elapsed_time > 0.5:
        logger.info(json.dumps(log_entry))


def log_rate_limit_exceeded(client_id: str, function_name: str) -> None:
    """
    Registra excedente de rate limit.
    
    Args:
        client_id: Identificador do cliente
        function_name: Nome da função
    """
    logger = logging.getLogger('ratelimit')
    logger.warning(
        f"Rate limit exceeded - "
        f"Client: {client_id}, "
        f"Function: {function_name}, "
        f"IP: {request.remote_addr}"
    )


# ============================================================================
# DECORATORS COMPOSTOS
# ============================================================================

def api_endpoint(f: Callable) -> Callable:
    """
    Decorator composto para endpoints de API.
    
    Combina:
    - login_required
    - validate_json
    - json_response
    - time_execution
    
    Args:
        f: Função a ser decorada
    
    Returns:
        Função decorada
    """
    @wraps(f)
    @login_required
    @validate_json()
    @json_response
    @time_execution
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    
    return decorated_function


def protected_route(f: Callable) -> Callable:
    """
    Decorator composto para rotas protegidas.
    
    Combina:
    - login_required
    - log_access
    - time_execution
    
    Args:
        f: Função a ser decorada
    
    Returns:
        Função decorada
    """
    @wraps(f)
    @login_required
    @log_access
    @time_execution
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    
    return decorated_function


def admin_api_endpoint(f: Callable) -> Callable:
    """
    Decorator composto para endpoints de API administrativos.
    
    Combina:
    - admin_required
    - api_endpoint
    - audit_action
    
    Args:
        f: Função a ser decorada
    
    Returns:
        Função decorada
    """
    @wraps(f)
    @admin_required
    @audit_action(f.__name__)
    def decorated_function(*args, **kwargs):
        return api_endpoint(f)(*args, **kwargs)
    
    return decorated_function


# ============================================================================
# DECORATORS PARA TESTES (desenvolvimento)
# ============================================================================

def development_only(f: Callable) -> Callable:
    """
    Decorator para permitir acesso apenas em desenvolvimento.
    
    Args:
        f: Função a ser decorada
    
    Returns:
        Função decorada
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app.debug:
            abort(404)
        return f(*args, **kwargs)
    return decorated_function


def mock_response(mock_data: Any) -> Callable:
    """
    Decorator para mockar resposta (útil para testes).
    
    Args:
        mock_data: Dados mockados
    
    Returns:
        Decorator
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_app.config.get('TESTING', False):
                return mock_data
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def skip_in_production(f: Callable) -> Callable:
    """
    Decorator para pular função em produção.
    
    Args:
        f: Função a ser decorada
    
    Returns:
        Função decorada
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app.debug:
            return None
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# EXEMPLOS DE USO
# ============================================================================

if __name__ == '__main__':
    # Exemplos de uso dos decorators
    
    # 1. Controle de acesso básico
    @login_required
    def dashboard():
        return "Painel do usuário"
    
    @admin_required
    def admin_panel():
        return "Painel administrativo"
    
    @permission_required('gerenciar_usuarios')
    def gerenciar_usuarios():
        return "Gerenciamento de usuários"
    
    # 2. Validação
    @validate_json({
        'nome': {'type': 'string', 'required': True},
        'idade': {'type': 'integer', 'min': 0}
    })
    def criar_pessoa():
        data = request.validated_data
        return f"Criando pessoa: {data['nome']}"
    
    @required_params('busca', 'pagina')
    def buscar():
        busca = request.args.get('busca')
        pagina = request.args.get('pagina')
        return f"Buscando '{busca}' na página {pagina}"
    
    # 3. Cache e performance
    @cache_response(seconds=60)
    def dados_cacheados():
        # Dados que mudam pouco
        return {'dados': 'cacheados por 60 segundos'}
    
    @memoize(ttl=300)
    def calculo_complexo(x):
        import time
        time.sleep(1)  # Simulação de cálculo pesado
        return x * 2
    
    @time_execution
    def operacao_lenta():
        import time
        time.sleep(2)
        return "Concluído"
    
    # 4. API e respostas
    @api_endpoint
    def api_dados():
        return {'status': 'ok', 'data': [1, 2, 3]}
    
    @json_response
    def api_simples():
        return {'message': 'Olá, mundo!'}
    
    @template_response('home.html')
    def home():
        return {'titulo': 'Página Inicial'}
    
    # 5. Auditoria e logging
    @audit_action('excluir_registro')
    def excluir_registro(id):
        return f"Registro {id} excluído"
    
    @log_access
    def rota_importante():
        return "Acesso registrado"
    
    # 6. Rate limiting
    @rate_limit(requests_per_minute=30)
    def api_limitada():
        return "Requisição dentro do limite"
    
    # 7. Decorators compostos
    @protected_route
    def rota_protegida():
        return "Rota protegida com logging e timing"
    
    @admin_api_endpoint
    def api_admin():
        return {'admin': 'dados'}
    
    print("Decorators carregados com sucesso!")