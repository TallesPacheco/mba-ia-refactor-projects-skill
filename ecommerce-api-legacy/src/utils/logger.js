const LEVELS = { debug: 10, info: 20, warn: 30, error: 40 };

function createLogger(level = 'info') {
    const min = LEVELS[level] || LEVELS.info;
    const log = (lvl) => (msg, meta = {}) => {
        if (LEVELS[lvl] < min) return;
        const line = JSON.stringify({ level: lvl, msg, ...meta, ts: new Date().toISOString() });
        (lvl === 'error' || lvl === 'warn' ? process.stderr : process.stdout).write(`${line}\n`);
    };
    return { debug: log('debug'), info: log('info'), warn: log('warn'), error: log('error') };
}

module.exports = { createLogger };
