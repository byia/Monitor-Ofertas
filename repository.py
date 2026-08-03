"""
Repository: só sabe salvar, buscar, atualizar. Não decide nada, não consulta
Mercado Livre, não sabe o que é "oportunidade" ou "desconto".
"""

from datetime import datetime, timedelta

from database.db import get_conn


# --- usuários ---------------------------------------------------------

def get_or_create_usuario(telegram_chat_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM usuarios WHERE telegram_chat_id = ?", (telegram_chat_id,)
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO usuarios (telegram_chat_id) VALUES (?)", (telegram_chat_id,)
        )
        conn.commit()
        return cur.lastrowid


# --- produtos -----------------------------------------------------------

def get_produto_by_item_id(item_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM produtos WHERE item_id = ?", (item_id,)
        ).fetchone()


def get_or_create_produto(item_id: str, titulo: str, url: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM produtos WHERE item_id = ?", (item_id,)
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO produtos (item_id, titulo, url) VALUES (?, ?, ?)",
            (item_id, titulo, url),
        )
        conn.commit()
        return cur.lastrowid


def listar_produtos_ativos():
    """Todo produto com pelo menos um monitoramento ativo."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT DISTINCT p.* FROM produtos p
            JOIN monitoramentos m ON m.produto_id = p.id
            WHERE m.ativo = 1
        """).fetchall()


def listar_usuarios_do_produto(produto_id: int):
    with get_conn() as conn:
        return conn.execute("""
            SELECT u.telegram_chat_id FROM usuarios u
            JOIN monitoramentos m ON m.usuario_id = u.id
            WHERE m.produto_id = ? AND m.ativo = 1
        """, (produto_id,)).fetchall()


# --- monitoramentos -------------------------------------------------------

def criar_monitoramento(usuario_id: int, produto_id: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO monitoramentos (usuario_id, produto_id, ativo)
            VALUES (?, ?, 1)
            ON CONFLICT(usuario_id, produto_id) DO UPDATE SET ativo = 1
        """, (usuario_id, produto_id))
        conn.commit()


# --- histórico de preços ---------------------------------------------------

def salvar_preco(produto_id: int, preco: float):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO historico_precos (produto_id, preco, capturado_em) VALUES (?, ?, ?)",
            (produto_id, preco, datetime.utcnow().isoformat()),
        )
        conn.commit()


def get_historico(produto_id: int, dias: int = 90):
    limite = (datetime.utcnow() - timedelta(days=dias)).isoformat()
    with get_conn() as conn:
        return conn.execute("""
            SELECT preco, capturado_em FROM historico_precos
            WHERE produto_id = ? AND capturado_em >= ?
            ORDER BY capturado_em
        """, (produto_id, limite)).fetchall()
