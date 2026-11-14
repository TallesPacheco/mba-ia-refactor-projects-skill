from flask import Blueprint

from models.constants import API_NAME, API_VERSION
from utils.helpers import localnow

system_bp = Blueprint('system', __name__)


@system_bp.route('/health')
def health():
    # Mantém o formato original: hora local do servidor (ver utils.helpers.localnow).
    return {'status': 'ok', 'timestamp': str(localnow())}


@system_bp.route('/')
def index():
    return {'message': API_NAME, 'version': API_VERSION}
