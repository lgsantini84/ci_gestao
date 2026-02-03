"""
Utilitários para manipulação de dados.
"""

import json
from datetime import datetime, date
from dateutil import parser
import pytz

_TZ = pytz.timezone('America/Sao_Paulo')

def to_brasilia(dt):
    """Converte datetime para fuso horário de Brasília (retorna datetime)."""
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = parser.parse(dt)
        except (ValueError, TypeError):
            return dt
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(_TZ)


def strftime(dt, fmt='%d/%m/%Y %H:%M'):
    """Formata datetime usando strftime."""
    if dt is None:
        return ''
    if isinstance(dt, str):
        return dt
    return dt.strftime(fmt)

def from_json(value):
    """Tenta carregar uma string como JSON."""
    if not value or not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value

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