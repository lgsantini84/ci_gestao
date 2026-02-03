"""
Rotas principais do sistema.
"""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models import (
    ColaboradorInterno, Alerta, Dependente,
    PlanoSaude, PlanoOdontologico, NumeroCadastro
)
from app import db
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/index')
@main_bp.route('/dashboard')
def index():
    """
    Página inicial / Dashboard.
    """
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Obter estatísticas para o dashboard
    estatisticas = {}
    
    # Total de colaboradores ativos
    estatisticas['total_colaboradores'] = ColaboradorInterno.query.filter_by(is_deleted=False).count()
    
    # Colaboradores com NC ativo
    estatisticas['total_ativos'] = ColaboradorInterno.query.filter_by(is_deleted=False)\
        .filter(ColaboradorInterno.id.in_(
            db.session.query(NumeroCadastro.colaborador_id).filter_by(ativo=True)
        )).count()
    
    # Distribuição por empresa
    dist_empresa = db.session.query(
        NumeroCadastro.cod_empresa,
        func.count(NumeroCadastro.id).label('total')
    ).filter_by(ativo=True).group_by(NumeroCadastro.cod_empresa).all()
    
    estatisticas['distribuicao_empresa'] = [
        {'empresa': emp, 'total': total}
        for emp, total in dist_empresa
    ]
    
    # Total de dependentes
    estatisticas['total_dependentes'] = Dependente.query.count()
    
    # Planos de saúde ativos
    estatisticas['total_planos_saude'] = PlanoSaude.query.filter_by(ativo=True).count()
    
    # Planos odontológicos ativos
    estatisticas['total_planos_odonto'] = PlanoOdontologico.query.filter_by(ativo=True).count()
    
    # Alertas abertos
    estatisticas['total_alertas_abertos'] = Alerta.query.filter_by(resolvido=False).count()
    
    # Alertas recentes
    estatisticas['alertas_recentes'] = Alerta.query.filter_by(resolvido=False)\
        .order_by(Alerta.data_alerta.desc())\
        .limit(5).all()
    
    return render_template('index.html', estatisticas=estatisticas)

@main_bp.route('/about')
def about():
    """
    Sobre o sistema.
    """
    return render_template('about.html')

@main_bp.route('/help')
def help():
    """
    Ajuda do sistema.
    """
    return render_template('help.html')