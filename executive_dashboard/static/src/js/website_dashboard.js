import { registry } from "@web/core/registry";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class WebsiteDashboard extends ExecutiveDashboardBase {
    static template = "executive_dashboard.WebsiteDashboard";
    static dataMethod = "get_website_dashboard_data";
    static actionMethod = "get_website_action";
    static filterFields = [
        FILTER_FIELDS.dateFrom,
        FILTER_FIELDS.dateTo,
        FILTER_FIELDS.company,
        FILTER_FIELDS.website,
        FILTER_FIELDS.websiteCustomer,
        FILTER_FIELDS.productCategory,
        FILTER_FIELDS.websiteOrderState,
    ];
}

registry.category("actions").add("executive_dashboard.website", WebsiteDashboard);
