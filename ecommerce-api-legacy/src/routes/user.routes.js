const { Router } = require('express');
const asyncHandler = require('../middlewares/asyncHandler');
const { methodNotAllowed } = require('../middlewares/notFound');

const PATH = '/api/users/:id';

module.exports = (userController, requireAdmin) => {
    const router = Router();
    router.delete(PATH, requireAdmin, asyncHandler(async (req, res) => {
        res.send(await userController.deleteUser(req.params.id));
    }));
    router.all(PATH, methodNotAllowed(['DELETE']));
    return router;
};
