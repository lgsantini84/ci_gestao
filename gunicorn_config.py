"""
Configuração do Gunicorn - VERSÃO OTIMIZADA
============================================

Configuração de produção para o servidor Gunicorn WSGI.

Esta configuração é otimizada para performance e estabilidade em produção,
com workers, timeouts e logging apropriados.

Usage:
    gunicorn -c gunicorn_config.py wsgi:app

Author: Equipe CI Gestão
Version: 2.0.0
"""

import multiprocessing
import os

# ============================================================================
# SERVER SOCKET
# ============================================================================

# Endereço e porta onde o Gunicorn vai escutar
# 127.0.0.1:8000 - Apenas local (use com proxy reverso)
# 0.0.0.0:8000 - Todas as interfaces (se não usar proxy)
bind = os.environ.get('GUNICORN_BIND', '127.0.0.1:8000')

# Tamanho da fila de conexões pendentes
# Aumentar se tiver muitas conexões simultâneas
backlog = 2048


# ============================================================================
# WORKER PROCESSES
# ============================================================================

# Número de workers
# Fórmula recomendada: (2 x núcleos CPU) + 1
# Ajuste conforme o uso de CPU e memória do servidor
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))

# Tipo de worker
# sync - Worker padrão, síncrono (recomendado para a maioria dos casos)
# gevent - Worker assíncrono (requer: pip install gevent)
# eventlet - Worker assíncrono (requer: pip install eventlet)
# tornado - Worker tornado
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'sync')

# Conexões simultâneas por worker (apenas para workers assíncronos)
worker_connections = 1000

# Tempo máximo que um worker pode processar uma requisição
# Importante para prevenir travamentos
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))  # 2 minutos

# Tempo para manter conexões keep-alive
keepalive = 5

# Número máximo de requisições que um worker processa antes de reiniciar
# Previne memory leaks
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 1000))

# Variação aleatória no max_requests (previne reinício simultâneo de workers)
max_requests_jitter = 50


# ============================================================================
# WORKER LIFECYCLE
# ============================================================================

# Tempo de espera para graceful shutdown
graceful_timeout = 30

# Reiniciar workers após atualização de código
reload = os.environ.get('GUNICORN_RELOAD', 'False').lower() == 'true'

# Arquivos para monitorar mudanças (se reload=True)
reload_extra_files = [
    'config.py',
    '.env'
]


# ============================================================================
# LOGGING
# ============================================================================

# Nível de log
# critical, error, warning, info, debug
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')

# Arquivo de log de acesso
accesslog = os.environ.get(
    'GUNICORN_ACCESS_LOG',
    'logs/gunicorn_access.log'
)

# Formato do log de acesso
# h - endereço remoto
# l - '-'
# u - usuário
# t - data/hora
# r - linha de requisição
# s - status
# b - tamanho da resposta
# f - referer
# a - user agent
# T - tempo de processamento em segundos
# D - tempo de processamento em microsegundos
# L - tempo de processamento em segundos decimais
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Arquivo de log de erros
errorlog = os.environ.get(
    'GUNICORN_ERROR_LOG',
    'logs/gunicorn_error.log'
)

# Capturar saída do stdout/stderr da aplicação
capture_output = True

# Habilitar logs coloridos (apenas para desenvolvimento)
enable_stdio_inheritance = False


# ============================================================================
# PROCESS NAMING
# ============================================================================

# Nome do processo (visível no ps, top, etc)
proc_name = 'ci_gestao'


# ============================================================================
# SERVER MECHANICS
# ============================================================================

# Executar em background (daemon)
# Não usar com systemd/supervisor
daemon = False

# Arquivo PID
pidfile = os.environ.get('GUNICORN_PID', 'gunicorn.pid')

# Usuário e grupo para executar os workers
# IMPORTANTE: Não execute como root!
user = os.environ.get('GUNICORN_USER', None)
group = os.environ.get('GUNICORN_GROUP', None)

# Diretório temporário para uploads
tmp_upload_dir = None

# Umask para arquivos criados
umask = 0

# Diretório de trabalho
# Importante: deve ser o diretório da aplicação
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============================================================================
# SSL (HTTPS)
# ============================================================================

# Apenas configure SSL aqui se não estiver usando proxy reverso (Nginx)
# Normalmente, deixe o Nginx lidar com SSL

# Arquivo da chave privada
keyfile = os.environ.get('GUNICORN_KEYFILE', None)

# Arquivo do certificado
certfile = os.environ.get('GUNICORN_CERTFILE', None)

# Arquivo CA certificates
ca_certs = os.environ.get('GUNICORN_CA_CERTS', None)

# Requer certificado do cliente
cert_reqs = 0  # 0 = não requer


# ============================================================================
# SECURITY
# ============================================================================

# Limitar o tamanho do header
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190


# ============================================================================
# HOOKS
# ============================================================================

def on_starting(server):
    """
    Executado quando o master process inicia.
    """
    server.log.info("=" * 70)
    server.log.info("Gunicorn iniciando...")
    server.log.info(f"Workers: {workers}")
    server.log.info(f"Worker class: {worker_class}")
    server.log.info(f"Timeout: {timeout}s")
    server.log.info(f"Bind: {bind}")
    server.log.info("=" * 70)


def on_reload(server):
    """
    Executado quando o server recarrega.
    """
    server.log.info("Servidor recarregado")


def when_ready(server):
    """
    Executado quando o server está pronto.
    """
    server.log.info("✓ Servidor pronto para receber requisições")


def pre_fork(server, worker):
    """
    Executado antes de fazer fork de um worker.
    """
    pass


def post_fork(server, worker):
    """
    Executado depois de fazer fork de um worker.
    """
    server.log.info(f"Worker {worker.pid} iniciado")


def pre_exec(server):
    """
    Executado antes de re-executar o master.
    """
    server.log.info("Forked child, re-executing.")


def worker_int(worker):
    """
    Executado quando worker recebe SIGINT ou SIGQUIT.
    """
    worker.log.info(f"Worker {worker.pid} recebeu sinal de interrupção")


def worker_abort(worker):
    """
    Executado quando worker recebe SIGABRT.
    """
    worker.log.error(f"Worker {worker.pid} abortado")


def pre_request(worker, req):
    """
    Executado antes de processar cada requisição.
    Útil para logging ou validações.
    """
    # Log detalhado (descomente se necessário)
    # worker.log.debug(f"{req.method} {req.path}")
    pass


def post_request(worker, req, environ, resp):
    """
    Executado depois de processar cada requisição.
    Útil para métricas.
    """
    # Log de métricas (descomente se necessário)
    # worker.log.info(f"{req.method} {req.path} - {resp.status_code}")
    pass


def child_exit(server, worker):
    """
    Executado quando um worker termina.
    """
    server.log.info(f"Worker {worker.pid} terminado")


def worker_exit(server, worker):
    """
    Executado quando um worker sai.
    """
    server.log.info(f"Worker {worker.pid} saiu")


def nworkers_changed(server, new_value, old_value):
    """
    Executado quando o número de workers muda.
    """
    server.log.info(f"Número de workers mudou de {old_value} para {new_value}")


def on_exit(server):
    """
    Executado quando o master process termina.
    """
    server.log.info("=" * 70)
    server.log.info("Gunicorn encerrando...")
    server.log.info("=" * 70)


# ============================================================================
# CONFIGURAÇÕES DE PERFORMANCE
# ============================================================================

# Pré-carregar a aplicação antes de fazer fork dos workers
# Economia de memória (workers compartilham código)
# Mas complica hot-reload
preload_app = os.environ.get('GUNICORN_PRELOAD', 'False').lower() == 'true'

# Enviar arquivo via sendfile() (mais eficiente)
sendfile = True

# Reusar sockets
reuse_port = True


# ============================================================================
# VARIÁVEIS DE AMBIENTE
# ============================================================================

# Variáveis de ambiente a serem passadas para workers
raw_env = [
    # Adicione variáveis aqui se necessário
    # 'DJANGO_SETTINGS_MODULE=myproject.settings',
]


# ============================================================================
# ESTATÍSTICAS
# ============================================================================

# Habilitar servidor de estatísticas
# Acesse em http://localhost:9191
statsd_host = os.environ.get('STATSD_HOST', None)
statsd_prefix = 'ci_gestao'


# ============================================================================
# CONFIGURAÇÕES AVANÇADAS
# ============================================================================

# Timeout para graceful restart
graceful_timeout = 30

# Ignorar EPIPE (Broken pipe)
suppress_ragged_eofs = True

# Especificar engine de worker
# Para aplicações que fazem chamadas longas de I/O, considere usar:
# - gevent (pip install gevent)
# - eventlet (pip install eventlet)

# Exemplo para usar gevent:
# worker_class = 'gevent'
# worker_connections = 1000

# Exemplo para usar threads:
# threads = 4  # Número de threads por worker


# ============================================================================
# NOTAS
# ============================================================================

"""
RECOMENDAÇÕES:

1. WORKERS:
   - Aplicações CPU-bound: workers = (2 x CPU) + 1
   - Aplicações I/O-bound: mais workers ou usar gevent/eventlet
   
2. TIMEOUT:
   - Ajuste conforme suas requisições mais longas
   - Importações grandes podem precisar de timeout maior
   
3. LOGS:
   - Em produção, considere usar syslog ou serviço centralizado
   - Rotacione logs regularmente
   
4. PROXY:
   - Use Nginx na frente do Gunicorn
   - Configure SSL no Nginx, não no Gunicorn
   
5. MONITORING:
   - Use Supervisor ou Systemd para gerenciar o processo
   - Configure alertas para crashes
   
6. PERFORMANCE:
   - Monitore uso de CPU e memória
   - Ajuste workers conforme necessário
   - Considere usar cache (Redis/Memcached)

COMANDOS ÚTEIS:

# Iniciar
gunicorn -c gunicorn_config.py wsgi:app

# Iniciar com logs no terminal
gunicorn -c gunicorn_config.py wsgi:app --access-logfile - --error-logfile -

# Verificar configuração
gunicorn -c gunicorn_config.py --check-config wsgi:app

# Recarregar (graceful restart)
kill -HUP <master_pid>

# Parar gracefully
kill -TERM <master_pid>

# Parar imediatamente
kill -KILL <master_pid>
"""
