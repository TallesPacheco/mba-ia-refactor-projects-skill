const { NotFoundError, MethodNotAllowedError } = require('../errors/AppError');

/**
 * Catch-all registrado DEPOIS dos routers e ANTES do error handler (PB-23):
 * sem ele, o Express responde a rota desconhecida com sua página HTML
 * (`Cannot GET /x`), fora do formato de erro da API.
 */
const notFound = () => (req, res, next) => next(
    new NotFoundError(`Rota não encontrada: ${req.method} ${req.path}`),
);

/**
 * Usado como `router.all(path, methodNotAllowed([...]))` depois dos handlers do
 * mesmo path: o método declarado casa primeiro, o resto cai aqui com 405.
 *
 * OPTIONS passa adiante: o Router do Express 4 responde preflight sozinho (200 +
 * Allow com os métodos do path). Capturá-lo aqui transformaria esse 200 em 405.
 */
const methodNotAllowed = (allowed) => (req, res, next) => {
    if (req.method === 'OPTIONS') return next();
    return next(new MethodNotAllowedError(`Método não permitido: ${req.method} ${req.path}`, allowed));
};

module.exports = { notFound, methodNotAllowed };
