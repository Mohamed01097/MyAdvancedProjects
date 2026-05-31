import { Component, onWillStart, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { formatFloat, formatInteger, formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import {
    AlertPreview,
    DashboardChart,
    DashboardFilters,
    DepartmentCard,
    KpiCard,
    LoadingState,
} from "./components/dashboard_components";
import { DashboardExportToolbar } from "./components/dashboard_export_toolbar";

export const DEFAULT_FILTERS = {
    date_from: false,
    date_to: false,
    salesperson_id: false,
    sales_team_id: false,
    company_id: false,
    warehouse_id: false,
    vendor_id: false,
    product_category_id: false,
    product_id: false,
    manufacturing_user_id: false,
    workcenter_id: false,
    manufacturing_state: false,
    maintenance_team_id: false,
    equipment_id: false,
    technician_id: false,
    maintenance_stage_id: false,
    hr_department_id: false,
    hr_employee_id: false,
    hr_manager_id: false,
    hr_job_id: false,
    helpdesk_team_id: false,
    helpdesk_user_id: false,
    helpdesk_stage_id: false,
    helpdesk_priority: false,
    pos_config_id: false,
    pos_cashier_id: false,
    pos_payment_method_id: false,
    pos_session_state: false,
    website_id: false,
    website_customer_id: false,
    website_order_state: false,
    department: false,
    severity: false,
    responsible_user_id: false,
    alert_status: false,
    alert_dashboard_key: false,
};

export const FILTER_FIELDS = {
    dateFrom: { name: "date_from", label: _t("Date From"), type: "date" },
    dateTo: { name: "date_to", label: _t("Date To"), type: "date" },
    salesperson: {
        name: "salesperson_id",
        label: _t("Salesperson"),
        type: "select",
        optionsKey: "salespersons",
        placeholder: _t("All Salespersons"),
        valueType: "integer",
    },
    salesTeam: {
        name: "sales_team_id",
        label: _t("Sales Team"),
        type: "select",
        optionsKey: "sales_teams",
        placeholder: _t("All Sales Teams"),
        valueType: "integer",
    },
    company: {
        name: "company_id",
        label: _t("Company"),
        type: "select",
        optionsKey: "companies",
        placeholder: _t("All Companies"),
        valueType: "integer",
    },
    warehouse: {
        name: "warehouse_id",
        label: _t("Warehouse"),
        type: "select",
        optionsKey: "warehouses",
        placeholder: _t("All Warehouses"),
        valueType: "integer",
    },
    vendor: {
        name: "vendor_id",
        label: _t("Vendor"),
        type: "select",
        optionsKey: "vendors",
        placeholder: _t("All Vendors"),
        valueType: "integer",
    },
    productCategory: {
        name: "product_category_id",
        label: _t("Product Category"),
        type: "select",
        optionsKey: "product_categories",
        placeholder: _t("All Categories"),
        labelField: "complete_name",
        valueType: "integer",
    },
    product: {
        name: "product_id",
        label: _t("Product"),
        type: "select",
        optionsKey: "products",
        placeholder: _t("All Products"),
        labelField: "display_name",
        valueType: "integer",
    },
    manufacturingUser: {
        name: "manufacturing_user_id",
        label: _t("MFG Responsible"),
        type: "select",
        optionsKey: "manufacturing_users",
        placeholder: _t("All Responsible"),
        valueType: "integer",
    },
    workcenter: {
        name: "workcenter_id",
        label: _t("Work Center"),
        type: "select",
        optionsKey: "workcenters",
        placeholder: _t("All Work Centers"),
        valueType: "integer",
    },
    manufacturingState: {
        name: "manufacturing_state",
        label: _t("MFG State"),
        type: "select",
        optionsKey: "manufacturing_states",
        placeholder: _t("All States"),
    },
    maintenanceTeam: {
        name: "maintenance_team_id",
        label: _t("Maintenance Team"),
        type: "select",
        optionsKey: "maintenance_teams",
        placeholder: _t("All Teams"),
        valueType: "integer",
    },
    equipment: {
        name: "equipment_id",
        label: _t("Equipment"),
        type: "select",
        optionsKey: "equipment",
        placeholder: _t("All Equipment"),
        labelField: "display_name",
        valueType: "integer",
    },
    technician: {
        name: "technician_id",
        label: _t("Technician"),
        type: "select",
        optionsKey: "technicians",
        placeholder: _t("All Technicians"),
        valueType: "integer",
    },
    maintenanceStage: {
        name: "maintenance_stage_id",
        label: _t("Maintenance Stage"),
        type: "select",
        optionsKey: "maintenance_stages",
        placeholder: _t("All Stages"),
        valueType: "integer",
    },
    hrDepartment: {
        name: "hr_department_id",
        label: _t("Department"),
        type: "select",
        optionsKey: "hr_departments",
        placeholder: _t("All Departments"),
        labelField: "complete_name",
        valueType: "integer",
    },
    hrEmployee: {
        name: "hr_employee_id",
        label: _t("Employee"),
        type: "select",
        optionsKey: "hr_employees",
        placeholder: _t("All Employees"),
        labelField: "display_name",
        valueType: "integer",
    },
    hrManager: {
        name: "hr_manager_id",
        label: _t("Manager"),
        type: "select",
        optionsKey: "hr_managers",
        placeholder: _t("All Managers"),
        labelField: "display_name",
        valueType: "integer",
    },
    hrJob: {
        name: "hr_job_id",
        label: _t("Job Position"),
        type: "select",
        optionsKey: "hr_jobs",
        placeholder: _t("All Job Positions"),
        valueType: "integer",
    },
    helpdeskTeam: {
        name: "helpdesk_team_id",
        label: _t("Helpdesk Team"),
        type: "select",
        optionsKey: "helpdesk_teams",
        placeholder: _t("All Teams"),
        valueType: "integer",
    },
    helpdeskUser: {
        name: "helpdesk_user_id",
        label: _t("Assigned User"),
        type: "select",
        optionsKey: "helpdesk_users",
        placeholder: _t("All Assigned Users"),
        valueType: "integer",
    },
    helpdeskStage: {
        name: "helpdesk_stage_id",
        label: _t("Ticket Stage"),
        type: "select",
        optionsKey: "helpdesk_stages",
        placeholder: _t("All Stages"),
        valueType: "integer",
    },
    helpdeskPriority: {
        name: "helpdesk_priority",
        label: _t("Priority"),
        type: "select",
        optionsKey: "helpdesk_priorities",
        placeholder: _t("All Priorities"),
    },
    posConfig: {
        name: "pos_config_id",
        label: _t("POS / Branch"),
        type: "select",
        optionsKey: "pos_configs",
        placeholder: _t("All POS / Branches"),
        valueType: "integer",
    },
    posCashier: {
        name: "pos_cashier_id",
        label: _t("Cashier"),
        type: "select",
        optionsKey: "pos_cashiers",
        placeholder: _t("All Cashiers"),
        valueType: "integer",
    },
    posPaymentMethod: {
        name: "pos_payment_method_id",
        label: _t("Payment Method"),
        type: "select",
        optionsKey: "pos_payment_methods",
        placeholder: _t("All Methods"),
        valueType: "integer",
    },
    posSessionState: {
        name: "pos_session_state",
        label: _t("Session State"),
        type: "select",
        optionsKey: "pos_session_states",
        placeholder: _t("All States"),
    },
    website: {
        name: "website_id",
        label: _t("Website"),
        type: "select",
        optionsKey: "websites",
        placeholder: _t("All Websites"),
        valueType: "integer",
    },
    websiteCustomer: {
        name: "website_customer_id",
        label: _t("Customer"),
        type: "select",
        optionsKey: "website_customers",
        placeholder: _t("All Customers"),
        labelField: "display_name",
        valueType: "integer",
    },
    websiteOrderState: {
        name: "website_order_state",
        label: _t("Order State"),
        type: "select",
        optionsKey: "website_order_states",
        placeholder: _t("All States"),
    },
    department: {
        name: "department",
        label: _t("Department"),
        type: "select",
        optionsKey: "alert_departments",
        placeholder: _t("All Departments"),
    },
    severity: {
        name: "severity",
        label: _t("Severity"),
        type: "select",
        optionsKey: "alert_severities",
        placeholder: _t("All Severities"),
    },
    responsibleUser: {
        name: "responsible_user_id",
        label: _t("Responsible"),
        type: "select",
        optionsKey: "responsible_users",
        placeholder: _t("All Responsible"),
        valueType: "integer",
    },
    alertStatus: {
        name: "alert_status",
        label: _t("Alert Status"),
        type: "select",
        optionsKey: "smart_alert_statuses",
        placeholder: _t("All Statuses"),
    },
    alertDashboard: {
        name: "alert_dashboard_key",
        label: _t("Alert Dashboard"),
        type: "select",
        optionsKey: "smart_alert_dashboards",
        placeholder: _t("All Dashboards"),
    },
};

export class ExecutiveDashboardBase extends Component {
    static components = {
        AlertPreview,
        DashboardChart,
        DashboardFilters,
        DashboardExportToolbar,
        DepartmentCard,
        KpiCard,
        LoadingState,
    };
    static props = { ...standardActionServiceProps };
    static dataMethod = "get_dashboard_data";
    static actionMethod = "get_action";
    static filterFields = [];
    static usesCharts = true;

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.requestToken = 0;
        this.state = useState({
            loading: true,
            error: false,
            chartjs: false,
            filters: { ...DEFAULT_FILTERS },
            data: null,
        });
        onWillStart(async () => {
            if (this.constructor.usesCharts) {
                await this.loadChartLibrary();
            }
            await this.loadData();
        });
    }

    async loadChartLibrary() {
        try {
            await loadBundle("web.chartjs_lib");
            this.state.chartjs = typeof Chart !== "undefined";
        } catch {
            this.state.chartjs = false;
        }
    }

    async loadData() {
        const token = ++this.requestToken;
        this.state.loading = true;
        this.state.error = false;
        try {
            const data = await this.orm.call(
                "executive.dashboard.service",
                this.constructor.dataMethod,
                [this.getFilterPayload()]
            );
            if (token !== this.requestToken) {
                return;
            }
            this.state.data = data;
            this.state.filters = { ...this.state.filters, ...(data.filters || {}) };
        } catch (error) {
            if (token !== this.requestToken) {
                return;
            }
            this.state.error = error.message || _t("The dashboard data could not be loaded.");
        } finally {
            if (token === this.requestToken) {
                this.state.loading = false;
            }
        }
    }

    getFilterPayload() {
        return { ...DEFAULT_FILTERS, ...this.state.filters };
    }

    async onFilterChange(filterName, value) {
        this.state.filters[filterName] = value;
        await this.loadData();
    }

    async clearFilters() {
        this.state.filters = { ...DEFAULT_FILTERS };
        await this.loadData();
    }

    async refresh() {
        await this.loadData();
    }

    async openAction(actionKey, extra = {}) {
        if (!actionKey) {
            return;
        }
        try {
            const action = await this.orm.call(
                "executive.dashboard.service",
                this.constructor.actionMethod,
                [actionKey, this.getFilterPayload(), extra]
            );
            if (action) {
                await this.action.doAction(action);
            }
        } catch (error) {
            this.notification.add(error.message || _t("The related records could not be opened."), {
                type: "danger",
            });
        }
    }

    openDashboard(actionXmlId) {
        if (actionXmlId) {
            return this.action.doAction(actionXmlId);
        }
    }

    openKpi(key) {
        if (key === "overview_critical_alerts") {
            return this.openDashboard("executive_dashboard.alerts_action");
        }
        return this.openAction(key);
    }

    openChart(actionKey, extra = {}) {
        return this.openAction(actionKey, extra);
    }

    openSaleRow(orderId) {
        return this.openAction("delayed_sale_row", { order_id: orderId });
    }

    openPipelineRow(row) {
        return this.openAction("pipeline_stage", {
            stage_id: row.stage_id || false,
            team_id: row.team_id || false,
        });
    }

    openShortageProduct(row) {
        return this.openAction("shortage_product", { product_id: row.product_id });
    }

    openShortageRelated(row) {
        return this.openAction("shortage_related_document", {
            related_model: row.related_model,
            related_id: row.related_id,
        });
    }

    openPendingReceiptPo(row) {
        return this.openAction("pending_receipt_po", { purchase_order_id: row.id });
    }

    openPendingReceiptPicking(row) {
        if (row.picking_id) {
            return this.openAction("pending_receipt_picking", { picking_id: row.picking_id });
        }
    }

    openVendorRow(row) {
        return this.openAction("vendor_performance", { vendor_id: row.vendor_id });
    }

    openManufacturingOrder(row) {
        return this.openAction("manufacturing_order_row", { mo_id: row.id });
    }

    openManufacturingShortageMo(row) {
        return this.openAction("manufacturing_shortage_mo", { mo_id: row.mo_id });
    }

    openManufacturingShortageProduct(row) {
        return this.openAction("manufacturing_shortage_product", { product_id: row.product_id });
    }

    openWorkcenter(row) {
        return this.openAction("workcenter_row", { workcenter_id: row.workcenter_id });
    }

    openMaintenanceRequest(row) {
        return this.openAction("maintenance_request_row", { request_id: row.id });
    }

    openEquipment(row) {
        return this.openAction("equipment_row", { equipment_id: row.equipment_id });
    }

    openHrEmployee(row) {
        return this.openAction("hr_employee_row", { employee_id: row.id });
    }

    openHrLeave(row) {
        return this.openAction("hr_leave_row", { leave_id: row.id });
    }

    openHrContract(row) {
        return this.openAction("hr_contract_row", { contract_id: row.id });
    }

    openHelpdeskTicket(row) {
        return this.openAction("helpdesk_ticket_row", { ticket_id: row.id });
    }

    openHelpdeskTeam(row) {
        return this.openAction("helpdesk_team_row", { team_id: row.team_id });
    }

    openPosSession(row) {
        return this.openAction("pos_session_row", { session_id: row.id });
    }

    openPosOrder(row) {
        return this.openAction("pos_order_row", { order_id: row.id });
    }

    openPosProduct(row) {
        return this.openAction("pos_product_row", { product_id: row.product_id });
    }

    openWebsiteOrder(row) {
        return this.openAction("website_order_row", { order_id: row.id });
    }

    openWebsiteProduct(row) {
        return this.openAction("website_product_row", { product_id: row.product_id });
    }

    openWebsiteCustomer(row) {
        return this.openAction("website_customer_row", { partner_id: row.partner_id });
    }

    async createShortageActivity(row) {
        await this.createActivity("create_shortage_activity", row);
    }

    async createManufacturingShortageActivity(row) {
        await this.createActivity("create_manufacturing_shortage_activity", row);
    }

    async createActivity(method, payload) {
        try {
            const result = await this.orm.call("executive.dashboard.service", method, [payload]);
            this.notification.add((result && result.message) || _t("Activity created."), {
                type: "success",
            });
        } catch (error) {
            this.notification.add(error.message || _t("The activity could not be created."), {
                type: "danger",
            });
        }
    }

    async openAlert(row) {
        try {
            const action = await this.orm.call("executive.dashboard.service", "get_alert_action", [row]);
            if (action) {
                await this.action.doAction(action);
            }
        } catch (error) {
            this.notification.add(error.message || _t("The alert record could not be opened."), {
                type: "danger",
            });
        }
    }

    async createAlertActivity(row) {
        await this.createActivity("create_alert_activity", row);
    }

    get filterFields() {
        return this.constructor.filterFields;
    }

    get filterOptions() {
        return (this.state.data && this.state.data.filter_options) || {};
    }

    get data() {
        return this.state.data || {};
    }

    get alertsPreview() {
        return this.data.alerts_preview || [];
    }

    get charts() {
        return (this.data.chart_data && this.data.chart_data.charts) || [];
    }

    get currencyId() {
        return this.data.currency_id;
    }

    get hasActiveFilters() {
        return Object.values(this.state.filters).some((value) => Boolean(value));
    }

    formatKpi(kpi) {
        if (kpi.display_value) {
            return kpi.display_value;
        }
        return this.formatValue(kpi.value, kpi.format);
    }

    formatValue(value, valueFormat = "integer") {
        const number = Number(value || 0);
        if (valueFormat === "monetary" && this.currencyId) {
            return formatMonetary(number, { currencyId: this.currencyId });
        }
        if (valueFormat === "percentage") {
            return `${formatFloat(number, { digits: [false, 1] })}%`;
        }
        if (valueFormat === "float") {
            return formatFloat(number, { digits: [false, 1] });
        }
        return formatInteger(number, { humanReadable: false });
    }

    chartHasData(chart) {
        if (chart.datasets && chart.datasets.length) {
            return chart.datasets.some((dataset) => dataset.values.some((value) => value));
        }
        return Boolean(chart.data && chart.data.some((point) => point.value));
    }

    maxChartValue(chart) {
        if (chart.datasets && chart.datasets.length) {
            return Math.max(0, ...chart.datasets.flatMap((dataset) => dataset.values));
        }
        return Math.max(0, ...(chart.data || []).map((point) => point.value));
    }

    barWidth(value, maxValue) {
        if (!value || !maxValue) {
            return "0%";
        }
        return `${Math.max(3, Math.round((value / maxValue) * 100))}%`;
    }

    getDatasetExtra(chart, pointIndex, dataset) {
        const point = (chart.data && chart.data[pointIndex]) || {};
        return { ...(point.extra || {}), segment: dataset.key };
    }

    statusClass(state) {
        const classes = {
            draft: "text-bg-secondary",
            sent: "text-bg-info",
            sale: "text-bg-success",
            done: "text-bg-success",
            cancel: "text-bg-danger",
            purchase: "text-bg-success",
            waiting: "text-bg-warning",
            confirmed: "text-bg-warning",
            partially_available: "text-bg-warning",
            assigned: "text-bg-info",
            pending: "text-bg-secondary",
            partial: "text-bg-warning",
            full: "text-bg-success",
            progress: "text-bg-primary",
            to_close: "text-bg-info",
            blocked: "text-bg-danger",
            ready: "text-bg-secondary",
            operational: "text-bg-success",
            open: "text-bg-warning",
            present: "text-bg-success",
            absent: "text-bg-danger",
            late: "text-bg-warning",
            leave: "text-bg-info",
            inactive: "text-bg-secondary",
            confirm: "text-bg-warning",
            validate1: "text-bg-info",
            validate: "text-bg-success",
            refuse: "text-bg-danger",
            opening_control: "text-bg-info",
            opened: "text-bg-success",
            closing_control: "text-bg-warning",
            closed: "text-bg-secondary",
            paid: "text-bg-success",
            new: "text-bg-info",
            in_progress: "text-bg-primary",
            escalated: "text-bg-danger",
            resolved: "text-bg-success",
            ignored: "text-bg-secondary",
        };
        return classes[state] || "text-bg-light";
    }

    priorityClass(priority) {
        const classes = {
            0: "text-bg-secondary",
            1: "text-bg-info",
            2: "text-bg-warning",
            3: "text-bg-danger",
        };
        return classes[priority] || "text-bg-light";
    }

    severityClass(severity) {
        const classes = {
            critical: "text-bg-danger",
            high: "text-bg-warning",
            medium: "text-bg-info",
            low: "text-bg-secondary",
        };
        return classes[severity] || "text-bg-light";
    }
}
