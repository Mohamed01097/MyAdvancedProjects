import { registry } from "@web/core/registry";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class ManufacturingDashboard extends ExecutiveDashboardBase {
    static template = "executive_dashboard.ManufacturingDashboard";
    static dataMethod = "get_manufacturing_dashboard_data";
    static actionMethod = "get_manufacturing_action";
    static filterFields = [
        FILTER_FIELDS.dateFrom,
        FILTER_FIELDS.dateTo,
        FILTER_FIELDS.company,
        FILTER_FIELDS.product,
        FILTER_FIELDS.manufacturingUser,
        FILTER_FIELDS.workcenter,
        FILTER_FIELDS.manufacturingState,
    ];
}

registry.category("actions").add("executive_dashboard.manufacturing", ManufacturingDashboard);
