import { registry } from "@web/core/registry";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class PosDashboard extends ExecutiveDashboardBase {
    static template = "executive_dashboard.PosDashboard";
    static dataMethod = "get_pos_dashboard_data";
    static actionMethod = "get_pos_action";
    static filterFields = [
        FILTER_FIELDS.dateFrom,
        FILTER_FIELDS.dateTo,
        FILTER_FIELDS.company,
        FILTER_FIELDS.posConfig,
        FILTER_FIELDS.posCashier,
        FILTER_FIELDS.posPaymentMethod,
        FILTER_FIELDS.posSessionState,
    ];
}

registry.category("actions").add("executive_dashboard.pos", PosDashboard);
