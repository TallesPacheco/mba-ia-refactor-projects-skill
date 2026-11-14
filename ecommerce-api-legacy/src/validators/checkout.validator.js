const { ValidationError } = require('../errors/AppError');

const isNonEmptyString = (value) => typeof value === 'string' && value.trim() !== '';
const isIdLike = (value) => (typeof value === 'number' && Number.isFinite(value))
    || (typeof value === 'string' && value.trim() !== '');

/**
 * Valida o corpo do checkout mantendo o contrato original (usr, eml, pwd, c_id, card)
 * e a resposta de erro original ("Bad Request", 400).
 */
function validateCheckout(body) {
    if (!body || typeof body !== 'object') throw new ValidationError('Bad Request');
    const { usr, eml, pwd, c_id: courseId, card } = body;

    if (!isNonEmptyString(usr) || !isNonEmptyString(eml) || !isIdLike(courseId) || !isNonEmptyString(card)) {
        throw new ValidationError('Bad Request');
    }
    if (pwd !== undefined && pwd !== null && typeof pwd !== 'string') {
        throw new ValidationError('Bad Request');
    }

    return { name: usr, email: eml, password: pwd || '', courseId, cardNumber: card };
}

module.exports = { validateCheckout };
