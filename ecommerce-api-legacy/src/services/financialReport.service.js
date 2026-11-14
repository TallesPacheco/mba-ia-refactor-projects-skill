const { PaymentStatus, UNKNOWN_STUDENT } = require('../models/constants');

function createFinancialReportService({ courseModel }) {
    return {
        async build() {
            const rows = await courseModel.listFinancialRows();
            const byCourse = new Map();

            for (const row of rows) {
                let entry = byCourse.get(row.course_id);
                if (!entry) {
                    entry = { course: row.course_title, revenue: 0, students: [] };
                    byCourse.set(row.course_id, entry);
                }
                if (row.enrollment_id === null) continue;

                if (row.payment_status === PaymentStatus.PAID) entry.revenue += row.payment_amount;
                entry.students.push({
                    student: row.student_name || UNKNOWN_STUDENT,
                    paid: row.payment_amount ?? 0,
                });
            }
            return [...byCourse.values()];
        },
    };
}

module.exports = { createFinancialReportService };
