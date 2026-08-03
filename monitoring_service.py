"""
Regra de negócio. Não sabe nada de Telegram, não monta SQL na mão.
Chama o provider pra descobrir preço, e o repository pra persistir.
"""

import logging

import config
from database import repository
from providers import mercadolivre

logger = logging.getLogger(__name__)


def fmt(v: float) -> str:
    """Formata número no padrão brasileiro (R$ 1.234,56)."""
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def registrar_link(telegram_chat_id: int, texto: str) -> str:
    """Chamado quando o usuário manda uma mensagem com um link. Retorna o texto de resposta."""
    item_id = mercadolivre.extrair_item_id(texto)
    if not item_id:
        return "Não achei um link de anúncio do Mercado Livre nessa mensagem. Manda o link do produto."

    info = mercadolivre.consultar(item_id)
    if not info:
        return "Não consegui consultar esse anúncio agora (pode ter sido removido ou o link mudou)."

    usuario_id = repository.get_or_create_usuario(telegram_chat_id)
    produto_id = repository.get_or_create_produto(item_id, info["titulo"], info["url"])
    repository.criar_monitoramento(usuario_id, produto_id)
    repository.salvar_preco(produto_id, info["preco"])

    return _montar_analise(produto_id, info["titulo"], info["preco"], recem_registrado=True)


def verificar_todos() -> list[tuple[int, str]]:
    """
    Chamado pelo scheduler. Consulta todos os produtos ativos, salva o preço
    novo e retorna uma lista de (chat_id, mensagem) só para os casos que
    valem notificação (queda real, não qualquer variação).
    """
    notificacoes = []
    produtos = repository.listar_produtos_ativos()

    for produto in produtos:
        info = mercadolivre.consultar(produto["item_id"])
        if not info:
            continue

        historico_antes = repository.get_historico(produto["id"])
        repository.salvar_preco(produto["id"], info["preco"])

        if not historico_antes:
            continue  # não tinha histórico prévio, nada a comparar ainda

        precos_antes = [r["preco"] for r in historico_antes]
        media_antes = sum(precos_antes) / len(precos_antes)
        minimo_antes = min(precos_antes)
        ultimo_preco = precos_antes[-1]  # preço na última verificação, não a média

        # Compara com o último preço visto (evita re-alertar preço estável só
        # porque a média histórica ainda carrega valores antigos mais altos)
        queda_desde_ultimo = ((ultimo_preco - info["preco"]) / ultimo_preco) * 100
        eh_novo_minimo = info["preco"] < minimo_antes

        if eh_novo_minimo or queda_desde_ultimo >= config.MIN_ALERT_PERCENT:
            texto = _montar_alerta(produto["titulo"], info["preco"], media_antes, minimo_antes, produto["url"])
            for u in repository.listar_usuarios_do_produto(produto["id"]):
                notificacoes.append((u["telegram_chat_id"], texto))

    return notificacoes


def _montar_analise(produto_id: int, titulo: str, preco_atual: float, recem_registrado: bool) -> str:
    historico = repository.get_historico(produto_id)

    if len(historico) <= 1:
        return (
            f"📌 *{titulo}*\n"
            f"Preço atual: {fmt(preco_atual)}\n\n"
            f"Monitoramento iniciado. Vou acompanhar esse anúncio e te aviso "
            f"automaticamente se o preço cair de verdade."
        )

    precos = [r["preco"] for r in historico]
    minimo, maximo = min(precos), max(precos)
    media = sum(precos) / len(precos)
    primeira_data = historico[0]["capturado_em"][:10]
    diff_pct = ((preco_atual - media) / media) * 100

    if preco_atual <= minimo:
        veredito = "🟢 Esse é o MENOR preço que já vi nesse anúncio."
    elif diff_pct <= -10:
        veredito = f"🟢 Tá {abs(diff_pct):.0f}% abaixo da média observada. Bom sinal."
    elif diff_pct >= 10:
        veredito = f"🔴 Tá {diff_pct:.0f}% acima da média observada. Não parece desconto real."
    else:
        veredito = "🟡 Tá dentro da faixa normal que já vi pra esse anúncio."

    return (
        f"📌 *{titulo}*\n"
        f"Preço atual: {fmt(preco_atual)}\n\n"
        f"Histórico desde {primeira_data} ({len(historico)} capturas):\n"
        f"• Mínimo: {fmt(minimo)}\n"
        f"• Média: {fmt(media)}\n"
        f"• Máximo: {fmt(maximo)}\n\n"
        f"{veredito}\n\n"
        f"Vou continuar acompanhando e te aviso se cair mais."
    )


def _montar_alerta(titulo: str, preco_atual: float, media_antes: float, minimo_antes: float, url: str) -> str:
    economia = media_antes - preco_atual
    queda_pct = (economia / media_antes) * 100
    novo_minimo = "\n\nMenor preço já registrado. 🏆" if preco_atual < minimo_antes else ""

    return (
        f"🔥 *OPORTUNIDADE*\n\n"
        f"📌 {titulo}\n\n"
        f"Média anterior: {fmt(media_antes)}\n"
        f"Preço atual: {fmt(preco_atual)}\n"
        f"Economia: {fmt(economia)} (↓{queda_pct:.0f}%)"
        f"{novo_minimo}\n\n"
        f"{url}"
    )
