# 🚀 GUIA DE DEPLOYMENT - SISTEMA CI GESTÃO

## Guia Completo de Implantação em Produção

---

## 📋 Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Deployment em Servidor Ubuntu](#deployment-em-servidor-ubuntu)
3. [Deployment com Docker](#deployment-com-docker)
4. [Deployment no Heroku](#deployment-no-heroku)
5. [Deployment na AWS](#deployment-na-aws)
6. [Deployment com Nginx + Gunicorn](#nginx--gunicorn)
7. [Configuração de HTTPS](#configuração-de-https)
8. [Backup e Recuperação](#backup-e-recuperação)
9. [Monitoramento](#monitoramento)
10. [Troubleshooting](#troubleshooting)

---

## 🔧 Pré-requisitos

### Conhecimentos Necessários
- Linux básico (comandos, permissões, etc)
- Git
- Conceitos de web servers
- SQL básico

### Recursos Mínimos
- **CPU:** 1 vCPU (2 vCPUs recomendado)
- **RAM:** 1GB (2GB recomendado)
- **Disco:** 10GB (20GB recomendado)
- **OS:** Ubuntu 20.04+ ou similar

### Softwares Necessários
- Python 3.8+
- PostgreSQL 12+ ou MySQL 8+
- Nginx ou Apache
- Supervisor ou Systemd
- Certbot (para HTTPS)

---

## 🖥️ Deployment em Servidor Ubuntu

### 1. Preparar o Servidor

```bash
# Atualizar pacotes
sudo apt-get update
sudo apt-get upgrade -y

# Instalar dependências do sistema
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    supervisor \
    git \
    build-essential \
    libpq-dev

# Criar usuário para a aplicação
sudo adduser --disabled-password --gecos "" cigestao
sudo usermod -aG sudo cigestao
```

### 2. Configurar PostgreSQL

```bash
# Conectar ao PostgreSQL
sudo -u postgres psql

# Criar banco e usuário
CREATE DATABASE ci_gestao;
CREATE USER cigestao_user WITH PASSWORD 'senha_super_segura_aqui';
GRANT ALL PRIVILEGES ON DATABASE ci_gestao TO cigestao_user;
ALTER USER cigestao_user CREATEDB;  # Para testes
\q
```

### 3. Clonar e Configurar a Aplicação

```bash
# Trocar para usuário da aplicação
sudo su - cigestao

# Clonar repositório
cd /home/cigestao
git clone https://github.com/seu-usuario/ci-gestao.git
cd ci-gestao

# Criar ambiente virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Criar arquivo .env
cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
DATABASE_URL=postgresql://cigestao_user:senha_super_segura_aqui@localhost/ci_gestao
SESSION_COOKIE_SECURE=true
HOST=0.0.0.0
PORT=8000
EOF

# Criar diretórios necessários
mkdir -p logs uploads backups

# Inicializar banco de dados
python app.py
```

### 4. Configurar Gunicorn

```bash
# Criar arquivo de configuração do Gunicorn
cat > /home/cigestao/ci-gestao/gunicorn_config.py << EOF
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/home/cigestao/ci-gestao/logs/gunicorn_access.log"
errorlog = "/home/cigestao/ci-gestao/logs/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "ci_gestao"

# Server mechanics
daemon = False
pidfile = "/home/cigestao/ci-gestao/gunicorn.pid"
user = "cigestao"
group = "cigestao"
tmp_upload_dir = None

# SSL (se usar HTTPS direto no Gunicorn)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"
EOF
```

### 5. Configurar Supervisor

```bash
# Sair do usuário cigestao
exit

# Criar configuração do Supervisor
sudo cat > /etc/supervisor/conf.d/ci_gestao.conf << EOF
[program:ci_gestao]
command=/home/cigestao/ci-gestao/venv/bin/gunicorn -c /home/cigestao/ci-gestao/gunicorn_config.py wsgi:app
directory=/home/cigestao/ci-gestao
user=cigestao
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/home/cigestao/ci-gestao/logs/supervisor_error.log
stdout_logfile=/home/cigestao/ci-gestao/logs/supervisor_output.log
EOF

# Recarregar Supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ci_gestao
sudo supervisorctl status ci_gestao
```

### 6. Configurar Nginx

```bash
# Criar configuração do Nginx
sudo cat > /etc/nginx/sites-available/ci_gestao << EOF
server {
    listen 80;
    server_name ci-gestao.seudominio.com.br;
    
    # Redirecionar para HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ci-gestao.seudominio.com.br;
    
    # SSL Configuration (será configurado pelo Certbot)
    # ssl_certificate /path/to/cert.pem;
    # ssl_certificate_key /path/to/key.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Logs
    access_log /var/log/nginx/ci_gestao_access.log;
    error_log /var/log/nginx/ci_gestao_error.log;
    
    # Max upload size
    client_max_body_size 100M;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml;
    
    # Static files
    location /static/ {
        alias /home/cigestao/ci-gestao/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Uploads (protegido)
    location /uploads/ {
        internal;
        alias /home/cigestao/ci-gestao/uploads/;
    }
    
    # Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

# Habilitar site
sudo ln -s /etc/nginx/sites-available/ci_gestao /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🐳 Deployment com Docker

### 1. Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn psycopg2-binary

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p logs uploads backups

# Expose port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "-c", "gunicorn_config.py", "wsgi:app"]
```

### 2. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=ci_gestao
      - POSTGRES_USER=cigestao_user
      - POSTGRES_PASSWORD=senha_super_segura
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cigestao_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build: .
    command: gunicorn -c gunicorn_config.py wsgi:app
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
      - ./backups:/app/backups
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://cigestao_user:senha_super_segura@db:5432/ci_gestao
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=sua_chave_secreta_aqui
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./app/static:/app/static:ro
      - ./uploads:/app/uploads:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - web
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

volumes:
  postgres_data:
```

### 3. Comandos Docker

```bash
# Build e iniciar
docker-compose up -d --build

# Ver logs
docker-compose logs -f web

# Executar migrações
docker-compose exec web python app.py

# Parar
docker-compose down

# Parar e remover volumes
docker-compose down -v
```

---

## ☁️ Deployment no Heroku

### 1. Preparar Projeto

```bash
# Criar Procfile
echo "web: gunicorn wsgi:app" > Procfile

# Criar runtime.txt
echo "python-3.11.7" > runtime.txt

# Criar .slugignore (arquivos a ignorar no deploy)
cat > .slugignore << EOF
*.pyc
__pycache__/
.git/
.env
tests/
*.md
.vscode/
EOF
```

### 2. Deploy

```bash
# Login no Heroku
heroku login

# Criar app
heroku create ci-gestao-producao

# Adicionar PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Adicionar Redis (opcional)
heroku addons:create heroku-redis:hobby-dev

# Configurar variáveis de ambiente
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
heroku config:set SESSION_COOKIE_SECURE=true

# Deploy
git push heroku main

# Executar comandos
heroku run python app.py

# Ver logs
heroku logs --tail

# Abrir app
heroku open
```

---

## 🔒 Configuração de HTTPS

### Com Certbot (Let's Encrypt)

```bash
# Instalar Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d ci-gestao.seudominio.com.br

# Renovação automática
sudo certbot renew --dry-run

# Adicionar ao crontab
sudo crontab -e
# Adicionar: 0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 💾 Backup e Recuperação

### Script de Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/home/cigestao/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="ci_gestao"
DB_USER="cigestao_user"

# Backup do banco
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup dos uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /home/cigestao/ci-gestao/uploads

# Manter apenas últimos 7 backups
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete
find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +7 -delete

echo "Backup concluído: $DATE"
```

### Agendar Backup

```bash
# Adicionar ao crontab
crontab -e
# Backup diário às 2h da manhã
0 2 * * * /home/cigestao/backup.sh >> /home/cigestao/logs/backup.log 2>&1
```

### Restaurar Backup

```bash
# Restaurar banco
gunzip < db_20250203_020000.sql.gz | psql -U cigestao_user ci_gestao

# Restaurar uploads
tar -xzf uploads_20250203_020000.tar.gz -C /
```

---

## 📊 Monitoramento

### 1. Logs

```bash
# Logs da aplicação
tail -f /home/cigestao/ci-gestao/logs/app.log

# Logs do Gunicorn
tail -f /home/cigestao/ci-gestao/logs/gunicorn_error.log

# Logs do Nginx
sudo tail -f /var/log/nginx/ci_gestao_error.log

# Logs do Supervisor
sudo tail -f /var/log/supervisor/supervisord.log
```

### 2. Health Check

```python
# Adicionar endpoint de health check
@app.route('/health')
def health():
    """Health check endpoint."""
    try:
        # Testar banco
        db.session.execute('SELECT 1')
        db_status = 'ok'
    except:
        db_status = 'error'
    
    return jsonify({
        'status': 'ok' if db_status == 'ok' else 'error',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0'
    }), 200 if db_status == 'ok' else 503
```

### 3. Monitoramento com Sentry

```python
# Adicionar ao app/__init__.py
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="https://...@sentry.io/...",
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
    environment="production"
)
```

---

## 🔍 Troubleshooting

### Problema: Aplicação não inicia

```bash
# Verificar logs
sudo supervisorctl tail ci_gestao stderr

# Verificar se porta está em uso
sudo netstat -tulpn | grep :8000

# Verificar permissões
ls -la /home/cigestao/ci-gestao

# Testar manualmente
cd /home/cigestao/ci-gestao
source venv/bin/activate
python wsgi.py
```

### Problema: Erro de conexão com banco

```bash
# Verificar se PostgreSQL está rodando
sudo systemctl status postgresql

# Testar conexão
psql -U cigestao_user -d ci_gestao -h localhost

# Verificar credenciais no .env
cat /home/cigestao/ci-gestao/.env | grep DATABASE_URL
```

### Problema: 502 Bad Gateway

```bash
# Verificar se Gunicorn está rodando
sudo supervisorctl status ci_gestao

# Verificar configuração do Nginx
sudo nginx -t

# Reiniciar serviços
sudo supervisorctl restart ci_gestao
sudo systemctl restart nginx
```

### Problema: Arquivos não são enviados

```bash
# Verificar permissões da pasta uploads
ls -la /home/cigestao/ci-gestao/uploads
chmod 755 /home/cigestao/ci-gestao/uploads

# Verificar tamanho máximo no Nginx
grep client_max_body_size /etc/nginx/sites-available/ci_gestao
```

---

## ✅ Checklist Pré-Produção

- [ ] Banco de dados PostgreSQL configurado
- [ ] SECRET_KEY alterada
- [ ] DEBUG=False
- [ ] HTTPS configurado
- [ ] Firewall configurado
- [ ] Backup automático configurado
- [ ] Logs configurados
- [ ] Monitoramento ativo
- [ ] Variáveis de ambiente seguras
- [ ] Senhas padrão alteradas
- [ ] Rate limiting ativo
- [ ] CORS configurado (se necessário)
- [ ] Domínio configurado
- [ ] Email configurado (se necessário)
- [ ] Documentação atualizada
- [ ] Plano de recuperação de desastres

---

## 📞 Suporte

Para mais informações:
- 📧 Email: suporte@ci-gestao.com.br
- 📝 Documentação: https://docs.ci-gestao.com.br
- 🐛 Issues: https://github.com/seu-usuario/ci-gestao/issues

---

**Desenvolvido com ❤️ pela Equipe CI Gestão**
