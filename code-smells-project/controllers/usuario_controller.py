from db.connection import get_db
from errors import NotFoundError
from models import usuario_model
from services import usuario_service
from validators.usuario_validator import validar_cadastro, validar_login


def list_usuarios():
    return usuario_model.listar(get_db())


def get_usuario(usuario_id):
    usuario = usuario_model.buscar_por_id(get_db(), usuario_id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return usuario


def create_usuario(dados):
    usuario = validar_cadastro(dados)
    return usuario_service.cadastrar(get_db(), usuario["nome"], usuario["email"], usuario["senha"])


def login(dados):
    credenciais = validar_login(dados)
    return usuario_service.autenticar(get_db(), credenciais["email"], credenciais["senha"])
