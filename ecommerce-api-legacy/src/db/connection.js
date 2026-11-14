const sqlite3 = require('sqlite3');

/**
 * Abre o banco SQLite e expõe uma API baseada em Promise (run/get/all/exec)
 * mais um helper de transação serializado na mesma conexão.
 *
 * Invariante de escrita: BEGIN/COMMIT/ROLLBACK valem para a conexão inteira, então
 * qualquer instrução submetida entre eles entra na transação em curso. Por isso:
 *   - dentro de withTransaction(work), use `run`;
 *   - fora dela, escreva com `write` (que passa pela mesma fila).
 * Usar `run` para uma escrita solta a deixaria sujeita ao ROLLBACK de outra
 * requisição — a resposta diria "ok" e a gravação seria desfeita.
 */
function createDb(filename) {
    const raw = new sqlite3.Database(filename);

    const run = (sql, params = []) => new Promise((resolve, reject) => {
        raw.run(sql, params, function onRun(err) {
            if (err) return reject(err);
            resolve({ lastID: this.lastID, changes: this.changes });
        });
    });
    const get = (sql, params = []) => new Promise((resolve, reject) => {
        raw.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
    });
    const all = (sql, params = []) => new Promise((resolve, reject) => {
        raw.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
    });
    const exec = (sql) => new Promise((resolve, reject) => {
        raw.exec(sql, (err) => (err ? reject(err) : resolve()));
    });
    const close = () => new Promise((resolve, reject) => {
        raw.close((err) => (err ? reject(err) : resolve()));
    });

    // Fila por conexão: evita "cannot start a transaction within a transaction".
    let queue = Promise.resolve();
    function withTransaction(work) {
        const result = queue.then(async () => {
            await run('BEGIN');
            try {
                const value = await work();
                await run('COMMIT');
                return value;
            } catch (err) {
                await run('ROLLBACK');
                throw err;
            }
        });
        queue = result.catch(() => {});
        return result;
    }

    // Escrita avulsa: entra na mesma fila, nunca no meio da transação de outra requisição.
    const write = (sql, params = []) => withTransaction(() => run(sql, params));

    return { run, get, all, exec, close, withTransaction, write };
}

module.exports = { createDb };
