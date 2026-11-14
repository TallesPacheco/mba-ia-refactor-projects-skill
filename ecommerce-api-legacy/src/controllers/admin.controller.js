const createAdminController = ({ financialReportService }) => ({
    getFinancialReport: () => financialReportService.build(),
});

module.exports = { createAdminController };
