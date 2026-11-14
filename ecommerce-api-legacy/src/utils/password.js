const crypto = require('node:crypto');
const { promisify } = require('node:util');

const scrypt = promisify(crypto.scrypt);
const KEY_LENGTH = 64;
const SALT_BYTES = 16;

async function hashPassword(plain) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const key = await scrypt(String(plain), salt, KEY_LENGTH);
    return `scrypt$${salt}$${key.toString('hex')}`;
}

function randomPassword() {
    return crypto.randomBytes(18).toString('base64url');
}

module.exports = { hashPassword, randomPassword };
