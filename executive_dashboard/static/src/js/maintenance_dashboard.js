import { registry } from "@web/core/registry";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class MaintenanceDashboard extends ExecutiveDashboardBase {
    static template = "executive_dashboard.MaintenanceDashboard";
    static dataMethod = "get_maintenance_dashboard_data";
    static actionMethod = "get_maintenance_action";
    static filterFields = [
        FILTER_FIELDS.dateFrom,
        FILTER_FIELDS.dateTo,
        FILTER_FIELDS.company,
        FILTER_FIELDS.maintenanceTeam,
        FILTER_FIELDS.equipment,
        FILTER_FIELDS.technician,
        FILTER_FIELDS.maintenanceStage,
    ];
}

registry.category("actions").add("executive_dashboard.maintenance", MaintenanceDashboard);
