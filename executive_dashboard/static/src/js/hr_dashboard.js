import { registry } from "@web/core/registry";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class HrDashboard extends ExecutiveDashboardBase {
    static template = "executive_dashboard.HrDashboard";
    static dataMethod = "get_hr_dashboard_data";
    static actionMethod = "get_hr_action";
    static filterFields = [
        FILTER_FIELDS.dateFrom,
        FILTER_FIELDS.dateTo,
        FILTER_FIELDS.company,
        FILTER_FIELDS.hrDepartment,
        FILTER_FIELDS.hrEmployee,
        FILTER_FIELDS.hrManager,
        FILTER_FIELDS.hrJob,
    ];
}

registry.category("actions").add("executive_dashboard.hr", HrDashboard);
