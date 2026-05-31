import { registry } from "@web/core/registry";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class CrmDashboard extends ExecutiveDashboardBase {
    static template = "executive_dashboard.CrmDashboard";
    static dataMethod = "get_crm_dashboard_data";
    static actionMethod = "get_crm_action";
    static filterFields = [
        FILTER_FIELDS.dateFrom,
        FILTER_FIELDS.dateTo,
        FILTER_FIELDS.salesperson,
        FILTER_FIELDS.salesTeam,
        FILTER_FIELDS.company,
    ];
}

registry.category("actions").add("executive_dashboard.crm", CrmDashboard);
