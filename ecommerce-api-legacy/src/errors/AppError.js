class AppError extends Error {
    constructor(message, statusCode = 500) {
        super(message);
        this.name = this.constructor.name;
        this.statusCode = statusCode;
    }
}

class ValidationError extends AppError {
    constructor(message = 'Bad Request') { super(message, 400); }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Não autorizado') { super(message, 401); }
}

class NotFoundError extends AppError {
    constructor(message = 'Não encontrado') { super(message, 404); }
}

class MethodNotAllowedError extends AppError {
    constructor(message = 'Método não permitido', allowed = []) {
        super(message, 405);
        this.allowed = allowed;
    }
}

class PaymentDeniedError extends AppError {
    constructor(message = 'Pagamento recusado') { super(message, 400); }
}

module.exports = {
    AppError,
    ValidationError,
    UnauthorizedError,
    NotFoundError,
    MethodNotAllowedError,
    PaymentDeniedError,
};
