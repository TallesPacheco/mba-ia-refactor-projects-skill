PRODUTO_COLUNAS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


def row_to_produto(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def listar(conn):
    rows = conn.execute(f"SELECT {PRODUTO_COLUNAS} FROM produtos ORDER BY id").fetchall()
    return [row_to_produto(row) for row in rows]


def buscar_por_id(conn, produto_id):
    row = conn.execute(f"SELECT {PRODUTO_COLUNAS} FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return row_to_produto(row) if row else None


def buscar_por_ids(conn, produto_ids):
    ids = list(set(produto_ids))
    if not ids:
        return {}
    placeholders = ", ".join("?" for _ in ids)
    rows = conn.execute(f"SELECT {PRODUTO_COLUNAS} FROM produtos WHERE id IN ({placeholders})", ids).fetchall()
    return {row["id"]: row_to_produto(row) for row in rows}


def buscar(conn, termo=None, categoria=None, preco_min=None, preco_max=None):
    clausulas, params = ["1=1"], []
    if termo:
        clausulas.append("(nome LIKE ? OR descricao LIKE ?)")
        params.extend([f"%{termo}%", f"%{termo}%"])
    if categoria:
        clausulas.append("categoria = ?")
        params.append(categoria)
    if preco_min is not None:
        clausulas.append("preco >= ?")
        params.append(preco_min)
    if preco_max is not None:
        clausulas.append("preco <= ?")
        params.append(preco_max)
    sql = f"SELECT {PRODUTO_COLUNAS} FROM produtos WHERE {' AND '.join(clausulas)} ORDER BY id"
    return [row_to_produto(row) for row in conn.execute(sql, params).fetchall()]


def criar(conn, nome, descricao, preco, estoque, categoria):
    with conn:
        cursor = conn.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
    return cursor.lastrowid


def atualizar(conn, produto_id, nome, descricao, preco, estoque, categoria):
    with conn:
        conn.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )


def deletar(conn, produto_id):
    with conn:
        conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))


def baixar_estoque(conn, produto_id, quantidade):
    """Baixa condicional; retorna False se o estoque não for suficiente. Deve rodar dentro de uma transação."""
    cursor = conn.execute(
        "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
        (quantidade, produto_id, quantidade),
    )
    return cursor.rowcount == 1


def contar(conn):
    return conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
