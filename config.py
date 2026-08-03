"""
Configuração central do projeto. Tudo que é ajustável vem de variáveis de
ambiente (.env), nada fica hardcoded no código.
"""

import os


def _get_allowed_ids() -> set[int]:
    raw = os.environ.get("ALLOWED_USER_IDS", "")
    ids = set()
    for parte in raw.split(","):
        parte = parte.strip()
        if parte:
            ids.add(int(parte))
    return ids


TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

# Se vazio, o bot responde a qualquer pessoa. Se tiver IDs, só responde a eles.
ALLOWED_USER_IDS = _get_allowed_ids()

# De quanto em quanto tempo o scheduler verifica os produtos monitorados
CHECK_INTERVAL_HOURS = float(os.environ.get("CHECK_INTERVAL_HOURS", "6"))

# Queda mínima (%) em relação à média histórica pra disparar notificação
MIN_ALERT_PERCENT = float(os.environ.get("MIN_ALERT_PERCENT", "10"))

DB_PATH = os.environ.get("DB_PATH", "ml_watcher.db")
