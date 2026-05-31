import { registry } from "@web/core/registry";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class InventoryDashboard extends ExecutiveDashboardBase {
    static template = "executive_dashboard.InventoryDashboard";
    static dataMethod = "get_inventory_dashboard_data";
    static actionMethod = "get_inventory_action";
    static filterFields = [
        FILTER_FIELDS.company,
        FILTER_FIELDS.warehouse,
        FILTER_FIELDS.productCategory,
        FILTER_FIELDS.product,
    ];
}

registry.category("actions").add("executive_dashboard.inventory", InventoryDashboard);
