"""
Utilitários gerais da aplicação
"""

from datetime import datetime, timezone


def now() -> datetime:
    """
    Retorna o datetime atual com timezone UTC.

    Esta função deve ser usada no lugar de datetime.utcnow() ou datetime.now()
    para garantir que todos os timestamps tenham informação de timezone.

    O backend sempre salva em UTC, e o frontend converte para o timezone local do usuário.

    Returns:
        datetime: Timestamp atual em UTC com timezone aware
    """
    return datetime.now(timezone.utc)
