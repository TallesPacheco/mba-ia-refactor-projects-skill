APP_VERSION = "1.0.0"

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
CATEGORIA_PADRAO = "geral"

NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

SENHA_MIN = 6
SENHA_MAX = 128

STATUS_PENDENTE = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_ENVIADO = "enviado"
STATUS_ENTREGUE = "entregue"
STATUS_CANCELADO = "cancelado"
STATUS_PEDIDO_VALIDOS = [STATUS_PENDENTE, STATUS_APROVADO, STATUS_ENVIADO, STATUS_ENTREGUE, STATUS_CANCELADO]

TIPO_CLIENTE = "cliente"
TIPO_ADMIN = "admin"

# (faturamento mínimo exclusivo, percentual de desconto), do maior para o menor
FAIXAS_DESCONTO = ((10000, 0.1), (5000, 0.05), (1000, 0.02))
