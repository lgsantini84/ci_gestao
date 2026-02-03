"""
Rotas para gerenciamento de Colaboradores Internos.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from datetime import datetime, date

from app import db
from app.models import (
    ColaboradorInterno, 
    NumeroCadastro, 
    Dependente, 
    PlanoSaude, 
    PlanoOdontologico,
    HistoricoCI,
    AtendimentoCoparticipacao
)
from app.decorators import admin_required
from app.services.ci_service import CIService
from app.utils.validators import clean_cpf, clean_nc, validate_date
from app.utils.pagination import Pagination

ci_bp = Blueprint('ci', __name__, url_prefix='/ci')
ci_service = CIService()


# ============================================================================
# ROTAS DE LISTAGEM E PESQUISA
# ============================================================================

@ci_bp.route('/')
@login_required
def listar():
    """
    Lista colaboradores internos com filtros e paginação.
    
    Filtros disponíveis:
    - nome: busca por nome (LIKE)
    - cpf: busca por CPF
    - empresa: filtra por empresa
    - status: 'ativo', 'inativo' ou 'excluido'
    - mostrar_excluidos: mostra colaboradores excluídos
    """
    # Parâmetros de paginação
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Parâmetros de filtro
    nome = request.args.get('nome', '').strip()
    cpf = request.args.get('cpf', '').strip()
    empresa = request.args.get('empresa', '')
    status = request.args.get('status', '')
    mostrar_excluidos = request.args.get('excluidos', 'false').lower() == 'true'
    
    try:
        # Buscar dados usando o serviço
        resultado = ci_service.buscar_com_filtros(
            nome=nome,
            cpf=cpf,
            empresa=empresa,
            status=status,
            mostrar_excluidos=mostrar_excluidos,
            page=page,
            per_page=per_page
        )
        
        # Estatísticas
        estatisticas = ci_service.obter_estatisticas(
            mostrar_excluidos=mostrar_excluidos
        )
        
        return render_template(
            'ci/list.html',
            cis=resultado['cis'],
            pagination=Pagination(
                page=page,
                per_page=per_page,
                total=resultado['total'],
                route='ci.listar'
            ),
            filtros={
                'nome': nome,
                'cpf': cpf,
                'empresa': empresa,
                'status': status,
                'mostrar_excluidos': mostrar_excluidos
            },
            estatisticas=estatisticas,
            current_user=current_user
        )
        
    except Exception as e:
        flash(f'Erro ao listar colaboradores: {str(e)}', 'error')
        return redirect(url_for('index'))


@ci_bp.route('/pesquisa-rapida')
@login_required
def pesquisa_rapida():
    """
    Pesquisa rápida de colaboradores (para autocomplete).
    Retorna JSON com resultados limitados.
    """
    termo = request.args.get('q', '').strip()
    limite = request.args.get('limit', 20, type=int)
    
    if not termo or len(termo) < 2:
        return jsonify({'results': []})
    
    try:
        # Buscar por nome, CPF ou NC
        resultados = ci_service.pesquisa_rapida(
            termo=termo,
            limite=limite
        )
        
        return jsonify({
            'results': [
                {
                    'id': ci.id,
                    'nome': ci.nome,
                    'cpf': ci.cpf,
                    'nc_atual': ci.nc_atual,
                    'empresa_atual': ci.empresa_atual,
                    'esta_ativo': ci.esta_ativo
                }
                for ci in resultados
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ROTAS DE DETALHES
# ============================================================================

@ci_bp.route('/<int:id>')
@login_required
def detalhes(id):
    """
    Mostra detalhes de um colaborador específico.
    
    Inclui:
    - Dados cadastrais
    - NCs (histórico)
    - Dependentes
    - Planos (saúde e odonto)
    - Histórico de eventos
    - Atendimentos de coparticipação
    """
    try:
        # Buscar colaborador
        ci = ColaboradorInterno.query.get_or_404(id)
        
        # Verificar permissão para ver excluídos
        if ci.is_deleted and not current_user.is_admin:
            flash('Acesso negado: colaborador excluído', 'error')
            return redirect(url_for('ci.listar'))
        
        # Buscar dados relacionados
        nc_ativo = ci.nc_ativo
        historico_ncs = ci.numeros_cadastro.all()
        dependentes = ci.dependentes.all()
        
        # Planos ativos
        planos_saude_ativos = ci.planos_saude.filter_by(ativo=True).all()
        planos_odonto_ativos = ci.planos_odonto.filter_by(ativo=True).all()
        
        # Histórico de eventos
        historico_events = ci.historico.order_by(
            HistoricoCI.data_evento.desc()
        ).limit(100).all()
        
        # Atendimentos de coparticipação por plano
        atendimentos_por_plano = {}
        totais_por_plano = {}
        
        for plano in ci.planos_saude.filter(
            PlanoSaude.tipo.in_(['COPARTICIPACAO', 'COBRANCA'])
        ).all():
            atendimentos = AtendimentoCoparticipacao.query.filter_by(
                plano_saude_id=plano.id
            ).order_by(
                AtendimentoCoparticipacao.data_atendimento.desc()
            ).all()
            
            atendimentos_por_plano[plano.id] = atendimentos
            
            # Calcular totais
            total_base = sum(
                float(atend.valor_base) if atend.valor_base else 0
                for atend in atendimentos
            )
            total_coparticipacao = sum(
                float(atend.valor_coparticipacao) if atend.valor_coparticipacao else 0
                for atend in atendimentos
            )
            
            totais_por_plano[plano.id] = {
                'total_base': total_base,
                'total_coparticipacao': total_coparticipacao,
                'percentual': (total_coparticipacao / total_base * 100) if total_base > 0 else 0
            }
        
        return render_template(
            'ci/detalhes.html',
            ci=ci,
            nc_ativo=nc_ativo,
            historico_ncs=historico_ncs,
            dependentes=dependentes,
            planos_saude_ativos=planos_saude_ativos,
            planos_odonto_ativos=planos_odonto_ativos,
            historico_events=historico_events,
            atendimentos_por_plano=atendimentos_por_plano,
            totais_por_plano=totais_por_plano,
            current_user=current_user
        )
        
    except Exception as e:
        flash(f'Erro ao carregar detalhes: {str(e)}', 'error')
        return redirect(url_for('ci.listar'))


@ci_bp.route('/<int:id>/json')
@login_required
def detalhes_json(id):
    """
    Retorna detalhes do colaborador em formato JSON.
    """
    try:
        ci = ColaboradorInterno.query.get_or_404(id)
        
        # Verificar permissão
        if ci.is_deleted and not current_user.is_admin:
            return jsonify({'error': 'Acesso negado'}), 403
        
        return jsonify(ci.to_dict(include_relationships=True))
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ROTAS DE CRIAÇÃO E EDIÇÃO
# ============================================================================

@ci_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    """
    Cria um novo colaborador.
    
    Método GET: Exibe formulário de criação
    Método POST: Processa criação do colaborador
    """
    if request.method == 'GET':
        return render_template('ci/editar.html', ci=None)
    
    # Método POST
    try:
        # Validar dados obrigatórios
        nome = request.form.get('nome', '').strip()
        cpf_raw = request.form.get('cpf', '').strip()
        
        if not nome:
            flash('Nome é obrigatório', 'error')
            return render_template('ci/editar.html', form_data=request.form)
        
        cpf = clean_cpf(cpf_raw)
        if not cpf:
            flash('CPF inválido', 'error')
            return render_template('ci/editar.html', form_data=request.form)
        
        # Verificar se CPF já existe
        if ColaboradorInterno.query.filter_by(cpf=cpf).first():
            flash('CPF já cadastrado', 'error')
            return render_template('ci/editar.html', form_data=request.form)
        
        # Coletar outros dados
        email = request.form.get('email', '').strip() or None
        telefone = request.form.get('telefone', '').strip() or None
        
        # Processar datas
        data_admissao = validate_date(request.form.get('data_admissao'))
        data_nascimento = validate_date(request.form.get('data_nascimento'))
        
        # Criar colaborador
        ci = ColaboradorInterno(
            nome=nome,
            cpf=cpf,
            email=email,
            telefone=telefone,
            data_admissao=data_admissao,
            data_nascimento=data_nascimento
        )
        
        db.session.add(ci)
        db.session.flush()  # Para obter o ID
        
        # Adicionar NC se fornecido
        nc_raw = request.form.get('nc', '').strip()
        empresa = request.form.get('empresa', '').strip()
        
        if nc_raw and empresa:
            nc = clean_nc(nc_raw)
            if nc and empresa:
                ci_service.adicionar_nc(
                    ci_id=ci.id,
                    nc=nc,
                    empresa=empresa,
                    motivo='CRIAÇÃO MANUAL'
                )
        
        # Adicionar histórico
        historico = HistoricoCI(
            colaborador_id=ci.id,
            tipo_evento='CRIAÇÃO_MANUAL',
            descricao=f'CI criado manualmente por {current_user.nome}',
            data_evento=date.today(),
            nc=nc if nc_raw else None,
            cod_empresa=empresa if empresa else None,
            dados_alterados={
                'nome': nome,
                'cpf': cpf,
                'email': email,
                'telefone': telefone,
                'data_admissao': data_admissao.isoformat() if data_admissao else None,
                'data_nascimento': data_nascimento.isoformat() if data_nascimento else None,
                'usuario': current_user.nome
            }
        )
        db.session.add(historico)
        
        db.session.commit()
        
        flash(f'Colaborador {nome} criado com sucesso!', 'success')
        return redirect(url_for('ci.detalhes', id=ci.id))
        
    except ValueError as e:
        flash(str(e), 'error')
        return render_template('ci/editar.html', form_data=request.form)
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar colaborador: {str(e)}', 'error')
        return render_template('ci/editar.html', form_data=request.form)


@ci_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    """
    Edita dados de um colaborador existente.
    
    Método GET: Exibe formulário de edição
    Método POST: Processa atualização dos dados
    """
    ci = ColaboradorInterno.query.get_or_404(id)
    
    # Verificar permissão para editar excluídos
    if ci.is_deleted and not current_user.is_admin:
        flash('Não é possível editar colaborador excluído', 'error')
        return redirect(url_for('ci.detalhes', id=id))
    
    if request.method == 'GET':
        return render_template('ci/editar.html', ci=ci)
    
    # Método POST
    try:
        # Registrar dados antigos para histórico
        dados_antigos = {
            'nome': ci.nome,
            'email': ci.email,
            'telefone': ci.telefone,
            'data_admissao': ci.data_admissao,
            'data_nascimento': ci.data_nascimento
        }
        
        # Atualizar dados
        novo_nome = request.form.get('nome', '').strip()
        if novo_nome:
            ci.nome = novo_nome
        
        # Atualizar outros campos apenas se não estiverem vazios
        email = request.form.get('email', '').strip()
        if email:
            ci.email = email
        
        telefone = request.form.get('telefone', '').strip()
        if telefone:
            ci.telefone = telefone
        
        # Atualizar datas
        data_admissao = validate_date(request.form.get('data_admissao'))
        if data_admissao:
            ci.data_admissao = data_admissao
        
        data_nascimento = validate_date(request.form.get('data_nascimento'))
        if data_nascimento:
            ci.data_nascimento = data_nascimento
        
        # Registrar alterações no histórico
        dados_novos = {
            'nome': ci.nome,
            'email': ci.email,
            'telefone': ci.telefone,
            'data_admissao': ci.data_admissao,
            'data_nascimento': ci.data_nascimento
        }
        
        alteracoes = {
            k: {'antigo': dados_antigos[k], 'novo': dados_novos[k]}
            for k in dados_antigos
            if dados_antigos[k] != dados_novos[k]
        }
        
        if alteracoes:
            historico = HistoricoCI(
                colaborador_id=ci.id,
                tipo_evento='ALTERACAO_DADOS',
                descricao='Alteração de dados cadastrais',
                data_evento=date.today(),
                nc=ci.nc_atual,
                cod_empresa=ci.empresa_atual,
                dados_alterados=alteracoes
            )
            db.session.add(historico)
        
        db.session.commit()
        
        flash('Dados do colaborador atualizados com sucesso!', 'success')
        return redirect(url_for('ci.detalhes', id=ci.id))
        
    except ValueError as e:
        flash(str(e), 'error')
        return render_template('ci/editar.html', ci=ci)
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar colaborador: {str(e)}', 'error')
        return render_template('ci/editar.html', ci=ci)


@ci_bp.route('/<int:id>/mudar-nc', methods=['POST'])
@login_required
def mudar_nc(id):
    """
    Muda o NC ativo de um colaborador.
    
    Valida se o novo NC não está em uso por outro colaborador ativo.
    """
    ci = ColaboradorInterno.query.get_or_404(id)
    
    if ci.is_deleted:
        flash('Não é possível mudar NC de um colaborador excluído', 'error')
        return redirect(url_for('ci.detalhes', id=id))
    
    try:
        novo_nc = request.form.get('novo_nc', '').strip()
        nova_empresa = request.form.get('nova_empresa', '').strip()
        motivo_mudanca = request.form.get('motivo_mudanca', '').strip() or 'MUDANÇA MANUAL'
        
        if not novo_nc or not nova_empresa:
            flash('Novo NC e empresa são obrigatórios', 'error')
            return redirect(url_for('ci.detalhes', id=id))
        
        nc_limpo = clean_nc(novo_nc)
        
        # Validar empresa
        from app import current_app
        valid_codes = current_app.config.get('VALID_COMPANY_CODES', {})
        if nova_empresa not in valid_codes:
            flash(f'Empresa {nova_empresa} não é válida', 'error')
            return redirect(url_for('ci.detalhes', id=id))
        
        # Verificar se NC já está em uso por outro colaborador ativo
        if ci_service.nc_em_uso(nc_limpo, ci.id):
            flash(f'O NC {novo_nc} já está em uso por outro colaborador ativo', 'error')
            return redirect(url_for('ci.detalhes', id=id))
        
        # Mudar NC usando serviço
        ci_service.mudar_nc(
            ci_id=ci.id,
            novo_nc=nc_limpo,
            nova_empresa=nova_empresa,
            motivo=motivo_mudanca,
            usuario_id=current_user.id
        )
        
        flash(f'NC alterado com sucesso para {novo_nc}!', 'success')
        
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao mudar NC: {str(e)}', 'error')
    
    return redirect(url_for('ci.detalhes', id=id))


# ============================================================================
# ROTAS DE EXCLUSÃO E RESTAURAÇÃO
# ============================================================================

@ci_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
@admin_required
def excluir(id):
    """
    Exclui um colaborador logicamente (soft delete).
    
    Requer permissão de administrador.
    """
    ci = ColaboradorInterno.query.get_or_404(id)
    
    if ci.is_deleted:
        flash('Este colaborador já está excluído', 'warning')
        return redirect(url_for('ci.detalhes', id=id))
    
    try:
        motivo = request.form.get('motivo', '').strip() or 'Exclusão manual pelo usuário'
        
        # Excluir usando serviço
        ci_service.excluir_colaborador(
            ci_id=ci.id,
            usuario_id=current_user.id,
            motivo=motivo
        )
        
        flash(f'Colaborador {ci.nome} excluído com sucesso!', 'success')
        return redirect(url_for('ci.listar'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir colaborador: {str(e)}', 'error')
        return redirect(url_for('ci.detalhes', id=id))


@ci_bp.route('/<int:id>/restaurar', methods=['POST'])
@login_required
@admin_required
def restaurar(id):
    """
    Restaura um colaborador excluído logicamente.
    
    Requer permissão de administrador.
    """
    ci = ColaboradorInterno.query.get_or_404(id)
    
    if not ci.is_deleted:
        flash('Este colaborador não está excluído', 'warning')
        return redirect(url_for('ci.detalhes', id=id))
    
    try:
        # Restaurar usando serviço
        sucesso = ci_service.restaurar_colaborador(
            ci_id=ci.id,
            usuario_id=current_user.id
        )
        
        if sucesso:
            flash(f'Colaborador {ci.nome} restaurado com sucesso!', 'success')
        else:
            flash(f'Não foi possível restaurar o colaborador', 'warning')
        
        return redirect(url_for('ci.detalhes', id=id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao restaurar colaborador: {str(e)}', 'error')
        return redirect(url_for('ci.detalhes', id=id))


@ci_bp.route('/<int:id>/excluir-definitivo', methods=['POST'])
@login_required
@admin_required
def excluir_definitivo(id):
    """
    Exclui um colaborador definitivamente do banco de dados.
    
    Requer permissão de administrador e confirmação explícita.
    Apenas para colaboradores já excluídos logicamente.
    """
    ci = ColaboradorInterno.query.get_or_404(id)
    
    if not ci.is_deleted:
        flash('Apenas colaboradores excluídos logicamente podem ser removidos definitivamente', 'error')
        return redirect(url_for('ci.detalhes', id=id))
    
    try:
        # Registrar histórico antes de excluir
        historico = HistoricoCI(
            colaborador_id=ci.id,
            tipo_evento='EXCLUSAO_DEFINITIVA',
            descricao=f'CI excluído definitivamente do banco por {current_user.nome}',
            data_evento=date.today(),
            nc=ci.nc_atual,
            cod_empresa=ci.empresa_atual,
            dados_alterados={
                'nome': ci.nome,
                'cpf': ci.cpf,
                'usuario': current_user.nome,
                'data_exclusao': datetime.now().isoformat()
            }
        )
        db.session.add(historico)
        
        # Excluir do banco
        db.session.delete(ci)
        db.session.commit()
        
        flash(f'Colaborador {ci.nome} removido definitivamente do sistema!', 'success')
        return redirect(url_for('ci.listar'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir colaborador definitivamente: {str(e)}', 'error')
        return redirect(url_for('ci.detalhes', id=id))


# ============================================================================
# ROTAS DE DEPENDENTES
# ============================================================================

@ci_bp.route('/<int:id>/dependentes')
@login_required
def listar_dependentes(id):
    """
    Lista dependentes de um colaborador.
    """
    ci = ColaboradorInterno.query.get_or_404(id)
    
    if ci.is_deleted and not current_user.is_admin:
        flash('Acesso negado: colaborador excluído', 'error')
        return redirect(url_for('ci.listar'))
    
    dependentes = ci.dependentes.all()
    
    return render_template(
        'ci/dependentes.html',
        ci=ci,
        dependentes=dependentes
    )


@ci_bp.route('/<int:id>/dependentes/novo', methods=['GET', 'POST'])
@login_required
def novo_dependente(id):
    """
    Adiciona um novo dependente ao colaborador.
    """
    ci = ColaboradorInterno.query.get_or_404(id)
    
    if ci.is_deleted:
        flash('Não é possível adicionar dependentes a um colaborador excluído', 'error')
        return redirect(url_for('ci.detalhes', id=id))
    
    if request.method == 'GET':
        return render_template('ci/dependente_editar.html', ci=ci, dependente=None)
    
    # Método POST
    try:
        nome = request.form.get('nome', '').strip()
        cpf_raw = request.form.get('cpf', '').strip()
        parentesco = request.form.get('parentesco', '').strip() or 'DEPENDENTE'
        data_nascimento = validate_date(request.form.get('data_nascimento'))
        
        if not nome:
            flash('Nome é obrigatório', 'error')
            return render_template('ci/dependente_editar.html', ci=ci, form_data=request.form)
        
        cpf = clean_cpf(cpf_raw) if cpf_raw else None
        
        # Verificar se dependente já existe (por nome ou CPF)
        if cpf:
            existente = Dependente.query.filter_by(
                cpf=cpf,
                colaborador_id=ci.id
            ).first()
            if existente:
                flash('Já existe um dependente com este CPF', 'error')
                return render_template('ci/dependente_editar.html', ci=ci, form_data=request.form)
        
        # Criar dependente
        dependente = Dependente(
            nome=nome,
            cpf=cpf,
            parentesco=parentesco,
            data_nascimento=data_nascimento,
            nc_vinculo=ci.nc_atual or '',
            colaborador_id=ci.id
        )
        
        db.session.add(dependente)
        
        # Registrar histórico
        historico = HistoricoCI(
            colaborador_id=ci.id,
            tipo_evento='ADICAO_DEPENDENTE',
            descricao=f'Dependente {nome} adicionado',
            data_evento=date.today(),
            nc=ci.nc_atual,
            cod_empresa=ci.empresa_atual,
            dados_alterados={
                'dependente_nome': nome,
                'dependente_cpf': cpf,
                'parentesco': parentesco,
                'usuario': current_user.nome
            }
        )
        db.session.add(historico)
        
        db.session.commit()
        
        flash(f'Dependente {nome} adicionado com sucesso!', 'success')
        return redirect(url_for('ci.detalhes', id=id))
        
    except ValueError as e:
        flash(str(e), 'error')
        return render_template('ci/dependente_editar.html', ci=ci, form_data=request.form)
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao adicionar dependente: {str(e)}', 'error')
        return render_template('ci/dependente_editar.html', ci=ci, form_data=request.form)


@ci_bp.route('/<int:ci_id>/dependentes/<int:dep_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_dependente(ci_id, dep_id):
    """
    Edita dados de um dependente.
    """
    ci = ColaboradorInterno.query.get_or_404(ci_id)
    dependente = Dependente.query.get_or_404(dep_id)
    
    if dependente.colaborador_id != ci.id:
        abort(404)
    
    if ci.is_deleted:
        flash('Não é possível editar dependentes de um colaborador excluído', 'error')
        return redirect(url_for('ci.detalhes', id=ci_id))
    
    if request.method == 'GET':
        return render_template('ci/dependente_editar.html', ci=ci, dependente=dependente)
    
    # Método POST
    try:
        # Registrar dados antigos
        dados_antigos = {
            'nome': dependente.nome,
            'cpf': dependente.cpf,
            'parentesco': dependente.parentesco,
            'data_nascimento': dependente.data_nascimento
        }
        
        # Atualizar dados
        novo_nome = request.form.get('nome', '').strip()
        if novo_nome:
            dependente.nome = novo_nome
        
        cpf_raw = request.form.get('cpf', '').strip()
        if cpf_raw:
            cpf = clean_cpf(cpf_raw)
            if cpf and cpf != dependente.cpf:
                # Verificar se CPF já existe em outro dependente
                existente = Dependente.query.filter(
                    Dependente.cpf == cpf,
                    Dependente.colaborador_id == ci.id,
                    Dependente.id != dep_id
                ).first()
                if existente:
                    flash('Já existe um dependente com este CPF', 'error')
                    return render_template('ci/dependente_editar.html', ci=ci, dependente=dependente)
                dependente.cpf = cpf
        
        parentesco = request.form.get('parentesco', '').strip()
        if parentesco:
            dependente.parentesco = parentesco
        
        data_nascimento = validate_date(request.form.get('data_nascimento'))
        if data_nascimento:
            dependente.data_nascimento = data_nascimento
        
        # Registrar histórico
        dados_novos = {
            'nome': dependente.nome,
            'cpf': dependente.cpf,
            'parentesco': dependente.parentesco,
            'data_nascimento': dependente.data_nascimento
        }
        
        alteracoes = {
            k: {'antigo': dados_antigos[k], 'novo': dados_novos[k]}
            for k in dados_antigos
            if dados_antigos[k] != dados_novos[k]
        }
        
        if alteracoes:
            historico = HistoricoCI(
                colaborador_id=ci.id,
                tipo_evento='ALTERACAO_DEPENDENTE',
                descricao=f'Dados do dependente {dependente.nome} alterados',
                data_evento=date.today(),
                nc=ci.nc_atual,
                cod_empresa=ci.empresa_atual,
                dados_alterados=alteracoes
            )
            db.session.add(historico)
        
        db.session.commit()
        
        flash(f'Dependente {dependente.nome} atualizado com sucesso!', 'success')
        return redirect(url_for('ci.detalhes', id=ci_id))
        
    except ValueError as e:
        flash(str(e), 'error')
        return render_template('ci/dependente_editar.html', ci=ci, dependente=dependente)
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar dependente: {str(e)}', 'error')
        return render_template('ci/dependente_editar.html', ci=ci, dependente=dependente)


@ci_bp.route('/<int:ci_id>/dependentes/<int:dep_id>/excluir', methods=['POST'])
@login_required
def excluir_dependente(ci_id, dep_id):
    """
    Exclui um dependente.
    """
    ci = ColaboradorInterno.query.get_or_404(ci_id)
    dependente = Dependente.query.get_or_404(dep_id)
    
    if dependente.colaborador_id != ci.id:
        abort(404)
    
    if ci.is_deleted:
        flash('Não é possível excluir dependentes de um colaborador excluído', 'error')
        return redirect(url_for('ci.detalhes', id=ci_id))
    
    try:
        # Registrar histórico antes de excluir
        historico = HistoricoCI(
            colaborador_id=ci.id,
            tipo_evento='EXCLUSAO_DEPENDENTE',
            descricao=f'Dependente {dependente.nome} excluído',
            data_evento=date.today(),
            nc=ci.nc_atual,
            cod_empresa=ci.empresa_atual,
            dados_alterados={
                'dependente_nome': dependente.nome,
                'dependente_cpf': dependente.cpf,
                'parentesco': dependente.parentesco,
                'usuario': current_user.nome
            }
        )
        db.session.add(historico)
        
        # Excluir dependente
        db.session.delete(dependente)
        db.session.commit()
        
        flash(f'Dependente {dependente.nome} excluído com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir dependente: {str(e)}', 'error')
    
    return redirect(url_for('ci.detalhes', id=ci_id))


# ============================================================================
# ROTAS DE EXPORTAÇÃO
# ============================================================================

@ci_bp.route('/<int:id>/exportar')
@login_required
def exportar(id):
    """
    Exporta dados do colaborador em formato CSV.
    """
    ci = ColaboradorInterno.query.get_or_404(id)
    
    if ci.is_deleted and not current_user.is_admin:
        flash('Acesso negado: colaborador excluído', 'error')
        return redirect(url_for('ci.listar'))
    
    try:
        # Gerar CSV usando serviço
        csv_data = ci_service.exportar_colaborador_csv(ci)
        
        from flask import send_file
        import io
        
        return send_file(
            io.BytesIO(csv_data.encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'colaborador_{ci.id}_{ci.nome.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'error')
        return redirect(url_for('ci.detalhes', id=id))


@ci_bp.route('/exportar-todos')
@login_required
def exportar_todos():
    """
    Exporta todos os colaboradores ativos em formato CSV.
    """
    try:
        # Gerar CSV usando serviço
        csv_data = ci_service.exportar_todos_csv()
        
        from flask import send_file
        import io
        
        return send_file(
            io.BytesIO(csv_data.encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'colaboradores_ativos_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
    except Exception as e:
        flash(f'Erro ao exportar dados: {str(e)}', 'error')
        return redirect(url_for('ci.listar'))


# ============================================================================
# ROTAS DE API (para AJAX)
# ============================================================================

@ci_bp.route('/api/verificar-cpf/<string:cpf>')
@login_required
def api_verificar_cpf(cpf):
    """
    Verifica se um CPF já está cadastrado.
    
    Retorna JSON com informações se o CPF está em uso.
    """
    cpf_limpo = clean_cpf(cpf)
    
    if not cpf_limpo:
        return jsonify({'error': 'CPF inválido'}), 400
    
    ci = ColaboradorInterno.query.filter_by(cpf=cpf_limpo).first()
    
    if ci:
        return jsonify({
            'em_uso': True,
            'colaborador_id': ci.id,
            'colaborador_nome': ci.nome,
            'esta_ativo': ci.esta_ativo,
            'is_deleted': ci.is_deleted,
            'nc_atual': ci.nc_atual,
            'empresa_atual': ci.empresa_atual
        })
    
    return jsonify({'em_uso': False})


@ci_bp.route('/api/verificar-nc/<string:nc>')
@login_required
def api_verificar_nc(nc):
    """
    Verifica se um NC já está em uso por outro colaborador ativo.
    
    Retorna JSON com informações se o NC está em uso.
    """
    nc_limpo = clean_nc(nc)
    
    if not nc_limpo:
        return jsonify({'error': 'NC inválido'}), 400
    
    # Buscar NC ativo
    nc_ativo = NumeroCadastro.query.filter_by(
        nc=nc_limpo,
        ativo=True
    ).first()
    
    if nc_ativo:
        return jsonify({
            'em_uso': True,
            'colaborador_id': nc_ativo.colaborador_id,
            'colaborador_nome': nc_ativo.colaborador.nome,
            'empresa': nc_ativo.cod_empresa,
            'data_inicio': nc_ativo.data_inicio.isoformat() if nc_ativo.data_inicio else None,
        })
    
    return jsonify({'em_uso': False})


@ci_bp.route('/api/estatisticas')
@login_required
def api_estatisticas():
    """
    Retorna estatísticas dos colaboradores em formato JSON.
    """
    try:
        estatisticas = ci_service.obter_estatisticas()
        return jsonify(estatisticas)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ci_bp.route('/api/<int:id>/resumo')
@login_required
def api_resumo(id):
    """
    Retorna resumo do colaborador em formato JSON.
    """
    ci = ColaboradorInterno.query.get_or_404(id)
    
    if ci.is_deleted and not current_user.is_admin:
        return jsonify({'error': 'Acesso negado'}), 403
    
    return jsonify({
        'id': ci.id,
        'nome': ci.nome,
        'cpf': ci.cpf,
        'esta_ativo': ci.esta_ativo,
        'empresa_atual': ci.empresa_atual,
        'nc_atual': ci.nc_atual,
        'total_dependentes': ci.total_dependentes,
        'total_planos_saude': ci.total_planos_saude,
        'total_planos_odonto': ci.total_planos_odonto,
        'data_admissao': ci.data_admissao.isoformat() if ci.data_admissao else None,
        'tempo_empresa_meses': ci.tempo_empresa
    })


# ============================================================================
# ERROR HANDLERS ESPECÍFICOS
# ============================================================================

@ci_bp.errorhandler(404)
def ci_nao_encontrado(error):
    """Handler para CI não encontrado."""
    flash('Colaborador não encontrado', 'error')
    return redirect(url_for('ci.listar'))


@ci_bp.errorhandler(403)
def acesso_negado(error):
    """Handler para acesso negado."""
    flash('Acesso negado: permissão insuficiente', 'error')
    return redirect(url_for('ci.listar'))