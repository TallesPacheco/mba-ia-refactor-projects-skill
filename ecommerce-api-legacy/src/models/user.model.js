const createUserModel = (db) => ({
    findIdByEmail: (email) => db.get('SELECT id FROM users WHERE email = ?', [email]),

    async create({ name, email, passHash }) {
        const { lastID } = await db.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [name, email, passHash],
        );
        return lastID;
    },

    // Escrita avulsa: `write` serializa na mesma fila das transações (ver db/connection.js).
    // Matrículas e pagamentos são removidos via ON DELETE CASCADE (PRAGMA foreign_keys = ON).
    deleteById: (id) => db.write('DELETE FROM users WHERE id = ?', [id]),
});

module.exports = { createUserModel };
