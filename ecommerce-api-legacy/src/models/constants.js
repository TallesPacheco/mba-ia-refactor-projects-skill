const PaymentStatus = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

// Regra do gateway simulado: cartões iniciados por este prefixo são aprovados.
const APPROVED_CARD_PREFIX = '4';

const UNKNOWN_STUDENT = 'Unknown';

module.exports = { PaymentStatus, APPROVED_CARD_PREFIX, UNKNOWN_STUDENT };
