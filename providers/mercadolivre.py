"""
Tudo que é específico do Mercado Livre mora aqui. O resto do sistema não
sabe (nem precisa saber) como o ML funciona por dentro.

Se um dia adicionarmos outra loja, ela ganha seu próprio arquivo aqui em
providers/, seguindo essa mesma interface: extrair_item_id() e consultar().
"""

import re
import logging

import requests

logger = logging.getLogger(__name__)

ID_REGEX = re.compile(r"(MLB-?\d{6,})", re.IGNORECASE)

# Sem isso, alguns encurtadores (ex: meli.la) bloqueiam a requisição por
# parecer tráfego de bot, mesmo só seguindo redirect.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
    )
}


def extrair_item_id(texto: str) -> str | None:
    """Extrai o item_id de uma mensagem, seguindo redirect se for link curto."""
    match = ID_REGEX.search(texto)
    if match:
        return _normaliza(match.group(1))

    url_match = re.search(r"https?://\S+", texto)
    if not url_match:
        return None

    try:
        resp = requests.get(
            url_match.group(0), headers=_HEADERS, allow_redirects=True, timeout=10
        )
        match = ID_REGEX.search(resp.url)
        if match:
            return _normaliza(match.group(1))
        match = ID_REGEX.search(resp.text[:20000])
        if match:
            return _normaliza(match.group(1))
    except requests.RequestException as e:
        logger.warning("Erro seguindo redirect: %s", e)
    return None


def consultar(item_id: str) -> dict | None:
    """Consulta a API pública do ML. Não requer autenticação para dados básicos."""
    url = f"https://api.mercadolibre.com/items/{item_id}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            logger.warning("ML API retornou %s para %s", resp.status_code, item_id)
            return None
        data = resp.json()
        if data.get("price") is None:
            return None
        return {
            "titulo": data.get("title", "Produto"),
            "preco": data["price"],
            "url": data.get("permalink", url),
            "disponivel": data.get("available_quantity", 0) > 0,
        }
    except requests.RequestException as e:
        logger.warning("Erro consultando ML API: %s", e)
        return None


def _normaliza(item_id: str) -> str:
    return item_id.upper().replace("MLB-", "MLB")
