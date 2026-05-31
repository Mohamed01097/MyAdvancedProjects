import { registry } from "@web/core/registry";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class SalesDashboard extends ExecutiveDashboardBase {
    static template = "executive_dashboard.SalesDashboard";
    static dataMethod = "get_sales_dashboard_data";
    static actionMethod = "get_sales_action";
    static filterFields = [
        FILTER_FIELDS.dateFrom,
        FILTER_FIELDS.dateTo,
        FILTER_FIELDS.salesperson,
        FILTER_FIELDS.company,
    ];
}

registry.category("actions").add("executive_dashboard.sales", SalesDashboard);
