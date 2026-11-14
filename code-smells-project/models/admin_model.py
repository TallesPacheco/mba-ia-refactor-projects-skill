def resetar(conn):
    with conn:
        conn.execute("DELETE FROM itens_pedido")
        conn.execute("DELETE FROM pedidos")
        conn.execute("DELETE FROM produtos")
        conn.execute("DELETE FROM usuarios")


def consultar(conn_somente_leitura, sql):
    rows = conn_somente_leitura.execute(sql).fetchall()
    return [dict(row) for row in rows]
