#!/usr/bin/env python3
"""
Sistema de Gestão de Colaboradores Internos (CI)
Aplicação principal com estrutura refatorada.
"""

import os
import sys
import warnings
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from app import create_app, db
from app.models import Usuario
from app.utils.validators import setup_directories

def create_admin_user():
    """Cria usuário admin padrão se não existir."""
    with app.app_context():
        if not Usuario.query.filter_by(username='admin').first():
            admin = Usuario(
                username='admin',
                nome='Administrador',
                email='admin@sistema.com',
                tipo_usuario='admin',
                ativo=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('[INFO] Usuário admin criado: admin / admin123')

def init_database():
    """Inicializa o banco de dados."""
    with app.app_context():
        db.create_all()
        print('[INFO] Banco de dados inicializado')

if __name__ == '__main__':
    # Criar aplicação
    app = create_app()
    
    # Configurar diretórios necessários
    setup_directories(app)
    
    # Inicializar banco e criar admin
    init_database()
    create_admin_user()
    
    # Iniciar servidor
    print(f'[INFO] Servidor iniciado em {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('[INFO] Acesse: http://localhost:5000')
    
    app.run(
        host=app.config.get('HOST', '0.0.0.0'),
        port=app.config.get('PORT', 5000),
        debug=app.config.get('DEBUG', False)
    )