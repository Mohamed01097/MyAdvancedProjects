import { registry } from "@web/core/registry";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class PurchaseDashboard extends ExecutiveDashboardBase {
    static template = "executive_dashboard.PurchaseDashboard";
    static dataMethod = "get_purchase_dashboard_data";
    static actionMethod = "get_purchase_action";
    static filterFields = [
        FILTER_FIELDS.dateFrom,
        FILTER_FIELDS.dateTo,
        FILTER_FIELDS.vendor,
        FILTER_FIELDS.company,
    ];
}

registry.category("actions").add("executive_dashboard.purchase", PurchaseDashboard);
