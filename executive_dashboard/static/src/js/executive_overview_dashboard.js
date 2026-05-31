import { registry } from "@web/core/registry";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class ExecutiveOverviewDashboard extends ExecutiveDashboardBase {
    static template = "executive_dashboard.OverviewDashboard";
    static dataMethod = "get_overview_data";
    static actionMethod = "get_action";
    static usesCharts = false;
    static filterFields = [
        FILTER_FIELDS.dateFrom,
        FILTER_FIELDS.dateTo,
        FILTER_FIELDS.company,
    ];
}

registry.category("actions").add("executive_dashboard.overview", ExecutiveOverviewDashboard);
registry.category("actions").add("executive_dashboard.action", ExecutiveOverviewDashboard);
