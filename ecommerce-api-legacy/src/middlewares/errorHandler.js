const { AppError } = require('../errors/AppError');

/**
 * Error handler central (registrar DEPOIS das rotas).
 * Mantém o formato original de erro: texto puro via res.send, sem stack trace.
 */
module.exports = (logger) => (err, req, res, next) => { // eslint-disable-line no-unused-vars
    if (err instanceof AppError) {
        // 405 exige o header Allow (RFC 9110 §15.5.6).
        if (Array.isArray(err.allowed) && err.allowed.length) res.set('Allow', err.allowed.join(', '));
        return res.status(err.statusCode).send(err.message);
    }
    // Erros do body-parser (JSON malformado, payload grande...): 4xx sem stack trace.
    if (err && err.type && Number.isInteger(err.status) && err.status >= 400 && err.status < 500) {
        return res.status(err.status).send('Bad Request');
    }
    logger.error('Erro não tratado', { message: err && err.message, stack: err && err.stack, path: req.path });
    return res.status(500).send('Erro interno do servidor');
};
