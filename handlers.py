"""
Camada de conversa. Nunca consulta banco, nunca faz request pro ML.
Só recebe mensagem, valida quem pode falar com o bot, e chama o service.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

import config
from services import monitoring_service

logger = logging.getLogger(__name__)


def _autorizado(chat_id: int) -> bool:
    if not config.ALLOWED_USER_IDS:
        return True  # sem restrição configurada
    return chat_id in config.ALLOWED_USER_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _autorizado(update.effective_chat.id):
        return
    await update.message.reply_text(
        "Oi! Me manda o link de um anúncio do Mercado Livre que eu começo a "
        "monitorar o preço e te aviso automaticamente se cair de verdade."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not _autorizado(chat_id):
        logger.info("Mensagem ignorada de chat_id não autorizado: %s", chat_id)
        return

    texto = update.message.text or ""
    resposta = monitoring_service.registrar_link(chat_id, texto)
    await update.message.reply_text(resposta, parse_mode="Markdown")


async def verificacao_periodica(context: ContextTypes.DEFAULT_TYPE):
    """Job chamado pelo scheduler do próprio python-telegram-bot."""
    notificacoes = monitoring_service.verificar_todos()
    for chat_id, texto in notificacoes:
        try:
            await context.bot.send_message(chat_id=chat_id, text=texto, parse_mode="Markdown")
        except Exception as e:
            logger.warning("Erro enviando notificação pra %s: %s", chat_id, e)
