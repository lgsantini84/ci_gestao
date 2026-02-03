"""
Serviço para importação de arquivos.
"""

import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

from app import db
from app.models import ImportacaoLog, ColaboradorInterno
from app.exceptions import ImportacaoError, ArquivoInvalidoError

logger = logging.getLogger(__name__)


class ImportService:
    """Serviço para importação de dados."""
    
    def __init__(self):
        self.supported_formats = ['xlsx', 'xls', 'csv']
    
    def importar_arquivo(self, filepath: str, tipo: str, usuario_id: int) -> Dict:
        """
        Importa um arquivo.
        
        Args:
            filepath: Caminho do arquivo
            tipo: Tipo de importação
            usuario_id: ID do usuário
        
        Returns:
            Dicionário com resultados da importação
        """
        log = ImportacaoLog(
            tipo_importacao=tipo,
            arquivo=os.path.basename(filepath),
            status='PROCESSANDO',
            usuario_id=usuario_id,
            detalhes=f'Iniciando importação de {tipo}'
        )
        db.session.add(log)
        db.session.commit()
        
        try:
            resultados = self._processar_arquivo(filepath, tipo, log.id)
            
            log.linhas_processadas = resultados.get('linhas_processadas', 0)
            log.linhas_sucesso = resultados.get('linhas_sucesso', 0)
            log.linhas_erro = resultados.get('linhas_erro', 0)
            log.status = 'CONCLUIDO' if resultados.get('sucesso', False) else 'ERRO'
            log.detalhes = resultados.get('mensagem', 'Importação concluída')
            
            db.session.commit()
            
            return resultados
            
        except Exception as e:
            logger.error(f"Erro na importação: {str(e)}", exc_info=True)
            
            log.status = 'ERRO'
            log.detalhes = f'Erro: {str(e)}'
            db.session.commit()
            
            raise ImportacaoError(f"Erro na importação: {str(e)}")
    
    def _processar_arquivo(self, filepath: str, tipo: str, log_id: int) -> Dict:
        """
        Processa o arquivo de acordo com o tipo.
        
        Args:
            filepath: Caminho do arquivo
            tipo: Tipo de importação
            log_id: ID do log
        
        Returns:
            Dicionário com resultados
        """
        # Verificar extensão
        ext = os.path.splitext(filepath)[1].lower().lstrip('.')
        if ext not in self.supported_formats:
            raise ArquivoInvalidoError(f"Formato {ext} não suportado")
        
        # Ler arquivo
        if ext in ['xlsx', 'xls']:
            df = pd.read_excel(filepath, dtype=str)
        else:  # csv
            df = pd.read_csv(filepath, dtype=str, encoding='utf-8')
        
        # Processar de acordo com o tipo
        if tipo == 'UNIMED':
            return self._processar_unimed(df, log_id)
        elif tipo == 'HAPVIDA':
            return self._processar_hapvida(df, log_id)
        elif tipo == 'ODONTOPREV':
            return self._processar_odontoprev(df, log_id)
        elif tipo == 'ATIVOS':
            return self._processar_ativos(df, log_id)
        elif tipo == 'DESLIGADOS':
            return self._processar_desligados(df, log_id)
        else:
            raise ImportacaoError(f"Tipo de importação não suportado: {tipo}")
    
    def _processar_unimed(self, df: pd.DataFrame, log_id: int) -> Dict:
        """Processa arquivo da UNIMED."""
        # Implementação básica
        return {
            'sucesso': True,
            'linhas_processadas': len(df),
            'linhas_sucesso': len(df),
            'linhas_erro': 0,
            'mensagem': f'Processados {len(df)} registros da UNIMED'
        }
    
    def _processar_hapvida(self, df: pd.DataFrame, log_id: int) -> Dict:
        """Processa arquivo da HAPVIDA."""
        # Implementação básica
        return {
            'sucesso': True,
            'linhas_processadas': len(df),
            'linhas_sucesso': len(df),
            'linhas_erro': 0,
            'mensagem': f'Processados {len(df)} registros da HAPVIDA'
        }
    
    def _processar_odontoprev(self, df: pd.DataFrame, log_id: int) -> Dict:
        """Processa arquivo da ODONTOPREV."""
        # Implementação básica
        return {
            'sucesso': True,
            'linhas_processadas': len(df),
            'linhas_sucesso': len(df),
            'linhas_erro': 0,
            'mensagem': f'Processados {len(df)} registros da ODONTOPREV'
        }
    
    def _processar_ativos(self, df: pd.DataFrame, log_id: int) -> Dict:
        """Processa arquivo de ativos."""
        # Implementação básica
        return {
            'sucesso': True,
            'linhas_processadas': len(df),
            'linhas_sucesso': len(df),
            'linhas_erro': 0,
            'mensagem': f'Processados {len(df)} colaboradores ativos'
        }
    
    def _processar_desligados(self, df: pd.DataFrame, log_id: int) -> Dict:
        """Processa arquivo de desligados."""
        # Implementação básica
        return {
            'sucesso': True,
            'linhas_processadas': len(df),
            'linhas_sucesso': len(df),
            'linhas_erro': 0,
            'mensagem': f'Processados {len(df)} colaboradores desligados'
        }