"""
Serviço para geração de relatórios.
"""

import io
import csv
from datetime import datetime, date
from typing import Dict, List, Any
from sqlalchemy import func, desc, asc

from app import db
from app.models import (
    ColaboradorInterno, NumeroCadastro, Dependente,
    PlanoSaude, PlanoOdontologico, Alerta
)


class ReportService:
    """Serviço para geração de relatórios."""
    
    def exportar_colaboradores_csv(self) -> str:
        """Exporta colaboradores para CSV."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
        
        # Cabeçalho
        writer.writerow([
            'ID', 'Nome', 'CPF', 'Email', 'Telefone',
            'Data Admissão', 'Data Nascimento', 'Idade',
            'NC Atual', 'Empresa', 'Status', 'Total Dependentes'
        ])
        
        # Dados
        colaboradores = ColaboradorInterno.query.filter_by(is_deleted=False)\
            .order_by(ColaboradorInterno.nome).all()
        
        for ci in colaboradores:
            nc = ci.nc_ativo
            writer.writerow([
                ci.id,
                ci.nome,
                ci.cpf,
                ci.email or '',
                ci.telefone or '',
                ci.data_admissao.strftime('%d/%m/%Y') if ci.data_admissao else '',
                ci.data_nascimento.strftime('%d/%m/%Y') if ci.data_nascimento else '',
                ci.idade or '',
                nc.nc if nc else '',
                nc.cod_empresa if nc else '',
                'ATIVO' if ci.esta_ativo else 'INATIVO',
                ci.total_dependentes
            ])
        
        return output.getvalue()
    
    def exportar_planos_saude_csv(self) -> str:
        """Exporta planos de saúde para CSV."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
        
        writer.writerow([
            'ID', 'Colaborador', 'CPF', 'Operadora', 'Plano',
            'Tipo', 'Contrato', 'Valor', 'Data Início', 'Data Fim',
            'Status', 'Empresa'
        ])
        
        planos = PlanoSaude.query.filter_by(ativo=True)\
            .order_by(PlanoSaude.operadora, PlanoSaude.plano).all()
        
        for plano in planos:
            writer.writerow([
                plano.id,
                plano.colaborador.nome if plano.colaborador else '',
                plano.colaborador.cpf if plano.colaborador else '',
                plano.operadora,
                plano.plano,
                plano.tipo,
                plano.contrato or '',
                f'{float(plano.valor):.2f}' if plano.valor else '',
                plano.data_inicio.strftime('%d/%m/%Y'),
                plano.data_fim.strftime('%d/%m/%Y') if plano.data_fim else '',
                'ATIVO' if plano.ativo else 'INATIVO',
                plano.empresa_cod
            ])
        
        return output.getvalue()
    
    def exportar_planos_odonto_csv(self) -> str:
        """Exporta planos odontológicos para CSV."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
        
        writer.writerow([
            'ID', 'Colaborador', 'CPF', 'Operadora', 'Plano',
            'Valor', 'Data Início', 'Data Fim', 'Status',
            'Empresa', 'Unidade'
        ])
        
        planos = PlanoOdontologico.query.filter_by(ativo=True)\
            .order_by(PlanoOdontologico.operadora, PlanoOdontologico.plano).all()
        
        for plano in planos:
            writer.writerow([
                plano.id,
                plano.colaborador.nome if plano.colaborador else '',
                plano.colaborador.cpf if plano.colaborador else '',
                plano.operadora,
                plano.plano,
                f'{float(plano.valor):.2f}' if plano.valor else '',
                plano.data_inicio.strftime('%d/%m/%Y'),
                plano.data_fim.strftime('%d/%m/%Y') if plano.data_fim else '',
                'ATIVO' if plano.ativo else 'INATIVO',
                plano.empresa_cod,
                plano.unidade or ''
            ])
        
        return output.getvalue()
    
    def exportar_dependentes_csv(self) -> str:
        """Exporta dependentes para CSV."""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_ALL)
        
        writer.writerow([
            'ID', 'Nome', 'CPF', 'Data Nascimento', 'Idade',
            'Parentesco', 'NC Vínculo', 'Titular', 'CPF Titular'
        ])
        
        dependentes = Dependente.query.order_by(Dependente.nome).all()
        
        for dep in dependentes:
            writer.writerow([
                dep.id,
                dep.nome,
                dep.cpf or '',
                dep.data_nascimento.strftime('%d/%m/%Y') if dep.data_nascimento else '',
                dep.idade or '',
                dep.parentesco or '',
                dep.nc_vinculo,
                dep.titular.nome if dep.titular else '',
                dep.titular.cpf if dep.titular else ''
            ])
        
        return output.getvalue()
    
    def obter_dados_dashboard(self) -> Dict[str, Any]:
        """Obtém dados para dashboard."""
        dados = {}
        
        # Totais
        dados['total_colaboradores'] = ColaboradorInterno.query.filter_by(is_deleted=False).count()
        dados['total_ativos'] = ColaboradorInterno.query.filter_by(is_deleted=False)\
            .filter(ColaboradorInterno.id.in_(
                db.session.query(NumeroCadastro.colaborador_id).filter_by(ativo=True)
            )).count()
        
        dados['total_dependentes'] = Dependente.query.count()
        dados['total_planos_saude'] = PlanoSaude.query.filter_by(ativo=True).count()
        dados['total_planos_odonto'] = PlanoOdontologico.query.filter_by(ativo=True).count()
        dados['total_alertas_abertos'] = Alerta.query.filter_by(resolvido=False).count()
        
        # Distribuição por empresa
        dist_empresa = db.session.query(
            NumeroCadastro.cod_empresa,
            func.count(NumeroCadastro.id).label('total')
        ).filter_by(ativo=True).group_by(NumeroCadastro.cod_empresa).all()
        
        dados['distribuicao_empresa'] = [
            {'empresa': emp, 'total': total}
            for emp, total in dist_empresa
        ]
        
        # Alertas recentes
        alertas_recentes = Alerta.query.filter_by(resolvido=False)\
            .order_by(desc(Alerta.data_alerta))\
            .limit(10).all()
        
        dados['alertas_recentes'] = [
            {
                'id': a.id,
                'tipo': a.tipo,
                'descricao': a.descricao[:100] + '...' if len(a.descricao) > 100 else a.descricao,
                'gravidade': a.gravidade,
                'cor_gravidade': a.cor_gravidade,
                'data_alerta': a.data_alerta.isoformat()
            }
            for a in alertas_recentes
        ]
        
        return dados

# ============================================================================
# INSTÂNCIA SINGLETON
# ============================================================================

# Criar instância única do serviço para uso global
report_service = ReportService()

# Exportar classes e instâncias
__all__ = ['ReportService', 'report_service']
