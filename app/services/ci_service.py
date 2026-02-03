"""
Serviço para operações de negócio relacionadas a Colaboradores Internos.
"""

import csv
import io
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import or_, and_, func, desc, asc
from sqlalchemy.orm import joinedload, contains_eager

from app import db
from app.models import (
    ColaboradorInterno,
    NumeroCadastro,
    Dependente,
    PlanoSaude,
    PlanoOdontologico,
    HistoricoCI,
    AtendimentoCoparticipacao,
    Usuario
)
from app.utils.validators import clean_cpf, clean_nc, clean_empresa
from app.utils.data_utils import serialize_for_json
from app.exceptions import (
    CINaoEncontradoError,
    NCEmUsoError,
    CPFJaCadastradoError,
    ColaboradorExcluidoError,
    ValidacaoError
)


class CIService:
    """Serviço para gerenciamento de Colaboradores Internos."""
    
    def __init__(self):
        self._cache = {}
    
    # ============================================================================
    # MÉTODOS DE BUSCA E CONSULTA
    # ============================================================================
    
    def buscar_com_filtros(
        self,
        nome: str = '',
        cpf: str = '',
        empresa: str = '',
        status: str = '',
        mostrar_excluidos: bool = False,
        page: int = 1,
        per_page: int = 50,
        ordenar_por: str = 'nome',
        ordem: str = 'asc'
    ) -> Dict[str, Any]:
        """
        Busca colaboradores com filtros e paginação.
        
        Args:
            nome: Termo para busca por nome (LIKE)
            cpf: CPF para filtro
            empresa: Código da empresa para filtro
            status: 'ativo', 'inativo' ou 'excluido'
            mostrar_excluidos: Incluir colaboradores excluídos logicamente
            page: Número da página
            per_page: Itens por página
            ordenar_por: Campo para ordenação
            ordem: 'asc' ou 'desc'
        
        Returns:
            Dict com 'cis' (lista) e 'total' (int)
        """
        try:
            # Construir query base
            query = ColaboradorInterno.query
            
            # Aplicar filtro de exclusão
            if not mostrar_excluidos:
                query = query.filter_by(is_deleted=False)
            
            # Aplicar filtros
            if nome:
                query = query.filter(ColaboradorInterno.nome.ilike(f'%{nome}%'))
            
            if cpf:
                cpf_limpo = clean_cpf(cpf)
                if cpf_limpo:
                    query = query.filter(ColaboradorInterno.cpf.ilike(f'%{cpf_limpo}%'))
            
            # Filtro por empresa (via NC ativo)
            if empresa:
                subquery = db.session.query(NumeroCadastro.colaborador_id).filter(
                    NumeroCadastro.cod_empresa == empresa,
                    NumeroCadastro.ativo == True
                ).subquery()
                query = query.filter(ColaboradorInterno.id.in_(subquery))
            
            # Filtro por status
            if status == 'ativo' and not mostrar_excluidos:
                subquery = db.session.query(NumeroCadastro.colaborador_id).filter(
                    NumeroCadastro.ativo == True
                ).subquery()
                query = query.filter(ColaboradorInterno.id.in_(subquery))
            
            elif status == 'inativo' and not mostrar_excluidos:
                subquery = db.session.query(NumeroCadastro.colaborador_id).filter(
                    NumeroCadastro.ativo == True
                ).subquery()
                query = query.filter(~ColaboradorInterno.id.in_(subquery))
            
            elif status == 'excluido':
                query = query.filter_by(is_deleted=True)
            
            # Aplicar ordenação
            order_map = {
                'nome': ColaboradorInterno.nome,
                'cpf': ColaboradorInterno.cpf,
                'data_admissao': ColaboradorInterno.data_admissao,
                'created_at': ColaboradorInterno.created_at,
                'id': ColaboradorInterno.id
            }
            
            order_column = order_map.get(ordenar_por, ColaboradorInterno.nome)
            
            if ordem.lower() == 'desc':
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))
            
            # Ordenação adicional para consistência
            if ordenar_por != 'id':
                query = query.order_by(asc(ColaboradorInterno.id))
            
            # Paginação
            total = query.count()
            cis = query.paginate(page=page, per_page=per_page, error_out=False)
            
            # Carregar relacionamentos necessários
            cis_loaded = []
            for ci in cis.items:
                # Carregar NC ativo
                ci.nc_ativo = NumeroCadastro.query.filter_by(
                    colaborador_id=ci.id,
                    ativo=True
                ).first()
                
                # Contar dependentes
                ci.total_dependentes_cache = Dependente.query.filter_by(
                    colaborador_id=ci.id
                ).count()
                
                # Contar planos ativos
                ci.total_planos_saude_cache = PlanoSaude.query.filter_by(
                    colaborador_id=ci.id,
                    ativo=True
                ).count()
                
                ci.total_planos_odonto_cache = PlanoOdontologico.query.filter_by(
                    colaborador_id=ci.id,
                    ativo=True
                ).count()
                
                cis_loaded.append(ci)
            
            return {
                'cis': cis_loaded,
                'total': total,
                'pagina_atual': page,
                'total_paginas': cis.pages,
                'por_pagina': per_page
            }
            
        except Exception as e:
            raise ValidacaoError(f"Erro na busca de colaboradores: {str(e)}")
    
    def pesquisa_rapida(self, termo: str, limite: int = 20) -> List[ColaboradorInterno]:
        """
        Pesquisa rápida de colaboradores para autocomplete.
        
        Args:
            termo: Termo de busca
            limite: Número máximo de resultados
        
        Returns:
            Lista de colaboradores
        """
        try:
            termo_limpo = termo.strip()
            if len(termo_limpo) < 2:
                return []
            
            # Buscar por nome, CPF ou NC
            query = ColaboradorInterno.query.filter(
                ColaboradorInterno.is_deleted == False
            ).filter(
                or_(
                    ColaboradorInterno.nome.ilike(f'%{termo_limpo}%'),
                    ColaboradorInterno.cpf.ilike(f'%{termo_limpo}%'),
                    ColaboradorInterno.id.in_(
                        db.session.query(NumeroCadastro.colaborador_id).filter(
                            NumeroCadastro.nc.ilike(f'%{termo_limpo}%'),
                            NumeroCadastro.ativo == True
                        )
                    )
                )
            ).order_by(ColaboradorInterno.nome).limit(limite)
            
            # Carregar NC ativo para cada resultado
            resultados = []
            for ci in query.all():
                ci.nc_ativo = NumeroCadastro.query.filter_by(
                    colaborador_id=ci.id,
                    ativo=True
                ).first()
                resultados.append(ci)
            
            return resultados
            
        except Exception as e:
            raise ValidacaoError(f"Erro na pesquisa rápida: {str(e)}")
    
    def obter_por_id(self, ci_id: int) -> Optional[ColaboradorInterno]:
        """
        Obtém um colaborador por ID com todos os relacionamentos.
        
        Args:
            ci_id: ID do colaborador
        
        Returns:
            ColaboradorInterno ou None
        """
        try:
            ci = ColaboradorInterno.query.get(ci_id)
            
            if not ci:
                return None
            
            # Carregar relacionamentos
            ci.nc_ativo = NumeroCadastro.query.filter_by(
                colaborador_id=ci.id,
                ativo=True
            ).first()
            
            ci.dependentes_cache = Dependente.query.filter_by(
                colaborador_id=ci.id
            ).all()
            
            ci.planos_saude_cache = PlanoSaude.query.filter_by(
                colaborador_id=ci.id
            ).order_by(PlanoSaude.data_inicio.desc()).all()
            
            ci.planos_odonto_cache = PlanoOdontologico.query.filter_by(
                colaborador_id=ci.id
            ).order_by(PlanoOdontologico.data_inicio.desc()).all()
            
            ci.historico_cache = HistoricoCI.query.filter_by(
                colaborador_id=ci.id
            ).order_by(HistoricoCI.data_evento.desc()).limit(100).all()
            
            return ci
            
        except Exception as e:
            raise ValidacaoError(f"Erro ao obter colaborador: {str(e)}")
    
    def obter_por_cpf(self, cpf: str) -> Optional[ColaboradorInterno]:
        """
        Obtém um colaborador por CPF.
        
        Args:
            cpf: CPF do colaborador
        
        Returns:
            ColaboradorInterno ou None
        """
        try:
            cpf_limpo = clean_cpf(cpf)
            if not cpf_limpo:
                return None
            
            return ColaboradorInterno.query.filter_by(cpf=cpf_limpo).first()
            
        except Exception as e:
            raise ValidacaoError(f"Erro ao buscar por CPF: {str(e)}")
    
    def obter_por_nc(self, nc: str, ativo: bool = True) -> Optional[ColaboradorInterno]:
        """
        Obtém um colaborador por NC.
        
        Args:
            nc: Número de Cadastro
            ativo: Buscar apenas NCs ativos
        
        Returns:
            ColaboradorInterno ou None
        """
        try:
            nc_limpo = clean_nc(nc)
            if not nc_limpo:
                return None
            
            nc_obj = NumeroCadastro.query.filter_by(
                nc=nc_limpo,
                ativo=ativo
            ).first()
            
            return nc_obj.colaborador if nc_obj else None
            
        except Exception as e:
            raise ValidacaoError(f"Erro ao buscar por NC: {str(e)}")
    
    # ============================================================================
    # MÉTODOS DE CRIAÇÃO E ATUALIZAÇÃO
    # ============================================================================
    
    def criar_colaborador(
        self,
        dados: Dict[str, Any],
        usuario_id: int
    ) -> ColaboradorInterno:
        """
        Cria um novo colaborador.
        
        Args:
            dados: Dicionário com dados do colaborador
            usuario_id: ID do usuário que está criando
        
        Returns:
            ColaboradorInterno criado
        
        Raises:
            CPFJaCadastradoError: Se CPF já estiver cadastrado
            ValidacaoError: Se dados forem inválidos
        """
        try:
            # Validar dados obrigatórios
            nome = dados.get('nome', '').strip()
            cpf_raw = dados.get('cpf', '').strip()
            
            if not nome:
                raise ValidacaoError("Nome é obrigatório")
            
            cpf = clean_cpf(cpf_raw)
            if not cpf:
                raise ValidacaoError("CPF inválido")
            
            # Verificar se CPF já existe
            if ColaboradorInterno.query.filter_by(cpf=cpf).first():
                raise CPFJaCadastradoError(cpf)
            
            # Coletar outros dados
            email = dados.get('email', '').strip() or None
            telefone = dados.get('telefone', '').strip() or None
            
            # Processar datas
            from app.utils.validators import validate_date
            data_admissao = validate_date(dados.get('data_admissao'))
            data_nascimento = validate_date(dados.get('data_nascimento'))
            
            # Criar colaborador
            ci = ColaboradorInterno(
                nome=nome,
                cpf=cpf,
                email=email,
                telefone=telefone,
                data_admissao=data_admissao,
                data_nascimento=data_nascimento,
                dados_adicionais=dados.get('dados_adicionais')
            )
            
            db.session.add(ci)
            db.session.flush()
            
            # Adicionar NC se fornecido
            nc_raw = dados.get('nc', '').strip()
            empresa = dados.get('empresa', '').strip()
            
            if nc_raw and empresa:
                nc = clean_nc(nc_raw)
                empresa_limpa = clean_empresa(empresa)
                
                if nc and empresa_limpa:
                    self.adicionar_nc(
                        ci_id=ci.id,
                        nc=nc,
                        empresa=empresa_limpa,
                        motivo='CRIAÇÃO MANUAL'
                    )
            
            # Registrar histórico
            usuario = Usuario.query.get(usuario_id)
            historico = HistoricoCI(
                colaborador_id=ci.id,
                tipo_evento='CRIAÇÃO_MANUAL',
                descricao=f'CI criado manualmente por {usuario.nome if usuario else "Sistema"}',
                data_evento=date.today(),
                nc=nc if nc_raw else None,
                cod_empresa=empresa_limpa if empresa else None,
                dados_alterados={
                    'nome': nome,
                    'cpf': cpf,
                    'email': email,
                    'telefone': telefone,
                    'data_admissao': data_admissao.isoformat() if data_admissao else None,
                    'data_nascimento': data_nascimento.isoformat() if data_nascimento else None,
                    'usuario': usuario.nome if usuario else 'Sistema'
                }
            )
            db.session.add(historico)
            
            db.session.commit()
            
            return ci
            
        except (CPFJaCadastradoError, ValidacaoError):
            raise
        except Exception as e:
            db.session.rollback()
            raise ValidacaoError(f"Erro ao criar colaborador: {str(e)}")
    
    def atualizar_colaborador(
        self,
        ci_id: int,
        dados: Dict[str, Any],
        usuario_id: int
    ) -> ColaboradorInterno:
        """
        Atualiza dados de um colaborador existente.
        
        Args:
            ci_id: ID do colaborador
            dados: Dicionário com dados para atualizar
            usuario_id: ID do usuário que está atualizando
        
        Returns:
            ColaboradorInterno atualizado
        
        Raises:
            CINaoEncontradoError: Se colaborador não existir
            ColaboradorExcluidoError: Se colaborador estiver excluído
            ValidacaoError: Se dados forem inválidos
        """
        try:
            ci = self.obter_por_id(ci_id)
            if not ci:
                raise CINaoEncontradoError(ci_id)
            
            if ci.is_deleted:
                raise ColaboradorExcluidoError(ci_id)
            
            # Registrar dados antigos para histórico
            dados_antigos = {
                'nome': ci.nome,
                'email': ci.email,
                'telefone': ci.telefone,
                'data_admissao': ci.data_admissao,
                'data_nascimento': ci.data_nascimento
            }
            
            # Atualizar dados
            if 'nome' in dados and dados['nome']:
                ci.nome = dados['nome'].strip()
            
            if 'email' in dados:
                ci.email = dados['email'].strip() if dados['email'] else None
            
            if 'telefone' in dados:
                ci.telefone = dados['telefone'].strip() if dados['telefone'] else None
            
            if 'data_admissao' in dados:
                from app.utils.validators import validate_date
                data = validate_date(dados['data_admissao'])
                if data:
                    ci.data_admissao = data
            
            if 'data_nascimento' in dados:
                from app.utils.validators import validate_date
                data = validate_date(dados['data_nascimento'])
                if data:
                    ci.data_nascimento = data
            
            if 'dados_adicionais' in dados:
                ci.dados_adicionais = dados['dados_adicionais']
            
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
                usuario = Usuario.query.get(usuario_id)
                historico = HistoricoCI(
                    colaborador_id=ci.id,
                    tipo_evento='ALTERACAO_DADOS',
                    descricao='Alteração de dados cadastrais',
                    data_evento=date.today(),
                    nc=ci.nc_atual.nc if ci.nc_ativo else None,
                    cod_empresa=ci.nc_ativo.cod_empresa if ci.nc_ativo else None,
                    dados_alterados=alteracoes
                )
                db.session.add(historico)
            
            db.session.commit()
            
            return ci
            
        except (CINaoEncontradoError, ColaboradorExcluidoError):
            raise
        except Exception as e:
            db.session.rollback()
            raise ValidacaoError(f"Erro ao atualizar colaborador: {str(e)}")
    
    # ============================================================================
    # MÉTODOS DE NC (NÚMERO DE CADASTRO)
    # ============================================================================
    
    def nc_em_uso(self, nc: str, excluir_ci_id: Optional[int] = None) -> bool:
        """
        Verifica se um NC já está em uso por outro colaborador ativo.
        
        Args:
            nc: Número de Cadastro
            excluir_ci_id: ID do colaborador a excluir da verificação
        
        Returns:
            True se NC estiver em uso, False caso contrário
        """
        try:
            nc_limpo = clean_nc(nc)
            if not nc_limpo:
                return False
            
            query = NumeroCadastro.query.filter_by(
                nc=nc_limpo,
                ativo=True
            )
            
            if excluir_ci_id:
                query = query.filter(NumeroCadastro.colaborador_id != excluir_ci_id)
            
            return query.first() is not None
            
        except Exception as e:
            raise ValidacaoError(f"Erro ao verificar NC: {str(e)}")
    
    def adicionar_nc(
        self,
        ci_id: int,
        nc: str,
        empresa: str,
        motivo: str = None
    ) -> NumeroCadastro:
        """
        Adiciona um novo NC para um colaborador.
        
        Args:
            ci_id: ID do colaborador
            nc: Número de Cadastro
            empresa: Código da empresa
            motivo: Motivo da adição
        
        Returns:
            NumeroCadastro criado
        
        Raises:
            CINaoEncontradoError: Se colaborador não existir
            NCEmUsoError: Se NC já estiver em uso
            ValidacaoError: Se dados forem inválidos
        """
        try:
            ci = self.obter_por_id(ci_id)
            if not ci:
                raise CINaoEncontradoError(ci_id)
            
            if ci.is_deleted:
                raise ColaboradorExcluidoError(ci_id)
            
            nc_limpo = clean_nc(nc)
            empresa_limpa = clean_empresa(empresa)
            
            if not nc_limpo:
                raise ValidacaoError("NC inválido")
            
            if not empresa_limpa:
                raise ValidacaoError("Empresa inválida")
            
            # Verificar se NC já está em uso
            if self.nc_em_uso(nc_limpo, ci_id):
                raise NCEmUsoError(nc_limpo)
            
            # Desativar NCs ativos anteriores
            ncs_ativos = NumeroCadastro.query.filter_by(
                colaborador_id=ci_id,
                ativo=True
            ).all()
            
            for nc_ativo in ncs_ativos:
                if nc_ativo.nc != nc_limpo:
                    nc_ativo.desativar(
                        data_fim=date.today(),
                        motivo=f'MUDANÇA PARA NC {nc_limpo}'
                    )
            
            # Verificar se já existe registro inativo para reativar
            nc_existente = NumeroCadastro.query.filter_by(
                colaborador_id=ci_id,
                nc=nc_limpo,
                ativo=False
            ).order_by(NumeroCadastro.data_inicio.desc()).first()
            
            if nc_existente:
                # Reativar NC existente
                nc_existente.reativar(
                    data_inicio=date.today(),
                    motivo=motivo or 'REATIVAÇÃO'
                )
                nc_existente.cod_empresa = empresa_limpa
                nc_obj = nc_existente
            else:
                # Criar novo NC
                nc_obj = NumeroCadastro(
                    nc=nc_limpo,
                    cod_empresa=empresa_limpa,
                    data_inicio=date.today(),
                    ativo=True,
                    motivo_mudanca=motivo or 'NOVO NC',
                    colaborador_id=ci_id
                )
                db.session.add(nc_obj)
            
            db.session.commit()
            
            return nc_obj
            
        except (CINaoEncontradoError, ColaboradorExcluidoError, NCEmUsoError):
            raise
        except Exception as e:
            db.session.rollback()
            raise ValidacaoError(f"Erro ao adicionar NC: {str(e)}")
    
    def mudar_nc(
        self,
        ci_id: int,
        novo_nc: str,
        nova_empresa: str,
        motivo: str,
        usuario_id: int
    ) -> None:
        """
        Muda o NC ativo de um colaborador.
        
        Args:
            ci_id: ID do colaborador
            novo_nc: Novo número de cadastro
            nova_empresa: Nova empresa
            motivo: Motivo da mudança
            usuario_id: ID do usuário que está fazendo a mudança
        
        Raises:
            CINaoEncontradoError: Se colaborador não existir
            NCEmUsoError: Se novo NC já estiver em uso
            ValidacaoError: Se dados forem inválidos
        """
        try:
            # Adicionar novo NC (já valida e desativa anteriores)
            self.adicionar_nc(
                ci_id=ci_id,
                nc=novo_nc,
                empresa=nova_empresa,
                motivo=motivo
            )
            
            # Registrar histórico específico
            ci = self.obter_por_id(ci_id)
            usuario = Usuario.query.get(usuario_id)
            
            historico = HistoricoCI(
                colaborador_id=ci_id,
                tipo_evento='MUDANCA_NC_MANUAL',
                descricao=f'Mudança de NC para {novo_nc} (Empresa: {nova_empresa})',
                data_evento=date.today(),
                nc=novo_nc,
                cod_empresa=nova_empresa,
                dados_alterados={
                    'nc_antigo': ci.nc_atual if ci.nc_ativo else None,
                    'empresa_antiga': ci.empresa_atual,
                    'motivo': motivo,
                    'usuario': usuario.nome if usuario else 'Sistema'
                }
            )
            db.session.add(historico)
            
            db.session.commit()
            
        except (CINaoEncontradoError, NCEmUsoError):
            raise
        except Exception as e:
            db.session.rollback()
            raise ValidacaoError(f"Erro ao mudar NC: {str(e)}")
    
    def obter_historico_nc(self, ci_id: int) -> List[NumeroCadastro]:
        """
        Obtém histórico de NCs de um colaborador.
        
        Args:
            ci_id: ID do colaborador
        
        Returns:
            Lista de NCs ordenados por data de início
        """
        try:
            return NumeroCadastro.query.filter_by(
                colaborador_id=ci_id
            ).order_by(
                NumeroCadastro.data_inicio.desc()
            ).all()
            
        except Exception as e:
            raise ValidacaoError(f"Erro ao obter histórico de NCs: {str(e)}")
    
    # ============================================================================
    # MÉTODOS DE DEPENDENTES
    # ============================================================================
    
    def adicionar_dependente(
        self,
        ci_id: int,
        dados: Dict[str, Any],
        usuario_id: int
    ) -> Dependente:
        """
        Adiciona um dependente a um colaborador.
        
        Args:
            ci_id: ID do colaborador
            dados: Dicionário com dados do dependente
            usuario_id: ID do usuário que está adicionando
        
        Returns:
            Dependente criado
        
        Raises:
            CINaoEncontradoError: Se colaborador não existir
            ColaboradorExcluidoError: Se colaborador estiver excluído
            ValidacaoError: Se dados forem inválidos
        """
        try:
            ci = self.obter_por_id(ci_id)
            if not ci:
                raise CINaoEncontradoError(ci_id)
            
            if ci.is_deleted:
                raise ColaboradorExcluidoError(ci_id)
            
            # Validar dados
            nome = dados.get('nome', '').strip()
            if not nome:
                raise ValidacaoError("Nome do dependente é obrigatório")
            
            cpf_raw = dados.get('cpf', '').strip()
            cpf = clean_cpf(cpf_raw) if cpf_raw else None
            
            # Verificar se CPF já existe para este colaborador
            if cpf:
                existente = Dependente.query.filter_by(
                    cpf=cpf,
                    colaborador_id=ci_id
                ).first()
                if existente:
                    raise ValidacaoError("Já existe um dependente com este CPF")
            
            parentesco = dados.get('parentesco', '').strip() or 'DEPENDENTE'
            
            from app.utils.validators import validate_date
            data_nascimento = validate_date(dados.get('data_nascimento'))
            
            # Criar dependente
            dependente = Dependente(
                nome=nome,
                cpf=cpf,
                parentesco=parentesco,
                data_nascimento=data_nascimento,
                nc_vinculo=ci.nc_atual or '',
                colaborador_id=ci_id
            )
            
            db.session.add(dependente)
            db.session.flush()
            
            # Registrar histórico
            usuario = Usuario.query.get(usuario_id)
            historico = HistoricoCI(
                colaborador_id=ci_id,
                tipo_evento='ADICAO_DEPENDENTE',
                descricao=f'Dependente {nome} adicionado',
                data_evento=date.today(),
                nc=ci.nc_atual,
                cod_empresa=ci.empresa_atual,
                dados_alterados={
                    'dependente_nome': nome,
                    'dependente_cpf': cpf,
                    'parentesco': parentesco,
                    'usuario': usuario.nome if usuario else 'Sistema'
                }
            )
            db.session.add(historico)
            
            db.session.commit()
            
            return dependente
            
        except (CINaoEncontradoError, ColaboradorExcluidoError):
            raise
        except Exception as e:
            db.session.rollback()
            raise ValidacaoError(f"Erro ao adicionar dependente: {str(e)}")
    
    def atualizar_dependente(
        self,
        dep_id: int,
        dados: Dict[str, Any],
        usuario_id: int
    ) -> Dependente:
        """
        Atualiza dados de um dependente.
        
        Args:
            dep_id: ID do dependente
            dados: Dicionário com dados para atualizar
            usuario_id: ID do usuário que está atualizando
        
        Returns:
            Dependente atualizado
        
        Raises:
            ValidacaoError: Se dependente não existir ou dados forem inválidos
        """
        try:
            dependente = Dependente.query.get(dep_id)
            if not dependente:
                raise ValidacaoError("Dependente não encontrado")
            
            ci = self.obter_por_id(dependente.colaborador_id)
            if ci and ci.is_deleted:
                raise ColaboradorExcluidoError(ci.id)
            
            # Registrar dados antigos
            dados_antigos = {
                'nome': dependente.nome,
                'cpf': dependente.cpf,
                'parentesco': dependente.parentesco,
                'data_nascimento': dependente.data_nascimento
            }
            
            # Atualizar dados
            if 'nome' in dados and dados['nome']:
                dependente.nome = dados['nome'].strip()
            
            if 'cpf' in dados:
                cpf_raw = dados['cpf'].strip() if dados['cpf'] else ''
                if cpf_raw:
                    cpf = clean_cpf(cpf_raw)
                    if cpf and cpf != dependente.cpf:
                        # Verificar se CPF já existe em outro dependente
                        existente = Dependente.query.filter(
                            Dependente.cpf == cpf,
                            Dependente.colaborador_id == dependente.colaborador_id,
                            Dependente.id != dep_id
                        ).first()
                        if existente:
                            raise ValidacaoError("Já existe um dependente com este CPF")
                        dependente.cpf = cpf
                else:
                    dependente.cpf = None
            
            if 'parentesco' in dados and dados['parentesco']:
                dependente.parentesco = dados['parentesco'].strip()
            
            if 'data_nascimento' in dados:
                from app.utils.validators import validate_date
                data = validate_date(dados['data_nascimento'])
                if data:
                    dependente.data_nascimento = data
            
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
                usuario = Usuario.query.get(usuario_id)
                historico = HistoricoCI(
                    colaborador_id=dependente.colaborador_id,
                    tipo_evento='ALTERACAO_DEPENDENTE',
                    descricao=f'Dados do dependente {dependente.nome} alterados',
                    data_evento=date.today(),
                    nc=ci.nc_atual if ci else None,
                    cod_empresa=ci.empresa_atual if ci else None,
                    dados_alterados=alteracoes
                )
                db.session.add(historico)
            
            db.session.commit()
            
            return dependente
            
        except Exception as e:
            db.session.rollback()
            raise ValidacaoError(f"Erro ao atualizar dependente: {str(e)}")
    
    def excluir_dependente(self, dep_id: int, usuario_id: int) -> None:
        """
        Exclui um dependente.
        
        Args:
            dep_id: ID do dependente
            usuario_id: ID do usuário que está excluindo
        
        Raises:
            ValidacaoError: Se dependente não existir
        """
        try:
            dependente = Dependente.query.get(dep_id)
            if not dependente:
                raise ValidacaoError("Dependente não encontrado")
            
            ci = self.obter_por_id(dependente.colaborador_id)
            if ci and ci.is_deleted:
                raise ColaboradorExcluidoError(ci.id)
            
            # Registrar histórico antes de excluir
            usuario = Usuario.query.get(usuario_id)
            historico = HistoricoCI(
                colaborador_id=dependente.colaborador_id,
                tipo_evento='EXCLUSAO_DEPENDENTE',
                descricao=f'Dependente {dependente.nome} excluído',
                data_evento=date.today(),
                nc=ci.nc_atual if ci else None,
                cod_empresa=ci.empresa_atual if ci else None,
                dados_alterados={
                    'dependente_nome': dependente.nome,
                    'dependente_cpf': dependente.cpf,
                    'parentesco': dependente.parentesco,
                    'usuario': usuario.nome if usuario else 'Sistema'
                }
            )
            db.session.add(historico)
            
            # Excluir dependente
            db.session.delete(dependente)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise ValidacaoError(f"Erro ao excluir dependente: {str(e)}")
    
    # ============================================================================
    # MÉTODOS DE EXCLUSÃO E RESTAURAÇÃO
    # ============================================================================
    
    def excluir_colaborador(
        self,
        ci_id: int,
        usuario_id: int,
        motivo: str = None
    ) -> None:
        """
        Exclui um colaborador logicamente (soft delete).
        
        Args:
            ci_id: ID do colaborador
            usuario_id: ID do usuário que está excluindo
            motivo: Motivo da exclusão
        
        Raises:
            CINaoEncontradoError: Se colaborador não existir
            ValidacaoError: Se colaborador já estiver excluído
        """
        try:
            ci = self.obter_por_id(ci_id)
            if not ci:
                raise CINaoEncontradoError(ci_id)
            
            if ci.is_deleted:
                raise ValidacaoError("Colaborador já está excluído")
            
            # Excluir colaborador
            ci.excluir_soft(
                usuario_id=usuario_id,
                motivo=motivo or 'Exclusão manual'
            )
            
            # Registrar histórico
            usuario = Usuario.query.get(usuario_id)
            historico = HistoricoCI(
                colaborador_id=ci_id,
                tipo_evento='EXCLUSAO',
                descricao=f'CI excluído logicamente por {usuario.nome if usuario else "Sistema"}',
                data_evento=date.today(),
                nc=ci.nc_atual,
                cod_empresa=ci.empresa_atual,
                dados_alterados={
                    'nome': ci.nome,
                    'cpf': ci.cpf,
                    'motivo': motivo,
                    'usuario': usuario.nome if usuario else 'Sistema',
                    'data_exclusao': datetime.now().isoformat()
                }
            )
            db.session.add(historico)
            
            db.session.commit()
            
        except (CINaoEncontradoError, ValidacaoError):
            raise
        except Exception as e:
            db.session.rollback()
            raise ValidacaoError(f"Erro ao excluir colaborador: {str(e)}")
    
    def restaurar_colaborador(
        self,
        ci_id: int,
        usuario_id: int
    ) -> bool:
        """
        Restaura um colaborador excluído logicamente.
        
        Args:
            ci_id: ID do colaborador
            usuario_id: ID do usuário que está restaurando
        
        Returns:
            True se restaurado com sucesso, False caso contrário
        
        Raises:
            CINaoEncontradoError: Se colaborador não existir
        """
        try:
            ci = self.obter_por_id(ci_id)
            if not ci:
                raise CINaoEncontradoError(ci_id)
            
            if not ci.is_deleted:
                return False
            
            # Restaurar colaborador
            sucesso = ci.restaurar(usuario_id)
            
            if sucesso:
                # Registrar histórico
                usuario = Usuario.query.get(usuario_id)
                historico = HistoricoCI(
                    colaborador_id=ci_id,
                    tipo_evento='RESTAURACAO',
                    descricao=f'CI restaurado por {usuario.nome if usuario else "Sistema"}',
                    data_evento=date.today(),
                    nc=ci.nc_atual,
                    cod_empresa=ci.empresa_atual,
                    dados_alterados={
                        'nome': ci.nome,
                        'cpf': ci.cpf,
                        'usuario': usuario.nome if usuario else 'Sistema',
                        'data_restauracao': datetime.now().isoformat()
                    }
                )
                db.session.add(historico)
                
                db.session.commit()
            
            return sucesso
            
        except (CINaoEncontradoError):
            raise
        except Exception as e:
            db.session.rollback()
            raise ValidacaoError(f"Erro ao restaurar colaborador: {str(e)}")
    
    # ============================================================================
    # MÉTODOS DE ESTATÍSTICAS
    # ============================================================================
    
    def obter_estatisticas(self, mostrar_excluidos: bool = False) -> Dict[str, Any]:
        """
        Obtém estatísticas dos colaboradores.
        
        Args:
            mostrar_excluidos: Incluir estatísticas de excluídos
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            estatisticas = {}
            
            # Query base
            query = ColaboradorInterno.query
            if not mostrar_excluidos:
                query = query.filter_by(is_deleted=False)
            
            # Totais
            estatisticas['total'] = query.count()
            
            # Contagem por status
            if not mostrar_excluidos:
                subquery = db.session.query(NumeroCadastro.colaborador_id).filter(
                    NumeroCadastro.ativo == True
                ).subquery()
                
                ativos_count = query.filter(
                    ColaboradorInterno.id.in_(subquery)
                ).count()
                
                estatisticas['ativos'] = ativos_count
                estatisticas['inativos'] = estatisticas['total'] - ativos_count
                estatisticas['excluidos'] = 0
            else:
                estatisticas['excluidos'] = query.filter_by(is_deleted=True).count()
                estatisticas['ativos'] = query.filter_by(is_deleted=False).count()
                estatisticas['inativos'] = 0
            
            # Distribuição por empresa
            distrib_empresa = db.session.query(
                NumeroCadastro.cod_empresa,
                func.count(NumeroCadastro.id).label('total')
            ).filter(
                NumeroCadastro.ativo == True
            ).group_by(
                NumeroCadastro.cod_empresa
            ).all()
            
            estatisticas['distribuicao_empresa'] = [
                {'empresa': emp, 'total': total}
                for emp, total in distrib_empresa
            ]
            
            # Planos
            estatisticas['planos_saude'] = PlanoSaude.query.filter_by(ativo=True).count()
            estatisticas['planos_odonto'] = PlanoOdontologico.query.filter_by(ativo=True).count()
            
            # Dependentes
            estatisticas['dependentes'] = Dependente.query.count()
            
            # Médias
            if estatisticas['ativos'] > 0:
                estatisticas['media_dependentes'] = round(
                    estatisticas['dependentes'] / estatisticas['ativos'], 2
                )
            else:
                estatisticas['media_dependentes'] = 0
            
            return estatisticas
            
        except Exception as e:
            raise ValidacaoError(f"Erro ao obter estatísticas: {str(e)}")
    
    # ============================================================================
    # MÉTODOS DE EXPORTAÇÃO
    # ============================================================================
    
    def exportar_colaborador_csv(self, ci: ColaboradorInterno) -> str:
        """
        Exporta dados de um colaborador para CSV.
        
        Args:
            ci: ColaboradorInterno
        
        Returns:
            String com conteúdo CSV
        """
        try:
            output = io.StringIO()
            writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
            
            # Cabeçalho
            writer.writerow(['SEÇÃO', 'CAMPO', 'VALOR'])
            
            # Dados básicos
            writer.writerow(['DADOS BÁSICOS', 'ID', ci.id])
            writer.writerow(['DADOS BÁSICOS', 'Nome', ci.nome])
            writer.writerow(['DADOS BÁSICOS', 'CPF', ci.cpf])
            writer.writerow(['DADOS BÁSICOS', 'Email', ci.email or ''])
            writer.writerow(['DADOS BÁSICOS', 'Telefone', ci.telefone or ''])
            writer.writerow(['DADOS BÁSICOS', 'Data Admissão', 
                           ci.data_admissao.strftime('%d/%m/%Y') if ci.data_admissao else ''])
            writer.writerow(['DADOS BÁSICOS', 'Data Nascimento',
                           ci.data_nascimento.strftime('%d/%m/%Y') if ci.data_nascimento else ''])
            writer.writerow(['DADOS BÁSICOS', 'Idade', ci.idade or ''])
            writer.writerow(['DADOS BÁSICOS', 'Tempo Empresa (meses)', ci.tempo_empresa or ''])
            
            # NC atual
            nc_ativo = ci.nc_ativo
            if nc_ativo:
                writer.writerow(['NC ATUAL', 'NC', nc_ativo.nc])
                writer.writerow(['NC ATUAL', 'Empresa', nc_ativo.cod_empresa])
                writer.writerow(['NC ATUAL', 'Data Início', 
                               nc_ativo.data_inicio.strftime('%d/%m/%Y')])
                writer.writerow(['NC ATUAL', 'Status', 'ATIVO' if nc_ativo.ativo else 'INATIVO'])
            
            # Histórico de NCs
            ncs = self.obter_historico_nc(ci.id)
            for i, nc in enumerate(ncs, 1):
                writer.writerow([f'NC HISTÓRICO #{i}', 'NC', nc.nc])
                writer.writerow([f'NC HISTÓRICO #{i}', 'Empresa', nc.cod_empresa])
                writer.writerow([f'NC HISTÓRICO #{i}', 'Data Início', 
                               nc.data_inicio.strftime('%d/%m/%Y')])
                writer.writerow([f'NC HISTÓRICO #{i}', 'Data Fim', 
                               nc.data_fim.strftime('%d/%m/%Y') if nc.data_fim else ''])
                writer.writerow([f'NC HISTÓRICO #{i}', 'Status', 'ATIVO' if nc.ativo else 'INATIVO'])
                writer.writerow([f'NC HISTÓRICO #{i}', 'Motivo', nc.motivo_mudanca or ''])
            
            # Dependentes
            dependentes = ci.dependentes_cache if hasattr(ci, 'dependentes_cache') else []
            for i, dep in enumerate(dependentes, 1):
                writer.writerow([f'DEPENDENTE #{i}', 'Nome', dep.nome])
                writer.writerow([f'DEPENDENTE #{i}', 'CPF', dep.cpf or ''])
                writer.writerow([f'DEPENDENTE #{i}', 'Parentesco', dep.parentesco or ''])
                writer.writerow([f'DEPENDENTE #{i}', 'Data Nascimento',
                               dep.data_nascimento.strftime('%d/%m/%Y') if dep.data_nascimento else ''])
                writer.writerow([f'DEPENDENTE #{i}', 'Idade', dep.idade or ''])
                writer.writerow([f'DEPENDENTE #{i}', 'NC Vínculo', dep.nc_vinculo])
            
            # Planos de Saúde
            planos_saude = ci.planos_saude_cache if hasattr(ci, 'planos_saude_cache') else []
            for i, plano in enumerate(planos_saude, 1):
                writer.writerow([f'PLANO SAÚDE #{i}', 'Operadora', plano.operadora])
                writer.writerow([f'PLANO SAÚDE #{i}', 'Plano', plano.plano])
                writer.writerow([f'PLANO SAÚDE #{i}', 'Tipo', plano.tipo])
                writer.writerow([f'PLANO SAÚDE #{i}', 'Contrato', plano.contrato or ''])
                writer.writerow([f'PLANO SAÚDE #{i}', 'Valor', 
                               f'R$ {float(plano.valor):.2f}' if plano.valor else ''])
                writer.writerow([f'PLANO SAÚDE #{i}', 'Data Início',
                               plano.data_inicio.strftime('%d/%m/%Y')])
                writer.writerow([f'PLANO SAÚDE #{i}', 'Data Fim',
                               plano.data_fim.strftime('%d/%m/%Y') if plano.data_fim else ''])
                writer.writerow([f'PLANO SAÚDE #{i}', 'Status', 'ATIVO' if plano.ativo else 'INATIVO'])
            
            # Planos Odontológicos
            planos_odonto = ci.planos_odonto_cache if hasattr(ci, 'planos_odonto_cache') else []
            for i, plano in enumerate(planos_odonto, 1):
                writer.writerow([f'PLANO ODONTO #{i}', 'Operadora', plano.operadora])
                writer.writerow([f'PLANO ODONTO #{i}', 'Plano', plano.plano])
                writer.writerow([f'PLANO ODONTO #{i}', 'Valor', 
                               f'R$ {float(plano.valor):.2f}' if plano.valor else ''])
                writer.writerow([f'PLANO ODONTO #{i}', 'Data Início',
                               plano.data_inicio.strftime('%d/%m/%Y')])
                writer.writerow([f'PLANO ODONTO #{i}', 'Data Fim',
                               plano.data_fim.strftime('%d/%m/%Y') if plano.data_fim else ''])
                writer.writerow([f'PLANO ODONTO #{i}', 'Status', 'ATIVO' if plano.ativo else 'INATIVO'])
                writer.writerow([f'PLANO ODONTO #{i}', 'Unidade', plano.unidade or ''])
            
            return output.getvalue()
            
        except Exception as e:
            raise ValidacaoError(f"Erro ao exportar colaborador: {str(e)}")
    
    def exportar_todos_csv(self, apenas_ativos: bool = True) -> str:
        """
        Exporta todos os colaboradores para CSV.
        
        Args:
            apenas_ativos: Exportar apenas colaboradores ativos
        
        Returns:
            String com conteúdo CSV
        """
        try:
            output = io.StringIO()
            writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
            
            # Cabeçalho
            writer.writerow([
                'ID', 'Nome', 'CPF', 'Email', 'Telefone',
                'Data Admissão', 'Data Nascimento', 'Idade',
                'NC Atual', 'Empresa Atual', 'Status NC',
                'Total Dependentes', 'Total Planos Saúde', 'Total Planos Odonto',
                'Esta Ativo', 'Excluído', 'Data Criação'
            ])
            
            # Buscar colaboradores
            query = ColaboradorInterno.query
            if apenas_ativos:
                query = query.filter_by(is_deleted=False)
            
            cis = query.order_by(ColaboradorInterno.nome).all()
            
            # Dados
            for ci in cis:
                nc_ativo = ci.nc_ativo
                
                writer.writerow([
                    ci.id,
                    ci.nome,
                    ci.cpf,
                    ci.email or '',
                    ci.telefone or '',
                    ci.data_admissao.strftime('%d/%m/%Y') if ci.data_admissao else '',
                    ci.data_nascimento.strftime('%d/%m/%Y') if ci.data_nascimento else '',
                    ci.idade or '',
                    nc_ativo.nc if nc_ativo else '',
                    nc_ativo.cod_empresa if nc_ativo else '',
                    'ATIVO' if nc_ativo and nc_ativo.ativo else 'INATIVO',
                    ci.total_dependentes,
                    ci.total_planos_saude,
                    ci.total_planos_odonto,
                    'SIM' if ci.esta_ativo else 'NÃO',
                    'SIM' if ci.is_deleted else 'NÃO',
                    ci.created_at.strftime('%d/%m/%Y %H:%M') if ci.created_at else ''
                ])
            
            return output.getvalue()
            
        except Exception as e:
            raise ValidacaoError(f"Erro ao exportar todos os colaboradores: {str(e)}")
    
    # ============================================================================
    # MÉTODOS AUXILIARES
    # ============================================================================
    
    def _limpar_cache(self) -> None:
        """Limpa o cache interno do serviço."""
        self._cache.clear()
    
    def _formatar_cpf(self, cpf: str) -> str:
        """Formata CPF para exibição."""
        if not cpf or len(cpf) != 11:
            return cpf
        return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'
    
    def _calcular_idade(self, data_nascimento: date) -> Optional[int]:
        """Calcula idade a partir da data de nascimento."""
        if not data_nascimento:
            return None
        
        hoje = date.today()
        idade = hoje.year - data_nascimento.year
        
        # Ajustar se ainda não fez aniversário este ano
        if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
            idade -= 1
        
        return idade
    
    def _calcular_tempo_empresa(self, data_admissao: date) -> Optional[int]:
        """Calcula tempo na empresa em meses."""
        if not data_admissao:
            return None
        
        hoje = date.today()
        return (hoje.year - data_admissao.year) * 12 + (hoje.month - data_admissao.month)

# ============================================================================
# INSTÂNCIA SINGLETON
# ============================================================================

# Criar instância única do serviço para uso global
ci_service = CIService()

# Exportar classes e instâncias
__all__ = ['CIService', 'ci_service']
