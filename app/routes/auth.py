"""
Rotas para autenticação, autorização e gerenciamento de usuários.
"""

from flask import (
    Blueprint, 
    render_template, 
    request, 
    flash, 
    redirect, 
    url_for, 
    session,
    jsonify
)
from flask_login import (
    login_user, 
    logout_user, 
    login_required, 
    current_user
)
from datetime import datetime
import re

from app import db
from app.models import Usuario
from app.decorators import admin_required
from app.utils.validators import (
    is_valid_email,
    clean_email,
    sanitize_input
)

auth_bp = Blueprint('auth', __name__)


# ============================================================================
# ROTAS DE AUTENTICAÇÃO
# ============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Página de login do sistema.
    
    Método GET: Exibe formulário de login
    Método POST: Processa autenticação
    
    Parâmetros POST:
    - username: Nome de usuário
    - password: Senha
    - remember: Manter login (opcional)
    """
    # Se usuário já está logado, redireciona para home
    if current_user.is_authenticated:
        flash('Você já está logado no sistema.', 'info')
        return redirect(url_for('index'))
    
    if request.method == 'GET':
        next_url = request.args.get('next', '')
        return render_template('auth/login.html', next=next_url)
    
    # Método POST - Processar login
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', '') == 'on'
        
        # Validar entrada
        if not username:
            flash('Nome de usuário é obrigatório', 'error')
            return render_template('auth/login.html')
        
        if not password:
            flash('Senha é obrigatória', 'error')
            return render_template('auth/login.html')
        
        # Buscar usuário
        usuario = Usuario.query.filter_by(
            username=username,
            ativo=True
        ).first()
        
        # Verificar credenciais
        if not usuario or not usuario.check_password(password):
            # Registrar tentativa falha (em produção, implementar rate limiting)
            flash('Usuário ou senha incorretos', 'error')
            return render_template('auth/login.html')
        
        # Verificar se usuário está ativo
        if not usuario.ativo:
            flash('Sua conta está desativada. Entre em contato com o administrador.', 'error')
            return render_template('auth/login.html')
        
        # Realizar login
        login_user(usuario, remember=remember)
        
        # Atualizar último login
        usuario.last_login = datetime.utcnow()
        db.session.commit()
        
        # Registrar login bem-sucedido
        session['usuario_id'] = usuario.id
        session['usuario_nome'] = usuario.nome
        session['tipo_usuario'] = usuario.tipo_usuario
        
        flash(f'Login realizado com sucesso! Bem-vindo(a), {usuario.nome}!', 'success')
        
        # Redirecionar para URL original ou home
        next_url = request.args.get('next', '')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao processar login: {str(e)}', 'error')
        return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Realiza logout do usuário.
    """
    try:
        # Registrar logout
        usuario_nome = current_user.nome
        
        # Realizar logout
        logout_user()
        session.clear()
        
        flash(f'Logout realizado com sucesso. Até logo, {usuario_nome}!', 'info')
        
    except Exception as e:
        flash(f'Erro ao realizar logout: {str(e)}', 'error')
    
    return redirect(url_for('auth.login'))


@auth_bp.route('/primeiro-acesso', methods=['GET', 'POST'])
def primeiro_acesso():
    """
    Página de primeiro acesso para alterar senha do admin.
    
    Apenas acessível se não houver usuários ativos no sistema.
    """
    # Verificar se já existem usuários ativos
    usuarios_ativos = Usuario.query.filter_by(ativo=True).count()
    if usuarios_ativos > 0 and current_user.is_anonymous:
        flash('O sistema já possui usuários cadastrados. Faça login.', 'info')
        return redirect(url_for('auth.login'))
    
    if request.method == 'GET':
        return render_template('auth/primeiro_acesso.html')
    
    # Método POST
    try:
        # Validar que é realmente primeiro acesso
        if usuarios_ativos > 0:
            flash('Esta funcionalidade não está mais disponível.', 'error')
            return redirect(url_for('auth.login'))
        
        # Obter dados do formulário
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validações
        errors = []
        
        if not nome:
            errors.append('Nome completo é obrigatório')
        
        if not email or not is_valid_email(email):
            errors.append('Email válido é obrigatório')
        
        if not username or len(username) < 3:
            errors.append('Nome de usuário deve ter pelo menos 3 caracteres')
        
        if not password or len(password) < 6:
            errors.append('Senha deve ter pelo menos 6 caracteres')
        
        if password != confirm_password:
            errors.append('As senhas não conferem')
        
        # Verificar se username já existe
        if Usuario.query.filter_by(username=username).first():
            errors.append('Nome de usuário já está em uso')
        
        # Verificar se email já existe
        if Usuario.query.filter_by(email=email).first():
            errors.append('Email já está cadastrado')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/primeiro_acesso.html')
        
        # Criar usuário admin
        usuario = Usuario(
            nome=nome,
            email=email,
            username=username,
            tipo_usuario='admin',
            ativo=True
        )
        usuario.set_password(password)
        
        db.session.add(usuario)
        db.session.commit()
        
        # Realizar login automático
        login_user(usuario)
        
        flash('Conta de administrador criada com sucesso!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar conta: {str(e)}', 'error')
        return render_template('auth/primeiro_acesso.html')


@auth_bp.route('/alterar-senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    """
    Permite ao usuário alterar sua própria senha.
    """
    if request.method == 'GET':
        return render_template('auth/alterar_senha.html')
    
    # Método POST
    try:
        senha_atual = request.form.get('senha_atual', '')
        nova_senha = request.form.get('nova_senha', '')
        confirmar_senha = request.form.get('confirmar_senha', '')
        
        # Validações
        if not senha_atual:
            flash('Senha atual é obrigatória', 'error')
            return render_template('auth/alterar_senha.html')
        
        if not nova_senha or len(nova_senha) < 6:
            flash('Nova senha deve ter pelo menos 6 caracteres', 'error')
            return render_template('auth/alterar_senha.html')
        
        if nova_senha != confirmar_senha:
            flash('As senhas não conferem', 'error')
            return render_template('auth/alterar_senha.html')
        
        # Verificar senha atual
        if not current_user.check_password(senha_atual):
            flash('Senha atual incorreta', 'error')
            return render_template('auth/alterar_senha.html')
        
        # Verificar se nova senha é igual à atual
        if current_user.check_password(nova_senha):
            flash('Nova senha não pode ser igual à atual', 'error')
            return render_template('auth/alterar_senha.html')
        
        # Alterar senha
        current_user.set_password(nova_senha)
        db.session.commit()
        
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao alterar senha: {str(e)}', 'error')
        return render_template('auth/alterar_senha.html')


# ============================================================================
# ROTAS DE GERENCIAMENTO DE USUÁRIOS (ADMIN)
# ============================================================================

@auth_bp.route('/usuarios')
@login_required
@admin_required
def listar_usuarios():
    """
    Lista todos os usuários do sistema.
    
    Apenas para administradores.
    """
    try:
        # Parâmetros de filtro
        tipo = request.args.get('tipo', '')
        status = request.args.get('status', '')
        search = request.args.get('search', '').strip()
        
        # Query base
        query = Usuario.query
        
        # Aplicar filtros
        if tipo:
            query = query.filter_by(tipo_usuario=tipo)
        
        if status == 'ativo':
            query = query.filter_by(ativo=True)
        elif status == 'inativo':
            query = query.filter_by(ativo=False)
        
        if search:
            term = f'%{search}%'
            query = query.filter(
                db.or_(
                    Usuario.nome.ilike(term),
                    Usuario.username.ilike(term),
                    Usuario.email.ilike(term)
                )
            )
        
        # Ordenação
        usuarios = query.order_by(
            Usuario.tipo_usuario.desc(),
            Usuario.nome
        ).all()
        
        # Estatísticas
        total = len(usuarios)
        ativos = sum(1 for u in usuarios if u.ativo)
        admins = sum(1 for u in usuarios if u.tipo_usuario == 'admin')
        
        return render_template(
            'auth/usuarios.html',
            usuarios=usuarios,
            filtros={
                'tipo': tipo,
                'status': status,
                'search': search
            },
            estatisticas={
                'total': total,
                'ativos': ativos,
                'inativos': total - ativos,
                'admins': admins,
                'usuarios': total - admins
            }
        )
        
    except Exception as e:
        flash(f'Erro ao listar usuários: {str(e)}', 'error')
        return redirect(url_for('index'))


@auth_bp.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
@admin_required
def novo_usuario():
    """
    Cria um novo usuário.
    
    Apenas para administradores.
    """
    if request.method == 'GET':
        return render_template('auth/usuario_editar.html', usuario=None)
    
    # Método POST
    try:
        # Obter dados do formulário
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        tipo_usuario = request.form.get('tipo_usuario', 'usuario')
        ativo = request.form.get('ativo', '') == 'on'
        
        # Validações
        errors = []
        
        if not nome:
            errors.append('Nome completo é obrigatório')
        
        if not email or not is_valid_email(email):
            errors.append('Email válido é obrigatório')
        
        if not username or len(username) < 3:
            errors.append('Nome de usuário deve ter pelo menos 3 caracteres')
        
        # Validar tipo de usuário
        if tipo_usuario not in ['admin', 'usuario']:
            errors.append('Tipo de usuário inválido')
        
        # Verificar unicidade
        if Usuario.query.filter_by(username=username).first():
            errors.append('Nome de usuário já está em uso')
        
        if Usuario.query.filter_by(email=email).first():
            errors.append('Email já está cadastrado')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/usuario_editar.html', 
                                 form_data=request.form,
                                 usuario=None)
        
        # Criar usuário
        usuario = Usuario(
            nome=nome,
            email=email,
            username=username,
            tipo_usuario=tipo_usuario,
            ativo=ativo
        )
        
        # Gerar senha temporária
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        senha_temporaria = ''.join(secrets.choice(alphabet) for _ in range(10))
        usuario.set_password(senha_temporaria)
        
        db.session.add(usuario)
        db.session.commit()
        
        # Em produção, enviar email com senha temporária
        flash(f'Usuário {nome} criado com sucesso! Senha temporária: {senha_temporaria}', 'success')
        
        return redirect(url_for('auth.listar_usuarios'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar usuário: {str(e)}', 'error')
        return render_template('auth/usuario_editar.html', 
                             form_data=request.form,
                             usuario=None)


@auth_bp.route('/usuarios/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(id):
    """
    Edita um usuário existente.
    
    Apenas para administradores.
    """
    usuario = Usuario.query.get_or_404(id)
    
    # Não permitir editar a si mesmo (para evitar desativação acidental)
    if usuario.id == current_user.id:
        flash('Use a página de perfil para alterar seus próprios dados', 'warning')
        return redirect(url_for('auth.perfil'))
    
    if request.method == 'GET':
        return render_template('auth/usuario_editar.html', usuario=usuario)
    
    # Método POST
    try:
        # Obter dados do formulário
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        tipo_usuario = request.form.get('tipo_usuario', 'usuario')
        ativo = request.form.get('ativo', '') == 'on'
        
        # Validações
        errors = []
        
        if not nome:
            errors.append('Nome completo é obrigatório')
        
        if not email or not is_valid_email(email):
            errors.append('Email válido é obrigatório')
        
        if not username or len(username) < 3:
            errors.append('Nome de usuário deve ter pelo menos 3 caracteres')
        
        if tipo_usuario not in ['admin', 'usuario']:
            errors.append('Tipo de usuário inválido')
        
        # Verificar unicidade (exceto para o próprio usuário)
        outro_usuario = Usuario.query.filter(
            Usuario.username == username,
            Usuario.id != id
        ).first()
        
        if outro_usuario:
            errors.append('Nome de usuário já está em uso')
        
        outro_email = Usuario.query.filter(
            Usuario.email == email,
            Usuario.id != id
        ).first()
        
        if outro_email:
            errors.append('Email já está cadastrado')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/usuario_editar.html', usuario=usuario)
        
        # Atualizar usuário
        usuario.nome = nome
        usuario.email = email
        usuario.username = username
        usuario.tipo_usuario = tipo_usuario
        usuario.ativo = ativo
        
        db.session.commit()
        
        flash(f'Usuário {nome} atualizado com sucesso!', 'success')
        return redirect(url_for('auth.listar_usuarios'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar usuário: {str(e)}', 'error')
        return render_template('auth/usuario_editar.html', usuario=usuario)


@auth_bp.route('/usuarios/<int:id>/resetar-senha', methods=['POST'])
@login_required
@admin_required
def resetar_senha_usuario(id):
    """
    Reseta a senha de um usuário para uma senha temporária.
    
    Apenas para administradores.
    """
    usuario = Usuario.query.get_or_404(id)
    
    # Não permitir resetar a própria senha
    if usuario.id == current_user.id:
        flash('Use a página de alterar senha para resetar sua própria senha', 'error')
        return redirect(url_for('auth.listar_usuarios'))
    
    try:
        # Gerar senha temporária
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        senha_temporaria = ''.join(secrets.choice(alphabet) for _ in range(10))
        
        # Alterar senha
        usuario.set_password(senha_temporaria)
        db.session.commit()
        
        flash(f'Senha do usuário {usuario.nome} resetada com sucesso! Nova senha: {senha_temporaria}', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao resetar senha: {str(e)}', 'error')
    
    return redirect(url_for('auth.listar_usuarios'))


@auth_bp.route('/usuarios/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir_usuario(id):
    """
    Exclui um usuário (soft delete).
    
    Apenas para administradores.
    """
    usuario = Usuario.query.get_or_404(id)
    
    # Não permitir excluir a si mesmo
    if usuario.id == current_user.id:
        flash('Você não pode excluir sua própria conta', 'error')
        return redirect(url_for('auth.listar_usuarios'))
    
    try:
        # Verificar se é o último admin ativo
        if usuario.tipo_usuario == 'admin' and usuario.ativo:
            admins_ativos = Usuario.query.filter_by(
                tipo_usuario='admin',
                ativo=True
            ).count()
            
            if admins_ativos <= 1:
                flash('Não é possível excluir o último administrador ativo', 'error')
                return redirect(url_for('auth.listar_usuarios'))
        
        # Desativar usuário (soft delete)
        usuario.ativo = False
        db.session.commit()
        
        flash(f'Usuário {usuario.nome} desativado com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir usuário: {str(e)}', 'error')
    
    return redirect(url_for('auth.listar_usuarios'))


@auth_bp.route('/usuarios/<int:id>/reativar', methods=['POST'])
@login_required
@admin_required
def reativar_usuario(id):
    """
    Reativa um usuário desativado.
    
    Apenas para administradores.
    """
    usuario = Usuario.query.get_or_404(id)
    
    try:
        usuario.ativo = True
        db.session.commit()
        
        flash(f'Usuário {usuario.nome} reativado com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao reativar usuário: {str(e)}', 'error')
    
    return redirect(url_for('auth.listar_usuarios'))


# ============================================================================
# ROTAS DE PERFIL DO USUÁRIO
# ============================================================================

@auth_bp.route('/perfil')
@login_required
def perfil():
    """
    Exibe perfil do usuário logado.
    """
    return render_template('auth/perfil.html', usuario=current_user)


@auth_bp.route('/perfil/editar', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    """
    Permite ao usuário editar seus próprios dados.
    """
    if request.method == 'GET':
        return render_template('auth/editar_perfil.html', usuario=current_user)
    
    # Método POST
    try:
        # Obter dados do formulário
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip() or None
        
        # Validações
        errors = []
        
        if not nome:
            errors.append('Nome completo é obrigatório')
        
        if not email or not is_valid_email(email):
            errors.append('Email válido é obrigatório')
        
        # Verificar se email já está em uso (exceto pelo próprio usuário)
        outro_email = Usuario.query.filter(
            Usuario.email == email,
            Usuario.id != current_user.id
        ).first()
        
        if outro_email:
            errors.append('Email já está cadastrado')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/editar_perfil.html', usuario=current_user)
        
        # Atualizar perfil
        current_user.nome = nome
        current_user.email = email
        
        # Atualizar telefone se fornecido
        if telefone:
            current_user.telefone = telefone
        
        db.session.commit()
        
        # Atualizar sessão
        session['usuario_nome'] = current_user.nome
        
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('auth.perfil'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar perfil: {str(e)}', 'error')
        return render_template('auth/editar_perfil.html', usuario=current_user)


# ============================================================================
# ROTAS DE API (para AJAX)
# ============================================================================

@auth_bp.route('/api/verificar-username/<string:username>')
@login_required
def api_verificar_username(username):
    """
    Verifica se um nome de usuário já está em uso.
    
    Retorna JSON.
    """
    try:
        username_clean = username.strip()
        usuario_id = request.args.get('excluir_id', type=int)
        
        query = Usuario.query.filter_by(username=username_clean)
        
        if usuario_id:
            query = query.filter(Usuario.id != usuario_id)
        
        usuario = query.first()
        
        return jsonify({
            'disponivel': usuario is None,
            'usuario': {
                'id': usuario.id if usuario else None,
                'nome': usuario.nome if usuario else None,
                'email': usuario.email if usuario else None
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/verificar-email/<string:email>')
@login_required
def api_verificar_email(email):
    """
    Verifica se um email já está em uso.
    
    Retorna JSON.
    """
    try:
        email_clean = clean_email(email)
        if not email_clean:
            return jsonify({'error': 'Email inválido'}), 400
        
        usuario_id = request.args.get('excluir_id', type=int)
        
        query = Usuario.query.filter_by(email=email_clean)
        
        if usuario_id:
            query = query.filter(Usuario.id != usuario_id)
        
        usuario = query.first()
        
        return jsonify({
            'disponivel': usuario is None,
            'usuario': {
                'id': usuario.id if usuario else None,
                'nome': usuario.nome if usuario else None,
                'username': usuario.username if usuario else None
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/api/estatisticas-login')
@login_required
@admin_required
def api_estatisticas_login():
    """
    Retorna estatísticas de login dos usuários.
    
    Apenas para administradores.
    Retorna JSON.
    """
    try:
        # Últimos logins
        ultimos_logins = Usuario.query.filter(
            Usuario.last_login.isnot(None)
        ).order_by(
            Usuario.last_login.desc()
        ).limit(10).all()
        
        # Contagem por tipo
        total_usuarios = Usuario.query.count()
        usuarios_ativos = Usuario.query.filter_by(ativo=True).count()
        administradores = Usuario.query.filter_by(tipo_usuario='admin').count()
        
        # Usuários nunca logados
        nunca_logados = Usuario.query.filter_by(last_login=None).count()
        
        # Usuários inativos há mais de 30 dias
        from datetime import datetime, timedelta
        trinta_dias_atras = datetime.utcnow() - timedelta(days=30)
        inativos_30_dias = Usuario.query.filter(
            Usuario.last_login < trinta_dias_atras
        ).count()
        
        return jsonify({
            'total_usuarios': total_usuarios,
            'usuarios_ativos': usuarios_ativos,
            'usuarios_inativos': total_usuarios - usuarios_ativos,
            'administradores': administradores,
            'usuarios_comuns': total_usuarios - administradores,
            'nunca_logados': nunca_logados,
            'inativos_30_dias': inativos_30_dias,
            'ultimos_logins': [
                {
                    'id': u.id,
                    'nome': u.nome,
                    'username': u.username,
                    'last_login': u.last_login.isoformat() if u.last_login else None,
                    'ativo': u.ativo
                }
                for u in ultimos_logins
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ROTAS DE RECUPERAÇÃO DE SENHA (simplificadas)
# ============================================================================

@auth_bp.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    """
    Inicia processo de recuperação de senha.
    
    Nota: Em produção, implementar envio de email.
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'GET':
        return render_template('auth/esqueci_senha.html')
    
    # Método POST (versão simplificada)
    try:
        email = request.form.get('email', '').strip()
        
        if not email or not is_valid_email(email):
            flash('Email inválido', 'error')
            return render_template('auth/esqueci_senha.html')
        
        # Verificar se usuário existe
        usuario = Usuario.query.filter_by(email=email, ativo=True).first()
        
        if usuario:
            # Em produção: gerar token, enviar email, etc.
            flash(f'Instruções de recuperação enviadas para {email} (simulado)', 'info')
        else:
            # Por segurança, mostrar mensagem genérica
            flash('Se o email estiver cadastrado, você receberá instruções de recuperação', 'info')
        
        # Redirecionar para login
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        flash(f'Erro ao processar solicitação: {str(e)}', 'error')
        return render_template('auth/esqueci_senha.html')


# ============================================================================
# MIDDLEWARE E FUNÇÕES AUXILIARES
# ============================================================================

@auth_bp.before_app_request
def verificar_primeiro_acesso():
    """
    Middleware para verificar se é primeiro acesso ao sistema.
    
    Redireciona para página de primeiro acesso se não houver usuários ativos.
    """
    # Ignorar rotas estáticas e de auth
    if request.endpoint and (
        request.endpoint.startswith('static') or
        request.endpoint.startswith('auth.')
    ):
        return
    
    # Verificar se há usuários ativos
    try:
        usuarios_ativos = Usuario.query.filter_by(ativo=True).count()
        
        # Se não há usuários ativos e não está na página de primeiro acesso
        if usuarios_ativos == 0 and request.endpoint != 'auth.primeiro_acesso':
            return redirect(url_for('auth.primeiro_acesso'))
            
    except Exception:
        # Em caso de erro no banco, permitir acesso à página de primeiro acesso
        if request.endpoint != 'auth.primeiro_acesso':
            return redirect(url_for('auth.primeiro_acesso'))


@auth_bp.context_processor
def injetar_usuario():
    """
    Injeta informações do usuário em todos os templates.
    """
    return {
        'current_user': current_user,
        'is_admin': current_user.is_authenticated and current_user.tipo_usuario == 'admin'
    }


# ============================================================================
# ERROR HANDLERS ESPECÍFICOS
# ============================================================================

@auth_bp.errorhandler(401)
def nao_autorizado(error):
    """
    Handler para erro 401 (Não autorizado).
    """
    flash('Faça login para acessar esta página', 'warning')
    return redirect(url_for('auth.login', next=request.url))


@auth_bp.errorhandler(403)
def acesso_negado(error):
    """
    Handler para erro 403 (Acesso negado).
    """
    flash('Acesso negado. Permissão insuficiente.', 'error')
    return redirect(url_for('index'))


# ============================================================================
# UTILITÁRIOS DE SESSÃO
# ============================================================================

@auth_bp.route('/session/info')
@login_required
def session_info():
    """
    Retorna informações da sessão atual (para debug).
    
    Apenas para administradores em ambiente de desenvolvimento.
    """
    if not current_app.debug or not current_user.is_admin:
        abort(404)
    
    session_info = {
        'session_id': session.get('_id', 'N/A'),
        'usuario_id': session.get('usuario_id'),
        'usuario_nome': session.get('usuario_nome'),
        'tipo_usuario': session.get('tipo_usuario'),
        'permanent': session.permanent,
        'new': session.new,
        'modified': session.modified,
        'keys': list(session.keys())
    }
    
    return jsonify(session_info)


@auth_bp.route('/session/clear')
@login_required
@admin_required
def session_clear():
    """
    Limpa dados específicos da sessão (para debug).
    
    Apenas para administradores em ambiente de desenvolvimento.
    """
    if not current_app.debug:
        abort(404)
    
    keys_to_clear = request.args.getlist('key')
    
    if not keys_to_clear:
        # Limpar todos exceto essenciais
        essential_keys = ['_id', '_fresh', '_user_id', '_permanent']
        for key in list(session.keys()):
            if key not in essential_keys:
                session.pop(key, None)
    else:
        for key in keys_to_clear:
            session.pop(key, None)
    
    session.modified = True
    
    flash('Sessão limpa', 'info')
    return redirect(url_for('index'))