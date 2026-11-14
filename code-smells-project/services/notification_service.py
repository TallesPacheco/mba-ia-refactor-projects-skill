import logging

logger = logging.getLogger(__name__)


class Notifier:
    """Notificações simuladas: apenas registram no log (sem PII)."""

    def pedido_criado(self, pedido_id, usuario_id):
        logger.info("ENVIANDO EMAIL: pedido_id=%s criado para usuario_id=%s", pedido_id, usuario_id)
        logger.info("ENVIANDO SMS: pedido_id=%s recebido", pedido_id)
        logger.info("ENVIANDO PUSH: novo pedido_id=%s recebido pelo sistema", pedido_id)

    def pedido_aprovado(self, pedido_id):
        logger.info("NOTIFICAÇÃO: pedido_id=%s aprovado, preparar envio", pedido_id)

    def pedido_cancelado(self, pedido_id):
        logger.info("NOTIFICAÇÃO: pedido_id=%s cancelado", pedido_id)
