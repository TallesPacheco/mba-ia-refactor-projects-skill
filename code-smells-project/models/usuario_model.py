from models.constants import TIPO_CLIENTE

USUARIO_COLUNAS_PUBLICAS = "id, nome, email, tipo, criado_em"


def row_to_usuario(row):
    # A senha (hash) nunca é serializada.
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


def listar(conn):
    rows = conn.execute(f"SELECT {USUARIO_COLUNAS_PUBLICAS} FROM usuarios ORDER BY id").fetchall()
    return [row_to_usuario(row) for row in rows]


def buscar_por_id(conn, usuario_id):
    row = conn.execute(f"SELECT {USUARIO_COLUNAS_PUBLICAS} FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return row_to_usuario(row) if row else None


def buscar_credenciais_por_email(conn, email):
    return conn.execute("SELECT id, nome, email, senha, tipo FROM usuarios WHERE email = ?", (email,)).fetchone()


def existe(conn, usuario_id):
    return conn.execute("SELECT 1 FROM usuarios WHERE id = ?", (usuario_id,)).fetchone() is not None


def email_existe(conn, email):
    return conn.execute("SELECT 1 FROM usuarios WHERE email = ?", (email,)).fetchone() is not None


def criar(conn, nome, email, senha_hash, tipo=TIPO_CLIENTE):
    with conn:
        cursor = conn.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, senha_hash, tipo),
        )
    return cursor.lastrowid


def contar(conn):
    return conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
