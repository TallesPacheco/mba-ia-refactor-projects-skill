const express = require('express');

const { createUserModel } = require('./models/user.model');
const { createCourseModel } = require('./models/course.model');
const { createEnrollmentModel } = require('./models/enrollment.model');
const { createPaymentModel } = require('./models/payment.model');
const { createAuditLogModel } = require('./models/auditLog.model');
const { createPaymentGateway } = require('./services/paymentGateway.service');
const { createCheckoutService } = require('./services/checkout.service');
const { createFinancialReportService } = require('./services/financialReport.service');
const { createCheckoutController } = require('./controllers/checkout.controller');
const { createAdminController } = require('./controllers/admin.controller');
const { createUserController } = require('./controllers/user.controller');
const checkoutRoutes = require('./routes/checkout.routes');
const adminRoutes = require('./routes/admin.routes');
const userRoutes = require('./routes/user.routes');
const { createRequireAdmin } = require('./middlewares/auth');
const { notFound } = require('./middlewares/notFound');
const errorHandler = require('./middlewares/errorHandler');

/**
 * Composition root: monta models, services, controllers, rotas e middlewares
 * a partir das dependências injetadas (db, config, logger).
 */
function createApp({ db, config, logger }) {
    const userModel = createUserModel(db);
    const courseModel = createCourseModel(db);
    const enrollmentModel = createEnrollmentModel(db);
    const paymentModel = createPaymentModel(db);
    const auditLogModel = createAuditLogModel(db);

    const paymentGateway = createPaymentGateway({ apiKey: config.paymentGatewayKey, logger });
    const checkoutService = createCheckoutService({
        db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentGateway, logger,
    });
    const financialReportService = createFinancialReportService({ courseModel });

    const requireAdmin = createRequireAdmin({ adminToken: config.adminToken });

    const app = express();
    app.use(express.json());

    app.use(checkoutRoutes(createCheckoutController({ checkoutService })));
    app.use(adminRoutes(createAdminController({ financialReportService }), requireAdmin));
    app.use(userRoutes(createUserController({ userModel }), requireAdmin));

    // Ordem obrigatória: parsers → rotas → catch-all 404 → error handler.
    app.use(notFound());
    app.use(errorHandler(logger)); // sempre por último
    return app;
}

module.exports = { createApp };
