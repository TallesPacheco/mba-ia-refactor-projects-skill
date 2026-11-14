// Entry point ("npm start" → node src/app.js): carrega config, prepara o banco e sobe o servidor.
const { config, assertConfig } = require('./config');
const { createDb } = require('./db/connection');
const { initSchema } = require('./db/schema');
const { createApp } = require('./app.factory');
const { createLogger } = require('./utils/logger');
const { ADMIN_TOKEN_HEADER } = require('./middlewares/auth');

const logger = createLogger(config.logLevel);

async function start() {
    assertConfig(config);
    if (config.adminTokenGenerated) {
        // Nenhum token literal no código: em dev o valor é sorteado por boot.
        logger.warn('ADMIN_TOKEN não definido; token gerado para esta execução', {
            header: ADMIN_TOKEN_HEADER,
            adminToken: config.adminToken,
        });
    }
    const db = createDb(config.dbPath);
    await initSchema(db, { config, logger }); // banco :memory: — schema + seed antes do listen
    const app = createApp({ db, config, logger });
    const server = app.listen(config.port, config.host, () => {
        logger.info(`LMS API rodando em http://${config.host}:${config.port}`);
    });

    const shutdown = (signal) => {
        logger.info('Encerrando', { signal });
        server.close(() => db.close().then(() => process.exit(0), () => process.exit(1)));
    };
    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGINT', () => shutdown('SIGINT'));
}

start().catch((err) => {
    logger.error('Falha no boot', { message: err.message });
    process.exit(1);
});
