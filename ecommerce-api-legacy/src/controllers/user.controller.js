const { validateUserId } = require('../validators/user.validator');

// Mensagem corrigida (PB-24): o texto anterior ("...as matrículas e pagamentos
// ficaram sujos no banco.") descrevia um comportamento que a cascata eliminou.
const DELETE_USER_MESSAGE = 'Usuário deletado, junto com suas matrículas e pagamentos.';

const createUserController = ({ userModel }) => ({
    async deleteUser(rawId) {
        await userModel.deleteById(validateUserId(rawId));
        return DELETE_USER_MESSAGE;
    },
});

module.exports = { createUserController };
