const { hashPassword, randomPassword } = require('../utils/password');
const { PaymentStatus } = require('../models/constants');

const SCHEMA = `
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    pass TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id)
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY,
    enrollment_id INTEGER NOT NULL UNIQUE REFERENCES enrollments(id) ON DELETE CASCADE,
    amount REAL NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY,
    action TEXT NOT NULL,
    created_at DATETIME
);
`;

// Mesmos registros do seed original. A senha não é mais literal (AP-01/PB-25):
// vem de SEED_USER_PASSWORD e, na ausência dela, é gerada e registrada no log.
const SEED_USER = { name: 'Leonan', email: 'leonan@fullcycle.com.br' };
const SEED_COURSES = [
    { title: 'Clean Architecture', price: 997.0, active: 1 },
    { title: 'Docker', price: 497.0, active: 1 },
];

function seedUserPassword({ config, logger }) {
    if (config.seedUserPassword) return config.seedUserPassword;
    if (config.isProduction) {
        throw new Error('SEED_USER_PASSWORD é obrigatório em produção para criar o usuário inicial');
    }
    const generated = randomPassword();
    logger.warn('[seed] SEED_USER_PASSWORD não definido; senha gerada para esta execução', {
        email: SEED_USER.email,
        password: generated,
    });
    return generated;
}

async function seed(db, { config, logger }) {
    const existing = await db.get('SELECT COUNT(*) AS total FROM users');
    if (existing.total > 0) return;

    const passHash = await hashPassword(seedUserPassword({ config, logger }));
    await db.withTransaction(async () => {
        const { lastID: userId } = await db.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [SEED_USER.name, SEED_USER.email, passHash],
        );
        const courseIds = [];
        for (const course of SEED_COURSES) {
            const { lastID } = await db.run(
                'INSERT INTO courses (title, price, active) VALUES (?, ?, ?)',
                [course.title, course.price, course.active],
            );
            courseIds.push(lastID);
        }
        const { lastID: enrollmentId } = await db.run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
            [userId, courseIds[0]],
        );
        await db.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, SEED_COURSES[0].price, PaymentStatus.PAID],
        );
    });
}

async function initSchema(db, { config, logger }) {
    await db.exec('PRAGMA foreign_keys = ON;');
    await db.exec(SCHEMA);
    await seed(db, { config, logger });
}

module.exports = { initSchema };
