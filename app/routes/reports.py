"""
Rotas para relatórios.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
import io
from datetime import datetime, date
import csv

from app import db
from app.models import ColaboradorInterno, PlanoSaude, PlanoOdontologico, Dependente
from app.decorators import admin_required
from app.services.report_service import ReportService

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/')
@login_required
def index():
    """
    Página principal de relatórios.
    """
    return render_template('reports/index.html')


@reports_bp.route('/colaboradores')
@login_required
def colaboradores():
    """
    Relatório de colaboradores.
    """
    # Filtros
    empresa = request.args.get('empresa', '')
    status = request.args.get('status', 'ativo')
    
    # Construir query
    query = ColaboradorInterno.query.filter_by(is_deleted=False)
    
    if empresa:
        query = query.filter(
            ColaboradorInterno.id.in_(
                db.session.query(NumeroCadastro.colaborador_id).filter(
                    NumeroCadastro.cod_empresa == empresa,
                    NumeroCadastro.ativo == True
                )
            )
        )
    
    if status == 'ativo':
        query = query.filter(
            ColaboradorInterno.id.in_(
                db.session.query(NumeroCadastro.colaborador_id).filter(
                    NumeroCadastro.ativo == True
                )
            )
        )
    elif status == 'inativo':
        query = query.filter(
            ~ColaboradorInterno.id.in_(
                db.session.query(NumeroCadastro.colaborador_id).filter(
                    NumeroCadastro.ativo == True
                )
            )
        )
    
    colaboradores = query.order_by(ColaboradorInterno.nome).all()
    
    return render_template(
        'reports/colaboradores.html',
        colaboradores=colaboradores,
        filtros={'empresa': empresa, 'status': status}
    )


@reports_bp.route('/planos-saude')
@login_required
def planos_saude():
    """
    Relatório de planos de saúde.
    """
    planos = PlanoSaude.query.filter_by(ativo=True).order_by(PlanoSaude.operadora).all()
    return render_template('reports/planos_saude.html', planos=planos)


@reports_bp.route('/planos-odonto')
@login_required
def planos_odonto():
    """
    Relatório de planos odontológicos.
    """
    planos = PlanoOdontologico.query.filter_by(ativo=True).order_by(PlanoOdontologico.operadora).all()
    return render_template('reports/planos_odonto.html', planos=planos)


@reports_bp.route('/dependentes')
@login_required
def dependentes():
    """
    Relatório de dependentes.
    """
    dependentes = Dependente.query.order_by(Dependente.nome).all()
    return render_template('reports/dependentes.html', dependentes=dependentes)


@reports_bp.route('/exportar/csv')
@login_required
def exportar_csv():
    """
    Exporta dados em formato CSV.
    """
    tipo = request.args.get('tipo', 'colaboradores')
    
    try:
        service = ReportService()
        
        if tipo == 'colaboradores':
            data = service.exportar_colaboradores_csv()
            filename = f'colaboradores_{date.today().strftime("%Y%m%d")}.csv'
        elif tipo == 'planos_saude':
            data = service.exportar_planos_saude_csv()
            filename = f'planos_saude_{date.today().strftime("%Y%m%d")}.csv'
        elif tipo == 'planos_odonto':
            data = service.exportar_planos_odonto_csv()
            filename = f'planos_odonto_{date.today().strftime("%Y%m%d")}.csv'
        elif tipo == 'dependentes':
            data = service.exportar_dependentes_csv()
            filename = f'dependentes_{date.today().strftime("%Y%m%d")}.csv'
        else:
            flash('Tipo de exportação inválido', 'error')
            return redirect(url_for('reports.index'))
        
        return send_file(
            io.BytesIO(data.encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        flash(f'Erro ao exportar: {str(e)}', 'error')
        return redirect(url_for('reports.index'))


@reports_bp.route('/api/dashboard')
@login_required
def api_dashboard():
    """
    Retorna dados para dashboard em formato JSON.
    """
    try:
        service = ReportService()
        dados = service.obter_dados_dashboard()
        return jsonify(dados)
    except Exception as e:
        return jsonify({'error': str(e)}), 500