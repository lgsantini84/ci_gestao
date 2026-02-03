"""
Serviço para gerenciamento de alertas do sistema.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import func, desc, asc, and_, or_
from sqlalchemy.orm import contains_eager

from app import db
from app.models import (
    Alerta, ColaboradorInterno, NumeroCadastro,
    PlanoSaude, PlanoOdontologico, Dependente,
    AtendimentoCoparticipacao, ImportacaoLog
)
from app.utils.data_utils import to_brasilia
from app.exceptions import AlertaError, ValidacaoError

logger = logging.getLogger(__name__)


class AlertService:
    """Serviço para gerenciamento de alertas."""
    
    def __init__(self):
        self.alert_types = {
            'CI_SEM_NC': {
                'descricao': 'Colaborador sem NC ativo',
                'gravidade': 'MEDIA',
                'acao_recomendada': 'Verificar se o colaborador possui um NC ativo vinculado'
            },
            'NC_DUPLICADO': {
                'descricao': 'NC duplicado em uso',
                'gravidade': 'ALTA',
                'acao_recomendada': 'Verificar qual colaborador está com o NC correto'
            },
            'CPF_DUPLICADO': {
                'descricao': 'CPF duplicado no sistema',
                'gravidade': 'ALTA',
                'acao_recomendada': 'Verificar dados dos colaboradores com CPF duplicado'
            },
            'PLANO_VENCIDO': {
                'descricao': 'Plano de saúde vencido',
                'gravidade': 'MEDIA',
                'acao_recomendada': 'Verificar renovação do plano'
            },
            'ATENDIMENTO_SEM_PLANO': {
                'descricao': 'Atendimento sem plano vinculado',
                'gravidade': 'BAIXA',
                'acao_recomendada': 'Verificar vínculo do atendimento com plano'
            },
            'DEPENDENTE_SEM_CPF': {
                'descricao': 'Dependente sem CPF cadastrado',
                'gravidade': 'BAIXA',
                'acao_recomendada': 'Solicitar CPF do dependente'
            },
            'IMPORTACAO_ERRO': {
                'descricao': 'Erro em importação recente',
                'gravidade': 'ALTA',
                'acao_recomendada': 'Verificar arquivo de importação'
            },
            'SISTEMA': {
                'descricao': 'Erro no sistema',
                'gravidade': 'CRITICA',
                'acao_recomendada': 'Verificar logs do sistema'
            }
        }
    
    # ============================================================================
    # MÉTODOS DE BUSCA E CONSULTA
    # ============================================================================
    
    def buscar_alertas(
        self,
        tipo: str = '',
        gravidade: str = '',
        resolvido: Optional[bool] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        limite: int = 100,
        ordenar_por: str = 'data_alerta',
        ordem: str = 'desc'
    ) -> List[Alerta]:
        """
        Busca alertas com filtros.
        
        Args:
            tipo: Tipo de alerta
            gravidade: Nível de gravidade
            resolvido: True para resolvidos, False para não resolvidos, None para ambos
            data_inicio: Data inicial
            data_fim: Data final
            limite: Limite de resultados
            ordenar_por: Campo para ordenação
            ordem: 'asc' ou 'desc'
        
        Returns:
            Lista de alertas
        """
        try:
            query = Alerta.query
            
            # Aplicar filtros
            if tipo:
                query = query.filter(Alerta.tipo == tipo)
            
            if gravidade:
                query = query.filter(Alerta.gravidade == gravidade)
            
            if resolvido is not None:
                query = query.filter(Alerta.resolvido == resolvido)
            
            if data_inicio:
                query = query.filter(Alerta.data_alerta >= data_inicio)
            
            if data_fim:
                # Adicionar um dia para incluir a data_fim completa
                data_fim_completa = data_fim + timedelta(days=1)
                query = query.filter(Alerta.data_alerta < data_fim_completa)
            
            # Ordenação
            order_column = getattr(Alerta, ordenar_por, Alerta.data_alerta)
            if ordem.lower() == 'asc':
                query = query.order_by(asc(order_column))
            else:
                query = query.order_by(desc(order_column))
            
            # Limite
            if limite > 0:
                query = query.limit(limite)
            
            return query.all()
            
        except Exception as e:
            raise AlertaError(f"Erro ao buscar alertas: {str(e)}")
    
    def obter_alerta_por_id(self, alerta_id: int) -> Optional[Alerta]:
        """
        Obtém um alerta por ID.
        
        Args:
            alerta_id: ID do alerta
        
        Returns:
            Alerta ou None
        """
        try:
            return Alerta.query.get(alerta_id)
        except Exception as e:
            raise AlertaError(f"Erro ao obter alerta: {str(e)}")
    
    def obter_alertas_recentes(
        self,
        limite: int = 10,
        apenas_nao_resolvidos: bool = True
    ) -> List[Alerta]:
        """
        Obtém alertas recentes.
        
        Args:
            limite: Limite de resultados
            apenas_nao_resolvidos: Apenas alertas não resolvidos
        
        Returns:
            Lista de alertas recentes
        """
        try:
            query = Alerta.query
            
            if apenas_nao_resolvidos:
                query = query.filter_by(resolvido=False)
            
            return query.order_by(
                desc(Alerta.data_alerta)
            ).limit(limite).all()
            
        except Exception as e:
            raise AlertaError(f"Erro ao obter alertas recentes: {str(e)}")
    
    # ============================================================================
    # MÉTODOS DE CRIAÇÃO
    # ============================================================================
    
    def criar_alerta(
        self,
        tipo: str,
        descricao: str,
        gravidade: str = None,
        acao_recomendada: str = None,
        dados_relacionados: Dict = None,
        evitar_duplicados: bool = True
    ) -> Alerta:
        """
        Cria um novo alerta.
        
        Args:
            tipo: Tipo de alerta
            descricao: Descrição do alerta
            gravidade: Gravidade (CRITICA, ALTA, MEDIA, BAIXA)
            acao_recomendada: Ação recomendada
            dados_relacionados: Dados relacionados
            evitar_duplicados: Evitar alertas duplicados no mesmo dia
        
        Returns:
            Alerta criado
        """
        try:
            # Validar tipo
            if tipo not in self.alert_types:
                logger.warning(f"Tipo de alerta desconhecido: {tipo}")
            
            # Definir gravidade padrão
            if not gravidade:
                gravidade = self.alert_types.get(tipo, {}).get('gravidade', 'MEDIA')
            
            # Definir ação recomendada padrão
            if not acao_recomendada:
                acao_recomendada = self.alert_types.get(tipo, {}).get('acao_recomendada', '')
            
            # Evitar alertas duplicados
            if evitar_duplicados:
                hoje = datetime.now().date()
                inicio_dia = datetime(hoje.year, hoje.month, hoje.day)
                fim_dia = inicio_dia + timedelta(days=1)
                
                similar = Alerta.query.filter(
                    Alerta.tipo == tipo,
                    Alerta.descricao == descricao,
                    Alerta.data_alerta >= inicio_dia,
                    Alerta.data_alerta < fim_dia,
                    Alerta.resolvido == False
                ).first()
                
                if similar:
                    logger.info(f"Alerta duplicado ignorado: {tipo} - {descricao}")
                    return similar
            
            # Criar alerta
            alerta = Alerta(
                tipo=tipo,
                descricao=descricao,
                gravidade=gravidade,
                acao_recomendada=acao_recomendada,
                dados_relacionados=dados_relacionados or {},
                resolvido=False,
                data_alerta=datetime.utcnow()
            )
            
            db.session.add(alerta)
            db.session.commit()
            
            logger.info(f"Alerta criado: {tipo} - {descricao}")
            return alerta
            
        except Exception as e:
            db.session.rollback()
            raise AlertaError(f"Erro ao criar alerta: {str(e)}")
    
    def criar_alerta_ci_sem_nc(self, colaborador: ColaboradorInterno) -> Optional[Alerta]:
        """
        Cria alerta para colaborador sem NC ativo.
        
        Args:
            colaborador: ColaboradorInterno
        
        Returns:
            Alerta criado ou None
        """
        try:
            if colaborador.is_deleted:
                return None
            
            # Verificar se tem NC ativo
            if colaborador.nc_ativo:
                return None
            
            # Verificar se já existe alerta não resolvido
            alerta_existente = Alerta.query.filter_by(
                tipo='CI_SEM_NC',
                resolvido=False
            ).filter(
                Alerta.dados_relacionados['colaborador_id'].astext == str(colaborador.id)
            ).first()
            
            if alerta_existente:
                return alerta_existente
            
            # Criar alerta
            return self.criar_alerta(
                tipo='CI_SEM_NC',
                descricao=f'Colaborador {colaborador.nome} (ID: {colaborador.id}) não possui NC ativo',
                gravidade='MEDIA',
                acao_recomendada='Verificar e atribuir um NC ativo para o colaborador',
                dados_relacionados={
                    'colaborador_id': colaborador.id,
                    'colaborador_nome': colaborador.nome,
                    'colaborador_cpf': colaborador.cpf
                }
            )
            
        except Exception as e:
            logger.error(f"Erro ao criar alerta CI_SEM_NC: {str(e)}")
            return None
    
    def criar_alerta_nc_duplicado(
        self,
        nc: str,
        ci_atual: ColaboradorInterno,
        ci_duplicado: ColaboradorInterno
    ) -> Optional[Alerta]:
        """
        Cria alerta para NC duplicado.
        
        Args:
            nc: Número de cadastro
            ci_atual: Colaborador atual com o NC
            ci_duplicado: Colaborador duplicado com o mesmo NC
        
        Returns:
            Alerta criado ou None
        """
        try:
            # Verificar se já existe alerta não resolvido
            alerta_existente = Alerta.query.filter_by(
                tipo='NC_DUPLICADO',
                resolvido=False
            ).filter(
                Alerta.dados_relacionados['nc'].astext == nc
            ).first()
            
            if alerta_existente:
                return alerta_existente
            
            # Criar alerta
            return self.criar_alerta(
                tipo='NC_DUPLICADO',
                descricao=f'NC {nc} está em uso por múltiplos colaboradores: {ci_atual.nome} (ID: {ci_atual.id}) e {ci_duplicado.nome} (ID: {ci_duplicado.id})',
                gravidade='ALTA',
                acao_recomendada='Verificar qual colaborador deve manter o NC e corrigir o outro',
                dados_relacionados={
                    'nc': nc,
                    'colaboradores': [
                        {
                            'id': ci_atual.id,
                            'nome': ci_atual.nome,
                            'cpf': ci_atual.cpf,
                            'empresa_atual': ci_atual.empresa_atual
                        },
                        {
                            'id': ci_duplicado.id,
                            'nome': ci_duplicado.nome,
                            'cpf': ci_duplicado.cpf,
                            'empresa_atual': ci_duplicado.empresa_atual
                        }
                    ]
                }
            )
            
        except Exception as e:
            logger.error(f"Erro ao criar alerta NC_DUPLICADO: {str(e)}")
            return None
    
    def criar_alerta_cpf_duplicado(
        self,
        cpf: str,
        ci_atual: ColaboradorInterno,
        ci_duplicado: ColaboradorInterno
    ) -> Optional[Alerta]:
        """
        Cria alerta para CPF duplicado.
        
        Args:
            cpf: CPF duplicado
            ci_atual: Colaborador atual com o CPF
            ci_duplicado: Colaborador duplicado com o mesmo CPF
        
        Returns:
            Alerta criado ou None
        """
        try:
            # Verificar se já existe alerta não resolvido
            alerta_existente = Alerta.query.filter_by(
                tipo='CPF_DUPLICADO',
                resolvido=False
            ).filter(
                Alerta.dados_relacionados['cpf'].astext == cpf
            ).first()
            
            if alerta_existente:
                return alerta_existente
            
            # Criar alerta
            return self.criar_alerta(
                tipo='CPF_DUPLICADO',
                descricao=f'CPF {cpf} está cadastrado para múltiplos colaboradores: {ci_atual.nome} (ID: {ci_atual.id}) e {ci_duplicado.nome} (ID: {ci_duplicado.id})',
                gravidade='ALTA',
                acao_recomendada='Verificar dados e corrigir o CPF duplicado',
                dados_relacionados={
                    'cpf': cpf,
                    'colaboradores': [
                        {
                            'id': ci_atual.id,
                            'nome': ci_atual.nome,
                            'nc_atual': ci_atual.nc_atual,
                            'empresa_atual': ci_atual.empresa_atual
                        },
                        {
                            'id': ci_duplicado.id,
                            'nome': ci_duplicado.nome,
                            'nc_atual': ci_duplicado.nc_atual,
                            'empresa_atual': ci_duplicado.empresa_atual
                        }
                    ]
                }
            )
            
        except Exception as e:
            logger.error(f"Erro ao criar alerta CPF_DUPLICADO: {str(e)}")
            return None
    
    def criar_alerta_plano_vencido(self, plano: PlanoSaude) -> Optional[Alerta]:
        """
        Cria alerta para plano de saúde vencido.
        
        Args:
            plano: Plano de saúde vencido
        
        Returns:
            Alerta criado ou None
        """
        try:
            if not plano.data_fim:
                return None
            
            # Verificar se plano está vencido há mais de 30 dias
            dias_vencido = (datetime.now().date() - plano.data_fim).days
            if dias_vencido <= 0:
                return None
            
            # Verificar se já existe alerta não resolvido
            alerta_existente = Alerta.query.filter_by(
                tipo='PLANO_VENCIDO',
                resolvido=False
            ).filter(
                Alerta.dados_relacionados['plano_id'].astext == str(plano.id)
            ).first()
            
            if alerta_existente:
                return alerta_existente
            
            # Criar alerta
            return self.criar_alerta(
                tipo='PLANO_VENCIDO',
                descricao=f'Plano {plano.operadora} - {plano.plano} vencido há {dias_vencido} dias para {plano.colaborador.nome}',
                gravidade='MEDIA' if dias_vencido <= 30 else 'ALTA',
                acao_recomendada=f'{"Atualizar" if plano.ativo else "Renovar"} plano de saúde',
                dados_relacionados={
                    'plano_id': plano.id,
                    'colaborador_id': plano.colaborador_id,
                    'colaborador_nome': plano.colaborador.nome,
                    'operadora': plano.operadora,
                    'plano': plano.plano,
                    'data_fim': plano.data_fim.isoformat(),
                    'dias_vencido': dias_vencido,
                    'esta_ativo': plano.ativo
                }
            )
            
        except Exception as e:
            logger.error(f"Erro ao criar alerta PLANO_VENCIDO: {str(e)}")
            return None
    
    def criar_alerta_dependente_sem_cpf(self, dependente: Dependente) -> Optional[Alerta]:
        """
        Cria alerta para dependente sem CPF.
        
        Args:
            dependente: Dependente sem CPF
        
        Returns:
            Alerta criado ou None
        """
        try:
            if dependente.cpf:
                return None
            
            # Verificar se já existe alerta não resolvido
            alerta_existente = Alerta.query.filter_by(
                tipo='DEPENDENTE_SEM_CPF',
                resolvido=False
            ).filter(
                Alerta.dados_relacionados['dependente_id'].astext == str(dependente.id)
            ).first()
            
            if alerta_existente:
                return alerta_existente
            
            # Criar alerta
            return self.criar_alerta(
                tipo='DEPENDENTE_SEM_CPF',
                descricao=f'Dependente {dependente.nome} não possui CPF cadastrado',
                gravidade='BAIXA',
                acao_recomendada='Solicitar e cadastrar CPF do dependente',
                dados_relacionados={
                    'dependente_id': dependente.id,
                    'dependente_nome': dependente.nome,
                    'colaborador_id': dependente.colaborador_id,
                    'colaborador_nome': dependente.titular.nome if dependente.titular else None,
                    'parentesco': dependente.parentesco
                }
            )
            
        except Exception as e:
            logger.error(f"Erro ao criar alerta DEPENDENTE_SEM_CPF: {str(e)}")
            return None
    
    # ============================================================================
    # MÉTODOS DE VERIFICAÇÃO E SCAN
    # ============================================================================
    
    def scan_colaboradores_sem_nc(self) -> Tuple[int, List[Alerta]]:
        """
        Verifica colaboradores sem NC ativo.
        
        Returns:
            Tuple (total_encontrados, alertas_criados)
        """
        try:
            # Buscar colaboradores ativos sem NC ativo
            colaboradores = ColaboradorInterno.query.filter_by(
                is_deleted=False
            ).filter(
                ~ColaboradorInterno.id.in_(
                    db.session.query(NumeroCadastro.colaborador_id).filter_by(
                        ativo=True
                    )
                )
            ).all()
            
            alertas = []
            for ci in colaboradores:
                alerta = self.criar_alerta_ci_sem_nc(ci)
                if alerta:
                    alertas.append(alerta)
            
            return len(colaboradores), alertas
            
        except Exception as e:
            raise AlertaError(f"Erro no scan de colaboradores sem NC: {str(e)}")
    
    def scan_ncs_duplicados(self) -> Tuple[int, List[Alerta]]:
        """
        Verifica NCs duplicados.
        
        Returns:
            Tuple (total_encontrados, alertas_criados)
        """
        try:
            # Buscar NCs ativos duplicados
            from sqlalchemy import distinct
            
            subquery = db.session.query(
                NumeroCadastro.nc,
                func.count(NumeroCadastro.id).label('count')
            ).filter_by(
                ativo=True
            ).group_by(
                NumeroCadastro.nc
            ).having(
                func.count(NumeroCadastro.id) > 1
            ).subquery()
            
            ncs_duplicados = db.session.query(NumeroCadastro).join(
                subquery, NumeroCadastro.nc == subquery.c.nc
            ).filter_by(
                ativo=True
            ).order_by(
                NumeroCadastro.nc
            ).all()
            
            # Agrupar por NC
            nc_groups = {}
            for nc_obj in ncs_duplicados:
                if nc_obj.nc not in nc_groups:
                    nc_groups[nc_obj.nc] = []
                nc_groups[nc_obj.nc].append(nc_obj.colaborador)
            
            # Criar alertas para cada NC duplicado
            alertas = []
            for nc, colaboradores in nc_groups.items():
                if len(colaboradores) >= 2:
                    alerta = self.criar_alerta_nc_duplicado(
                        nc=nc,
                        ci_atual=colaboradores[0],
                        ci_duplicado=colaboradores[1]
                    )
                    if alerta:
                        alertas.append(alerta)
            
            return len(nc_groups), alertas
            
        except Exception as e:
            raise AlertaError(f"Erro no scan de NCs duplicados: {str(e)}")
    
    def scan_cpfs_duplicados(self) -> Tuple[int, List[Alerta]]:
        """
        Verifica CPFs duplicados.
        
        Returns:
            Tuple (total_encontrados, alertas_criados)
        """
        try:
            # Buscar CPFs duplicados
            from sqlalchemy import distinct
            
            subquery = db.session.query(
                ColaboradorInterno.cpf,
                func.count(ColaboradorInterno.id).label('count')
            ).filter_by(
                is_deleted=False
            ).filter(
                ColaboradorInterno.cpf.isnot(None)
            ).group_by(
                ColaboradorInterno.cpf
            ).having(
                func.count(ColaboradorInterno.id) > 1
            ).subquery()
            
            cps_duplicados = db.session.query(ColaboradorInterno).join(
                subquery, ColaboradorInterno.cpf == subquery.c.cpf
            ).filter_by(
                is_deleted=False
            ).order_by(
                ColaboradorInterno.cpf
            ).all()
            
            # Agrupar por CPF
            cpf_groups = {}
            for ci in cps_duplicados:
                if ci.cpf not in cpf_groups:
                    cpf_groups[ci.cpf] = []
                cpf_groups[ci.cpf].append(ci)
            
            # Criar alertas para cada CPF duplicado
            alertas = []
            for cpf, colaboradores in cpf_groups.items():
                if len(colaboradores) >= 2:
                    alerta = self.criar_alerta_cpf_duplicado(
                        cpf=cpf,
                        ci_atual=colaboradores[0],
                        ci_duplicado=colaboradores[1]
                    )
                    if alerta:
                        alertas.append(alerta)
            
            return len(cpf_groups), alertas
            
        except Exception as e:
            raise AlertaError(f"Erro no scan de CPFs duplicados: {str(e)}")
    
    def scan_planos_vencidos(self, dias_tolerancia: int = 30) -> Tuple[int, List[Alerta]]:
        """
        Verifica planos de saúde vencidos.
        
        Args:
            dias_tolerancia: Dias de tolerância após o vencimento
        
        Returns:
            Tuple (total_encontrados, alertas_criados)
        """
        try:
            data_limite = datetime.now().date() - timedelta(days=dias_tolerancia)
            
            # Buscar planos vencidos
            planos_vencidos = PlanoSaude.query.filter(
                PlanoSaude.data_fim.isnot(None),
                PlanoSaude.data_fim < data_limite,
                PlanoSaude.ativo == True
            ).all()
            
            alertas = []
            for plano in planos_vencidos:
                alerta = self.criar_alerta_plano_vencido(plano)
                if alerta:
                    alertas.append(alerta)
            
            return len(planos_vencidos), alertas
            
        except Exception as e:
            raise AlertaError(f"Erro no scan de planos vencidos: {str(e)}")
    
    def scan_dependentes_sem_cpf(self) -> Tuple[int, List[Alerta]]:
        """
        Verifica dependentes sem CPF.
        
        Returns:
            Tuple (total_encontrados, alertas_criados)
        """
        try:
            # Buscar dependentes sem CPF
            dependentes_sem_cpf = Dependente.query.filter(
                or_(
                    Dependente.cpf.is_(None),
                    Dependente.cpf == ''
                )
            ).all()
            
            alertas = []
            for dependente in dependentes_sem_cpf:
                alerta = self.criar_alerta_dependente_sem_cpf(dependente)
                if alerta:
                    alertas.append(alerta)
            
            return len(dependentes_sem_cpf), alertas
            
        except Exception as e:
            raise AlertaError(f"Erro no scan de dependentes sem CPF: {str(e)}")
    
    def scan_importacoes_com_erro(self, dias: int = 7) -> Tuple[int, List[Alerta]]:
        """
        Verifica importações com erro nos últimos dias.
        
        Args:
            dias: Número de dias para verificar
        
        Returns:
            Tuple (total_encontrados, alertas_criados)
        """
        try:
            data_limite = datetime.utcnow() - timedelta(days=dias)
            
            # Buscar importações com erro
            importacoes_erro = ImportacaoLog.query.filter(
                ImportacaoLog.status.in_(['ERRO', 'FALHA']),
                ImportacaoLog.data_importacao >= data_limite
            ).all()
            
            alertas = []
            for imp in importacoes_erro:
                # Verificar se já existe alerta não resolvido
                alerta_existente = Alerta.query.filter_by(
                    tipo='IMPORTACAO_ERRO',
                    resolvido=False
                ).filter(
                    Alerta.dados_relacionados['importacao_id'].astext == str(imp.id)
                ).first()
                
                if alerta_existente:
                    alertas.append(alerta_existente)
                    continue
                
                # Criar alerta
                alerta = self.criar_alerta(
                    tipo='IMPORTACAO_ERRO',
                    descricao=f'Importação {imp.tipo_importacao} falhou: {imp.detalhes[:100]}...',
                    gravidade='ALTA',
                    acao_recomendada='Verificar arquivo de importação e tentar novamente',
                    dados_relacionados={
                        'importacao_id': imp.id,
                        'tipo_importacao': imp.tipo_importacao,
                        'arquivo': imp.arquivo,
                        'erro': imp.detalhes,
                        'data_importacao': imp.data_importacao.isoformat()
                    }
                )
                if alerta:
                    alertas.append(alerta)
            
            return len(importacoes_erro), alertas
            
        except Exception as e:
            raise AlertaError(f"Erro no scan de importações com erro: {str(e)}")
    
    def executar_scan_completo(self) -> Dict[str, Any]:
        """
        Executa todos os scans de verificação.
        
        Returns:
            Dicionário com resultados de todos os scans
        """
        try:
            resultados = {
                'timestamp': datetime.utcnow().isoformat(),
                'scans': {}
            }
            
            # Executar cada scan
            scans = [
                ('colaboradores_sem_nc', self.scan_colaboradores_sem_nc),
                ('ncs_duplicados', self.scan_ncs_duplicados),
                ('cpfs_duplicados', self.scan_cpfs_duplicados),
                ('planos_vencidos', self.scan_planos_vencidos),
                ('dependentes_sem_cpf', self.scan_dependentes_sem_cpf),
                ('importacoes_erro', self.scan_importacoes_com_erro)
            ]
            
            total_alertas = 0
            
            for nome, scan_func in scans:
                try:
                    total, alertas = scan_func()
                    resultados['scans'][nome] = {
                        'total_encontrados': total,
                        'alertas_criados': len(alertas),
                        'status': 'SUCESSO'
                    }
                    total_alertas += len(alertas)
                except Exception as e:
                    logger.error(f"Erro no scan {nome}: {str(e)}")
                    resultados['scans'][nome] = {
                        'total_encontrados': 0,
                        'alertas_criados': 0,
                        'status': 'ERRO',
                        'erro': str(e)
                    }
            
            resultados['total_alertas_criados'] = total_alertas
            resultados['status_geral'] = 'SUCESSO' if total_alertas > 0 else 'SEM_ALERTAS'
            
            # Criar alerta do scan se houver muitos alertas
            if total_alertas >= 10:
                self.criar_alerta(
                    tipo='SISTEMA',
                    descricao=f'Scan completo detectou {total_alertas} alertas pendentes',
                    gravidade='MEDIA',
                    acao_recomendada='Revisar alertas do sistema'
                )
            
            return resultados
            
        except Exception as e:
            raise AlertaError(f"Erro no scan completo: {str(e)}")
    
    # ============================================================================
    # MÉTODOS DE RESOLUÇÃO E MANUTENÇÃO
    # ============================================================================
    
    def resolver_alerta(self, alerta_id: int, observacao: str = None) -> Optional[Alerta]:
        """
        Marca um alerta como resolvido.
        
        Args:
            alerta_id: ID do alerta
            observacao: Observação adicional
        
        Returns:
            Alerta resolvido ou None
        """
        try:
            alerta = self.obter_alerta_por_id(alerta_id)
            if not alerta:
                raise ValidacaoError(f"Alerta {alerta_id} não encontrado")
            
            if alerta.resolvido:
                return alerta
            
            # Adicionar observação se fornecida
            if observacao:
                alerta.descricao = f"{alerta.descricao}\n\n--- RESOLUÇÃO ---\n{observacao}"
            
            alerta.resolver()
            db.session.commit()
            
            logger.info(f"Alerta {alerta_id} resolvido")
            return alerta
            
        except Exception as e:
            db.session.rollback()
            raise AlertaError(f"Erro ao resolver alerta: {str(e)}")
    
    def reabrir_alerta(self, alerta_id: int, motivo: str = None) -> Optional[Alerta]:
        """
        Reabre um alerta resolvido.
        
        Args:
            alerta_id: ID do alerta
            motivo: Motivo da reabertura
        
        Returns:
            Alerta reaberto ou None
        """
        try:
            alerta = self.obter_alerta_por_id(alerta_id)
            if not alerta:
                raise ValidacaoError(f"Alerta {alerta_id} não encontrado")
            
            if not alerta.resolvido:
                return alerta
            
            # Adicionar motivo se fornecido
            if motivo:
                alerta.descricao = f"{alerta.descricao}\n\n--- REABERTURA ---\n{motivo}"
            
            alerta.reabrir()
            db.session.commit()
            
            logger.info(f"Alerta {alerta_id} reaberto")
            return alerta
            
        except Exception as e:
            db.session.rollback()
            raise AlertaError(f"Erro ao reabrir alerta: {str(e)}")
    
    def excluir_alerta(self, alerta_id: int) -> bool:
        """
        Exclui um alerta.
        
        Args:
            alerta_id: ID do alerta
        
        Returns:
            True se excluído com sucesso
        """
        try:
            alerta = self.obter_alerta_por_id(alerta_id)
            if not alerta:
                return False
            
            db.session.delete(alerta)
            db.session.commit()
            
            logger.info(f"Alerta {alerta_id} excluído")
            return True
            
        except Exception as e:
            db.session.rollback()
            raise AlertaError(f"Erro ao excluir alerta: {str(e)}")
    
    def limpar_alertas_resolvidos(self, dias: int = 30) -> int:
        """
        Remove alertas resolvidos antigos.
        
        Args:
            dias: Remover alertas resolvidos há mais de X dias
        
        Returns:
            Número de alertas removidos
        """
        try:
            data_limite = datetime.utcnow() - timedelta(days=dias)
            
            # Contar antes de excluir
            total = Alerta.query.filter_by(resolvido=True)\
                .filter(Alerta.data_resolucao < data_limite)\
                .count()
            
            # Excluir
            Alerta.query.filter_by(resolvido=True)\
                .filter(Alerta.data_resolucao < data_limite)\
                .delete(synchronize_session=False)
            
            db.session.commit()
            
            logger.info(f"{total} alertas resolvidos removidos (mais de {dias} dias)")
            return total
            
        except Exception as e:
            db.session.rollback()
            raise AlertaError(f"Erro ao limpar alertas resolvidos: {str(e)}")
    
    # ============================================================================
    # MÉTODOS DE ESTATÍSTICAS
    # ============================================================================
    
    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas de alertas.
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            estatisticas = {}
            
            # Totais
            estatisticas['total'] = Alerta.query.count()
            estatisticas['abertos'] = Alerta.query.filter_by(resolvido=False).count()
            estatisticas['resolvidos'] = Alerta.query.filter_by(resolvido=True).count()
            
            # Por gravidade
            for gravidade in ['CRITICA', 'ALTA', 'MEDIA', 'BAIXA']:
                estatisticas[f'{gravidade.lower()}_abertos'] = Alerta.query.filter_by(
                    gravidade=gravidade,
                    resolvido=False
                ).count()
                estatisticas[f'{gravidade.lower()}_total'] = Alerta.query.filter_by(
                    gravidade=gravidade
                ).count()
            
            # Por tipo
            tipos = db.session.query(
                Alerta.tipo,
                func.count(Alerta.id).label('total')
            ).filter_by(resolvido=False).group_by(Alerta.tipo).all()
            
            estatisticas['por_tipo'] = [
                {'tipo': tipo, 'total': total}
                for tipo, total in tipos
            ]
            
            # Alertas recentes (últimos 7 dias)
            data_limite = datetime.utcnow() - timedelta(days=7)
            estatisticas['recentes_7_dias'] = Alerta.query.filter(
                Alerta.data_alerta >= data_limite
            ).count()
            
            # Média de resolução
            alertas_resolvidos = Alerta.query.filter_by(resolvido=True)\
                .filter(Alerta.data_resolucao.isnot(None))\
                .all()
            
            if alertas_resolvidos:
                tempos = []
                for a in alertas_resolvidos:
                    if a.data_resolucao and a.data_alerta:
                        tempo = (a.data_resolucao - a.data_alerta).total_seconds() / 86400  # em dias
                        tempos.append(tempo)
                
                if tempos:
                    estatisticas['media_resolucao_dias'] = round(sum(tempos) / len(tempos), 2)
                    estatisticas['max_resolucao_dias'] = round(max(tempos), 2)
                    estatisticas['min_resolucao_dias'] = round(min(tempos), 2)
            
            return estatisticas
            
        except Exception as e:
            raise AlertaError(f"Erro ao obter estatísticas: {str(e)}")
    
    def obter_tendencias(self, dias: int = 30) -> Dict[str, Any]:
        """
        Obtém tendências de alertas.
        
        Args:
            dias: Número de dias para análise
        
        Returns:
            Dicionário com tendências
        """
        try:
            data_inicio = datetime.utcnow() - timedelta(days=dias)
            
            # Query para alertas por dia
            alertas_por_dia = db.session.query(
                func.date(Alerta.data_alerta).label('data'),
                func.count(Alerta.id).label('total'),
                func.sum(func.case((Alerta.resolvido == True, 1), else_=0)).label('resolvidos')
            ).filter(
                Alerta.data_alerta >= data_inicio
            ).group_by(
                func.date(Alerta.data_alerta)
            ).order_by(
                'data'
            ).all()
            
            tendencias = {
                'periodo_dias': dias,
                'total_alertas': sum(a.total for a in alertas_por_dia),
                'total_resolvidos': sum(a.resolvidos for a in alertas_por_dia),
                'taxa_resolucao': 0,
                'por_dia': []
            }
            
            for a in alertas_por_dia:
                tendencias['por_dia'].append({
                    'data': a.data.isoformat() if hasattr(a.data, 'isoformat') else str(a.data),
                    'total': a.total,
                    'resolvidos': a.resolvidos,
                    'abertos': a.total - a.resolvidos
                })
            
            if tendencias['total_alertas'] > 0:
                tendencias['taxa_resolucao'] = round(
                    (tendencias['total_resolvidos'] / tendencias['total_alertas']) * 100, 2
                )
            
            return tendencias
            
        except Exception as e:
            raise AlertaError(f"Erro ao obter tendências: {str(e)}")
    
    # ============================================================================
    # MÉTODOS AUXILIARES
    # ============================================================================
    
    def obter_tipos_alertas(self) -> List[Dict[str, str]]:
        """
        Retorna os tipos de alerta disponíveis.
        
        Returns:
            Lista de tipos de alerta
        """
        return [
            {
                'tipo': tipo,
                'descricao': info['descricao'],
                'gravidade': info['gravidade'],
                'acao_recomendada': info['acao_recomendada']
            }
            for tipo, info in self.alert_types.items()
        ]
    
    def obter_alertas_por_colaborador(self, ci_id: int, apenas_abertos: bool = True) -> List[Alerta]:
        """
        Obtém alertas relacionados a um colaborador.
        
        Args:
            ci_id: ID do colaborador
            apenas_abertos: Apenas alertas não resolvidos
        
        Returns:
            Lista de alertas
        """
        try:
            query = Alerta.query.filter(
                Alerta.dados_relacionados['colaborador_id'].astext == str(ci_id)
            )
            
            if apenas_abertos:
                query = query.filter_by(resolvido=False)
            
            return query.order_by(desc(Alerta.data_alerta)).all()
            
        except Exception as e:
            raise AlertaError(f"Erro ao obter alertas do colaborador: {str(e)}")
    
    def verificar_e_criar_alertas_colaborador(self, ci: ColaboradorInterno) -> List[Alerta]:
        """
        Verifica e cria todos os alertas possíveis para um colaborador.
        
        Args:
            ci: ColaboradorInterno
        
        Returns:
            Lista de alertas criados
        """
        alertas = []
        
        # Verificar se tem NC ativo
        if not ci.nc_ativo:
            alerta = self.criar_alerta_ci_sem_nc(ci)
            if alerta:
                alertas.append(alerta)
        
        # Verificar dependentes sem CPF
        for dependente in ci.dependentes:
            if not dependente.cpf:
                alerta = self.criar_alerta_dependente_sem_cpf(dependente)
                if alerta:
                    alertas.append(alerta)
        
        # Verificar planos vencidos
        for plano in ci.planos_saude:
            if plano.data_fim and plano.data_fim < datetime.now().date() and plano.ativo:
                alerta = self.criar_alerta_plano_vencido(plano)
                if alerta:
                    alertas.append(alerta)
        
        return alertas


# Singleton instance
alert_service = AlertService()