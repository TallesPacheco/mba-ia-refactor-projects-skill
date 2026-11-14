from errors import ValidationError
from models.constants import CATEGORIA_PADRAO, CATEGORIAS_VALIDAS, NOME_PRODUTO_MAX, NOME_PRODUTO_MIN
from validators.common import is_int, is_number


def validar_produto(dados):
    """Validação única para criação e atualização de produto."""
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    if "nome" not in dados:
        raise ValidationError("Nome é obrigatório")
    if "preco" not in dados:
        raise ValidationError("Preço é obrigatório")
    if "estoque" not in dados:
        raise ValidationError("Estoque é obrigatório")

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not isinstance(nome, str):
        raise ValidationError("Nome deve ser texto")
    if descricao is None:
        descricao = ""
    if not isinstance(descricao, str):
        raise ValidationError("Descrição deve ser texto")
    if not is_number(preco):
        raise ValidationError("Preço deve ser numérico")
    if not is_int(estoque):
        raise ValidationError("Estoque deve ser um número inteiro")

    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_PRODUTO_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_PRODUTO_MAX:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS))

    return {"nome": nome, "descricao": descricao, "preco": preco, "estoque": estoque, "categoria": categoria}


def validar_filtros_busca(args):
    def _preco(nome_param):
        valor = args.get(nome_param, None)
        if valor is None or valor == "":
            return None  # ausente: o model distingue None (sem filtro) de 0 (filtro válido)
        try:
            return float(valor)
        except ValueError:
            raise ValidationError(nome_param + " inválido")

    return {
        "termo": args.get("q", ""),
        "categoria": args.get("categoria", None),
        "preco_min": _preco("preco_min"),
        "preco_max": _preco("preco_max"),
    }
