// Express 4 não captura rejeições de Promise: encaminha para o error handler central.
module.exports = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
