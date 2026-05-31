import { registry } from "@web/core/registry";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class HelpdeskDashboard extends ExecutiveDashboardBase {
    static template = "executive_dashboard.HelpdeskDashboard";
    static dataMethod = "get_helpdesk_dashboard_data";
    static actionMethod = "get_helpdesk_action";
    static filterFields = [
        FILTER_FIELDS.dateFrom,
        FILTER_FIELDS.dateTo,
        FILTER_FIELDS.company,
        FILTER_FIELDS.helpdeskTeam,
        FILTER_FIELDS.helpdeskUser,
        FILTER_FIELDS.helpdeskStage,
        FILTER_FIELDS.helpdeskPriority,
    ];
}

registry.category("actions").add("executive_dashboard.helpdesk", HelpdeskDashboard);
