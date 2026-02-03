# app/utils/import_functions.py
"""Funcoes de importacao de dados."""

import csv
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from app import db
from app.models import ColaboradorInterno, NumeroCadastro, ImportacaoLog

logger = logging.getLogger(__name__)


def _parse_date(date_str: str) -> Optional[datetime]:
    """Converte string de data para datetime."""
    if not date_str or date_str == '00/00/0000':
        return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _clean_cpf(cpf: str) -> str:
    """Remove formatacao do CPF, mantendo apenas digitos."""
    if not cpf:
        return ''
    return ''.join(filter(str.isdigit, str(cpf))).zfill(11)


def _clean_nc(nc: str) -> str:
    """Limpa NC removendo zeros a esquerda."""
    if not nc:
        return ''
    digits = ''.join(filter(str.isdigit, str(nc)))
    return digits.lstrip('0') or '0'


def importar_ativos(filepath: str, usuario_id: int = None) -> Dict[str, Any]:
    """
    Importa colaboradores ativos a partir de arquivo CSV.

    Formato esperado: CSV com delimitador ';' contendo colunas:
    - MATRICULA: Numero de cadastro (NC)
    - NOME COLABORADOR: Nome completo
    - CPF: CPF do colaborador
    - DATA ADMISSÃO: Data de admissao
    - DATA DE NASCIMENTO: Data de nascimento
    - E-MAIL PESSOAL: Email
    - TELEFONE: Telefone
    - EMPRESA: Codigo da empresa
    - NOME CARGO: Cargo
    - NOME CCUSTO: Centro de custo/setor
    - NOME FILIAL: Filial
    """
    resultado = {
        'sucesso': True,
        'total': 0,
        'importados': 0,
        'atualizados': 0,
        'erros': [],
        'detalhes': []
    }

    try:
        # Detectar encoding
        encoding = 'utf-8'
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                f.read(1024)
        except UnicodeDecodeError:
            encoding = 'latin-1'

        with open(filepath, 'r', encoding=encoding) as f:
            # Detectar delimitador
            sample = f.read(2048)
            f.seek(0)

            delimiter = ';' if sample.count(';') > sample.count(',') else ','
            reader = csv.reader(f, delimiter=delimiter)

            # Ler cabecalho e criar mapeamento de indices
            header = next(reader)
            # Renomear colunas duplicadas (EMPRESA aparece 2x)
            col_map = {}
            empresa_count = 0
            for i, col in enumerate(header):
                col_clean = col.strip()
                if col_clean == 'EMPRESA':
                    if empresa_count == 0:
                        col_map['COD_EMPRESA'] = i
                    else:
                        col_map['NOME_EMPRESA'] = i
                    empresa_count += 1
                else:
                    col_map[col_clean] = i

            def get_val(row_data, col_name, default=''):
                idx = col_map.get(col_name)
                if idx is not None and idx < len(row_data):
                    return row_data[idx]
                return default

            for row_num, row_data in enumerate(reader, start=2):
                resultado['total'] += 1

                try:
                    # Extrair dados principais
                    cpf_raw = get_val(row_data, 'CPF')
                    cpf = _clean_cpf(cpf_raw)

                    if not cpf or len(cpf) != 11:
                        resultado['erros'].append(f"Linha {row_num}: CPF invalido '{cpf_raw}'")
                        continue

                    nome = get_val(row_data, 'NOME COLABORADOR').strip()
                    if not nome:
                        resultado['erros'].append(f"Linha {row_num}: Nome vazio")
                        continue

                    nc_raw = get_val(row_data, 'MATRICULA')
                    nc = _clean_nc(nc_raw)
                    if not nc:
                        resultado['erros'].append(f"Linha {row_num}: Matricula/NC invalido")
                        continue

                    # Dados opcionais
                    data_admissao = _parse_date(get_val(row_data, 'DATA ADMISSÃO'))
                    data_nascimento = _parse_date(get_val(row_data, 'DATA DE NASCIMENTO'))
                    email = get_val(row_data, 'E-MAIL PESSOAL').strip() or None
                    telefone = get_val(row_data, 'TELEFONE').strip() or None
                    # Usar COD_EMPRESA (primeira coluna EMPRESA com codigo)
                    cod_empresa = get_val(row_data, 'COD_EMPRESA', '0106').strip()[:10]

                    # Dados adicionais para armazenar em JSON
                    dados_adicionais = {
                        'empresa_nome': get_val(row_data, 'NOME_EMPRESA').strip(),
                        'cargo': get_val(row_data, 'NOME CARGO').strip(),
                        'setor': get_val(row_data, 'NOME CCUSTO').strip(),
                        'filial': get_val(row_data, 'NOME FILIAL').strip(),
                        'cod_filial': get_val(row_data, 'CÓD. FILIAL').strip(),
                        'sexo': get_val(row_data, 'SEXO').strip(),
                        'tipo_contrato': get_val(row_data, 'TIPO CONTRATO').strip(),
                        'situacao': get_val(row_data, 'SITUAÇÃO').strip(),
                        'cod_situacao': get_val(row_data, 'COD SITUAÇÃO').strip(),
                        'login': get_val(row_data, 'LOGIN').strip(),
                        'cracha': get_val(row_data, 'CRACHA').strip(),
                        'lider_imediato': get_val(row_data, 'LIDER IMEDIATO').strip(),
                        'lider_superior': get_val(row_data, 'LIDER SUPERIOR').strip(),
                        'endereco': {
                            'logradouro': get_val(row_data, 'ENDEREÇO').strip(),
                            'numero': get_val(row_data, 'NÚMERO').strip(),
                            'bairro': get_val(row_data, 'BAIRRO').strip(),
                            'cidade': get_val(row_data, 'CIDADE').strip(),
                            'cep': get_val(row_data, 'CEP').strip(),
                        }
                    }

                    # Buscar ou criar colaborador
                    colaborador = ColaboradorInterno.query.filter_by(cpf=cpf).first()

                    if colaborador:
                        # Atualizar dados existentes
                        colaborador.nome = nome
                        colaborador.email = email or colaborador.email
                        colaborador.telefone = telefone or colaborador.telefone
                        colaborador.data_admissao = data_admissao or colaborador.data_admissao
                        colaborador.data_nascimento = data_nascimento or colaborador.data_nascimento
                        colaborador.dados_adicionais = dados_adicionais
                        colaborador.is_deleted = False
                        colaborador.deleted_at = None
                        resultado['atualizados'] += 1
                    else:
                        # Criar novo colaborador
                        colaborador = ColaboradorInterno(
                            nome=nome,
                            cpf=cpf,
                            email=email,
                            telefone=telefone,
                            data_admissao=data_admissao,
                            data_nascimento=data_nascimento,
                            dados_adicionais=dados_adicionais
                        )
                        db.session.add(colaborador)
                        resultado['importados'] += 1

                    db.session.flush()  # Para obter o ID do colaborador

                    # Verificar e criar NC se necessario
                    nc_existente = NumeroCadastro.query.filter_by(
                        nc=nc,
                        colaborador_id=colaborador.id,
                        ativo=True
                    ).first()

                    if not nc_existente:
                        # Desativar NCs anteriores do colaborador (um por um para evitar conflitos)
                        ncs_ativos = NumeroCadastro.query.filter_by(
                            colaborador_id=colaborador.id,
                            ativo=True
                        ).all()

                        for nc_ativo in ncs_ativos:
                            # Verificar se ja existe um NC inativo com mesmo valor
                            nc_inativo_existente = NumeroCadastro.query.filter_by(
                                nc=nc_ativo.nc,
                                colaborador_id=colaborador.id,
                                ativo=False
                            ).first()

                            if nc_inativo_existente:
                                # Ja existe inativo, apenas deletar o ativo
                                db.session.delete(nc_ativo)
                            else:
                                nc_ativo.ativo = False
                                nc_ativo.data_fim = datetime.now().date()

                        # Verificar se o novo NC ja existe como inativo
                        nc_novo_inativo = NumeroCadastro.query.filter_by(
                            nc=nc,
                            colaborador_id=colaborador.id,
                            ativo=False
                        ).first()

                        if nc_novo_inativo:
                            # Reativar o NC existente
                            nc_novo_inativo.ativo = True
                            nc_novo_inativo.data_fim = None
                            nc_novo_inativo.data_inicio = data_admissao or nc_novo_inativo.data_inicio
                            nc_novo_inativo.cod_empresa = cod_empresa
                        else:
                            # Criar novo NC
                            novo_nc = NumeroCadastro(
                                nc=nc,
                                cod_empresa=cod_empresa,
                                data_inicio=data_admissao or datetime.now().date(),
                                colaborador_id=colaborador.id,
                                ativo=True
                            )
                            db.session.add(novo_nc)

                except Exception as e:
                    resultado['erros'].append(f"Linha {row_num}: {str(e)}")
                    logger.error(f"Erro ao processar linha {row_num}: {e}")
                    continue

            # Commit das alteracoes
            db.session.commit()

            resultado['detalhes'].append(
                f"Total: {resultado['total']}, "
                f"Novos: {resultado['importados']}, "
                f"Atualizados: {resultado['atualizados']}, "
                f"Erros: {len(resultado['erros'])}"
            )

    except Exception as e:
        db.session.rollback()
        resultado['sucesso'] = False
        resultado['erros'].append(f"Erro ao processar arquivo: {str(e)}")
        logger.exception(f"Erro na importacao de ativos: {e}")

    # Registrar log de importacao
    try:
        log = ImportacaoLog(
            tipo_importacao='ATIVOS',
            arquivo=filepath.split('/')[-1].split('\\')[-1],
            status='SUCESSO' if resultado['sucesso'] and not resultado['erros'] else 'PARCIAL' if resultado['sucesso'] else 'ERRO',
            linhas_processadas=resultado['total'],
            linhas_sucesso=resultado['importados'] + resultado['atualizados'],
            linhas_erro=len(resultado['erros']),
            detalhes='; '.join(resultado['erros'][:10]) if resultado['erros'] else None,
            usuario_id=usuario_id
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")

    return resultado


def importar_desligados(filepath: str, usuario_id: int = None) -> Dict[str, Any]:
    """
    Importa colaboradores desligados a partir de arquivo CSV.
    Marca colaboradores como inativos/excluidos.
    """
    resultado = {
        'sucesso': True,
        'total': 0,
        'processados': 0,
        'erros': []
    }

    try:
        encoding = 'utf-8'
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                f.read(1024)
        except UnicodeDecodeError:
            encoding = 'latin-1'

        with open(filepath, 'r', encoding=encoding) as f:
            sample = f.read(2048)
            f.seek(0)
            delimiter = ';' if sample.count(';') > sample.count(',') else ','
            reader = csv.DictReader(f, delimiter=delimiter)

            for row_num, row in enumerate(reader, start=2):
                resultado['total'] += 1

                try:
                    cpf = _clean_cpf(row.get('CPF', ''))
                    if not cpf or len(cpf) != 11:
                        continue

                    colaborador = ColaboradorInterno.query.filter_by(cpf=cpf).first()
                    if colaborador:
                        colaborador.is_deleted = True
                        colaborador.deleted_at = datetime.now()
                        colaborador.deleted_reason = 'Importacao de desligados'

                        # Desativar NCs
                        NumeroCadastro.query.filter_by(
                            colaborador_id=colaborador.id,
                            ativo=True
                        ).update({'ativo': False, 'data_fim': datetime.now().date()})

                        resultado['processados'] += 1

                except Exception as e:
                    resultado['erros'].append(f"Linha {row_num}: {str(e)}")

            db.session.commit()

    except Exception as e:
        db.session.rollback()
        resultado['sucesso'] = False
        resultado['erros'].append(str(e))

    return resultado


def importar_unimed(filepath: str, tipo: str, usuario_id: int = None) -> Dict[str, Any]:
    """Stub para funcao de importacao UNIMED."""
    # TODO: Implementar
    return {'sucesso': False, 'erros': ['Funcao nao implementada']}


def importar_hapvida_saude(filepath: str, empresa: str, tipo: str, usuario_id: int = None) -> Dict[str, Any]:
    """Stub para funcao de importacao Hapvida Saude."""
    # TODO: Implementar
    return {'sucesso': False, 'erros': ['Funcao nao implementada']}


def importar_hapvida_odonto(filepath: str, empresa: str, unidade: str = None, usuario_id: int = None) -> Dict[str, Any]:
    """Stub para funcao de importacao Hapvida Odonto."""
    # TODO: Implementar
    return {'sucesso': False, 'erros': ['Funcao nao implementada']}


def importar_odontoprev(filepath: str, empresa: str, usuario_id: int = None) -> Dict[str, Any]:
    """Stub para funcao de importacao Odontoprev."""
    # TODO: Implementar
    return {'sucesso': False, 'erros': ['Funcao nao implementada']}


def limpar_duplicados_coparticipacao(competencia: str = None, contrato: str = None) -> int:
    """Stub para funcao de limpeza de duplicados."""
    # TODO: Implementar
    return 0
