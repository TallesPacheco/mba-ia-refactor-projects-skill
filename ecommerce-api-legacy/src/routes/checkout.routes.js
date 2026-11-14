const { Router } = require('express');
const asyncHandler = require('../middlewares/asyncHandler');
const { methodNotAllowed } = require('../middlewares/notFound');

const PATH = '/api/checkout';

module.exports = (checkoutController) => {
    const router = Router();
    router.post(PATH, asyncHandler(async (req, res) => {
        res.status(200).json(await checkoutController.checkout(req.body));
    }));
    router.all(PATH, methodNotAllowed(['POST']));
    return router;
};
