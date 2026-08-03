"""
Ponto de entrada. Só monta as peças: inicializa banco, registra handlers,
registra o job periódico, sobe o bot.
"""

import logging

from telegram.ext import Application, MessageHandler, CommandHandler, filters

import config
from database.db import init_db
from bot import handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    if not config.TELEGRAM_TOKEN:
        raise SystemExit("Defina a variável de ambiente TELEGRAM_TOKEN antes de rodar.")

    init_db()

    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))

    intervalo_segundos = config.CHECK_INTERVAL_HOURS * 3600
    app.job_queue.run_repeating(
        handlers.verificacao_periodica,
        interval=intervalo_segundos,
        first=intervalo_segundos,  # espera um ciclo antes da 1ª verificação automática
    )

    logger.info(
        "Bot rodando. Verificação automática a cada %.1fh, alerta a partir de %.0f%% de queda.",
        config.CHECK_INTERVAL_HOURS, config.MIN_ALERT_PERCENT,
    )
    app.run_polling()


if __name__ == "__main__":
    main()
