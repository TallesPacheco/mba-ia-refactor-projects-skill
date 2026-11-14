import logging
import os
import secrets

from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        descricao TEXT,
        preco REAL NOT NULL,
        estoque INTEGER NOT NULL,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        status TEXT DEFAULT 'pendente',
        total REAL NOT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # produto_id sem FK de propósito: o histórico do pedido sobrevive à deleção do produto
    # (a resposta mostra "Desconhecido"), como no comportamento original. A existência do
    # produto é validada na escrita por services/pedido_service.py.
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
        produto_id INTEGER NOT NULL,
        quantidade INTEGER NOT NULL,
        preco_unitario REAL NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_pedidos_usuario_id ON pedidos(usuario_id)",
    "CREATE INDEX IF NOT EXISTS idx_itens_pedido_pedido_id ON itens_pedido(pedido_id)",
)

SEED_PRODUTOS = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]

# (nome, email, variável de ambiente com a senha, tipo). Nenhuma senha nem hash fica no código:
# sem a variável definida, uma senha aleatória é gerada e registrada uma única vez no log.
SEED_USUARIOS = [
    ("Admin", "admin@loja.com", "SEED_ADMIN_PASSWORD", "admin"),
    ("João Silva", "joao@email.com", "SEED_JOAO_PASSWORD", "cliente"),
    ("Maria Santos", "maria@email.com", "SEED_MARIA_PASSWORD", "cliente"),
]


def senha_de_seed(variavel):
    valor = os.environ.get(variavel)
    if valor:
        return valor
    if os.environ.get("APP_ENV", "development") not in ("development", "test"):
        raise RuntimeError(variavel + " é obrigatória fora de development/test")
    valor = secrets.token_urlsafe(12)
    logger.warning("[seed] %s não definida; senha gerada para esta execução: %s", variavel, valor)
    return valor


def init_schema(conn):
    with conn:
        for statement in SCHEMA:
            conn.execute(statement)
    seed(conn)


def seed(conn):
    if conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] != 0:
        return
    with conn:
        conn.executemany(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            SEED_PRODUTOS,
        )
        if conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                [
                    (nome, email, generate_password_hash(senha_de_seed(variavel)), tipo)
                    for nome, email, variavel, tipo in SEED_USUARIOS
                ],
            )
