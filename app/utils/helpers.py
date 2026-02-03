# app/utils/helpers.py
import json
import pytz
from datetime import datetime, date, timedelta
import pandas as pd
from app import db
from app.models import ColaboradorInterno, NumeroCadastro, HistoricoCI
import hashlib
import os

# ─── TIMEZONE HELPERS ────────────────────────────────────────────────────────
_TZ = pytz.timezone('America/Sao_Paulo')

def get_utc_now():
    return datetime.utcnow()

def _to_brasilia(dt):
    """Converte datetime para fuso horário de Brasília."""
    if dt is None:
        return ''
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(_TZ).strftime('%d/%m/%Y %H:%M')

# ─── UTILITY FUNCTIONS ───────────────────────────────────────────────────────
_DATE_FORMATS = ['%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d-%m-%y', '%Y-%m-%d', '%Y/%m/%d']
_EXCEL_BASE = datetime(1899, 12, 30).date()

def convert_excel_date(val):
    """Converte data Excel serial ou string para datetime.date."""
    if val is None:
        return None
    try:
        if isinstance(val, (int, float)):
            if not (1 <= val <= 50000):
                return None
            result = _EXCEL_BASE + timedelta(days=int(val))
            return result if 1900 <= result.year <= 2100 else None
        if isinstance(val, str):
            val = val.strip()
            for fmt in _DATE_FORMATS:
                try:
                    return datetime.strptime(val, fmt).date()
                except ValueError:
                    continue
    except Exception:
        pass
    return None

def parse_date_field(row, field_name):
    """Extrai e converte campo de data de uma linha do DataFrame."""
    if field_name not in row:
        return None
    raw = row[field_name]
    if not pd.notna(raw):
        return None
    if isinstance(raw, (int, float)):
        return convert_excel_date(raw)
    try:
        return pd.to_datetime(raw).date()
    except Exception:
        return convert_excel_date(raw)

def serialize_for_json(data):
    """Serializa objetos Python para JSON."""
    if isinstance(data, dict):
        return {k: serialize_for_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [serialize_for_json(i) for i in data]
    if isinstance(data, (date, datetime)):
        return data.isoformat()
    if hasattr(data, '__dict__'):
        return serialize_for_json(data.__dict__)
    return data

def clean_cpf(cpf):
    """Limpa e valida CPF."""
    if not cpf:
        return None
    digits = ''.join(filter(str.isdigit, str(cpf)))
    return digits if len(digits) == 11 else None

def clean_nc(nc):
    """Limpa e formata NC (Número de Cadastro)."""
    if not nc:
        return None
    return str(nc).strip().zfill(6)

def clean_empresa(raw):
    """Limpa código de empresa: retém apenas dígitos e remove zeros à esquerda."""
    if not raw:
        return None
    digits = ''.join(filter(str.isdigit, str(raw).strip()))
    return digits.lstrip('0') or None

def parse_valor(raw):
    """Converte string de valor monetário brasileiro para float."""
    if not raw or not str(raw).strip():
        return 0.0
    
    try:
        # Converter para string e limpar
        valor_str = str(raw).strip()
        
        # Remover R$ e espaços
        valor_str = valor_str.replace('R$', '').replace('$', '').strip()
        
        # Se começa com =", remove aspas (ex: ="5622")
        if valor_str.startswith('="') and valor_str.endswith('"'):
            valor_str = valor_str[2:-1]
        
        # Verificar se tem vírgula ou ponto
        tem_virgula = ',' in valor_str
        tem_ponto = '.' in valor_str
        
        # Se não tem nenhum separador decimal, pode ser centavos
        if not tem_virgula and not tem_ponto:
            try:
                valor_int = int(valor_str)
                # Para HAPVIDA: valores como 5622 são 56,22 (dividir por 100)
                # Mas também pode ser valor pequeno como 5 (que seria 5,00)
                if abs(valor_int) >= 100:  # Se for >= 100, assume centavos
                    return valor_int / 100.0
                else:
                    return float(valor_int)
            except ValueError:
                return 0.0
        
        # Se tem vírgula e ponto, é formato brasileiro (1.234,56)
        if tem_virgula and tem_ponto:
            # Remove pontos de milhar
            valor_str = valor_str.replace('.', '')
            # Substitui vírgula por ponto
            valor_str = valor_str.replace(',', '.')
        # Se só tem vírgula, é decimal brasileiro (1234,56)
        elif tem_virgula:
            valor_str = valor_str.replace(',', '.')
        # Se só tem ponto, pode ser decimal internacional (1234.56) ou milhar (1.234)
        elif tem_ponto:
            # Verificar se é milhar ou decimal
            parts = valor_str.split('.')
            if len(parts) == 2:
                # Tem uma parte decimal
                if len(parts[1]) <= 2:  # Máximo 2 casas decimais
                    # É decimal: 1234.56
                    pass
                else:
                    # Pode ser milhar com erro: 1.234
                    # Para Hapvida, se tem ponto e é grande, remove o ponto
                    valor_str = valor_str.replace('.', '')
            else:
                # Mais de um ponto: 1.234.567 -> é milhar
                valor_str = valor_str.replace('.', '')
        
        return float(valor_str) if valor_str else 0.0
        
    except (ValueError, TypeError) as e:
        # Log do erro (se tiver logger configurado)
        return 0.0

def extract_nc_from_matricula(matricula):
    """Extrai NC (6 dígitos) de uma matrícula do Hapvida."""
    if not matricula:
        return None
    
    # Extrair apenas dígitos
    digits = ''.join(filter(str.isdigit, str(matricula)))
    
    # Se tiver 10+ dígitos, pegar os últimos 6
    if len(digits) >= 6:
        return digits[-6:].lstrip('0') or '000001'
    
    # Se não, completar com zeros à esquerda
    return digits.zfill(6)

def rename_columns(df, mapping):
    """Renomeia colunas do DataFrame usando mapeamento {alvo: [possíveis nomes]}."""
    for target, candidates in mapping.items():
        if target not in df.columns:
            for name in candidates:
                if name in df.columns:
                    df = df.rename(columns={name: target})
                    break
    return df

def find_ci(cpf=None, nc=None):
    """Busca ColaboradorInterno por CPF e/ou NC."""
    ci = None
    if cpf:
        ci = ColaboradorInterno.query.filter_by(cpf=cpf).first()
    if not ci and nc:
        nc_obj = NumeroCadastro.query.filter_by(nc=nc).first()
        if nc_obj:
            ci = nc_obj.colaborador
    return ci

def _add_historico(ci_id, tipo_evento, descricao, nc=None, empresa=None, dados=None):
    """Adiciona registro de histórico ao CI."""
    db.session.add(HistoricoCI(
        colaborador_id=ci_id, tipo_evento=tipo_evento,
        descricao=descricao, data_evento=date.today(),
        nc=nc, cod_empresa=empresa,
        dados_alterados=serialize_for_json(dados) if dados else None,
    ))

def _sync_nc(ci, nc, empresa, origem):
    """Sincroniza o NC ativo de um CI durante importação.
    
    Desativa NCs anteriores, reativa ou cria o NC necessário.
    Registra histórico automaticamente.
    """
    # Já existe este NC ativo?
    nc_ativo = NumeroCadastro.query.filter(
        NumeroCadastro.colaborador_id == ci.id,
        NumeroCadastro.nc == nc, NumeroCadastro.ativo == True
    ).first()

    if nc_ativo:
        if nc_ativo.cod_empresa != empresa:
            _add_historico(ci.id, 'ALTERACAO_EMPRESA_IMPORT',
                           f'NC {nc} alterado de empresa {nc_ativo.cod_empresa} para {empresa} via {origem}',
                           nc=nc, empresa=empresa,
                           dados={'empresa_antiga': nc_ativo.cod_empresa, 'empresa_nova': empresa})
            nc_ativo.cod_empresa = empresa
            nc_ativo.motivo_mudanca = f'ATUALIZAÇÃO EMPRESA VIA {origem}'
        return

    # Desativar outros NCs ativos deste CI
    for nc_old in NumeroCadastro.query.filter_by(colaborador_id=ci.id, ativo=True).all():
        if nc_old.nc == nc:
            continue
        _add_historico(ci.id, 'DESATIVACAO_NC_IMPORT',
                       f'NC {nc_old.nc} desativado para mudança para NC {nc}',
                       nc=nc_old.nc, empresa=nc_old.cod_empresa,
                       dados={'motivo': f'MUDANÇA PARA NC {nc}', 'origem': origem})
        nc_old.desativar(data_fim=date.today(), motivo=f'MUDANÇA PARA NC {nc} VIA {origem}')

    # Verificar se existe registro inativo para reativar
    nc_inativo = NumeroCadastro.query.filter(
        NumeroCadastro.colaborador_id == ci.id,
        NumeroCadastro.nc == nc, NumeroCadastro.ativo == False
    ).order_by(NumeroCadastro.data_inicio.desc()).first()

    if nc_inativo:
        _add_historico(ci.id, 'REATIVACAO_NC_IMPORT',
                       f'NC {nc} reativado (Empresa: {empresa}) via {origem}',
                       nc=nc, empresa=empresa,
                       dados={'empresa_antiga': nc_inativo.cod_empresa, 'empresa_nova': empresa})
        nc_inativo.ativo = True
        nc_inativo.data_inicio = date.today()
        nc_inativo.data_fim = None
        nc_inativo.cod_empresa = empresa
        nc_inativo.motivo_mudanca = f'REATIVAÇÃO VIA {origem}'
    else:
        _add_historico(ci.id, 'MUDANCA_NC_IMPORT',
                       f'Mudança para NC {nc} (Empresa: {empresa}) via {origem}',
                       nc=nc, empresa=empresa,
                       dados={'origem': origem, 'tipo': 'NOVO_NC'})
        db.session.add(NumeroCadastro(
            nc=nc, cod_empresa=empresa, data_inicio=date.today(),
            ativo=True, motivo_mudanca=f'CRIAÇÃO VIA {origem}',
            colaborador_id=ci.id,
        ))

def _determinar_parentesco_por_idade(data_nascimento_dep, data_nascimento_titular):
    """Determina parentesco baseado na diferença de idade."""
    if not data_nascimento_dep or not data_nascimento_titular:
        return 'DEPENDENTE'
    
    # Calcular idades
    hoje = date.today()
    idade_dep = hoje.year - data_nascimento_dep.year - (
        (hoje.month, hoje.day) < (data_nascimento_dep.month, data_nascimento_dep.day)
    )
    idade_titular = hoje.year - data_nascimento_titular.year - (
        (hoje.month, hoje.day) < (data_nascimento_titular.month, data_nascimento_titular.day)
    )
    
    # Calcular diferença de idade
    diferenca_idade = idade_titular - idade_dep
    
    # Lógica de parentesco
    if abs(diferenca_idade) <= 5:
        # Diferença pequena (até 5 anos) - provavelmente CONJUGE
        return 'CONJUGE'
    elif diferenca_idade >= 15:
        # Titular é pelo menos 15 anos mais velho - FILHO
        return 'FILHO(A)'
    elif diferenca_idade <= -15:
        # Titular é pelo menos 15 anos mais novo - PAIS
        return 'PAIS'
    else:
        # Outra relação familiar
        return 'OUTROS'

def extrair_codigo_beneficiario(beneficiario_field):
    """Extrai código beneficiário do campo 'BENEFICIARIO' no formato '0AFP5000442003-LUIZ GUSTAVO SANTINI'"""
    if not beneficiario_field:
        return None
    
    parts = str(beneficiario_field).split('-', 1)
    if len(parts) > 0:
        # Remover qualquer ponto, espaço ou hífen do código
        codigo = ''.join(filter(lambda c: c.isalnum(), parts[0]))
        return codigo
    return None