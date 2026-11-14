const { validateCheckout } = require('../validators/checkout.validator');

const createCheckoutController = ({ checkoutService }) => ({
    async checkout(body) {
        const input = validateCheckout(body);
        const { enrollmentId } = await checkoutService.checkout(input);
        return { msg: 'Sucesso', enrollment_id: enrollmentId };
    },
});

module.exports = { createCheckoutController };
