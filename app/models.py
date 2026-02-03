from flask_login import UserMixin

"""
Modelos do banco de dados para o Sistema de Gestão de Colaboradores Internos.
"""

import hashlib
import json
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates

from app import db


# ============================================================================
# FUNÇÕES ÚTEIS
# ============================================================================

def get_utc_now() -> datetime:
    """Retorna datetime atual em UTC."""
    return datetime.utcnow()


def serialize_for_json(data: Any) -> Any:
    """
    Serializa objetos Python para JSON.
    
    Args:
        data: Dados a serem serializados
        
    Returns:
        Dados serializados
    """
    if isinstance(data, dict):
        return {k: serialize_for_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [serialize_for_json(i) for i in data]
    if isinstance(data, (date, datetime)):
        return data.isoformat()
    if hasattr(data, '__dict__'):
        return serialize_for_json(data.__dict__)
    return data


# ============================================================================
# MODELOS BASE
# ============================================================================

class BaseModel(db.Model):
    """Classe base abstrata para todos os modelos."""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime, 
        default=get_utc_now, 
        onupdate=get_utc_now, 
        nullable=False
    )
    

    # ========================================================================
    # MÉTODOS DO FLASK-LOGIN
    # ========================================================================
    
    @property
    def is_authenticated(self):
        """Retorna True se o usuário está autenticado."""
        return True
    
    @property
    def is_active(self):
        """Retorna True se o usuário está ativo."""
        return self.ativo
    
    @property
    def is_anonymous(self):
        """Retorna False - usuários reais não são anônimos."""
        return False
    
    def get_id(self):
        """Retorna o ID do usuário como string (requerido pelo Flask-Login)."""
        return str(self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Converte modelo para dicionário."""
        raise NotImplementedError("Subclasses devem implementar to_dict()")
    
    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.id}>'


class TimestampMixin:
    """Mixin para adicionar timestamps aos modelos."""
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime, 
        default=get_utc_now, 
        onupdate=get_utc_now, 
        nullable=False
    )


# ============================================================================
# MODELO DE USUÁRIO
# ============================================================================

class Usuario(UserMixin, BaseModel):
    """Modelo de usuário do sistema."""
    __tablename__ = 'usuarios'
    
    # Campos básicos
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    tipo_usuario = db.Column(db.String(20), default='usuario', index=True)
    ativo = db.Column(db.Boolean, default=True, index=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Validações
    @validates('email')
    def validate_email(self, key: str, email: str) -> str:
        """Valida formato do email."""
        if '@' not in email:
            raise ValueError('Email inválido')
        return email.lower()
    
    # Métodos de senha
    def set_password(self, password: str) -> None:
        """Define hash da senha usando SHA-256."""
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password: str) -> bool:
        """Verifica se a senha está correta."""
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()
    
    # Propriedades
    @property
    def is_admin(self) -> bool:
        """Verifica se o usuário é administrador."""
        return self.tipo_usuario == 'admin'
    
    @property
    def is_active(self) -> bool:
        """Verifica se o usuário está ativo."""
        return self.ativo
    
    # Métodos
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Converte usuário para dicionário."""
        data = {
            'id': self.id,
            'username': self.username,
            'nome': self.nome,
            'email': self.email,
            'tipo_usuario': self.tipo_usuario,
            'ativo': self.ativo,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data['is_admin'] = self.is_admin
            data['is_active'] = self.is_active
            
        return data
    
    def __repr__(self) -> str:
        return f'<Usuario {self.id}: {self.username}>'


# ============================================================================
# MODELOS DE COLABORADORES
# ============================================================================

class ColaboradorInterno(BaseModel):
    """Modelo de Colaborador Interno."""
    __tablename__ = 'colaboradores_internos'
    
    # Campos básicos
    nome = db.Column(db.String(200), nullable=False, index=True)
    cpf = db.Column(db.String(11), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), nullable=True, index=True)
    telefone = db.Column(db.String(20), nullable=True)
    data_admissao = db.Column(db.Date, nullable=True, index=True)
    data_nascimento = db.Column(db.Date, nullable=True, index=True)
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, nullable=True)
    deleted_reason = db.Column(db.Text, nullable=True)
    
    # Dados adicionais
    dados_adicionais = db.Column(db.JSON, nullable=True)
    
    # Validações
    @validates('cpf')
    def validate_cpf(self, key: str, cpf: str) -> str:
        """Valida formato do CPF (apenas dígitos)."""
        if not cpf.isdigit() or len(cpf) != 11:
            raise ValueError('CPF deve conter 11 dígitos')
        return cpf
    
    # Relacionamentos
    numeros_cadastro = db.relationship(
        'NumeroCadastro',
        backref='colaborador',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='NumeroCadastro.data_inicio.desc()'
    )
    
    dependentes = db.relationship(
        'Dependente',
        backref='titular',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Dependente.nome'
    )
    
    planos_saude = db.relationship(
        'PlanoSaude',
        backref='colaborador',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='PlanoSaude.data_inicio.desc()'
    )
    
    planos_odonto = db.relationship(
        'PlanoOdontologico',
        backref='colaborador',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='PlanoOdontologico.data_inicio.desc()'
    )
    
    historico = db.relationship(
        'HistoricoCI',
        backref='colaborador',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='HistoricoCI.data_evento.desc()'
    )
    
    # Propriedades
    @property
    def nc_ativo(self) -> Optional['NumeroCadastro']:
        """Retorna o NC ativo do colaborador."""
        return self.numeros_cadastro.filter_by(ativo=True).first()
    
    @property
    def empresa_atual(self) -> Optional[str]:
        """Retorna a empresa atual do colaborador."""
        nc = self.nc_ativo
        return nc.cod_empresa if nc else None
    
    @property
    def nc_atual(self) -> Optional[str]:
        """Retorna o NC atual do colaborador."""
        nc = self.nc_ativo
        return nc.nc if nc else None
    
    @property
    def esta_ativo(self) -> bool:
        """Verifica se o colaborador está ativo."""
        return self.nc_ativo is not None and not self.is_deleted
    
    @property
    def total_dependentes(self) -> int:
        """Retorna o total de dependentes."""
        return self.dependentes.count()
    
    @property
    def total_planos_saude(self) -> int:
        """Retorna o total de planos de saúde ativos."""
        return self.planos_saude.filter_by(ativo=True).count()
    
    @property
    def total_planos_odonto(self) -> int:
        """Retorna o total de planos odontológicos ativos."""
        return self.planos_odonto.filter_by(ativo=True).count()
    
    @property
    def idade(self) -> Optional[int]:
        """Calcula a idade do colaborador."""
        if not self.data_nascimento:
            return None
        
        today = date.today()
        born = self.data_nascimento
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    
    @property
    def tempo_empresa(self) -> Optional[int]:
        """Calcula tempo na empresa em meses."""
        if not self.data_admissao:
            return None
        
        today = date.today()
        admission = self.data_admissao
        return (today.year - admission.year) * 12 + today.month - admission.month
    
    # Métodos
    def adicionar_nc(self, nc: str, empresa: str, motivo: str = None) -> 'NumeroCadastro':
        """Adiciona um novo número de cadastro."""
        from app.services.ci_service import CIService
        return CIService.adicionar_nc(self.id, nc, empresa, motivo)
    
    def excluir_soft(self, usuario_id: int, motivo: str = None) -> None:
        """Exclui o colaborador logicamente."""
        self.is_deleted = True
        self.deleted_at = get_utc_now()
        self.deleted_by = usuario_id
        self.deleted_reason = motivo or 'Exclusão manual'
        
        # Desativar NCs ativos
        for nc in self.numeros_cadastro.filter_by(ativo=True).all():
            nc.desativar(data_fim=date.today(), motivo='EXCLUSÃO DO CI')
    
    def restaurar(self, usuario_id: int) -> bool:
        """Restaura um colaborador excluído."""
        if not self.is_deleted:
            return False
        
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.deleted_reason = None
        
        # Tentar reativar o último NC
        ultimo_nc = self.numeros_cadastro.order_by(
            NumeroCadastro.data_inicio.desc()
        ).first()
        
        if ultimo_nc and not ultimo_nc.ativo:
            # Verificar se não há conflito
            from app.services.ci_service import CIService
            if not CIService.nc_em_uso(ultimo_nc.nc, self.id):
                ultimo_nc.ativo = True
                ultimo_nc.data_fim = None
                ultimo_nc.motivo_mudanca = 'RESTAURAÇÃO'
        
        return True
    
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """Converte colaborador para dicionário."""
        data = {
            'id': self.id,
            'nome': self.nome,
            'cpf': self.cpf,
            'cpf_formatado': f'{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}' 
                            if self.cpf and len(self.cpf) == 11 else self.cpf,
            'email': self.email,
            'telefone': self.telefone,
            'data_admissao': self.data_admissao.isoformat() if self.data_admissao else None,
            'data_nascimento': self.data_nascimento.isoformat() if self.data_nascimento else None,
            'idade': self.idade,
            'tempo_empresa': self.tempo_empresa,
            'esta_ativo': self.esta_ativo,
            'is_deleted': self.is_deleted,
            'empresa_atual': self.empresa_atual,
            'nc_atual': self.nc_atual,
            'total_dependentes': self.total_dependentes,
            'total_planos_saude': self.total_planos_saude,
            'total_planos_odonto': self.total_planos_odonto,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
        }
        
        if include_relationships:
            data.update({
                'dependentes': [dep.to_dict() for dep in self.dependentes],
                'planos_saude': [plano.to_dict() for plano in self.planos_saude.filter_by(ativo=True)],
                'planos_odonto': [plano.to_dict() for plano in self.planos_odonto.filter_by(ativo=True)],
                'numeros_cadastro': [nc.to_dict() for nc in self.numeros_cadastro],
                'historico': [hist.to_dict() for hist in self.historico],
            })
        
        return data
    
    def __repr__(self) -> str:
        return f'<ColaboradorInterno {self.id}: {self.nome}>'


class NumeroCadastro(BaseModel):
    """Modelo de Número de Cadastro (NC)."""
    __tablename__ = 'numeros_cadastro'
    
    # Campos
    nc = db.Column(db.String(50), nullable=False, index=True)
    cod_empresa = db.Column(db.String(10), nullable=False, index=True)
    data_inicio = db.Column(db.Date, nullable=False, index=True)
    data_fim = db.Column(db.Date, nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)
    motivo_mudanca = db.Column(db.String(200), nullable=True)
    
    # Foreign Key
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey('colaboradores_internos.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('nc', 'ativo', 'colaborador_id', name='unique_nc_ativo_per_ci'),
        db.Index('idx_nc_colaborador_ativo', 'colaborador_id', 'ativo'),
        db.Index('idx_nc_empresa_ativo', 'nc', 'cod_empresa', 'ativo'),
    )
    
    # Validações
    @validates('nc')
    def validate_nc(self, key: str, nc: str) -> str:
        """Valida e limpa o NC."""
        # Remover caracteres não numéricos e zeros à esquerda
        digits = ''.join(filter(str.isdigit, str(nc)))
        if not digits:
            raise ValueError('NC inválido')
        return digits.lstrip('0') or '0'
    
    @validates('cod_empresa')
    def validate_empresa(self, key: str, empresa: str) -> str:
        """Valida código da empresa."""
        from app import current_app
        valid_codes = current_app.config.get('VALID_COMPANY_CODES', {})
        
        if empresa not in valid_codes:
            raise ValueError(f'Empresa {empresa} não é válida')
        
        return empresa
    
    # Métodos
    def desativar(self, data_fim: Optional[date] = None, motivo: Optional[str] = None) -> None:
        """Desativa o NC."""
        self.ativo = False
        self.data_fim = data_fim or date.today()
        if motivo:
            self.motivo_mudanca = motivo
        
        # Atualizar updated_at
        self.updated_at = get_utc_now()
    
    def reativar(self, data_inicio: Optional[date] = None, motivo: Optional[str] = None) -> None:
        """Reativa o NC."""
        self.ativo = True
        self.data_inicio = data_inicio or date.today()
        self.data_fim = None
        if motivo:
            self.motivo_mudanca = motivo
        
        # Atualizar updated_at
        self.updated_at = get_utc_now()
    
    @property
    def empresa_nome(self) -> str:
        """Retorna o nome da empresa."""
        from app import current_app
        valid_codes = current_app.config.get('VALID_COMPANY_CODES', {})
        return valid_codes.get(self.cod_empresa, self.cod_empresa)
    
    @property
    def duracao_dias(self) -> Optional[int]:
        """Calcula duração em dias."""
        if not self.data_inicio:
            return None
        
        fim = self.data_fim or date.today()
        return (fim - self.data_inicio).days
    

    # ========================================================================
    # MÉTODOS DO FLASK-LOGIN
    # ========================================================================
    
    @property
    def is_authenticated(self):
        """Retorna True se o usuário está autenticado."""
        return True
    
    @property
    def is_active(self):
        """Retorna True se o usuário está ativo."""
        return self.ativo
    
    @property
    def is_anonymous(self):
        """Retorna False - usuários reais não são anônimos."""
        return False
    
    def get_id(self):
        """Retorna o ID do usuário como string (requerido pelo Flask-Login)."""
        return str(self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Converte NC para dicionário."""
        return {
            'id': self.id,
            'nc': self.nc,
            'cod_empresa': self.cod_empresa,
            'empresa_nome': self.empresa_nome,
            'data_inicio': self.data_inicio.isoformat(),
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'ativo': self.ativo,
            'motivo_mudanca': self.motivo_mudanca,
            'duracao_dias': self.duracao_dias,
            'colaborador_id': self.colaborador_id,
            'colaborador_nome': self.colaborador.nome if self.colaborador else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        status = 'ATIVO' if self.ativo else 'INATIVO'
        return f'<NumeroCadastro {self.nc} ({self.cod_empresa}) - {status}>'


class Dependente(BaseModel):
    """Modelo de Dependente."""
    __tablename__ = 'dependentes'
    
    # Campos
    nome = db.Column(db.String(200), nullable=False, index=True)
    cpf = db.Column(db.String(11), nullable=True, index=True)
    data_nascimento = db.Column(db.Date, nullable=True, index=True)
    parentesco = db.Column(db.String(50), nullable=True, index=True)
    nc_vinculo = db.Column(db.String(50), nullable=False, index=True)
    
    # Foreign Key
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey('colaboradores_internos.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Validações
    @validates('cpf')
    def validate_cpf(self, key: str, cpf: str) -> Optional[str]:
        """Valida CPF do dependente."""
        if not cpf:
            return None
        
        digits = ''.join(filter(str.isdigit, str(cpf)))
        if len(digits) != 11:
            raise ValueError('CPF deve conter 11 dígitos')
        
        return digits
    
    @property
    def idade(self) -> Optional[int]:
        """Calcula idade do dependente."""
        if not self.data_nascimento:
            return None
        
        today = date.today()
        born = self.data_nascimento
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    

    # ========================================================================
    # MÉTODOS DO FLASK-LOGIN
    # ========================================================================
    
    @property
    def is_authenticated(self):
        """Retorna True se o usuário está autenticado."""
        return True
    
    @property
    def is_active(self):
        """Retorna True se o usuário está ativo."""
        return self.ativo
    
    @property
    def is_anonymous(self):
        """Retorna False - usuários reais não são anônimos."""
        return False
    
    def get_id(self):
        """Retorna o ID do usuário como string (requerido pelo Flask-Login)."""
        return str(self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Converte dependente para dicionário."""
        return {
            'id': self.id,
            'nome': self.nome,
            'cpf': self.cpf,
            'cpf_formatado': f'{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}' 
                            if self.cpf and len(self.cpf) == 11 else self.cpf,
            'data_nascimento': self.data_nascimento.isoformat() if self.data_nascimento else None,
            'idade': self.idade,
            'parentesco': self.parentesco,
            'nc_vinculo': self.nc_vinculo,
            'colaborador_id': self.colaborador_id,
            'colaborador_nome': self.titular.nome if self.titular else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<Dependente {self.id}: {self.nome}>'


# ============================================================================
# MODELOS DE PLANOS
# ============================================================================

class PlanoSaude(BaseModel):
    """Modelo de Plano de Saúde."""
    __tablename__ = 'planos_saude'
    
    # Campos
    operadora = db.Column(db.String(100), nullable=False, index=True)
    plano = db.Column(db.String(100), nullable=False, index=True)
    tipo = db.Column(db.String(50), nullable=False, index=True)  # MENSALIDADE, COPARTICIPACAO, etc.
    contrato = db.Column(db.String(50), nullable=True, index=True)
    nc_contratacao = db.Column(db.String(50), nullable=False, index=True)
    data_inicio = db.Column(db.Date, nullable=False, index=True)
    data_fim = db.Column(db.Date, nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)
    valor = db.Column(db.Numeric(10, 2), nullable=True)
    empresa_cod = db.Column(db.String(10), nullable=False, index=True)
    competencia = db.Column(db.String(6), nullable=True, index=True)  # YYYYMM
    ultimo_atendimento = db.Column(db.Date, nullable=True)
    
    # Dados adicionais
    dados_adicionais = db.Column(db.JSON, nullable=True)
    
    # Foreign Key
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey('colaboradores_internos.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Relacionamentos
    atendimentos = db.relationship(
        'AtendimentoCoparticipacao',
        backref='plano_saude',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='AtendimentoCoparticipacao.data_atendimento.desc()'
    )
    
    # Propriedades
    @property
    def empresa_nome(self) -> str:
        """Retorna nome da empresa."""
        from app import current_app
        valid_codes = current_app.config.get('VALID_COMPANY_CODES', {})
        return valid_codes.get(self.empresa_cod, self.empresa_cod)
    
    @property
    def total_atendimentos(self) -> int:
        """Retorna total de atendimentos."""
        return self.atendimentos.count()
    
    @property
    def valor_total_coparticipacao(self) -> float:
        """Calcula valor total de coparticipação."""
        if self.tipo != 'COPARTICIPACAO':
            return 0.0
        
        total = self.atendimentos.with_entities(
            func.sum(AtendimentoCoparticipacao.valor_coparticipacao)
        ).scalar()
        
        return float(total) if total else 0.0
    

    # ========================================================================
    # MÉTODOS DO FLASK-LOGIN
    # ========================================================================
    
    @property
    def is_authenticated(self):
        """Retorna True se o usuário está autenticado."""
        return True
    
    @property
    def is_active(self):
        """Retorna True se o usuário está ativo."""
        return self.ativo
    
    @property
    def is_anonymous(self):
        """Retorna False - usuários reais não são anônimos."""
        return False
    
    def get_id(self):
        """Retorna o ID do usuário como string (requerido pelo Flask-Login)."""
        return str(self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Converte plano de saúde para dicionário."""
        return {
            'id': self.id,
            'operadora': self.operadora,
            'plano': self.plano,
            'tipo': self.tipo,
            'contrato': self.contrato,
            'nc_contratacao': self.nc_contratacao,
            'data_inicio': self.data_inicio.isoformat(),
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'ativo': self.ativo,
            'valor': float(self.valor) if self.valor else None,
            'empresa_cod': self.empresa_cod,
            'empresa_nome': self.empresa_nome,
            'competencia': self.competencia,
            'ultimo_atendimento': self.ultimo_atendimento.isoformat() if self.ultimo_atendimento else None,
            'colaborador_id': self.colaborador_id,
            'colaborador_nome': self.colaborador.nome if self.colaborador else None,
            'total_atendimentos': self.total_atendimentos,
            'valor_total_coparticipacao': self.valor_total_coparticipacao,
            'dados_adicionais': self.dados_adicionais,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        status = 'ATIVO' if self.ativo else 'INATIVO'
        return f'<PlanoSaude {self.id}: {self.operadora} - {self.plano} ({status})>'


class AtendimentoCoparticipacao(BaseModel):
    """Modelo de Atendimento de Coparticipação."""
    __tablename__ = 'atendimentos_coparticipacao'
    
    # Campos
    competencia = db.Column(db.String(6), nullable=False, index=True)  # YYYYMM
    contrato = db.Column(db.String(50), nullable=False, index=True)
    cpf = db.Column(db.String(11), nullable=True, index=True)
    beneficiario = db.Column(db.String(200), nullable=False, index=True)
    nc = db.Column(db.String(50), nullable=False, index=True)
    guia = db.Column(db.String(50), nullable=True, index=True)
    data_atendimento = db.Column(db.Date, nullable=False, index=True)
    descricao = db.Column(db.String(200), nullable=True)
    quantidade = db.Column(db.Numeric(10, 2), default=1.00)
    valor_base = db.Column(db.Numeric(10, 2), nullable=True)
    valor_coparticipacao = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Dados adicionais
    dados_adicionais = db.Column(db.JSON, nullable=True)
    
    # Foreign Keys
    plano_saude_id = db.Column(
        db.Integer,
        db.ForeignKey('planos_saude.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey('colaboradores_internos.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint(
            'competencia', 'contrato', 'cpf', 'nc', 'guia', 'data_atendimento', 'descricao',
            name='unique_atendimento'
        ),
        db.Index('idx_atendimento_competencia_contrato', 'competencia', 'contrato'),
    )
    
    # Propriedades
    @property
    def valor_base_float(self) -> float:
        """Retorna valor_base como float."""
        return float(self.valor_base) if self.valor_base else 0.0
    
    @property
    def valor_coparticipacao_float(self) -> float:
        """Retorna valor_coparticipacao como float."""
        return float(self.valor_coparticipacao) if self.valor_coparticipacao else 0.0
    
    @property
    def valor_total(self) -> float:
        """Calcula valor total (base + coparticipação)."""
        return self.valor_base_float + self.valor_coparticipacao_float
    
    @property
    def percentual_coparticipacao(self) -> float:
        """Calcula percentual de coparticipação."""
        if self.valor_base_float == 0:
            return 0.0
        return (self.valor_coparticipacao_float / self.valor_base_float) * 100
    

    # ========================================================================
    # MÉTODOS DO FLASK-LOGIN
    # ========================================================================
    
    @property
    def is_authenticated(self):
        """Retorna True se o usuário está autenticado."""
        return True
    
    @property
    def is_active(self):
        """Retorna True se o usuário está ativo."""
        return self.ativo
    
    @property
    def is_anonymous(self):
        """Retorna False - usuários reais não são anônimos."""
        return False
    
    def get_id(self):
        """Retorna o ID do usuário como string (requerido pelo Flask-Login)."""
        return str(self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Converte atendimento para dicionário."""
        return {
            'id': self.id,
            'competencia': self.competencia,
            'contrato': self.contrato,
            'cpf': self.cpf,
            'cpf_formatado': f'{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}' 
                            if self.cpf and len(self.cpf) == 11 else self.cpf,
            'beneficiario': self.beneficiario,
            'nc': self.nc,
            'guia': self.guia,
            'data_atendimento': self.data_atendimento.isoformat() if self.data_atendimento else None,
            'descricao': self.descricao,
            'quantidade': float(self.quantidade) if self.quantidade else 1.0,
            'valor_base': self.valor_base_float,
            'valor_coparticipacao': self.valor_coparticipacao_float,
            'valor_total': self.valor_total,
            'percentual_coparticipacao': round(self.percentual_coparticipacao, 2),
            'plano_saude_id': self.plano_saude_id,
            'colaborador_id': self.colaborador_id,
            'colaborador_nome': self.colaborador.nome if self.colaborador else None,
            'operadora': self.plano_saude.operadora if self.plano_saude else None,
            'plano': self.plano_saude.plano if self.plano_saude else None,
            'dados_adicionais': self.dados_adicionais,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<AtendimentoCoparticipacao {self.id}: {self.beneficiario} - R$ {self.valor_coparticipacao}>'


class PlanoOdontologico(BaseModel):
    """Modelo de Plano Odontológico."""
    __tablename__ = 'planos_odontologicos'
    
    # Campos
    operadora = db.Column(db.String(100), nullable=False, index=True)
    plano = db.Column(db.String(100), nullable=False, index=True)
    nc_contratacao = db.Column(db.String(50), nullable=False, index=True)
    data_inicio = db.Column(db.Date, nullable=False, index=True)
    data_fim = db.Column(db.Date, nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)
    valor = db.Column(db.Numeric(10, 2), nullable=True)
    empresa_cod = db.Column(db.String(10), nullable=False, index=True)
    unidade = db.Column(db.String(100), nullable=True, index=True)
    
    # Foreign Key
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey('colaboradores_internos.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Propriedades
    @property
    def empresa_nome(self) -> str:
        """Retorna nome da empresa."""
        from app import current_app
        valid_codes = current_app.config.get('VALID_COMPANY_CODES', {})
        return valid_codes.get(self.empresa_cod, self.empresa_cod)
    
    @property
    def duracao_meses(self) -> Optional[int]:
        """Calcula duração em meses."""
        if not self.data_inicio:
            return None
        
        fim = self.data_fim or date.today()
        return (fim.year - self.data_inicio.year) * 12 + (fim.month - self.data_inicio.month)
    

    # ========================================================================
    # MÉTODOS DO FLASK-LOGIN
    # ========================================================================
    
    @property
    def is_authenticated(self):
        """Retorna True se o usuário está autenticado."""
        return True
    
    @property
    def is_active(self):
        """Retorna True se o usuário está ativo."""
        return self.ativo
    
    @property
    def is_anonymous(self):
        """Retorna False - usuários reais não são anônimos."""
        return False
    
    def get_id(self):
        """Retorna o ID do usuário como string (requerido pelo Flask-Login)."""
        return str(self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Converte plano odontológico para dicionário."""
        return {
            'id': self.id,
            'operadora': self.operadora,
            'plano': self.plano,
            'nc_contratacao': self.nc_contratacao,
            'data_inicio': self.data_inicio.isoformat(),
            'data_fim': self.data_fim.isoformat() if self.data_fim else None,
            'ativo': self.ativo,
            'valor': float(self.valor) if self.valor else None,
            'empresa_cod': self.empresa_cod,
            'empresa_nome': self.empresa_nome,
            'unidade': self.unidade,
            'colaborador_id': self.colaborador_id,
            'colaborador_nome': self.colaborador.nome if self.colaborador else None,
            'duracao_meses': self.duracao_meses,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        status = 'ATIVO' if self.ativo else 'INATIVO'
        return f'<PlanoOdontologico {self.id}: {self.operadora} - {self.plano} ({status})>'


# ============================================================================
# MODELOS DE HISTÓRICO E LOGS
# ============================================================================

class HistoricoCI(BaseModel):
    """Modelo de Histórico de Colaborador Interno."""
    __tablename__ = 'historico_ci'
    
    # Campos
    tipo_evento = db.Column(db.String(50), nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=False)
    data_evento = db.Column(db.Date, nullable=False, index=True)
    nc = db.Column(db.String(50), nullable=True, index=True)
    cod_empresa = db.Column(db.String(10), nullable=True, index=True)
    dados_alterados = db.Column(db.JSON, nullable=True)
    
    # Foreign Key
    colaborador_id = db.Column(
        db.Integer,
        db.ForeignKey('colaboradores_internos.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Propriedades
    @property
    def empresa_nome(self) -> str:
        """Retorna nome da empresa."""
        if not self.cod_empresa:
            return ''
        
        from app import current_app
        valid_codes = current_app.config.get('VALID_COMPANY_CODES', {})
        return valid_codes.get(self.cod_empresa, self.cod_empresa)
    

    # ========================================================================
    # MÉTODOS DO FLASK-LOGIN
    # ========================================================================
    
    @property
    def is_authenticated(self):
        """Retorna True se o usuário está autenticado."""
        return True
    
    @property
    def is_active(self):
        """Retorna True se o usuário está ativo."""
        return self.ativo
    
    @property
    def is_anonymous(self):
        """Retorna False - usuários reais não são anônimos."""
        return False
    
    def get_id(self):
        """Retorna o ID do usuário como string (requerido pelo Flask-Login)."""
        return str(self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Converte histórico para dicionário."""
        return {
            'id': self.id,
            'tipo_evento': self.tipo_evento,
            'descricao': self.descricao,
            'data_evento': self.data_evento.isoformat(),
            'nc': self.nc,
            'cod_empresa': self.cod_empresa,
            'empresa_nome': self.empresa_nome,
            'dados_alterados': self.dados_alterados,
            'colaborador_id': self.colaborador_id,
            'colaborador_nome': self.colaborador.nome if self.colaborador else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<HistoricoCI {self.id}: {self.tipo_evento} - {self.data_evento}>'


class ImportacaoLog(BaseModel):
    """Modelo de Log de Importação."""
    __tablename__ = 'importacao_log'
    
    # Campos
    tipo_importacao = db.Column(db.String(50), nullable=False, index=True)
    arquivo = db.Column(db.String(255), nullable=False)
    data_importacao = db.Column(db.DateTime, default=get_utc_now, nullable=False, index=True)
    linhas_processadas = db.Column(db.Integer, default=0)
    linhas_sucesso = db.Column(db.Integer, default=0)
    linhas_erro = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='PENDENTE', index=True)
    detalhes = db.Column(db.Text, nullable=True)
    usuario_id = db.Column(db.Integer, nullable=True, index=True)
    
    # Propriedades
    @property
    def taxa_sucesso(self) -> float:
        """Calcula taxa de sucesso."""
        if self.linhas_processadas == 0:
            return 0.0
        return (self.linhas_sucesso / self.linhas_processadas) * 100
    
    @property
    def usuario_nome(self) -> Optional[str]:
        """Retorna nome do usuário."""
        if not self.usuario_id:
            return None
        
        usuario = Usuario.query.get(self.usuario_id)
        return usuario.nome if usuario else None
    

    # ========================================================================
    # MÉTODOS DO FLASK-LOGIN
    # ========================================================================
    
    @property
    def is_authenticated(self):
        """Retorna True se o usuário está autenticado."""
        return True
    
    @property
    def is_active(self):
        """Retorna True se o usuário está ativo."""
        return self.ativo
    
    @property
    def is_anonymous(self):
        """Retorna False - usuários reais não são anônimos."""
        return False
    
    def get_id(self):
        """Retorna o ID do usuário como string (requerido pelo Flask-Login)."""
        return str(self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Converte log de importação para dicionário."""
        return {
            'id': self.id,
            'tipo_importacao': self.tipo_importacao,
            'arquivo': self.arquivo,
            'data_importacao': self.data_importacao.isoformat(),
            'linhas_processadas': self.linhas_processadas,
            'linhas_sucesso': self.linhas_sucesso,
            'linhas_erro': self.linhas_erro,
            'taxa_sucesso': round(self.taxa_sucesso, 2),
            'status': self.status,
            'detalhes': self.detalhes,
            'usuario_id': self.usuario_id,
            'usuario_nome': self.usuario_nome,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<ImportacaoLog {self.id}: {self.tipo_importacao} - {self.status}>'


class Alerta(BaseModel):
    """Modelo de Alerta do Sistema."""
    __tablename__ = 'alertas'
    
    # Campos
    tipo = db.Column(db.String(50), nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=False)
    gravidade = db.Column(db.String(20), default='MEDIA', index=True)
    resolvido = db.Column(db.Boolean, default=False, index=True)
    data_alerta = db.Column(db.DateTime, default=get_utc_now, nullable=False, index=True)
    data_resolucao = db.Column(db.DateTime, nullable=True)
    acao_recomendada = db.Column(db.Text, nullable=True)
    dados_relacionados = db.Column(db.JSON, nullable=True)
    
    # Propriedades
    @property
    def dias_aberto(self) -> int:
        """Calcula dias desde a criação do alerta."""
        if self.resolvido and self.data_resolucao:
            fim = self.data_resolucao
        else:
            fim = get_utc_now()
        
        return (fim - self.data_alerta).days
    
    @property
    def cor_gravidade(self) -> str:
        """Retorna cor CSS baseada na gravidade."""
        cores = {
            'CRITICA': 'danger',
            'ALTA': 'warning',
            'MEDIA': 'info',
            'BAIXA': 'success'
        }
        return cores.get(self.gravidade, 'secondary')
    
    def resolver(self, data_resolucao: Optional[datetime] = None) -> None:
        """Marca alerta como resolvido."""
        self.resolvido = True
        self.data_resolucao = data_resolucao or get_utc_now()
        self.updated_at = get_utc_now()
    
    def reabrir(self) -> None:
        """Reabre um alerta resolvido."""
        self.resolvido = False
        self.data_resolucao = None
        self.updated_at = get_utc_now()
    

    # ========================================================================
    # MÉTODOS DO FLASK-LOGIN
    # ========================================================================
    
    @property
    def is_authenticated(self):
        """Retorna True se o usuário está autenticado."""
        return True
    
    @property
    def is_active(self):
        """Retorna True se o usuário está ativo."""
        return self.ativo
    
    @property
    def is_anonymous(self):
        """Retorna False - usuários reais não são anônimos."""
        return False
    
    def get_id(self):
        """Retorna o ID do usuário como string (requerido pelo Flask-Login)."""
        return str(self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Converte alerta para dicionário."""
        return {
            'id': self.id,
            'tipo': self.tipo,
            'descricao': self.descricao,
            'gravidade': self.gravidade,
            'cor_gravidade': self.cor_gravidade,
            'resolvido': self.resolvido,
            'data_alerta': self.data_alerta.isoformat(),
            'data_resolucao': self.data_resolucao.isoformat() if self.data_resolucao else None,
            'dias_aberto': self.dias_aberto,
            'acao_recomendada': self.acao_recomendada,
            'dados_relacionados': self.dados_relacionados,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        status = 'RESOLVIDO' if self.resolvido else 'ABERTO'
        return f'<Alerta {self.id}: {self.tipo} ({self.gravidade}) - {status}>'