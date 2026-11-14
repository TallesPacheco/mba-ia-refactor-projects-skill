from models.constants import STATUS_APROVADO, STATUS_CANCELADO, STATUS_PENDENTE

_SELECT_PEDIDOS_COM_ITENS = """
    SELECT p.id AS pedido_id, p.usuario_id, p.status, p.total, p.criado_em,
           i.id AS item_id, i.produto_id, i.quantidade, i.preco_unitario,
           pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
"""


def _agrupar(rows):
    pedidos = {}
    for row in rows:
        pedido = pedidos.setdefault(row["pedido_id"], {
            "id": row["pedido_id"],
            "usuario_id": row["usuario_id"],
            "status": row["status"],
            "total": row["total"],
            "criado_em": row["criado_em"],
            "itens": [],
        })
        if row["item_id"] is not None:
            pedido["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] if row["produto_nome"] is not None else "Desconhecido",
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
    return list(pedidos.values())


def listar(conn, usuario_id=None):
    sql, params = _SELECT_PEDIDOS_COM_ITENS, []
    if usuario_id is not None:
        sql += " WHERE p.usuario_id = ?"
        params.append(usuario_id)
    sql += " ORDER BY p.id, i.id"
    return _agrupar(conn.execute(sql, params).fetchall())


def existe(conn, pedido_id):
    return conn.execute("SELECT 1 FROM pedidos WHERE id = ?", (pedido_id,)).fetchone() is not None


def inserir(conn, usuario_id, total, status=STATUS_PENDENTE):
    """Deve rodar dentro de uma transação aberta pelo service."""
    cursor = conn.execute(
        "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
        (usuario_id, status, total),
    )
    return cursor.lastrowid


def inserir_item(conn, pedido_id, produto_id, quantidade, preco_unitario):
    conn.execute(
        "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
        (pedido_id, produto_id, quantidade, preco_unitario),
    )


def atualizar_status(conn, pedido_id, novo_status):
    with conn:
        conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))


def resumo_vendas(conn):
    row = conn.execute(
        """
        SELECT COUNT(*) AS total_pedidos,
               COALESCE(SUM(total), 0) AS faturamento,
               COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS pendentes,
               COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS aprovados,
               COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS cancelados
        FROM pedidos
        """,
        (STATUS_PENDENTE, STATUS_APROVADO, STATUS_CANCELADO),
    ).fetchone()
    return dict(row)


def contar(conn):
    return conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
