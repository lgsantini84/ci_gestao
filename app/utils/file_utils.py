"""
Utilitários para manipulação de arquivos.
"""

import os
import pandas as pd
import pdfplumber
import re
from werkzeug.utils import secure_filename

def allowed_file(filename, allowed_extensions):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def secure_upload(file, upload_folder, allowed_extensions):
    """Salva arquivo de upload de forma segura."""
    if not file or file.filename == '':
        return None, 'Nenhum arquivo selecionado'
    
    if not allowed_file(file.filename, allowed_extensions):
        return None, 'Tipo de arquivo não permitido'
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    
    # Criar diretório se não existir
    os.makedirs(upload_folder, exist_ok=True)
    
    file.save(filepath)
    return filepath, None