# 🏢 Sistema de Gestão de Colaboradores Internos (CI)

> Sistema completo e profissional para gestão de colaboradores, planos de saúde, dependentes e importação de dados de múltiplas operadoras.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-orange.svg)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Índice

- [Características](#-características)
- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Uso](#-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [API Documentation](#-api-documentation)
- [Testes](#-testes)
- [Deployment](#-deployment)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)

## ✨ Características

### 🎯 Funcionalidades Principais

- **Gestão Completa de Colaboradores**
  - Cadastro com validação de CPF
  - Histórico completo de alterações
  - Exclusão lógica (soft delete)
  - Múltiplos NCs por colaborador

- **Gerenciamento de Planos**
  - Planos de Saúde (múltiplas operadoras)
  - Planos Odontológicos
  - Coparticipação e cobrança
  - Controle de atendimentos

- **Importação Avançada**
  - Suporte a Excel (.xlsx, .xls)
  - Suporte a CSV
  - Suporte a PDF (extração automática)
  - Múltiplas operadoras: Unimed, Hapvida, Odontoprev
  - Validação automática de dados
  - Log detalhado de importações

- **Sistema de Alertas**
  - Detecção automática de inconsistências
  - Níveis de gravidade
  - Notificações e resolução
  - Dashboard de alertas

- **Relatórios e Exportação**
  - Exportação em múltiplos formatos
  - Relatórios estatísticos
  - Dashboards interativos
  - Filtros avançados

- **Segurança e Auditoria**
  - Autenticação de usuários
  - Controle de permissões (Admin/Operador)
  - Logs de todas as ações
  - Senhas criptografadas
  - Proteção CSRF
  - Sanitização de inputs

### 🚀 Melhorias Implementadas

#### Performance
- ✅ Eager loading para evitar N+1 queries
- ✅ Caching de consultas frequentes
- ✅ Indexação otimizada no banco
- ✅ Paginação eficiente
- ✅ Processamento assíncrono de importações

#### Segurança
- ✅ Validação completa de inputs
- ✅ Proteção contra SQL Injection
- ✅ Proteção XSS
- ✅ Rate limiting em APIs
- ✅ Logs de auditoria completos

#### Code Quality
- ✅ Type hints completos
- ✅ Docstrings em todas as funções
- ✅ Código seguindo PEP 8
- ✅ Tratamento robusto de erros
- ✅ Testes unitários e de integração

#### UX/UI
- ✅ Interface responsiva
- ✅ Validação client-side
- ✅ Feedback visual de ações
- ✅ Mensagens de erro claras
- ✅ Loading states

## 📦 Requisitos

### Requisitos do Sistema

- Python 3.8 ou superior
- SQLite (desenvolvimento) / PostgreSQL ou MySQL (produção)
- 512MB RAM mínimo (2GB recomendado)
- 100MB espaço em disco

### Dependências Python

```txt
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.2
Flask-Migrate==4.0.4
pandas==2.0.3
openpyxl==3.1.2
pdfplumber==0.9.0
python-dotenv==1.0.0
Werkzeug==2.3.6
```

## 🔧 Instalação

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/ci-gestao.git
cd ci-gestao
```

### 2. Crie um Ambiente Virtual

```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Instale as Dependências

```bash
# Produção
pip install -r requirements.txt

# Desenvolvimento (inclui ferramentas de teste e debug)
pip install -r requirements_dev.txt
```

### 4. Configure as Variáveis de Ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações:

```env
FLASK_ENV=development
SECRET_KEY=sua-chave-secreta-aqui
DATABASE_URL=sqlite:///database.db
```

### 5. Inicialize o Banco de Dados

```bash
python app.py
```

O sistema criará automaticamente:
- Banco de dados SQLite
- Tabelas necessárias
- Usuário admin padrão (admin/admin123)

## ⚙️ Configuração

### Configuração Básica (config.py)

```python
class Config:
    # Segurança
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sua-chave-secreta')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
    
    # Upload
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'pdf', 'txt'}
    
    # Empresas Válidas
    VALID_COMPANY_CODES = {
        '106': 'PSF',
        '110': 'PASCC',
        '170': 'NPAA'
    }
```

### Configuração de Produção

Para produção, use PostgreSQL ou MySQL:

```env
# PostgreSQL
DATABASE_URL=postgresql://usuario:senha@localhost/ci_gestao

# MySQL
DATABASE_URL=mysql://usuario:senha@localhost/ci_gestao
```

## 🎯 Uso

### Iniciando o Servidor

#### Desenvolvimento

```bash
python app.py
```

Acesse: `http://localhost:5000`

#### Produção (com Gunicorn)

```bash
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
```

### Primeiro Acesso

1. Acesse o sistema
2. Login padrão:
   - **Usuário:** admin
   - **Senha:** admin123
3. ⚠️ **IMPORTANTE:** Altere a senha padrão imediatamente!

### Fluxo de Trabalho Típico

#### 1. Importar Colaboradores Ativos

```
Importar → Selecionar "Ativos" → Upload do Excel → Processar
```

#### 2. Importar Planos de Saúde

```
Importar → Selecionar "Unimed/Hapvida/Odontoprev" → Upload → Processar
```

#### 3. Visualizar e Editar Colaboradores

```
Colaboradores → Buscar/Filtrar → Detalhes → Editar
```

#### 4. Gerar Relatórios

```
Relatórios → Selecionar tipo → Aplicar filtros → Exportar
```

## 📁 Estrutura do Projeto

```
ci_gestao/
├── app/
│   ├── __init__.py              # Factory da aplicação
│   ├── models.py                # Modelos do banco de dados
│   ├── exceptions.py            # Exceções customizadas
│   ├── decorators.py            # Decorators (auth, cache, etc)
│   │
│   ├── routes/                  # Rotas (Controllers)
│   │   ├── __init__.py
│   │   ├── auth.py              # Autenticação
│   │   ├── ci.py                # CRUD de colaboradores
│   │   ├── import_routes.py     # Importações
│   │   ├── alerts.py            # Alertas
│   │   ├── reports.py           # Relatórios
│   │   ├── api.py               # API REST
│   │   └── main.py              # Rotas principais
│   │
│   ├── services/                # Camada de serviços (Business Logic)
│   │   ├── __init__.py
│   │   ├── ci_service.py        # Lógica de colaboradores
│   │   ├── import_service.py    # Lógica de importação
│   │   ├── alert_service.py     # Lógica de alertas
│   │   └── report_service.py    # Lógica de relatórios
│   │
│   ├── utils/                   # Utilitários
│   │   ├── __init__.py
│   │   ├── validators.py        # Validações
│   │   ├── data_utils.py        # Manipulação de dados
│   │   ├── file_utils.py        # Manipulação de arquivos
│   │   ├── import_utils.py      # Utilitários de importação
│   │   ├── helpers.py           # Helpers gerais
│   │   └── pagination.py        # Paginação
│   │
│   ├── templates/               # Templates HTML
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── auth/
│   │   ├── ci/
│   │   ├── import/
│   │   ├── alerts/
│   │   ├── reports/
│   │   └── errors/
│   │
│   └── static/                  # Arquivos estáticos
│       ├── css/
│       ├── js/
│       └── img/
│
├── tests/                       # Testes automatizados
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_routes.py
│   └── test_utils.py
│
├── uploads/                     # Arquivos enviados
├── logs/                        # Logs da aplicação
│
├── app.py                       # Entry point
├── wsgi.py                      # WSGI para produção
├── config.py                    # Configurações
├── requirements.txt             # Dependências
├── requirements_dev.txt         # Dependências de dev
├── .env.example                 # Exemplo de variáveis de ambiente
├── .gitignore
└── README.md
```

## 📡 API Documentation

### Autenticação

Todas as rotas da API requerem autenticação via API Key no header:

```http
Authorization: Bearer YOUR_API_KEY
```

### Endpoints Principais

#### GET /api/v1/health

Verifica status da API.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-02-03T10:30:00Z",
  "version": "1.0.0"
}
```

#### GET /api/v1/colaboradores

Lista todos os colaboradores.

**Query Parameters:**
- `page` (int): Número da página (default: 1)
- `per_page` (int): Itens por página (default: 100)

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "nome": "João Silva",
      "cpf": "12345678901",
      "email": "joao@example.com",
      "nc_ativo": {
        "nc": "123456",
        "empresa": "106"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 100,
    "total": 150,
    "pages": 2
  }
}
```

#### GET /api/v1/colaboradores/{id}

Obtém detalhes de um colaborador específico.

**Response:**
```json
{
  "id": 1,
  "nome": "João Silva",
  "cpf": "12345678901",
  "email": "joao@example.com",
  "telefone": "11999999999",
  "data_admissao": "2020-01-15",
  "data_nascimento": "1990-05-20",
  "ncs": [...],
  "dependentes": [...],
  "planos_saude": [...],
  "planos_odonto": [...]
}
```

## 🧪 Testes

### Executar Todos os Testes

```bash
pytest
```

### Com Cobertura

```bash
pytest --cov=app --cov-report=html
```

### Testes Específicos

```bash
# Testar modelos
pytest tests/test_models.py

# Testar serviços
pytest tests/test_services.py

# Testar rotas
pytest tests/test_routes.py
```

## 🚀 Deployment

### Com Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "wsgi:app"]
```

```bash
docker build -t ci-gestao .
docker run -p 8000:8000 -e DATABASE_URL=postgresql://... ci-gestao
```

### Com Heroku

```bash
heroku create seu-app-ci-gestao
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
heroku run python app.py
```

### Com servidor tradicional (Ubuntu)

```bash
# Instalar dependências do sistema
sudo apt-get update
sudo apt-get install python3.9 python3-pip postgresql nginx supervisor

# Configurar aplicação
cd /var/www/ci-gestao
pip3 install -r requirements.txt

# Configurar Gunicorn com Supervisor
sudo nano /etc/supervisor/conf.d/ci-gestao.conf

# Configurar Nginx como reverse proxy
sudo nano /etc/nginx/sites-available/ci-gestao

# Reiniciar serviços
sudo supervisorctl reread
sudo supervisorctl update
sudo nginx -t && sudo systemctl restart nginx
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Padrões de Código

- Seguir PEP 8
- Type hints em todas as funções
- Docstrings em formato Google
- Testes para novas funcionalidades
- Commits em português, descritivos

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👥 Autores

- **Equipe de Desenvolvimento** - *Trabalho Inicial*

## 🙏 Agradecimentos

- Flask Framework
- SQLAlchemy
- Pandas
- Todas as bibliotecas open-source utilizadas

## 📞 Suporte

- 📧 Email: suporte@ci-gestao.com
- 📝 Issues: [GitHub Issues](https://github.com/seu-usuario/ci-gestao/issues)
- 📖 Documentação: [Wiki](https://github.com/seu-usuario/ci-gestao/wiki)

---

**Desenvolvido com ❤️ pela equipe CI Gestão**
