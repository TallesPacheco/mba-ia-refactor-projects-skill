const { Router } = require('express');
const asyncHandler = require('../middlewares/asyncHandler');
const { methodNotAllowed } = require('../middlewares/notFound');

const PATH = '/api/admin/financial-report';

module.exports = (adminController, requireAdmin) => {
    const router = Router();
    router.get(PATH, requireAdmin, asyncHandler(async (req, res) => {
        res.json(await adminController.getFinancialReport());
    }));
    router.all(PATH, methodNotAllowed(['GET']));
    return router;
};
