const { PaymentStatus, APPROVED_CARD_PREFIX } = require('../models/constants');

/**
 * Gateway de pagamento simulado. A chave é injetada pela config e nunca logada.
 */
function createPaymentGateway({ apiKey, logger }) {
    return {
        charge({ cardNumber, amount }) {
            logger.info('Processando pagamento', {
                cardLast4: cardNumber.slice(-4),
                amount,
                gatewayConfigured: Boolean(apiKey),
            });
            return cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PaymentStatus.PAID : PaymentStatus.DENIED;
        },
    };
}

module.exports = { createPaymentGateway };
