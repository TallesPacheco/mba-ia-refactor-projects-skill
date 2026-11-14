const { NotFoundError, PaymentDeniedError } = require('../errors/AppError');
const { PaymentStatus } = require('../models/constants');
const { hashPassword, randomPassword } = require('../utils/password');

function createCheckoutService({ db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentGateway, logger }) {
    return {
        /**
         * Fluxo: curso ativo → decisão de pagamento → (transação) usuário + matrícula + pagamento + auditoria.
         * O pagamento é decidido antes de qualquer escrita para não criar registros órfãos.
         */
        async checkout({ name, email, password, courseId, cardNumber }) {
            const course = await courseModel.findActiveById(courseId);
            if (!course) throw new NotFoundError('Curso não encontrado');

            const status = paymentGateway.charge({ cardNumber, amount: course.price });
            if (status === PaymentStatus.DENIED) throw new PaymentDeniedError('Pagamento recusado');

            const existing = await userModel.findIdByEmail(email);
            // Sem senha informada, gera uma aleatória (antes: default fixo "123456").
            const passHash = existing ? null : await hashPassword(password || randomPassword());

            const result = await db.withTransaction(async () => {
                let userId = existing && existing.id;
                if (!userId) {
                    const again = await userModel.findIdByEmail(email);
                    userId = again ? again.id : await userModel.create({ name, email, passHash });
                }
                const enrollmentId = await enrollmentModel.create({ userId, courseId: course.id });
                await paymentModel.create({ enrollmentId, amount: course.price, status });
                await auditLogModel.record(`Checkout curso ${courseId} por ${userId}`);
                return { userId, enrollmentId };
            });

            logger.info('Checkout concluído', { userId: result.userId, courseId: course.id, enrollmentId: result.enrollmentId });
            return result;
        },
    };
}

module.exports = { createCheckoutService };
