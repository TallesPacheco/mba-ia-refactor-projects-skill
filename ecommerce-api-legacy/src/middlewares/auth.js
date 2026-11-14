const crypto = require('node:crypto');
const { UnauthorizedError } = require('../errors/AppError');

const ADMIN_TOKEN_HEADER = 'X-Admin-Token';

function createRequireAdmin({ adminToken }) {
    const expected = Buffer.from(adminToken || '');
    return (req, res, next) => {
        const provided = Buffer.from(req.get(ADMIN_TOKEN_HEADER) || '');
        const valid = expected.length > 0
            && provided.length === expected.length
            && crypto.timingSafeEqual(provided, expected);
        if (!valid) return next(new UnauthorizedError('Não autorizado'));
        return next();
    };
}

module.exports = { createRequireAdmin, ADMIN_TOKEN_HEADER };
