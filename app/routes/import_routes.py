# app/routes/import_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, session, send_file
from flask_login import login_required, current_user
from app import db
from app.models import ImportacaoLog, ColaboradorInterno, NumeroCadastro
from app.utils.pagination import paginate_query
from app.utils.helpers import _to_brasilia
from app.utils.import_functions import (
    importar_ativos, importar_desligados, importar_unimed, 
    importar_hapvida_saude, importar_hapvida_odonto, importar_odontoprev,
    limpar_duplicados_coparticipacao
)
import os
import json
from datetime import datetime
import io
import csv
from werkzeug.utils import secure_filename

import_bp = Blueprint('import', __name__)

@import_bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar():
    from app import current_app as app
    
    if request.method == 'POST':
        arquivos = request.files.getlist('arquivos[]')
        tipo = request.form['tipo']
        empresa = request.form.get('empresa', '')
        subtipo = request.form.get('subtipo', '')

        if not arquivos or all(a.filename == '' for a in arquivos):
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)

        # Mapeamento: tipo → função de importação
        import_map = {
            'ATIVOS': lambda fp: importar_ativos(fp, session.get('usuario_id')),
            'DESLIGADOS': lambda fp: importar_desligados(fp, session.get('usuario_id')),
            'UNIMED': lambda fp: importar_unimed(fp, subtipo, session.get('usuario_id')),
            'HAPVIDA_SAUDE': lambda fp: importar_hapvida_saude(fp, empresa, subtipo, session.get('usuario_id')),
            'HAPVIDA_ODONTO': lambda fp: importar_hapvida_odonto(fp, empresa, request.form.get('unidade', ''), session.get('usuario_id')),
            'ODONTOPREV': lambda fp: importar_odontoprev(fp, empresa, session.get('usuario_id')),
        }

        if tipo not in import_map:
            flash('Tipo de importação não suportado', 'error')
            return redirect(request.url)

        resultados = []

        for arquivo in arquivos:
            if not arquivo.filename or not allowed_file(arquivo.filename, app.config['ALLOWED_EXTENSIONS']):
                continue

            filename = secure_filename(arquivo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], tipo.lower(), filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            arquivo.save(filepath)

            # Log inicial
            log = ImportacaoLog(tipo_importacao=tipo, arquivo=filename,
                                usuario_id=session.get('usuario_id'), status='PROCESSANDO')
            db.session.add(log)
            db.session.flush()
            log_id = log.id

            try:
                resultado = import_map[tipo](filepath)

                # Atualizar log
                log = db.session.get(ImportacaoLog, log_id)
                if log and resultado:
                    erros_n = len(resultado['erros']) if isinstance(resultado.get('erros'), list) else resultado.get('erros', 0)
                    log.linhas_processadas = resultado.get('total', 0)
                    log.linhas_sucesso = resultado.get('sucessos', 0)
                    log.linhas_erro = erros_n
                    log.status = 'SUCESSO' if resultado.get('sucesso') else 'ERRO'
                    lista_e = resultado.get('lista_erros', [])
                    log.detalhes = json.dumps(lista_e[:20], ensure_ascii=False)[:10000] if isinstance(lista_e, list) else str(lista_e)[:10000]

                resultados.append({
                    'arquivo': filename,
                    'sucesso': resultado.get('sucesso', False),
                    'sucessos': resultado.get('sucessos', 0),
                    'mensagem': (resultado.get('lista_erros') or resultado.get('erros') or [''])[0][:200]
                                if not resultado.get('sucesso') else None,
                })
                db.session.commit()

            except Exception as e:
                try:
                    log = db.session.get(ImportacaoLog, log_id)
                    if log:
                        log.status = 'ERRO'
                        log.detalhes = str(e)[:10000]
                    db.session.commit()
                except Exception:
                    db.session.rollback()

                resultados.append({'arquivo': filename, 'sucesso': False, 'sucessos': 0, 'mensagem': str(e)[:200]})

            finally:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass

        # Flash resumo
        ok = sum(1 for r in resultados if r['sucesso'])
        flash(f'Importação concluída: {ok}/{len(resultados)} arquivos com sucesso.', 'success')
        for r in resultados[:3]:
            if r['sucesso']:
                flash(f"✓ {r['arquivo']}: {r['sucessos']} registros", 'success')
            else:
                flash(f"✗ {r['arquivo']}: {r.get('mensagem', 'Erro')}", 'error')
        if len(resultados) > 3:
            flash(f"... e mais {len(resultados) - 3} arquivos", 'info')

        return redirect(url_for('import.importar'))

    # GET
    return render_template('import.html',
        importacoes=ImportacaoLog.query.order_by(ImportacaoLog.data_importacao.desc()).limit(10).all(),
        current_date=datetime.now(),
        valid_company_codes=app.config['VALID_COMPANY_CODES'],
        unimed_contracts=app.config.get('UNIMED_CONTRACTS', {}),
        allowed_extensions=list(app.config['ALLOWED_EXTENSIONS']),
        max_content_length=app.config['MAX_CONTENT_LENGTH'],
    )

@import_bp.route('/importar/historico')
@login_required
def historico_importacoes():
    page = request.args.get('page', 1, type=int)
    tipo = request.args.get('tipo', '')
    status = request.args.get('status', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')

    query = ImportacaoLog.query
    if tipo:
        query = query.filter_by(tipo_importacao=tipo)
    if status:
        query = query.filter_by(status=status)
    if data_inicio:
        try:
            query = query.filter(ImportacaoLog.data_importacao >= datetime.strptime(data_inicio, '%Y-%m-%d'))
        except ValueError:
            pass
    if data_fim:
        try:
            query = query.filter(ImportacaoLog.data_importacao <= datetime.strptime(data_fim, '%Y-%m-%d'))
        except ValueError:
            pass

    importacoes, pagination = paginate_query(query.order_by(ImportacaoLog.data_importacao.desc()), 50)

    return render_template('historico_importacoes.html',
        importacoes=importacoes,
        pagination=pagination,
        tipo=tipo, data_inicio=data_inicio, data_fim=data_fim, status=status,
        valid_company_codes=app.config['VALID_COMPANY_CODES'],
    )

@import_bp.route('/limpar/duplicados/coparticipacao', methods=['POST'])
@login_required
def limpar_duplicados_coparticipacao_route():
    """Rota para limpar duplicados de coparticipação."""
    from app import current_app as app
    
    competencia = request.form.get('competencia', '').strip() or None
    contrato = request.form.get('contrato', '').strip() or None
    
    try:
        removidos = limpar_duplicados_coparticipacao(competencia, contrato)
        flash(f'Removidos {removidos} registros duplicados de coparticipação', 'success')
    except Exception as e:
        flash(f'Erro ao limpar duplicados: {e}', 'error')
    
    return redirect(url_for('config.configuracoes'))

@import_bp.route('/exportar/coparticipacao/geral')
@login_required
def exportar_coparticipacao_geral():
    """Exporta todos os atendimentos de coparticipação do sistema."""
    from app import current_app as app
    from app.models import AtendimentoCoparticipacao, PlanoSaude
    
    # Buscar todos os atendimentos
    atendimentos = AtendimentoCoparticipacao.query.join(
        PlanoSaude
    ).filter(
        PlanoSaude.tipo == 'COPARTICIPACAO'
    ).order_by(
        AtendimentoCoparticipacao.competencia,
        AtendimentoCoparticipacao.contrato,
        AtendimentoCoparticipacao.data_atendimento
    ).all()
    
    if not atendimentos:
        flash('Nenhum atendimento de coparticipação encontrado', 'warning')
        return redirect(url_for('main.index'))
    
    # Criar CSV
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
    
    # Cabeçalho
    writer.writerow([
        'ID Plano', 'Contrato', 'Competência', 'CPF', 'Beneficiário', 'NC',
        'Colaborador', 'Empresa', 'Guia', 'Data Atendimento', 'Descrição', 
        'Quantidade', 'Valor Base', 'Valor Coparticipação', 'Data Importação'
    ])
    
    # Dados
    for atend in atendimentos:
        plano = atend.plano_saude
        ci = plano.colaborador
        empresa_nome = app.config['VALID_COMPANY_CODES'].get(plano.empresa_cod, plano.empresa_cod)
        
        writer.writerow([
            plano.id,
            atend.contrato,
            atend.competencia,
            atend.cpf or '',
            atend.beneficiario,
            atend.nc,
            ci.nome,
            empresa_nome,
            atend.guia or '',
            atend.data_atendimento.strftime('%d/%m/%Y') if atend.data_atendimento else '',
            atend.descricao or '',
            str(atend.quantidade).replace('.', ','),
            str(atend.valor_base).replace('.', ',') if atend.valor_base else '0,00',
            str(atend.valor_coparticipacao).replace('.', ','),
            atend.created_at.strftime('%d/%m/%Y %H:%M') if atend.created_at else ''
        ])
    
    output.seek(0)
    
    # Nome do arquivo
    filename = f"coparticipacao_geral_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions