const crypto = require('node:crypto');

const appEnv = process.env.APP_ENV || process.env.NODE_ENV || 'development';
const isProduction = appEnv === 'production';

// Sem fallback literal para o token de admin (AP-01): fora de produção, um token
// aleatório é gerado a cada boot e registrado no log; em produção, ADMIN_TOKEN é
// obrigatório (assertConfig). Token vazio = rotas admin sempre 401.
const envAdminToken = process.env.ADMIN_TOKEN || '';
const adminTokenGenerated = !envAdminToken && !isProduction;
const adminToken = envAdminToken
    || (adminTokenGenerated ? crypto.randomBytes(24).toString('base64url') : '');

const config = Object.freeze({
    appEnv,
    isProduction,
    port: Number(process.env.PORT) || 3000,
    host: process.env.HOST || '127.0.0.1',
    dbPath: process.env.DB_PATH || ':memory:',
    adminToken,
    adminTokenGenerated,
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
    logLevel: process.env.LOG_LEVEL || 'info',
    // Senha do usuário de seed; vazia = gerada aleatoriamente no seed (ver db/schema.js).
    seedUserPassword: process.env.SEED_USER_PASSWORD || '',
});

function assertConfig(cfg) {
    if (!cfg.isProduction) return;
    const missing = [];
    if (!cfg.adminToken) missing.push('ADMIN_TOKEN');
    if (!cfg.paymentGatewayKey) missing.push('PAYMENT_GATEWAY_KEY');
    if (missing.length) {
        throw new Error(`Configuração obrigatória ausente em produção: ${missing.join(', ')}`);
    }
}

module.exports = { config, assertConfig };
