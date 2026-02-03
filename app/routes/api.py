"""
API REST para o sistema.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from app import db
from app.models import (
    ColaboradorInterno, NumeroCadastro, Dependente,
    PlanoSaude, PlanoOdontologico, Alerta
)
from app.decorators import api_key_required
from app.services.ci_service import CIService

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


@api_bp.route('/health')
def health():
    """
    Endpoint de saúde da API.
    """
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })


@api_bp.route('/colaboradores', methods=['GET'])
@api_key_required
def listar_colaboradores():
    """
    Lista colaboradores (requer API key).
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        
        colaboradores = ColaboradorInterno.query.filter_by(is_deleted=False)\
            .order_by(ColaboradorInterno.nome)\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'data': [ci.to_dict() for ci in colaboradores.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': colaboradores.total,
                'pages': colaboradores.pages
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/colaboradores/<int:id>', methods=['GET'])
@api_key_required
def obter_colaborador(id):
    """
    Obtém um colaborador por ID.
    """
    try:
        ci = ColaboradorInterno.query.get_or_404(id)
        
        if ci.is_deleted:
            return jsonify({'error': 'Colaborador excluído'}), 404
        
        return jsonify(ci.to_dict(include_relationships=True))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/colaboradores/por-cpf/<string:cpf>', methods=['GET'])
@api_key_required
def obter_colaborador_por_cpf(cpf):
    """
    Obtém um colaborador por CPF.
    """
    try:
        from app.utils.validators import clean_cpf
        cpf_limpo = clean_cpf(cpf)
        
        if not cpf_limpo:
            return jsonify({'error': 'CPF inválido'}), 400
        
        ci = ColaboradorInterno.query.filter_by(cpf=cpf_limpo).first()
        
        if not ci:
            return jsonify({'error': 'Colaborador não encontrado'}), 404
        
        if ci.is_deleted:
            return jsonify({'error': 'Colaborador excluído'}), 404
        
        return jsonify(ci.to_dict(include_relationships=True))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/colaboradores/por-nc/<string:nc>', methods=['GET'])
@api_key_required
def obter_colaborador_por_nc(nc):
    """
    Obtém um colaborador por NC.
    """
    try:
        from app.utils.validators import clean_nc
        nc_limpo = clean_nc(nc)
        
        if not nc_limpo:
            return jsonify({'error': 'NC inválido'}), 400
        
        nc_obj = NumeroCadastro.query.filter_by(
            nc=nc_limpo,
            ativo=True
        ).first()
        
        if not nc_obj:
            return jsonify({'error': 'NC não encontrado ou inativo'}), 404
        
        ci = nc_obj.colaborador
        
        if ci.is_deleted:
            return jsonify({'error': 'Colaborador excluído'}), 404
        
        return jsonify(ci.to_dict(include_relationships=True))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/alertas/abertos', methods=['GET'])
@api_key_required
def alertas_abertos():
    """
    Lista alertas abertos.
    """
    try:
        alertas = Alerta.query.filter_by(resolvido=False)\
            .order_by(Alerta.data_alerta.desc())\
            .limit(50).all()
        
        return jsonify({
            'data': [a.to_dict() for a in alertas]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/estatisticas', methods=['GET'])
@api_key_required
def estatisticas():
    """
    Retorna estatísticas do sistema.
    """
    try:
        service = CIService()
        stats = service.obter_estatisticas()
        
        # Adicionar outras estatísticas
        stats['total_alertas_abertos'] = Alerta.query.filter_by(resolvido=False).count()
        stats['total_planos_saude'] = PlanoSaude.query.filter_by(ativo=True).count()
        stats['total_planos_odonto'] = PlanoOdontologico.query.filter_by(ativo=True).count()
        stats['total_dependentes'] = Dependente.query.count()
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.errorhandler(404)
def nao_encontrado(error):
    return jsonify({'error': 'Recurso não encontrado'}), 404


@api_bp.errorhandler(500)
def erro_interno(error):
    return jsonify({'error': 'Erro interno do servidor'}), 500