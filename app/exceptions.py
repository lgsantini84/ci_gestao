# app/exceptions.py - VERSÃO COMPLETA E FINAL
"""
Exceções personalizadas para o sistema de gestão de CI.
"""

class SistemaCIError(Exception):
    """Exceção base para erros do sistema."""
    def __init__(self, message="Erro no sistema de CI", code=500):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ImportacaoError(SistemaCIError):
    """Erro durante importação de arquivos."""
    def __init__(self, message="Erro na importação", arquivo=None, linha=None):
        self.arquivo = arquivo
        self.linha = linha
        if arquivo:
            message = f"{message} (Arquivo: {arquivo})"
        if linha:
            message = f"{message} (Linha: {linha})"
        super().__init__(message, code=400)


class ArquivoInvalidoError(ImportacaoError):
    """Erro quando o arquivo é inválido ou tem formato não suportado."""
    def __init__(self, message="Arquivo inválido", extensao=None):
        if extensao:
            message = f"{message}: formato '{extensao}' não suportado"
        super().__init__(message)


class FormatoArquivoError(ArquivoInvalidoError):
    """Erro específico para problemas de formato de arquivo."""
    def __init__(self, message="Formato de arquivo inválido", detalhes=None):
        if detalhes:
            message = f"{message}: {detalhes}"
        super().__init__(message)


class LeituraArquivoError(ImportacaoError):
    """Erro ao ler arquivo (encoding, delimitador, etc)."""
    def __init__(self, message="Erro ao ler arquivo", encoding=None, linha=None):
        if encoding:
            message = f"{message} - Encoding: {encoding}"
        super().__init__(message, linha=linha)


class DadosInvalidosError(ImportacaoError):
    """Erro quando os dados no arquivo são inválidos."""
    def __init__(self, message="Dados inválidos no arquivo", campo=None, valor=None):
        if campo and valor:
            message = f"{message}: campo '{campo}' com valor '{valor}'"
        elif campo:
            message = f"{message}: campo '{campo}'"
        super().__init__(message)


class CPFInvalidoError(DadosInvalidosError):
    """Erro quando um CPF é inválido."""
    def __init__(self, cpf=None):
        message = "CPF inválido"
        if cpf:
            message = f"{message}: '{cpf}'"
        super().__init__(message, campo='cpf', valor=cpf)


class NCInvalidoError(DadosInvalidosError):
    """Erro quando um Número de Cadastro (NC) é inválido."""
    def __init__(self, nc=None):
        message = "NC inválido"
        if nc:
            message = f"{message}: '{nc}'"
        super().__init__(message, campo='nc', valor=nc)


class EmpresaInvalidaError(DadosInvalidosError):
    """Erro quando o código da empresa é inválido."""
    def __init__(self, empresa=None, empresas_validas=None):
        message = "Empresa inválida"
        if empresa:
            message = f"{message}: '{empresa}'"
        if empresas_validas:
            message = f"{message}. Empresas válidas: {', '.join(empresas_validas)}"
        super().__init__(message, campo='empresa', valor=empresa)


class ContratoInvalidoError(DadosInvalidosError):
    """Erro quando o contrato é inválido."""
    def __init__(self, contrato=None):
        message = "Contrato inválido"
        if contrato:
            message = f"{message}: '{contrato}'"
        super().__init__(message, campo='contrato', valor=contrato)


class ValorInvalidoError(DadosInvalidosError):
    """Erro quando um valor monetário é inválido."""
    def __init__(self, valor=None, campo='valor'):
        message = f"Valor inválido"
        if valor:
            message = f"{message}: '{valor}'"
        super().__init__(message, campo=campo, valor=valor)


class DataInvalidaError(DadosInvalidosError):
    """Erro quando uma data é inválida."""
    def __init__(self, data=None, campo='data'):
        message = "Data inválida"
        if data:
            message = f"{message}: '{data}'"
        super().__init__(message, campo=campo, valor=data)


# EXCEÇÕES PARA COLABORADORES E NCs
class ColaboradorNaoEncontradoError(SistemaCIError):
    """Erro quando um colaborador não é encontrado."""
    def __init__(self, cpf=None, nc=None, id=None):
        message = "Colaborador não encontrado"
        if cpf:
            message = f"{message} (CPF: {cpf})"
        elif nc:
            message = f"{message} (NC: {nc})"
        elif id:
            message = f"{message} (ID: {id})"
        super().__init__(message, code=404)


class CINaoEncontradoError(SistemaCIError):
    """Erro quando um Colaborador Interno não é encontrado."""
    def __init__(self, id=None, cpf=None, nc=None):
        message = "Colaborador Interno não encontrado"
        if id:
            message = f"{message} (ID: {id})"
        elif cpf:
            message = f"{message} (CPF: {cpf})"
        elif nc:
            message = f"{message} (NC: {nc})"
        super().__init__(message, code=404)


class NCDuplicadoError(SistemaCIError):
    """Erro quando um NC está duplicado."""
    def __init__(self, nc=None):
        message = "NC duplicado"
        if nc:
            message = f"{message}: {nc}"
        super().__init__(message, code=409)


class NCEmUsoError(SistemaCIError):
    """Erro quando um NC já está em uso por outro colaborador."""
    def __init__(self, nc=None, colaborador_id=None, colaborador_nome=None):
        message = "NC já está em uso"
        if nc:
            message = f"{message}: {nc}"
        if colaborador_nome:
            message = f"{message} por {colaborador_nome}"
        elif colaborador_id:
            message = f"{message} (ID do colaborador: {colaborador_id})"
        self.nc = nc
        self.colaborador_id = colaborador_id
        self.colaborador_nome = colaborador_nome
        super().__init__(message, code=409)


class CPFJaCadastradoError(SistemaCIError):
    """Erro quando um CPF já está cadastrado para outro colaborador."""
    def __init__(self, cpf=None, colaborador_id=None, colaborador_nome=None):
        message = "CPF já cadastrado"
        if cpf:
            message = f"{message}: {cpf}"
        if colaborador_nome:
            message = f"{message} para {colaborador_nome}"
        elif colaborador_id:
            message = f"{message} (ID do colaborador: {colaborador_id})"
        self.cpf = cpf
        self.colaborador_id = colaborador_id
        self.colaborador_nome = colaborador_nome
        super().__init__(message, code=409)


class ColaboradorExcluidoError(SistemaCIError):
    """Erro quando tentam acessar ou modificar um colaborador excluído."""
    def __init__(self, colaborador_id=None, colaborador_nome=None):
        message = "Colaborador excluído"
        if colaborador_nome:
            message = f"{message}: {colaborador_nome}"
        elif colaborador_id:
            message = f"{message} (ID: {colaborador_id})"
        self.colaborador_id = colaborador_id
        self.colaborador_nome = colaborador_nome
        super().__init__(message, code=410)  # 410 Gone


class ColaboradorInativoError(SistemaCIError):
    """Erro quando um colaborador está inativo."""
    def __init__(self, colaborador_id=None, colaborador_nome=None):
        message = "Colaborador inativo"
        if colaborador_nome:
            message = f"{message}: {colaborador_nome}"
        elif colaborador_id:
            message = f"{message} (ID: {colaborador_id})"
        super().__init__(message, code=400)


class ColaboradorComPlanosAtivosError(SistemaCIError):
    """Erro quando um colaborador tem planos ativos vinculados."""
    def __init__(self, colaborador_id=None, colaborador_nome=None, quantidade_planos=0):
        message = f"Colaborador possui {quantidade_planos} plano(s) ativo(s)"
        if colaborador_nome:
            message = f"{message}: {colaborador_nome}"
        elif colaborador_id:
            message = f"{message} (ID: {colaborador_id})"
        super().__init__(message, code=409)


class NCInativoError(SistemaCIError):
    """Erro quando um NC está inativo."""
    def __init__(self, nc=None):
        message = "NC inativo"
        if nc:
            message = f"{message}: {nc}"
        super().__init__(message, code=400)


class CIEmpresaAtivaError(SistemaCIError):
    """Erro quando um CI já tem uma empresa ativa."""
    def __init__(self, ci_id=None, empresa_cod=None, empresa_nome=None):
        message = "Colaborador já possui empresa ativa"
        if empresa_cod:
            if empresa_nome:
                message = f"{message}: {empresa_cod} ({empresa_nome})"
            else:
                message = f"{message}: {empresa_cod}"
        super().__init__(message, code=409)


class CIExcluidoError(SistemaCIError):
    """Erro quando tentam acessar um CI excluído."""
    def __init__(self, ci_id=None, ci_nome=None):
        message = "Colaborador Interno excluído"
        if ci_nome:
            message = f"{message}: {ci_nome}"
        elif ci_id:
            message = f"{message} (ID: {ci_id})"
        super().__init__(message, code=410)  # 410 Gone


class PlanosVinculadosError(SistemaCIError):
    """Erro quando um CI tem planos vinculados ativos."""
    def __init__(self, ci_id=None, quantidade_planos=0):
        message = f"Colaborador possui {quantidade_planos} plano(s) ativo(s) vinculado(s)"
        super().__init__(message, code=409)


class HistoricoNaoEncontradoError(SistemaCIError):
    """Erro quando um histórico não é encontrado."""
    def __init__(self, historico_id=None, ci_id=None):
        message = "Histórico não encontrado"
        if historico_id:
            message = f"{message} (ID: {historico_id})"
        elif ci_id:
            message = f"{message} para o CI (ID: {ci_id})"
        super().__init__(message, code=404)


# EXCEÇÕES PARA OPERAÇÕES DO SISTEMA
class BancoDadosError(SistemaCIError):
    """Erro de banco de dados."""
    def __init__(self, message="Erro de banco de dados", operacao=None):
        if operacao:
            message = f"{message} durante {operacao}"
        super().__init__(message, code=500)


class ValidacaoError(SistemaCIError):
    """Erro de validação de dados."""
    def __init__(self, message="Erro de validação", campos=None):
        self.campos = campos or []
        if campos:
            message = f"{message}: {', '.join(campos)}"
        super().__init__(message, code=400)


class AutenticacaoError(SistemaCIError):
    """Erro de autenticação."""
    def __init__(self, message="Erro de autenticação"):
        super().__init__(message, code=401)


class AutorizacaoError(SistemaCIError):
    """Erro de autorização (permissão)."""
    def __init__(self, message="Acesso não autorizado"):
        super().__init__(message, code=403)


class ConfiguracaoError(SistemaCIError):
    """Erro de configuração do sistema."""
    def __init__(self, message="Erro de configuração", chave=None):
        if chave:
            message = f"{message}: {chave}"
        super().__init__(message, code=500)


class PDFProcessamentoError(ImportacaoError):
    """Erro específico para processamento de PDF."""
    def __init__(self, message="Erro ao processar PDF", operadora=None):
        if operadora:
            message = f"{message} da {operadora}"
        super().__init__(message)


class AlertaError(SistemaCIError):
    """Erro relacionado a alertas."""
    def __init__(self, message="Erro no sistema de alertas"):
        super().__init__(message, code=500)


class ExportacaoError(SistemaCIError):
    """Erro durante exportação de dados."""
    def __init__(self, message="Erro na exportação", formato=None):
        if formato:
            message = f"{message} para formato {formato}"
        super().__init__(message, code=500)


class OperacaoNaoPermitidaError(SistemaCIError):
    """Erro quando uma operação não é permitida."""
    def __init__(self, message="Operação não permitida"):
        super().__init__(message, code=403)


# EXCEÇÕES PARA IMPORTAÇÃO ESPECÍFICA
class ImportacaoUnimedError(ImportacaoError):
    """Erro específico para importação da UNIMED."""
    def __init__(self, message="Erro na importação da UNIMED", tipo=None):
        if tipo:
            message = f"{message} - Tipo: {tipo}"
        super().__init__(message)


class ImportacaoHapvidaError(ImportacaoError):
    """Erro específico para importação da HAPVIDA."""
    def __init__(self, message="Erro na importação da HAPVIDA", tipo=None, empresa=None):
        if tipo:
            message = f"{message} - Tipo: {tipo}"
        if empresa:
            message = f"{message} - Empresa: {empresa}"
        super().__init__(message)


class ImportacaoOdontoprevError(ImportacaoError):
    """Erro específico para importação da ODONTOPREV."""
    def __init__(self, message="Erro na importação da ODONTOPREV"):
        super().__init__(message)


class ImportacaoAtivosError(ImportacaoError):
    """Erro específico para importação de ativos."""
    def __init__(self, message="Erro na importação de ativos"):
        super().__init__(message)


class ImportacaoDesligadosError(ImportacaoError):
    """Erro específico para importação de desligados."""
    def __init__(self, message="Erro na importação de desligados"):
        super().__init__(message)


# EXCEÇÕES PARA DEPENDENTES
class DependenteNaoEncontradoError(SistemaCIError):
    """Erro quando um dependente não é encontrado."""
    def __init__(self, dependente_id=None, ci_id=None):
        message = "Dependente não encontrado"
        if dependente_id:
            message = f"{message} (ID: {dependente_id})"
        elif ci_id:
            message = f"{message} para o CI (ID: {ci_id})"
        super().__init__(message, code=404)


class DependenteDuplicadoError(SistemaCIError):
    """Erro quando um dependente está duplicado."""
    def __init__(self, nome=None, cpf=None, ci_id=None):
        message = "Dependente duplicado"
        if nome:
            message = f"{message}: {nome}"
        if cpf:
            message = f"{message} (CPF: {cpf})"
        super().__init__(message, code=409)


# EXCEÇÕES PARA PLANOS
class PlanoNaoEncontradoError(SistemaCIError):
    """Erro quando um plano não é encontrado."""
    def __init__(self, plano_id=None, ci_id=None):
        message = "Plano não encontrado"
        if plano_id:
            message = f"{message} (ID: {plano_id})"
        elif ci_id:
            message = f"{message} para o CI (ID: {ci_id})"
        super().__init__(message, code=404)


class PlanoInativoError(SistemaCIError):
    """Erro quando um plano está inativo."""
    def __init__(self, plano_id=None):
        message = "Plano inativo"
        if plano_id:
            message = f"{message} (ID: {plano_id})"
        super().__init__(message, code=400)


# Funções utilitárias para tratamento de exceções
def tratar_erro_importacao(e, contexto=None):
    """
    Converte exceções genéricas em exceções específicas de importação.
    
    Args:
        e: Exceção original
        contexto: Dicionário com contexto adicional (arquivo, linha, etc)
    
    Returns:
        Exceção apropriada do sistema
    """
    contexto = contexto or {}
    
    if isinstance(e, (ValueError, TypeError)) and 'data' in str(e).lower():
        return DataInvalidaError(
            data=contexto.get('valor'),
            campo=contexto.get('campo', 'data')
        )
    elif isinstance(e, (ValueError, TypeError)) and any(
        term in str(e).lower() for term in ['cpf', 'número', 'number']
    ):
        return CPFInvalidoError(cpf=contexto.get('valor'))
    elif isinstance(e, ValueError):
        return DadosInvalidosError(
            message=str(e),
            campo=contexto.get('campo'),
            valor=contexto.get('valor')
        )
    elif isinstance(e, KeyError):
        return DadosInvalidosError(
            message=f"Campo obrigatório ausente: {e}",
            campo=str(e)
        )
    
    # Se não conseguir mapear, retorna uma ImportacaoError genérica
    return ImportacaoError(
        message=str(e),
        arquivo=contexto.get('arquivo'),
        linha=contexto.get('linha')
    )


def formatar_erro_para_usuario(e):
    """
    Formata uma exceção para exibição amigável ao usuário.
    
    Args:
        e: Exceção
    
    Returns:
        Tupla (mensagem_usuario, detalhes_tecnicos)
    """
    if isinstance(e, SistemaCIError):
        # Exceções do sistema já têm mensagens amigáveis
        mensagem_usuario = e.message
        
        # Adiciona detalhes específicos se disponíveis
        if isinstance(e, DadosInvalidosError) and e.campo:
            if e.valor:
                mensagem_usuario = f"{mensagem_usuario} (Valor: {e.valor})"
        
        detalhes_tecnicos = str(e)
        
    else:
        # Exceções genéricas: mensagem genérica para usuário
        mensagem_usuario = "Ocorreu um erro interno no sistema"
        detalhes_tecnicos = f"{type(e).__name__}: {str(e)}"
    
    return mensagem_usuario, detalhes_tecnicos


def log_excecao(e, logger, contexto=None):
    """
    Registra uma exceção no log com contexto.
    
    Args:
        e: Exceção
        logger: Objeto logger
        contexto: Dicionário com contexto adicional
    """
    contexto = contexto or {}
    
    # Determina nível de log baseado no tipo de exceção
    if isinstance(e, (AutenticacaoError, AutorizacaoError)):
        nivel = 'warning'
    elif isinstance(e, (ValidacaoError, DadosInvalidosError)):
        nivel = 'info'
    else:
        nivel = 'error'
    
    # Mensagem de log
    mensagem = f"Exceção: {type(e).__name__}"
    if contexto:
        mensagem += f" | Contexto: {contexto}"
    mensagem += f" | Mensagem: {str(e)}"
    
    # Log com stack trace para erros internos
    if nivel == 'error':
        logger.error(mensagem, exc_info=True)
    elif nivel == 'warning':
        logger.warning(mensagem)
    else:
        logger.info(mensagem)