"""
Rotas para gerenciamento de alertas do sistema.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, asc
from datetime import datetime, timedelta

from app import db
from app.models import Alerta, ImportacaoLog
from app.decorators import admin_required, permission_required
from app.utils.pagination import Pagination

alerts_bp = Blueprint('alerts', __name__, url_prefix='/alerts')


@alerts_bp.route('/')
@login_required
def listar():
    """
    Lista alertas do sistema.
    
    Filtros disponíveis:
    - tipo: tipo de alerta
    - gravidade: nível de gravidade
    - resolvido: 'true' ou 'false'
    - data_inicio: data inicial
    - data_fim: data final
    """
    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Parâmetros de filtro
    tipo = request.args.get('tipo', '').strip()
    gravidade = request.args.get('gravidade', '').strip()
    resolvido = request.args.get('resolvido', '').strip()
    data_inicio_str = request.args.get('data_inicio', '').strip()
    data_fim_str = request.args.get('data_fim', '').strip()
    
    # Construir query
    query = Alerta.query
    
    # Aplicar filtros
    if tipo:
        query = query.filter(Alerta.tipo == tipo)
    
    if gravidade:
        query = query.filter(Alerta.gravidade == gravidade)
    
    if resolvido.lower() == 'true':
        query = query.filter(Alerta.resolvido == True)
    elif resolvido.lower() == 'false':
        query = query.filter(Alerta.resolvido == False)
    
    # Filtrar por data
    try:
        if data_inicio_str:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
            query = query.filter(Alerta.data_alerta >= data_inicio)
        
        if data_fim_str:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Alerta.data_alerta < data_fim)
    except ValueError:
        flash('Formato de data inválido. Use YYYY-MM-DD', 'warning')
    
    # Ordenação
    order_by = request.args.get('order_by', 'data_alerta')
    order_dir = request.args.get('order_dir', 'desc')
    
    if order_dir.lower() == 'asc':
        query = query.order_by(asc(getattr(Alerta, order_by, Alerta.data_alerta)))
    else:
        query = query.order_by(desc(getattr(Alerta, order_by, Alerta.data_alerta)))
    
    # Paginação
    total = query.count()
    alertas = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Estatísticas
    total_alertas = Alerta.query.count()
    alertas_abertos = Alerta.query.filter_by(resolvido=False).count()
    alertas_criticos = Alerta.query.filter_by(gravidade='CRITICA', resolvido=False).count()
    
    # Tipos de alerta disponíveis
    tipos = db.session.query(Alerta.tipo).distinct().all()
    tipos = [t[0] for t in tipos]
    
    # Níveis de gravidade
    gravidades = ['CRITICA', 'ALTA', 'MEDIA', 'BAIXA']
    
    return render_template(
        'alerts/list.html',
        alertas=alertas.items,
        pagination=Pagination(
            page=page,
            per_page=per_page,
            total=total,
            route='alerts.listar'
        ),
        filtros={
            'tipo': tipo,
            'gravidade': gravidade,
            'resolvido': resolvido,
            'data_inicio': data_inicio_str,
            'data_fim': data_fim_str,
            'order_by': order_by,
            'order_dir': order_dir
        },
        estatisticas={
            'total': total_alertas,
            'abertos': alertas_abertos,
            'criticos': alertas_criticos
        },
        tipos=tipos,
        gravidades=gravidades,
        current_user=current_user
    )


@alerts_bp.route('/<int:id>')
@login_required
def detalhes(id):
    """
    Mostra detalhes de um alerta específico.
    """
    alerta = Alerta.query.get_or_404(id)
    
    return render_template(
        'alerts/detalhes.html',
        alerta=alerta,
        current_user=current_user
    )


@alerts_bp.route('/<int:id>/resolver', methods=['POST'])
@login_required
@admin_required
def resolver(id):
    """
    Marca um alerta como resolvido.
    """
    alerta = Alerta.query.get_or_404(id)
    
    if alerta.resolvido:
        flash('Este alerta já está resolvido', 'warning')
        return redirect(url_for('alerts.detalhes', id=id))
    
    try:
        observacao = request.form.get('observacao', '').strip()
        
        alerta.resolver()
        
        if observacao:
            alerta.descricao = f"{alerta.descricao}\n\n--- RESOLUÇÃO ---\n{observacao}\nUsuário: {current_user.nome}"
            db.session.commit()
        
        flash(f'Alerta #{id} marcado como resolvido!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao resolver alerta: {str(e)}', 'error')
    
    return redirect(url_for('alerts.detalhes', id=id))


@alerts_bp.route('/<int:id>/reabrir', methods=['POST'])
@login_required
@admin_required
def reabrir(id):
    """
    Reabre um alerta resolvido.
    """
    alerta = Alerta.query.get_or_404(id)
    
    if not alerta.resolvido:
        flash('Este alerta já está aberto', 'warning')
        return redirect(url_for('alerts.detalhes', id=id))
    
    try:
        motivo = request.form.get('motivo', '').strip()
        
        alerta.reabrir()
        
        if motivo:
            alerta.descricao = f"{alerta.descricao}\n\n--- REABERTURA ---\n{motivo}\nUsuário: {current_user.nome}"
            db.session.commit()
        
        flash(f'Alerta #{id} reaberto!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao reabrir alerta: {str(e)}', 'error')
    
    return redirect(url_for('alerts.detalhes', id=id))


@alerts_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir(id):
    """
    Exclui um alerta.
    """
    alerta = Alerta.query.get_or_404(id)
    
    try:
        db.session.delete(alerta)
        db.session.commit()
        
        flash(f'Alerta #{id} excluído com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir alerta: {str(e)}', 'error')
    
    return redirect(url_for('alerts.listar'))


@alerts_bp.route('/limpar-resolvidos', methods=['POST'])
@login_required
@admin_required
def limpar_resolvidos():
    """
    Remove todos os alertas resolvidos.
    """
    try:
        # Contar antes de excluir
        total_antes = Alerta.query.filter_by(resolvido=True).count()
        
        # Excluir alertas resolvidos
        Alerta.query.filter_by(resolvido=True).delete()
        db.session.commit()
        
        flash(f'{total_antes} alertas resolvidos removidos do sistema!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao limpar alertas resolvidos: {str(e)}', 'error')
    
    return redirect(url_for('alerts.listar'))


@alerts_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """
    Retorna estatísticas de alertas em formato JSON.
    """
    try:
        total = Alerta.query.count()
        abertos = Alerta.query.filter_by(resolvido=False).count()
        resolvidos = Alerta.query.filter_by(resolvido=True).count()
        
        # Por gravidade
        critica = Alerta.query.filter_by(gravidade='CRITICA', resolvido=False).count()
        alta = Alerta.query.filter_by(gravidade='ALTA', resolvido=False).count()
        media = Alerta.query.filter_by(gravidade='MEDIA', resolvido=False).count()
        baixa = Alerta.query.filter_by(gravidade='BAIXA', resolvido=False).count()
        
        # Por tipo
        tipos = db.session.query(
            Alerta.tipo,
            db.func.count(Alerta.id).label('total')
        ).filter_by(resolvido=False).group_by(Alerta.tipo).all()
        
        return jsonify({
            'total': total,
            'abertos': abertos,
            'resolvidos': resolvidos,
            'por_gravidade': {
                'critica': critica,
                'alta': alta,
                'media': media,
                'baixa': baixa
            },
            'por_tipo': [
                {'tipo': tipo, 'total': total}
                for tipo, total in tipos
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@alerts_bp.route('/api/recentes')
@login_required
def api_recentes():
    """
    Retorna alertas recentes para dashboard.
    """
    try:
        limite = request.args.get('limit', 10, type=int)
        
        alertas = Alerta.query.filter_by(resolvido=False).order_by(
            desc(Alerta.data_alerta)
        ).limit(limite).all()
        
        return jsonify({
            'alertas': [
                {
                    'id': a.id,
                    'tipo': a.tipo,
                    'descricao': a.descricao,
                    'gravidade': a.gravidade,
                    'cor_gravidade': a.cor_gravidade,
                    'data_alerta': a.data_alerta.isoformat(),
                    'dias_aberto': a.dias_aberto
                }
                for a in alertas
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@alerts_bp.errorhandler(404)
def alerta_nao_encontrado(error):
    """Handler para alerta não encontrado."""
    flash('Alerta não encontrado', 'error')
    return redirect(url_for('alerts.listar'))


@alerts_bp.errorhandler(403)
def acesso_negado(error):
    """Handler para acesso negado."""
    flash('Acesso negado: permissão insuficiente', 'error')
    return redirect(url_for('alerts.listar'))