from errors import ValidationError
from models.constants import SENHA_MAX, SENHA_MIN


def validar_cadastro(dados):
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")
    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not all(isinstance(valor, str) for valor in (nome, email, senha)):
        raise ValidationError("Nome, email e senha devem ser texto")
    email = email.strip()
    local, _, dominio = email.partition("@")
    if not local or "." not in dominio or " " in email:
        raise ValidationError("Email inválido")
    if len(senha) < SENHA_MIN:
        raise ValidationError("Senha deve ter pelo menos %d caracteres" % SENHA_MIN)
    if len(senha) > SENHA_MAX:
        raise ValidationError("Senha muito longa")
    return {"nome": nome, "email": email, "senha": senha}


def validar_login(dados):
    if not isinstance(dados, dict):
        dados = {}
    email = dados.get("email", "")
    senha = dados.get("senha", "")
    if not email or not senha or not isinstance(email, str) or not isinstance(senha, str):
        raise ValidationError("Email e senha são obrigatórios")
    return {"email": email, "senha": senha}
