const { ValidationError } = require('../errors/AppError');

/**
 * Valida o path param `:id` de /api/users/:id.
 *
 * Antes, qualquer valor (`abc`, `0`, `1 OR 1=1`) chegava ao SQL parametrizado,
 * não apagava nada e ainda respondia 200 com mensagem de sucesso. Agora valores
 * que não são id válido respondem 400. Um id bem formado mas inexistente
 * continua 200 (preservação do baseline — ver Remaining Known Issues).
 */
function validateUserId(raw) {
    if (typeof raw !== 'string' || !/^\d+$/.test(raw)) throw new ValidationError('Bad Request');
    const id = Number(raw);
    if (!Number.isSafeInteger(id) || id < 1) throw new ValidationError('Bad Request');
    return id;
}

module.exports = { validateUserId };
