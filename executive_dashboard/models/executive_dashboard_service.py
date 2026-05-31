from collections import defaultdict
from datetime import datetime, time, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class ExecutiveDashboardService(models.AbstractModel):
    _name = "executive.dashboard.service"
    _description = "Executive Dashboard Service"

    # -------------------------------------------------------------------------
    # Public RPC API
    # -------------------------------------------------------------------------

    @api.model
    def get_dashboard_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "sales_kpis": self._get_sales_kpis(filters),
            "crm_kpis": self._get_crm_kpis(filters),
            "delayed_sales": self._get_delayed_sales(filters),
            "pipeline_summary": self._get_pipeline_summary(filters),
            "chart_data": self._get_chart_data(filters),
            "inventory_kpis": self._get_inventory_kpis(filters),
            "purchase_kpis": self._get_purchase_kpis(filters),
            "missing_materials": self._get_missing_materials(filters),
            "pending_receipts": self._get_pending_receipts(filters),
            "vendor_performance": self._get_vendor_performance(filters),
            "inventory_purchase_chart_data": self._get_inventory_purchase_charts(filters),
            "manufacturing_kpis": self._get_manufacturing_kpis(filters),
            "manufacturing_orders": self._get_manufacturing_orders(filters),
            "manufacturing_shortages": self._get_manufacturing_shortages(filters),
            "workcenter_kpis": self._get_workcenter_kpis(filters),
            "workcenter_performance": self._get_workcenter_performance(filters),
            "manufacturing_chart_data": self._get_manufacturing_charts(filters),
            "maintenance_kpis": self._get_maintenance_kpis(filters),
            "maintenance_requests": self._get_maintenance_requests(filters),
            "equipment_status": self._get_equipment_status(filters),
            "maintenance_chart_data": self._get_maintenance_charts(filters),
            "meta": {
                "has_delivery_status": self._has_field("sale.order", "delivery_status"),
                "has_sale_stock": self._has_field("sale.order", "picking_ids"),
                "has_inventory_value": self._can_read_inventory_value(),
                "has_purchase_receipts": self._has_field("purchase.order", "receipt_status"),
                "has_maintenance_downtime": False,
            },
        }

    @api.model
    def get_overview_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "overview_kpis": self._get_overview_kpis(filters),
            "department_cards": self._get_department_cards(filters),
            "alerts_preview": self._get_alert_rows(filters, limit=6, severity="critical"),
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_sales_dashboard_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "sales_kpis": self._get_sales_kpis(filters),
            "delayed_sales": self._get_delayed_sales(filters, limit=50),
            "chart_data": self._get_sales_charts(filters),
            "alerts_preview": self._get_alert_rows(filters, limit=10, department="sales"),
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_crm_dashboard_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "crm_kpis": self._get_crm_kpis(filters),
            "pipeline_summary": self._get_pipeline_summary(filters),
            "chart_data": self._get_crm_charts(filters),
            "alerts_preview": [],
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_inventory_dashboard_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "inventory_kpis": self._get_inventory_kpis(filters),
            "missing_materials": self._get_missing_materials(filters, limit=50),
            "chart_data": self._get_inventory_charts(filters),
            "alerts_preview": self._get_alert_rows(filters, limit=10, department="inventory"),
            "meta": {
                "has_inventory_value": self._can_read_inventory_value(),
            },
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_purchase_dashboard_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "purchase_kpis": self._get_purchase_kpis(filters),
            "pending_receipts": self._get_pending_receipts(filters, limit=50),
            "vendor_performance": self._get_vendor_performance(filters),
            "chart_data": self._get_purchase_charts(filters),
            "alerts_preview": self._get_alert_rows(filters, limit=10, department="purchase"),
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_manufacturing_dashboard_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "manufacturing_kpis": self._get_manufacturing_kpis(filters),
            "manufacturing_orders": self._get_manufacturing_orders(filters, limit=50),
            "manufacturing_shortages": self._get_manufacturing_shortages(filters, limit=50),
            "workcenter_kpis": self._get_workcenter_kpis(filters),
            "workcenter_performance": self._get_workcenter_performance(filters, limit=50),
            "chart_data": self._get_manufacturing_charts(filters),
            "alerts_preview": self._get_alert_rows(filters, limit=10, department="manufacturing"),
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_maintenance_dashboard_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "maintenance_kpis": self._get_maintenance_kpis(filters),
            "maintenance_requests": self._get_maintenance_requests(filters, limit=50),
            "equipment_status": self._get_equipment_status(filters, limit=50),
            "chart_data": self._get_maintenance_charts(filters),
            "alerts_preview": self._get_alert_rows(filters, limit=10, department="maintenance"),
            "meta": {
                "has_maintenance_downtime": False,
            },
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_hr_dashboard_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "hr_kpis": self._get_hr_kpis(filters),
            "employees_overview": self._get_hr_employees_overview(filters, limit=50),
            "leave_requests": self._get_hr_leave_requests(filters, limit=50),
            "contracts_expiring": self._get_hr_contracts_expiring(filters, limit=50),
            "chart_data": self._get_hr_charts(filters),
            "alerts_preview": [],
            "meta": self._get_hr_meta(),
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_helpdesk_dashboard_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "helpdesk_kpis": self._get_helpdesk_kpis(filters),
            "tickets_overview": self._get_helpdesk_tickets_overview(filters, limit=50),
            "delayed_tickets": self._get_helpdesk_delayed_tickets(filters, limit=50),
            "team_performance": self._get_helpdesk_team_performance(filters, limit=50),
            "chart_data": self._get_helpdesk_charts(filters),
            "alerts_preview": [],
            "meta": self._get_helpdesk_meta(),
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_pos_dashboard_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "pos_kpis": self._get_pos_kpis(filters),
            "pos_sessions": self._get_pos_sessions_table(filters, limit=50),
            "pos_orders": self._get_pos_orders_table(filters, limit=50),
            "pos_products": self._get_pos_products_table(filters, limit=50),
            "chart_data": self._get_pos_charts(filters),
            "alerts_preview": [],
            "meta": self._get_pos_meta(),
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_website_dashboard_data(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "currency_id": self.env.company.currency_id.id,
            "website_kpis": self._get_website_kpis(filters),
            "website_orders": self._get_website_orders_table(filters, limit=50),
            "website_products": self._get_website_products_table(filters, limit=50),
            "website_customers": self._get_website_customers_table(filters, limit=50),
            "chart_data": self._get_website_charts(filters),
            "alerts_preview": [],
            "meta": self._get_website_meta(),
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_alerts_data(self, filters=None):
        filters = self._normalize_filters(filters)
        alerts = self._get_alert_rows(filters, limit=100)
        smart_alerts = self._get_smart_alert_rows(filters, limit=100)
        return {
            "filters": self._serialize_filters(filters),
            "filter_options": self._get_filter_options(),
            "alerts": alerts,
            "smart_alerts": smart_alerts,
            "summary": self._get_alert_summary(alerts),
            "smart_summary": self._get_smart_alert_summary(smart_alerts),
            "last_updated": self._last_updated_label(),
        }

    @api.model
    def get_sales_action(self, action_key, filters=None, extra_context=None):
        return self.get_action(action_key, filters, extra_context)

    @api.model
    def get_crm_action(self, action_key, filters=None, extra_context=None):
        return self.get_action(action_key, filters, extra_context)

    @api.model
    def get_inventory_action(self, action_key, filters=None, extra_context=None):
        return self.get_action(action_key, filters, extra_context)

    @api.model
    def get_purchase_action(self, action_key, filters=None, extra_context=None):
        return self.get_action(action_key, filters, extra_context)

    @api.model
    def get_alert_action(self, payload):
        payload = payload or {}
        smart_alert_id = self._parse_int(payload.get("smart_alert_id"))
        if smart_alert_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "executive.dashboard.alert.history",
                "res_id": smart_alert_id,
                "view_mode": "form",
                "target": "current",
            }
        return self._open_record_action(
            payload.get("related_model"),
            payload.get("related_id"),
            payload.get("related_document") or _("Related Record"),
        )

    @api.model
    def create_alert_activity(self, data):
        return self._create_alert_activity(data or {})

    @api.model
    def get_sales_kpis(self, filters=None):
        return self._get_sales_kpis(self._normalize_filters(filters))

    @api.model
    def get_crm_kpis(self, filters=None):
        return self._get_crm_kpis(self._normalize_filters(filters))

    @api.model
    def get_delayed_sales(self, filters=None):
        return self._get_delayed_sales(self._normalize_filters(filters))

    @api.model
    def get_pipeline_summary(self, filters=None):
        return self._get_pipeline_summary(self._normalize_filters(filters))

    @api.model
    def get_chart_data(self, filters=None):
        return self._get_chart_data(self._normalize_filters(filters))

    @api.model
    def get_inventory_kpis(self, filters=None):
        return self._get_inventory_kpis(self._normalize_filters(filters))

    @api.model
    def get_purchase_kpis(self, filters=None):
        return self._get_purchase_kpis(self._normalize_filters(filters))

    @api.model
    def get_missing_materials(self, filters=None):
        return self._get_missing_materials(self._normalize_filters(filters))

    @api.model
    def get_pending_receipts(self, filters=None):
        return self._get_pending_receipts(self._normalize_filters(filters))

    @api.model
    def get_vendor_performance(self, filters=None):
        return self._get_vendor_performance(self._normalize_filters(filters))

    @api.model
    def get_inventory_purchase_charts(self, filters=None):
        return self._get_inventory_purchase_charts(self._normalize_filters(filters))

    @api.model
    def create_shortage_activity(self, data):
        return self._create_shortage_activity(data or {})

    @api.model
    def get_manufacturing_kpis(self, filters=None):
        return self._get_manufacturing_kpis(self._normalize_filters(filters))

    @api.model
    def get_manufacturing_orders(self, filters=None):
        return self._get_manufacturing_orders(self._normalize_filters(filters))

    @api.model
    def get_manufacturing_shortages(self, filters=None):
        return self._get_manufacturing_shortages(self._normalize_filters(filters))

    @api.model
    def get_workcenter_performance(self, filters=None):
        return self._get_workcenter_performance(self._normalize_filters(filters))

    @api.model
    def get_manufacturing_charts(self, filters=None):
        return self._get_manufacturing_charts(self._normalize_filters(filters))

    @api.model
    def create_manufacturing_shortage_activity(self, data):
        return self._create_manufacturing_shortage_activity(data or {})

    @api.model
    def get_manufacturing_action(self, action_key, filters=None, extra_context=None):
        return self._get_manufacturing_action(
            action_key,
            self._normalize_filters(filters),
            extra_context or {},
        )

    @api.model
    def get_maintenance_kpis(self, filters=None):
        return self._get_maintenance_kpis(self._normalize_filters(filters))

    @api.model
    def get_maintenance_requests(self, filters=None):
        return self._get_maintenance_requests(self._normalize_filters(filters))

    @api.model
    def get_equipment_status(self, filters=None):
        return self._get_equipment_status(self._normalize_filters(filters))

    @api.model
    def get_maintenance_charts(self, filters=None):
        return self._get_maintenance_charts(self._normalize_filters(filters))

    @api.model
    def get_maintenance_action(self, action_key, filters=None, extra_context=None):
        return self._get_maintenance_action(
            action_key,
            self._normalize_filters(filters),
            extra_context or {},
        )

    @api.model
    def get_hr_kpis(self, filters=None):
        return self._get_hr_kpis(self._normalize_filters(filters))

    @api.model
    def get_hr_tables(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "employees_overview": self._get_hr_employees_overview(filters, limit=50),
            "leave_requests": self._get_hr_leave_requests(filters, limit=50),
            "contracts_expiring": self._get_hr_contracts_expiring(filters, limit=50),
        }

    @api.model
    def get_hr_charts(self, filters=None):
        return self._get_hr_charts(self._normalize_filters(filters))

    @api.model
    def get_hr_action(self, action_key, filters=None, extra_context=None):
        return self._get_hr_action(
            action_key,
            self._normalize_filters(filters),
            extra_context or {},
        )

    @api.model
    def get_helpdesk_kpis(self, filters=None):
        return self._get_helpdesk_kpis(self._normalize_filters(filters))

    @api.model
    def get_helpdesk_tables(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "tickets_overview": self._get_helpdesk_tickets_overview(filters, limit=50),
            "delayed_tickets": self._get_helpdesk_delayed_tickets(filters, limit=50),
            "team_performance": self._get_helpdesk_team_performance(filters, limit=50),
        }

    @api.model
    def get_helpdesk_charts(self, filters=None):
        return self._get_helpdesk_charts(self._normalize_filters(filters))

    @api.model
    def get_helpdesk_action(self, action_key, filters=None, extra_context=None):
        return self._get_helpdesk_action(
            action_key,
            self._normalize_filters(filters),
            extra_context or {},
        )

    @api.model
    def get_pos_kpis(self, filters=None):
        return self._get_pos_kpis(self._normalize_filters(filters))

    @api.model
    def get_pos_tables(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "pos_sessions": self._get_pos_sessions_table(filters, limit=50),
            "pos_orders": self._get_pos_orders_table(filters, limit=50),
            "pos_products": self._get_pos_products_table(filters, limit=50),
        }

    @api.model
    def get_pos_charts(self, filters=None):
        return self._get_pos_charts(self._normalize_filters(filters))

    @api.model
    def get_pos_action(self, action_key, filters=None, extra_context=None):
        return self._get_pos_action(
            action_key,
            self._normalize_filters(filters),
            extra_context or {},
        )

    @api.model
    def get_website_kpis(self, filters=None):
        return self._get_website_kpis(self._normalize_filters(filters))

    @api.model
    def get_website_tables(self, filters=None):
        filters = self._normalize_filters(filters)
        return {
            "website_orders": self._get_website_orders_table(filters, limit=50),
            "website_products": self._get_website_products_table(filters, limit=50),
            "website_customers": self._get_website_customers_table(filters, limit=50),
        }

    @api.model
    def get_website_charts(self, filters=None):
        return self._get_website_charts(self._normalize_filters(filters))

    @api.model
    def get_website_action(self, action_key, filters=None, extra_context=None):
        return self._get_website_action(
            action_key,
            self._normalize_filters(filters),
            extra_context or {},
        )

    @api.model
    def get_inventory_purchase_action(self, action_key, filters=None, extra_context=None):
        return self._get_inventory_purchase_action(
            action_key,
            self._normalize_filters(filters),
            extra_context or {},
        )

    @api.model
    def get_action(self, action_key, filters=None, extra_context=None):
        filters = self._normalize_filters(filters)
        extra = extra_context or {}
        sale_domains = self._sales_domains(filters)
        crm_domains = self._crm_domains(filters)

        actions = {
            "total_customers": lambda: self._window_action(
                _("Total Customers"),
                "res.partner",
                self._partner_domain(filters),
            ),
            "customers_with_sales_orders": lambda: self._window_action(
                _("Customers with Sales Orders"),
                "res.partner",
                self._partner_ids_domain(
                    self._sale_partner_ids(sale_domains["total_sales_orders"])
                ),
            ),
            "customers_with_quotations": lambda: self._window_action(
                _("Customers with Quotations"),
                "res.partner",
                self._partner_ids_domain(
                    self._sale_partner_ids(sale_domains["total_quotations"])
                ),
            ),
            "total_quotations": lambda: self._window_action(
                _("Total Quotations"), "sale.order", sale_domains["total_quotations"]
            ),
            "open_quotations": lambda: self._window_action(
                _("Open Quotations"), "sale.order", sale_domains["open_quotations"]
            ),
            "delayed_quotations": lambda: self._window_action(
                _("Delayed Quotations"), "sale.order", sale_domains["delayed_quotations"]
            ),
            "quotations_converted": lambda: self._window_action(
                _("Quotations Converted to Sales Orders"),
                "sale.order",
                sale_domains["quotations_converted"],
            ),
            "total_sales_orders": lambda: self._window_action(
                _("Total Sales Orders"), "sale.order", sale_domains["total_sales_orders"]
            ),
            "confirmed_sales_orders": lambda: self._window_action(
                _("Confirmed Sales Orders"),
                "sale.order",
                sale_domains["confirmed_sales_orders"],
            ),
            "delivered_sales_orders": lambda: self._window_action(
                _("Delivered Sales Orders"),
                "sale.order",
                sale_domains["delivered_sales_orders"],
            ),
            "undelivered_sales_orders": lambda: self._window_action(
                _("Undelivered Sales Orders"),
                "sale.order",
                sale_domains["undelivered_sales_orders"],
            ),
            "delayed_sales_orders": lambda: self._window_action(
                _("Delayed Sales Orders"),
                "sale.order",
                sale_domains["delayed_sales_orders"],
            ),
            "orders_delivery_today": lambda: self._window_action(
                _("Orders Planned for Delivery Today"),
                "sale.order",
                sale_domains["orders_delivery_today"],
            ),
            "orders_delivery_week": lambda: self._window_action(
                _("Orders Planned for Delivery This Week"),
                "sale.order",
                sale_domains["orders_delivery_week"],
            ),
            "orders_delivery_month": lambda: self._window_action(
                _("Orders Planned for Delivery This Month"),
                "sale.order",
                sale_domains["orders_delivery_month"],
            ),
            "total_leads": lambda: self._window_action(
                _("Total Leads"), "crm.lead", crm_domains["total_leads"]
            ),
            "total_opportunities": lambda: self._window_action(
                _("Total Opportunities"),
                "crm.lead",
                crm_domains["total_opportunities"],
                context={"active_test": False},
            ),
            "won_opportunities": lambda: self._window_action(
                _("Won Opportunities"),
                "crm.lead",
                crm_domains["won_opportunities"],
                context={"active_test": False},
            ),
            "lost_opportunities": lambda: self._window_action(
                _("Lost Opportunities"),
                "crm.lead",
                crm_domains["lost_opportunities"],
                context={"active_test": False},
            ),
            "conversion_rate": lambda: self._window_action(
                _("Closed Opportunities"),
                "crm.lead",
                crm_domains["closed_opportunities"],
                context={"active_test": False},
            ),
            "sent_quotations_crm": lambda: self._window_action(
                _("Sent Quotations from CRM"),
                "sale.order",
                sale_domains["sent_quotations_crm"],
            ),
            "expected_revenue": lambda: self._window_action(
                _("Expected Revenue Opportunities"),
                "crm.lead",
                crm_domains["pipeline_opportunities"],
            ),
            "pipeline_value": lambda: self._window_action(
                _("Pipeline Opportunities"),
                "crm.lead",
                crm_domains["pipeline_opportunities"],
            ),
        }

        if action_key in actions:
            return actions[action_key]()
        if action_key == "delayed_sale_row":
            return self._open_sale_order(extra.get("order_id"))
        if action_key == "pipeline_stage":
            return self._pipeline_stage_action(filters, extra)
        if action_key == "chart_monthly_sales":
            return self._chart_monthly_sales_action(filters, extra)
        if action_key == "chart_quotations_vs_sales":
            return self._chart_quotations_vs_sales_action(filters, extra)
        if action_key == "chart_salesperson_performance":
            return self._chart_salesperson_action(filters, extra)
        if action_key == "chart_crm_pipeline_stage":
            return self._chart_crm_stage_action(filters, extra)
        phase2_action = self._get_inventory_purchase_action(action_key, filters, extra)
        if phase2_action:
            return phase2_action
        phase3_action = self._get_manufacturing_action(action_key, filters, extra)
        if phase3_action:
            return phase3_action
        maintenance_action = self._get_maintenance_action(action_key, filters, extra)
        if maintenance_action:
            return maintenance_action
        hr_action = self._get_hr_action(action_key, filters, extra)
        if hr_action:
            return hr_action
        helpdesk_action = self._get_helpdesk_action(action_key, filters, extra)
        if helpdesk_action:
            return helpdesk_action
        pos_action = self._get_pos_action(action_key, filters, extra)
        if pos_action:
            return pos_action
        website_action = self._get_website_action(action_key, filters, extra)
        if website_action:
            return website_action
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "warning",
                "message": _("The requested dashboard action is not available."),
            },
        }

    # -------------------------------------------------------------------------
    # Filter helpers
    # -------------------------------------------------------------------------

    def _normalize_filters(self, filters):
        filters = filters if isinstance(filters, dict) else {}
        allowed_company_ids = self.env.companies.ids or [self.env.company.id]

        date_from = self._parse_date(filters.get("date_from"))
        date_to = self._parse_date(filters.get("date_to"))
        if date_from and date_to and date_from > date_to:
            date_from, date_to = date_to, date_from

        salesperson_id = self._parse_int(filters.get("salesperson_id"))
        company_id = self._parse_int(filters.get("company_id"))
        if company_id not in allowed_company_ids:
            company_id = False
        company_ids = [company_id] if company_id else allowed_company_ids

        sales_team_id = self._parse_int(filters.get("sales_team_id"))
        if sales_team_id:
            team = self.env["crm.team"].search(
                [
                    ("id", "=", sales_team_id),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "in", company_ids),
                ],
                limit=1,
            )
            sales_team_id = team.id or False

        warehouse_id = self._parse_int(filters.get("warehouse_id"))
        if warehouse_id:
            warehouse = self.env["stock.warehouse"].search(
                [("id", "=", warehouse_id), ("company_id", "in", company_ids)],
                limit=1,
            )
            warehouse_id = warehouse.id or False

        vendor_id = self._parse_int(filters.get("vendor_id"))
        if vendor_id:
            vendor = self.env["res.partner"].search(
                [
                    ("id", "=", vendor_id),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "in", company_ids),
                ],
                limit=1,
            )
            vendor_id = vendor.id or False

        product_category_id = self._parse_int(filters.get("product_category_id"))
        if product_category_id:
            category = self.env["product.category"].search(
                [("id", "=", product_category_id)],
                limit=1,
            )
            product_category_id = category.id or False

        product_id = self._parse_int(filters.get("product_id"))
        if product_id:
            product = self.env["product.product"].search(
                [
                    ("id", "=", product_id),
                    ("is_storable", "=", True),
                    "|",
                    ("product_tmpl_id.company_id", "=", False),
                    ("product_tmpl_id.company_id", "in", company_ids),
                ],
                limit=1,
            )
            product_id = product.id or False

        manufacturing_user_id = self._parse_int(filters.get("manufacturing_user_id"))
        if manufacturing_user_id:
            user = self.env["res.users"].search(
                [("id", "=", manufacturing_user_id), ("share", "=", False)],
                limit=1,
            )
            manufacturing_user_id = user.id or False

        workcenter_id = self._parse_int(filters.get("workcenter_id"))
        if workcenter_id:
            workcenter = self.env["mrp.workcenter"].search(
                [
                    ("id", "=", workcenter_id),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "in", company_ids),
                ],
                limit=1,
            )
            workcenter_id = workcenter.id or False

        manufacturing_state = filters.get("manufacturing_state") or False
        if manufacturing_state not in self._selection_values("mrp.production", "state"):
            manufacturing_state = False

        maintenance_team_id = self._parse_int(filters.get("maintenance_team_id"))
        if maintenance_team_id:
            team = self.env["maintenance.team"].search(
                [
                    ("id", "=", maintenance_team_id),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "in", company_ids),
                ],
                limit=1,
            )
            maintenance_team_id = team.id or False

        equipment_id = self._parse_int(filters.get("equipment_id"))
        if equipment_id:
            equipment = self.env["maintenance.equipment"].search(
                [
                    ("id", "=", equipment_id),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "in", company_ids),
                ],
                limit=1,
            )
            equipment_id = equipment.id or False

        technician_id = self._parse_int(filters.get("technician_id"))
        if technician_id:
            technician = self.env["res.users"].search(
                [("id", "=", technician_id), ("share", "=", False)],
                limit=1,
            )
            technician_id = technician.id or False

        maintenance_stage_id = self._parse_int(filters.get("maintenance_stage_id"))
        if maintenance_stage_id:
            stage = self.env["maintenance.stage"].search(
                [("id", "=", maintenance_stage_id)],
                limit=1,
            )
            maintenance_stage_id = stage.id or False

        hr_department_id = self._parse_int(filters.get("hr_department_id"))
        if hr_department_id and self._has_model("hr.department"):
            department_domain = [("id", "=", hr_department_id)]
            if self._has_field("hr.department", "company_id"):
                department_domain += [
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "in", company_ids),
                ]
            department = self.env["hr.department"].search(department_domain, limit=1)
            hr_department_id = department.id or False
        else:
            hr_department_id = False

        hr_employee_id = self._parse_int(filters.get("hr_employee_id"))
        if hr_employee_id and self._has_model("hr.employee"):
            employee_domain = [("id", "=", hr_employee_id)]
            if self._has_field("hr.employee", "company_id"):
                employee_domain.append(("company_id", "in", company_ids))
            employee = self.env["hr.employee"].with_context(active_test=False).search(
                employee_domain,
                limit=1,
            )
            hr_employee_id = employee.id or False
        else:
            hr_employee_id = False

        hr_manager_id = self._parse_int(filters.get("hr_manager_id"))
        if hr_manager_id and self._has_model("hr.employee"):
            manager_domain = [("id", "=", hr_manager_id)]
            if self._has_field("hr.employee", "company_id"):
                manager_domain.append(("company_id", "in", company_ids))
            manager = self.env["hr.employee"].with_context(active_test=False).search(
                manager_domain,
                limit=1,
            )
            hr_manager_id = manager.id or False
        else:
            hr_manager_id = False

        hr_job_id = self._parse_int(filters.get("hr_job_id"))
        if hr_job_id and self._has_model("hr.job"):
            job_domain = [("id", "=", hr_job_id)]
            if self._has_field("hr.job", "company_id"):
                job_domain += [
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "in", company_ids),
                ]
            job = self.env["hr.job"].search(job_domain, limit=1)
            hr_job_id = job.id or False
        else:
            hr_job_id = False

        helpdesk_team_id = self._parse_int(filters.get("helpdesk_team_id"))
        if helpdesk_team_id and self._has_model("helpdesk.team"):
            team_domain = [("id", "=", helpdesk_team_id)]
            if self._has_field("helpdesk.team", "company_id"):
                team_domain.append(("company_id", "in", company_ids))
            team = self.env["helpdesk.team"].search(team_domain, limit=1)
            helpdesk_team_id = team.id or False
        else:
            helpdesk_team_id = False

        helpdesk_user_id = self._parse_int(filters.get("helpdesk_user_id"))
        if helpdesk_user_id:
            user = self.env["res.users"].search(
                [("id", "=", helpdesk_user_id), ("share", "=", False)],
                limit=1,
            )
            helpdesk_user_id = user.id or False

        helpdesk_stage_id = self._parse_int(filters.get("helpdesk_stage_id"))
        if helpdesk_stage_id and self._has_model("helpdesk.stage"):
            stage = self.env["helpdesk.stage"].search(
                [("id", "=", helpdesk_stage_id)],
                limit=1,
            )
            helpdesk_stage_id = stage.id or False
        else:
            helpdesk_stage_id = False

        helpdesk_priority = filters.get("helpdesk_priority") or False
        if helpdesk_priority not in self._selection_values("helpdesk.ticket", "priority"):
            helpdesk_priority = False

        pos_config_id = self._parse_int(filters.get("pos_config_id"))
        if pos_config_id and self._has_model("pos.config"):
            pos_config_domain = [("id", "=", pos_config_id)]
            if self._has_field("pos.config", "company_id"):
                pos_config_domain.append(("company_id", "in", company_ids))
            pos_config = self.env["pos.config"].search(pos_config_domain, limit=1)
            pos_config_id = pos_config.id or False
        else:
            pos_config_id = False

        pos_cashier_id = self._parse_int(filters.get("pos_cashier_id"))
        if pos_cashier_id:
            cashier = self.env["res.users"].search(
                [("id", "=", pos_cashier_id), ("share", "=", False)],
                limit=1,
            )
            pos_cashier_id = cashier.id or False

        pos_payment_method_id = self._parse_int(filters.get("pos_payment_method_id"))
        if pos_payment_method_id and self._has_model("pos.payment.method"):
            payment_method_domain = [("id", "=", pos_payment_method_id)]
            if self._has_field("pos.payment.method", "company_id"):
                payment_method_domain.append(("company_id", "in", company_ids))
            payment_method = self.env["pos.payment.method"].search(payment_method_domain, limit=1)
            pos_payment_method_id = payment_method.id or False
        else:
            pos_payment_method_id = False

        pos_session_state = filters.get("pos_session_state") or False
        if pos_session_state not in self._selection_values("pos.session", "state"):
            pos_session_state = False

        website_id = self._parse_int(filters.get("website_id"))
        if website_id and self._has_model("website"):
            website_domain = [("id", "=", website_id)]
            if self._has_field("website", "company_id"):
                website_domain.append(("company_id", "in", company_ids))
            website = self.env["website"].search(website_domain, limit=1)
            website_id = website.id or False
        else:
            website_id = False

        website_customer_id = self._parse_int(filters.get("website_customer_id"))
        if website_customer_id:
            customer = self.env["res.partner"].search(
                [
                    ("id", "=", website_customer_id),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "in", company_ids),
                ],
                limit=1,
            )
            website_customer_id = customer.id or False

        website_order_state = filters.get("website_order_state") or False
        if website_order_state not in self._selection_values("sale.order", "state"):
            website_order_state = False

        responsible_user_id = self._parse_int(filters.get("responsible_user_id"))
        if responsible_user_id:
            user = self.env["res.users"].search(
                [("id", "=", responsible_user_id), ("share", "=", False)],
                limit=1,
            )
            responsible_user_id = user.id or False

        department = filters.get("department") or False
        if department not in self._alert_department_keys():
            department = False

        severity = filters.get("severity") or False
        if severity not in self._alert_severity_keys():
            severity = False

        alert_status = filters.get("alert_status") or False
        if alert_status not in self._smart_alert_status_keys():
            alert_status = False

        alert_dashboard_key = filters.get("alert_dashboard_key") or False
        if alert_dashboard_key not in self._smart_alert_dashboard_keys():
            alert_dashboard_key = False

        return {
            "date_from": date_from,
            "date_to": date_to,
            "salesperson_id": salesperson_id,
            "company_id": company_id,
            "company_ids": company_ids,
            "sales_team_id": sales_team_id,
            "warehouse_id": warehouse_id,
            "vendor_id": vendor_id,
            "product_category_id": product_category_id,
            "product_id": product_id,
            "manufacturing_user_id": manufacturing_user_id,
            "workcenter_id": workcenter_id,
            "manufacturing_state": manufacturing_state,
            "maintenance_team_id": maintenance_team_id,
            "equipment_id": equipment_id,
            "technician_id": technician_id,
            "maintenance_stage_id": maintenance_stage_id,
            "hr_department_id": hr_department_id,
            "hr_employee_id": hr_employee_id,
            "hr_manager_id": hr_manager_id,
            "hr_job_id": hr_job_id,
            "helpdesk_team_id": helpdesk_team_id,
            "helpdesk_user_id": helpdesk_user_id,
            "helpdesk_stage_id": helpdesk_stage_id,
            "helpdesk_priority": helpdesk_priority,
            "pos_config_id": pos_config_id,
            "pos_cashier_id": pos_cashier_id,
            "pos_payment_method_id": pos_payment_method_id,
            "pos_session_state": pos_session_state,
            "website_id": website_id,
            "website_customer_id": website_customer_id,
            "website_order_state": website_order_state,
            "responsible_user_id": responsible_user_id,
            "department": department,
            "severity": severity,
            "alert_status": alert_status,
            "alert_dashboard_key": alert_dashboard_key,
        }

    def _serialize_filters(self, filters):
        return {
            "date_from": fields.Date.to_string(filters["date_from"])
            if filters["date_from"]
            else False,
            "date_to": fields.Date.to_string(filters["date_to"])
            if filters["date_to"]
            else False,
            "salesperson_id": filters["salesperson_id"] or False,
            "company_id": filters["company_id"] or False,
            "sales_team_id": filters["sales_team_id"] or False,
            "warehouse_id": filters["warehouse_id"] or False,
            "vendor_id": filters["vendor_id"] or False,
            "product_category_id": filters["product_category_id"] or False,
            "product_id": filters["product_id"] or False,
            "manufacturing_user_id": filters["manufacturing_user_id"] or False,
            "workcenter_id": filters["workcenter_id"] or False,
            "manufacturing_state": filters["manufacturing_state"] or False,
            "maintenance_team_id": filters["maintenance_team_id"] or False,
            "equipment_id": filters["equipment_id"] or False,
            "technician_id": filters["technician_id"] or False,
            "maintenance_stage_id": filters["maintenance_stage_id"] or False,
            "hr_department_id": filters["hr_department_id"] or False,
            "hr_employee_id": filters["hr_employee_id"] or False,
            "hr_manager_id": filters["hr_manager_id"] or False,
            "hr_job_id": filters["hr_job_id"] or False,
            "helpdesk_team_id": filters["helpdesk_team_id"] or False,
            "helpdesk_user_id": filters["helpdesk_user_id"] or False,
            "helpdesk_stage_id": filters["helpdesk_stage_id"] or False,
            "helpdesk_priority": filters["helpdesk_priority"] or False,
            "pos_config_id": filters["pos_config_id"] or False,
            "pos_cashier_id": filters["pos_cashier_id"] or False,
            "pos_payment_method_id": filters["pos_payment_method_id"] or False,
            "pos_session_state": filters["pos_session_state"] or False,
            "website_id": filters["website_id"] or False,
            "website_customer_id": filters["website_customer_id"] or False,
            "website_order_state": filters["website_order_state"] or False,
            "responsible_user_id": filters["responsible_user_id"] or False,
            "department": filters["department"] or False,
            "severity": filters["severity"] or False,
            "alert_status": filters.get("alert_status") or False,
            "alert_dashboard_key": filters.get("alert_dashboard_key") or False,
        }

    def _get_filter_options(self):
        companies = [
            {"id": company.id, "name": company.display_name}
            for company in self.env.companies
        ]
        users = self.env["res.users"].search_read(
            [("share", "=", False)], ["id", "name"], order="name", limit=200
        )
        sales_teams = self.env["crm.team"].search_read(
            [
                "|",
                ("company_id", "=", False),
                ("company_id", "in", self.env.companies.ids),
            ],
            ["id", "name", "company_id"],
            order="name",
            limit=200,
        )
        warehouses = self.env["stock.warehouse"].search_read(
            [("company_id", "in", self.env.companies.ids)],
            ["id", "name", "company_id"],
            order="name",
            limit=200,
        )
        vendors = self.env["res.partner"].search_read(
            [
                ("supplier_rank", ">", 0),
                "|",
                ("company_id", "=", False),
                ("company_id", "in", self.env.companies.ids),
            ],
            ["id", "name"],
            order="name",
            limit=200,
        )
        product_categories = self.env["product.category"].search_read(
            [], ["id", "complete_name"], order="complete_name", limit=300
        )
        product_domain = [
            ("is_storable", "=", True),
            "|",
            ("product_tmpl_id.company_id", "=", False),
            ("product_tmpl_id.company_id", "in", self.env.companies.ids),
        ]
        products = self.env["product.product"].search_read(
            product_domain,
            ["id", "display_name"],
            order="name",
            limit=300,
        )
        workcenters = self.env["mrp.workcenter"].search_read(
            [
                "|",
                ("company_id", "=", False),
                ("company_id", "in", self.env.companies.ids),
            ],
            ["id", "name", "company_id"],
            order="name",
            limit=200,
        )
        maintenance_teams = self.env["maintenance.team"].search_read(
            [
                "|",
                ("company_id", "=", False),
                ("company_id", "in", self.env.companies.ids),
            ],
            ["id", "name", "company_id"],
            order="name",
            limit=200,
        )
        equipment = self.env["maintenance.equipment"].search_read(
            [
                "|",
                ("company_id", "=", False),
                ("company_id", "in", self.env.companies.ids),
            ],
            ["id", "display_name", "company_id"],
            order="name",
            limit=300,
        )
        maintenance_stages = self.env["maintenance.stage"].search_read(
            [], ["id", "name"], order="sequence, id", limit=100
        )
        hr_departments = []
        if self._can_read_model("hr.department"):
            hr_department_fields = ["id", "name"]
            if self._has_field("hr.department", "complete_name"):
                hr_department_fields.append("complete_name")
            if self._has_field("hr.department", "company_id"):
                hr_department_fields.append("company_id")
            hr_departments = self.env["hr.department"].search_read(
                [
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "in", self.env.companies.ids),
                ]
                if self._has_field("hr.department", "company_id")
                else [],
                hr_department_fields,
                # complete_name is computed/non-stored on Odoo 19 hr.department,
                # so it cannot be used in SQL ORDER BY.
                order="name",
                limit=200,
            )
            for department in hr_departments:
                department["complete_name"] = department.get("complete_name") or department.get("name")

        hr_employees = []
        if self._can_read_model("hr.employee"):
            hr_employee_fields = ["id", "display_name"]
            for field_name in ("department_id", "company_id"):
                if self._has_field("hr.employee", field_name):
                    hr_employee_fields.append(field_name)
            hr_employee_domain = (
                [("company_id", "in", self.env.companies.ids)]
                if self._has_field("hr.employee", "company_id")
                else []
            )
            hr_employees = self.env["hr.employee"].with_context(active_test=False).search_read(
                hr_employee_domain,
                hr_employee_fields,
                order="name",
                limit=300,
            )

        hr_managers = []
        if self._can_read_model("hr.employee"):
            manager_domain = (
                [("child_ids", "!=", False)]
                if self._has_field("hr.employee", "child_ids")
                else []
            )
            if self._has_field("hr.employee", "company_id"):
                manager_domain.append(("company_id", "in", self.env.companies.ids))
            hr_managers = self.env["hr.employee"].with_context(active_test=False).search_read(
                manager_domain,
                ["id", "display_name"],
                order="name",
                limit=200,
            )

        hr_jobs = []
        if self._can_read_model("hr.job"):
            hr_job_fields = ["id", "name"]
            if self._has_field("hr.job", "company_id"):
                hr_job_fields.append("company_id")
            if self._has_field("hr.job", "department_id"):
                hr_job_fields.append("department_id")
            hr_jobs = self.env["hr.job"].search_read(
                [
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "in", self.env.companies.ids),
                ]
                if self._has_field("hr.job", "company_id")
                else [],
                hr_job_fields,
                order="name",
                limit=200,
            )

        helpdesk_teams = []
        if self._can_read_model("helpdesk.team"):
            helpdesk_team_fields = ["id", "name"]
            if self._has_field("helpdesk.team", "company_id"):
                helpdesk_team_fields.append("company_id")
            helpdesk_teams = self.env["helpdesk.team"].search_read(
                [("company_id", "in", self.env.companies.ids)]
                if self._has_field("helpdesk.team", "company_id")
                else [],
                helpdesk_team_fields,
                order="name",
                limit=200,
            )

        helpdesk_stages = []
        if self._can_read_model("helpdesk.stage"):
            helpdesk_stages = self.env["helpdesk.stage"].search_read(
                [],
                ["id", "name"],
                order="sequence, id",
                limit=100,
            )

        pos_configs = []
        if self._can_read_model("pos.config"):
            pos_config_fields = ["id", "name"]
            if self._has_field("pos.config", "company_id"):
                pos_config_fields.append("company_id")
            pos_configs = self.env["pos.config"].search_read(
                [("company_id", "in", self.env.companies.ids)]
                if self._has_field("pos.config", "company_id")
                else [],
                pos_config_fields,
                order="name",
                limit=200,
            )

        pos_payment_methods = []
        if self._can_read_model("pos.payment.method"):
            pos_payment_method_fields = ["id", "name"]
            if self._has_field("pos.payment.method", "company_id"):
                pos_payment_method_fields.append("company_id")
            pos_payment_methods = self.env["pos.payment.method"].search_read(
                [("company_id", "in", self.env.companies.ids)]
                if self._has_field("pos.payment.method", "company_id")
                else [],
                pos_payment_method_fields,
                order="name",
                limit=200,
            )

        websites = []
        if self._can_read_model("website"):
            website_fields = ["id", "name"]
            if self._has_field("website", "company_id"):
                website_fields.append("company_id")
            websites = self.env["website"].search_read(
                [("company_id", "in", self.env.companies.ids)]
                if self._has_field("website", "company_id")
                else [],
                website_fields,
                order="name",
                limit=100,
            )

        website_customers = []
        if self._has_field("sale.order", "website_id"):
            partner_groups = self.env["sale.order"].read_group(
                [
                    ("website_id", "!=", False),
                    ("partner_id", "!=", False),
                    ("company_id", "in", self.env.companies.ids),
                ],
                ["partner_id"],
                ["partner_id"],
                lazy=False,
            )
            partner_ids = [group["partner_id"][0] for group in partner_groups[:300] if group.get("partner_id")]
            if partner_ids:
                website_customers = self.env["res.partner"].search_read(
                    [("id", "in", partner_ids)],
                    ["id", "display_name"],
                    order="name",
                    limit=300,
                )
        return {
            "companies": companies,
            "salespersons": users,
            "sales_teams": sales_teams,
            "warehouses": warehouses,
            "vendors": vendors,
            "product_categories": product_categories,
            "products": products,
            "manufacturing_users": users,
            "workcenters": workcenters,
            "manufacturing_states": [
                {"id": value, "name": label}
                for value, label in self._selection_labels("mrp.production", "state").items()
            ],
            "maintenance_teams": maintenance_teams,
            "equipment": equipment,
            "technicians": users,
            "maintenance_stages": maintenance_stages,
            "hr_departments": hr_departments,
            "hr_employees": hr_employees,
            "hr_managers": hr_managers,
            "hr_jobs": hr_jobs,
            "helpdesk_teams": helpdesk_teams,
            "helpdesk_users": users,
            "helpdesk_stages": helpdesk_stages,
            "helpdesk_priorities": [
                {"id": value, "name": label}
                for value, label in self._selection_labels("helpdesk.ticket", "priority").items()
            ],
            "pos_configs": pos_configs,
            "pos_cashiers": users,
            "pos_payment_methods": pos_payment_methods,
            "pos_session_states": [
                {"id": value, "name": label}
                for value, label in self._selection_labels("pos.session", "state").items()
            ],
            "websites": websites,
            "website_customers": website_customers,
            "website_order_states": [
                {"id": value, "name": label}
                for value, label in self._selection_labels("sale.order", "state").items()
            ],
            "responsible_users": users,
            "alert_departments": [
                {"id": key, "name": label}
                for key, label in self._alert_department_labels().items()
            ],
            "alert_severities": [
                {"id": key, "name": label}
                for key, label in self._alert_severity_labels().items()
            ],
            "smart_alert_statuses": [
                {"id": key, "name": label}
                for key, label in self._smart_alert_status_labels().items()
            ],
            "smart_alert_dashboards": [
                {"id": key, "name": label}
                for key, label in self._smart_alert_dashboard_labels().items()
            ],
        }

    def _parse_date(self, value):
        if not value:
            return False
        try:
            return fields.Date.to_date(value)
        except (TypeError, ValueError):
            return False

    def _parse_int(self, value):
        if not value:
            return False
        try:
            return int(value)
        except (TypeError, ValueError):
            return False

    # -------------------------------------------------------------------------
    # KPI data
    # -------------------------------------------------------------------------

    def _get_sales_kpis(self, filters):
        SaleOrder = self.env["sale.order"]
        domains = self._sales_domains(filters)

        # A quotation is the same sale.order record after confirmation in Odoo;
        # there is no default historical "converted from quotation" field.
        # Phase 1 therefore counts confirmed sales orders as converted quotations.
        return [
            self._kpi(
                "total_customers",
                _("Total Customers"),
                self.env["res.partner"].search_count(self._partner_domain(filters)),
            ),
            self._kpi(
                "customers_with_sales_orders",
                _("Customers with Sales Orders"),
                self._sale_distinct_partner_count(domains["total_sales_orders"]),
            ),
            self._kpi(
                "customers_with_quotations",
                _("Customers with Quotations"),
                self._sale_distinct_partner_count(domains["total_quotations"]),
            ),
            self._kpi(
                "total_quotations",
                _("Total Quotations"),
                SaleOrder.search_count(domains["total_quotations"]),
            ),
            self._kpi(
                "open_quotations",
                _("Open Quotations"),
                SaleOrder.search_count(domains["open_quotations"]),
            ),
            self._kpi(
                "delayed_quotations",
                _("Delayed Quotations"),
                SaleOrder.search_count(domains["delayed_quotations"]),
            ),
            self._kpi(
                "quotations_converted",
                _("Quotations Converted to Sales Orders"),
                SaleOrder.search_count(domains["quotations_converted"]),
            ),
            self._kpi(
                "total_sales_orders",
                _("Total Sales Orders"),
                SaleOrder.search_count(domains["total_sales_orders"]),
            ),
            self._kpi(
                "sales_revenue",
                _("Sales Revenue"),
                self._sum(SaleOrder, domains["total_sales_orders"], "amount_total"),
                value_format="monetary",
            ),
            self._kpi(
                "confirmed_sales_orders",
                _("Confirmed Sales Orders"),
                SaleOrder.search_count(domains["confirmed_sales_orders"]),
            ),
            self._kpi(
                "delivered_sales_orders",
                _("Delivered Sales Orders"),
                SaleOrder.search_count(domains["delivered_sales_orders"]),
            ),
            self._kpi(
                "undelivered_sales_orders",
                _("Undelivered Sales Orders"),
                SaleOrder.search_count(domains["undelivered_sales_orders"]),
            ),
            self._kpi(
                "delayed_sales_orders",
                _("Delayed Sales Orders"),
                SaleOrder.search_count(domains["delayed_sales_orders"]),
            ),
            self._kpi(
                "orders_delivery_today",
                _("Orders Planned for Delivery Today"),
                SaleOrder.search_count(domains["orders_delivery_today"]),
            ),
            self._kpi(
                "orders_delivery_week",
                _("Orders Planned for Delivery This Week"),
                SaleOrder.search_count(domains["orders_delivery_week"]),
            ),
            self._kpi(
                "orders_delivery_month",
                _("Orders Planned for Delivery This Month"),
                SaleOrder.search_count(domains["orders_delivery_month"]),
            ),
        ]

    def _get_crm_kpis(self, filters):
        Lead = self.env["crm.lead"]
        LeadAll = Lead.with_context(active_test=False)
        SaleOrder = self.env["sale.order"]
        crm_domains = self._crm_domains(filters)
        sale_domains = self._sales_domains(filters)

        won_count = LeadAll.search_count(crm_domains["won_opportunities"])
        lost_count = LeadAll.search_count(crm_domains["lost_opportunities"])
        closed_count = won_count + lost_count
        conversion_rate = round((won_count / closed_count) * 100, 1) if closed_count else 0

        return [
            self._kpi(
                "total_leads",
                _("Total Leads"),
                Lead.search_count(crm_domains["total_leads"]),
            ),
            self._kpi(
                "total_opportunities",
                _("Total Opportunities"),
                LeadAll.search_count(crm_domains["total_opportunities"]),
            ),
            self._kpi("won_opportunities", _("Won Opportunities"), won_count),
            self._kpi("lost_opportunities", _("Lost Opportunities"), lost_count),
            self._kpi(
                "conversion_rate",
                _("Conversion Rate"),
                conversion_rate,
                value_format="percentage",
            ),
            self._kpi(
                "sent_quotations_crm",
                _("Sent Quotations from CRM"),
                SaleOrder.search_count(sale_domains["sent_quotations_crm"]),
            ),
            self._kpi(
                "expected_revenue",
                _("Expected Revenue"),
                self._sum(Lead, crm_domains["pipeline_opportunities"], "expected_revenue"),
                value_format="monetary",
            ),
            self._kpi(
                "pipeline_value",
                _("Pipeline Value"),
                self._sum(Lead, crm_domains["pipeline_opportunities"], "prorated_revenue"),
                value_format="monetary",
            ),
        ]

    def _get_inventory_kpis(self, filters):
        Product = self.env["product.product"].with_context(**self._stock_context(filters))
        Picking = self.env["stock.picking"]
        product_domain = self._stockable_product_domain(filters)
        orderpoint_domain = self._orderpoint_domain(filters)
        below_rule_product_ids = self._below_reordering_product_ids(filters)
        has_orderpoints = bool(self.env["stock.warehouse.orderpoint"].search_count(orderpoint_domain))
        low_stock_count = (
            len(below_rule_product_ids)
            if has_orderpoints
            else Product.search_count(product_domain + [("virtual_available", "<=", 0)])
        )
        inventory_value = self._current_inventory_value(filters)
        inventory_value_kpi = self._kpi(
            "current_inventory_value",
            _("Current Inventory Value"),
            inventory_value or 0,
            value_format="monetary",
            display_value=False if inventory_value is not None else _("Unavailable"),
        )

        return [
            self._kpi(
                "total_stockable_products",
                _("Total Stockable Products"),
                Product.search_count(product_domain),
            ),
            self._kpi(
                "out_of_stock_products",
                _("Out of Stock Products"),
                Product.search_count(product_domain + [("qty_available", "<=", 0)]),
            ),
            self._kpi("low_stock_products", _("Low Stock Products"), low_stock_count),
            self._kpi(
                "products_below_reordering_rules",
                _("Products Below Reordering Rules"),
                len(below_rule_product_ids),
            ),
            inventory_value_kpi,
            self._kpi(
                "open_internal_transfers",
                _("Open Internal Transfers"),
                Picking.search_count(self._stock_picking_domain(filters, "internal")),
            ),
            self._kpi(
                "pending_receipts",
                _("Pending Receipts"),
                Picking.search_count(self._stock_picking_domain(filters, "incoming")),
            ),
            self._kpi(
                "pending_deliveries",
                _("Pending Deliveries"),
                Picking.search_count(self._stock_picking_domain(filters, "outgoing")),
            ),
            self._kpi(
                "delayed_deliveries",
                _("Delayed Deliveries"),
                Picking.search_count(self._delayed_delivery_domain(filters)),
            ),
            self._kpi(
                "orders_blocked_missing_materials",
                _("Orders Blocked Due to Missing Materials"),
                Picking.search_count(self._blocked_delivery_domain(filters)),
            ),
        ]

    def _get_purchase_kpis(self, filters):
        PurchaseOrder = self.env["purchase.order"]
        Picking = self.env["stock.picking"]
        purchase_domains = self._purchase_domains(filters)
        most_vendor = self._most_used_vendor(filters)

        return [
            self._kpi(
                "total_vendors",
                _("Total Vendors"),
                self.env["res.partner"].search_count(self._vendor_domain(filters)),
            ),
            self._kpi(
                "total_rfqs",
                _("Total RFQs"),
                PurchaseOrder.search_count(purchase_domains["total_rfqs"]),
            ),
            self._kpi(
                "total_purchase_orders",
                _("Total Purchase Orders"),
                PurchaseOrder.search_count(purchase_domains["total_purchase_orders"]),
            ),
            self._kpi(
                "open_rfqs",
                _("Open RFQs"),
                PurchaseOrder.search_count(purchase_domains["open_rfqs"]),
            ),
            self._kpi(
                "open_purchase_orders",
                _("Open Purchase Orders"),
                PurchaseOrder.search_count(purchase_domains["open_purchase_orders"]),
            ),
            self._kpi(
                "delayed_purchase_orders",
                _("Delayed Purchase Orders"),
                PurchaseOrder.search_count(purchase_domains["delayed_purchase_orders"]),
            ),
            self._kpi(
                "purchase_orders_not_fully_received",
                _("Purchase Orders Not Fully Received"),
                PurchaseOrder.search_count(purchase_domains["not_fully_received"]),
            ),
            self._kpi(
                "pending_warehouse_receipts",
                _("Pending Warehouse Receipts"),
                Picking.search_count(self._purchase_receipt_picking_domain(filters)),
            ),
            self._kpi(
                "total_purchase_amount",
                _("Total Purchase Amount"),
                self._sum(PurchaseOrder, purchase_domains["total_purchase_orders"], self._purchase_amount_field()),
                value_format="monetary",
            ),
            self._kpi(
                "most_used_vendor",
                _("Most Used Vendor"),
                most_vendor["count"],
                display_value=most_vendor["name"] or _("None"),
            ),
        ]

    def _kpi(self, key, label, value, value_format="integer", display_value=False):
        kpi = {
            "key": key,
            "label": label,
            "value": value or 0,
            "format": value_format,
        }
        if display_value:
            kpi["display_value"] = display_value
        return kpi

    def _overview_kpi(self, key, label, value, value_format="integer", action_key=False):
        kpi = self._kpi(key, label, value, value_format=value_format)
        if action_key:
            kpi["action_key"] = action_key
        return kpi

    def _get_overview_kpis(self, filters):
        SaleOrder = self.env["sale.order"]
        Lead = self.env["crm.lead"].with_context(active_test=False)
        Product = self.env["product.product"].with_context(**self._stock_context(filters))
        Picking = self.env["stock.picking"]
        PurchaseOrder = self.env["purchase.order"]
        Production = self.env["mrp.production"]
        MaintenanceRequest = self.env["maintenance.request"]

        sale_domains = self._sales_domains(filters)
        crm_domains = self._crm_domains(filters)
        purchase_domains = self._purchase_domains(filters)
        manufacturing_domains = self._manufacturing_domains(filters)
        maintenance_domains = self._maintenance_domains(filters)
        product_domain = self._stockable_product_domain(filters)
        below_rule_count = len(self._below_reordering_product_ids(filters))
        low_stock_count = below_rule_count or Product.search_count(product_domain + [("virtual_available", "<=", 0)])

        return [
            self._overview_kpi(
                "overview_sales_revenue",
                _("Total Sales Revenue"),
                self._sum(SaleOrder, sale_domains["total_sales_orders"], "amount_total"),
                value_format="monetary",
                action_key="total_sales_orders",
            ),
            self._overview_kpi(
                "overview_sales_orders",
                _("Total Sales Orders"),
                SaleOrder.search_count(sale_domains["total_sales_orders"]),
                action_key="total_sales_orders",
            ),
            self._overview_kpi(
                "overview_delayed_sales_orders",
                _("Delayed Sales Orders"),
                SaleOrder.search_count(sale_domains["delayed_sales_orders"]),
                action_key="delayed_sales_orders",
            ),
            self._overview_kpi(
                "overview_open_crm_opportunities",
                _("Open CRM Opportunities"),
                Lead.search_count(crm_domains["pipeline_opportunities"]),
                action_key="total_opportunities",
            ),
            self._overview_kpi(
                "overview_inventory_shortages",
                _("Inventory Shortage Alerts"),
                low_stock_count,
                action_key="low_stock_products",
            ),
            self._overview_kpi(
                "overview_pending_receipts",
                _("Pending Receipts"),
                Picking.search_count(self._stock_picking_domain(filters, "incoming")),
                action_key="pending_receipts",
            ),
            self._overview_kpi(
                "overview_delayed_purchase_orders",
                _("Delayed Purchase Orders"),
                PurchaseOrder.search_count(purchase_domains["delayed_purchase_orders"]),
                action_key="delayed_purchase_orders",
            ),
            self._overview_kpi(
                "overview_manufacturing_delays",
                _("Manufacturing Delays"),
                Production.search_count(manufacturing_domains["delayed"]),
                action_key="manufacturing_delayed",
            ),
            self._overview_kpi(
                "overview_maintenance_delays",
                _("Maintenance Delays"),
                MaintenanceRequest.search_count(maintenance_domains["delayed"]),
                action_key="maintenance_delayed",
            ),
            self._overview_kpi(
                "overview_critical_alerts",
                _("Open Critical Alerts"),
                self._critical_alert_count(filters),
            ),
        ]

    def _get_department_cards(self, filters):
        SaleOrder = self.env["sale.order"]
        Lead = self.env["crm.lead"].with_context(active_test=False)
        Product = self.env["product.product"].with_context(**self._stock_context(filters))
        Picking = self.env["stock.picking"]
        PurchaseOrder = self.env["purchase.order"]
        Production = self.env["mrp.production"]
        MaintenanceRequest = self.env["maintenance.request"]

        sale_domains = self._sales_domains(filters)
        crm_domains = self._crm_domains(filters)
        purchase_domains = self._purchase_domains(filters)
        manufacturing_domains = self._manufacturing_domains(filters)
        maintenance_domains = self._maintenance_domains(filters)
        product_domain = self._stockable_product_domain(filters)

        sales_total = SaleOrder.search_count(sale_domains["total_sales_orders"])
        sales_delayed = SaleOrder.search_count(sale_domains["delayed_sales_orders"])
        open_opportunities = Lead.search_count(crm_domains["pipeline_opportunities"])
        low_stock = len(self._below_reordering_product_ids(filters)) or Product.search_count(product_domain + [("virtual_available", "<=", 0)])
        pending_receipts = Picking.search_count(self._stock_picking_domain(filters, "incoming"))
        delayed_purchase = PurchaseOrder.search_count(purchase_domains["delayed_purchase_orders"])
        delayed_mos = Production.search_count(manufacturing_domains["delayed"])
        mo_shortages = Production.search_count(manufacturing_domains["missing_materials"])
        delayed_maintenance = MaintenanceRequest.search_count(maintenance_domains["delayed"])
        open_equipment = len(self._equipment_with_open_maintenance_ids(filters))
        critical_alerts = self._critical_alert_count(filters)
        hr_total = (
            self.env["hr.employee"].with_context(active_test=False).search_count(
                self._hr_employee_domain(filters)
            )
            if self._can_read_model("hr.employee")
            else 0
        )
        hr_pending_leaves = (
            self.env["hr.leave"].search_count(self._hr_leave_domains(filters)["pending"])
            if self._can_read_model("hr.leave")
            else 0
        )
        helpdesk_open = (
            self.env["helpdesk.ticket"].search_count(self._helpdesk_domains(filters)["open"])
            if self._can_read_model("helpdesk.ticket")
            else 0
        )
        helpdesk_delayed = (
            self.env["helpdesk.ticket"].search_count(self._helpdesk_domains(filters)["delayed"])
            if self._can_read_model("helpdesk.ticket")
            else 0
        )
        pos_orders = (
            self.env["pos.order"].search_count(self._pos_order_domain(filters))
            if self._can_read_model("pos.order")
            else 0
        )
        pos_open_sessions = (
            self.env["pos.session"].search_count(self._pos_session_domains(filters)["open"])
            if self._can_read_model("pos.session")
            else 0
        )
        website_orders = (
            self.env["sale.order"].search_count(self._website_order_domains(filters)["total"])
            if self._has_field("sale.order", "website_id")
            else 0
        )
        website_pending = (
            self.env["sale.order"].search_count(self._website_order_domains(filters)["draft"])
            if self._has_field("sale.order", "website_id")
            else 0
        )

        return [
            self._department_card(
                "sales",
                _("Sales"),
                _("Total Sales Orders"),
                sales_total,
                sales_delayed,
                _("Delayed Orders: %s", sales_delayed),
                "executive_dashboard.sales_action",
            ),
            self._department_card(
                "crm",
                _("CRM"),
                _("Open Opportunities"),
                open_opportunities,
                0,
                _("Active pipeline opportunities"),
                "executive_dashboard.crm_action",
            ),
            self._department_card(
                "inventory",
                _("Inventory"),
                _("Low Stock Products"),
                low_stock,
                low_stock,
                _("Pending Receipts: %s", pending_receipts),
                "executive_dashboard.inventory_action",
            ),
            self._department_card(
                "purchase",
                _("Purchase"),
                _("Delayed Purchase Orders"),
                delayed_purchase,
                delayed_purchase,
                _("Pending Receipts: %s", pending_receipts),
                "executive_dashboard.purchase_action",
            ),
            self._department_card(
                "manufacturing",
                _("Manufacturing"),
                _("Delayed MOs"),
                delayed_mos,
                delayed_mos + mo_shortages,
                _("MO Shortages: %s", mo_shortages),
                "executive_dashboard.manufacturing_action",
            ),
            self._department_card(
                "maintenance",
                _("Maintenance"),
                _("Delayed Requests"),
                delayed_maintenance,
                delayed_maintenance,
                _("Equipment With Open Maintenance: %s", open_equipment),
                "executive_dashboard.maintenance_action",
            ),
            self._department_card(
                "hr",
                _("HR"),
                _("Total Employees"),
                hr_total,
                hr_pending_leaves,
                _("Pending Leave Requests: %s", hr_pending_leaves),
                "executive_dashboard.hr_action",
            ),
            self._department_card(
                "helpdesk",
                _("Helpdesk"),
                _("Open Tickets"),
                helpdesk_open,
                helpdesk_delayed,
                _("Delayed Tickets: %s", helpdesk_delayed),
                "executive_dashboard.helpdesk_action",
            ),
            self._department_card(
                "pos",
                _("POS"),
                _("POS Orders"),
                pos_orders,
                pos_open_sessions,
                _("Open Sessions: %s", pos_open_sessions),
                "executive_dashboard.pos_action",
            ),
            self._department_card(
                "website",
                _("Website"),
                _("Website Orders"),
                website_orders,
                website_pending,
                _("Draft Carts: %s", website_pending),
                "executive_dashboard.website_action",
            ),
            self._department_card(
                "alerts",
                _("Alerts Center"),
                _("Critical Alerts"),
                critical_alerts,
                critical_alerts,
                _("Centralized operational alerts"),
                "executive_dashboard.alerts_action",
            ),
        ]

    def _department_card(self, key, name, main_label, main_value, alert_count, status_text, action_xmlid):
        return {
            "key": key,
            "name": name,
            "main_label": main_label,
            "main_value": main_value or 0,
            "alert_count": alert_count or 0,
            "status_text": status_text,
            "action_xmlid": action_xmlid,
        }

    def _get_manufacturing_kpis(self, filters):
        Production = self.env["mrp.production"]
        Workorder = self.env["mrp.workorder"]
        domains = self._manufacturing_domains(filters)
        quantity_summary = self._manufacturing_quantity_summary(filters)

        return [
            self._kpi(
                "total_manufacturing_orders",
                _("Total Manufacturing Orders"),
                Production.search_count(domains["total"]),
            ),
            self._kpi(
                "manufacturing_in_progress",
                _("In Progress Manufacturing Orders"),
                Production.search_count(domains["in_progress"]),
            ),
            self._kpi(
                "manufacturing_planned",
                _("Planned Manufacturing Orders"),
                Production.search_count(domains["planned"]),
            ),
            self._kpi(
                "manufacturing_done",
                _("Done Manufacturing Orders"),
                Production.search_count(domains["done"]),
            ),
            self._kpi(
                "manufacturing_cancelled",
                _("Cancelled Manufacturing Orders"),
                Production.search_count(domains["cancelled"]),
            ),
            self._kpi(
                "manufacturing_delayed",
                _("Delayed Manufacturing Orders"),
                Production.search_count(domains["delayed"]),
            ),
            self._kpi(
                "manufacturing_missing_materials",
                _("Manufacturing Orders Blocked Due to Missing Materials"),
                Production.search_count(domains["missing_materials"]),
            ),
            self._kpi(
                "manufacturing_avg_progress",
                _("Average Manufacturing Progress"),
                quantity_summary["average_progress"],
                value_format="percentage",
            ),
            self._kpi(
                "manufacturing_qty_to_produce",
                _("Total Quantity To Produce"),
                quantity_summary["qty_to_produce"],
                value_format="float",
            ),
            self._kpi(
                "manufacturing_qty_produced",
                _("Total Quantity Produced"),
                quantity_summary["qty_produced"],
                value_format="float",
            ),
            self._kpi(
                "manufacturing_qty_remaining",
                _("Total Remaining Quantity"),
                quantity_summary["qty_remaining"],
                value_format="float",
            ),
            self._kpi(
                "manufacturing_delivery_commitment",
                _("Delivery Commitment"),
                self._manufacturing_delivery_commitment(filters),
                value_format="percentage",
            ),
            self._kpi(
                "work_orders_in_progress",
                _("Work Orders In Progress"),
                Workorder.search_count(self._workorder_domains(filters)["in_progress"]),
            ),
            self._kpi(
                "work_orders_delayed",
                _("Delayed Work Orders"),
                Workorder.search_count(self._workorder_domains(filters)["delayed"]),
            ),
        ]

    def _get_workcenter_kpis(self, filters):
        Workcenter = self.env["mrp.workcenter"]
        Workorder = self.env["mrp.workorder"]
        workcenter_domain = self._workcenter_domain(filters)
        workorder_domains = self._workorder_domains(filters)
        efficiency = self._workorder_efficiency(workorder_domains["done"])

        return [
            self._kpi(
                "workcenters_total",
                _("Total Work Centers"),
                Workcenter.search_count(workcenter_domain),
            ),
            self._kpi(
                "workcenters_active",
                _("Active Work Centers"),
                Workcenter.search_count(workcenter_domain + [("active", "=", True)]),
            ),
            self._kpi(
                "workcenter_work_orders_in_progress",
                _("Work Orders In Progress"),
                Workorder.search_count(workorder_domains["in_progress"]),
            ),
            self._kpi(
                "workcenter_done_work_orders",
                _("Done Work Orders"),
                Workorder.search_count(workorder_domains["done"]),
            ),
            self._kpi(
                "workcenter_delayed_work_orders",
                _("Delayed Work Orders"),
                Workorder.search_count(workorder_domains["delayed"]),
            ),
            self._kpi(
                "workcenter_avg_efficiency",
                _("Average Work Center Efficiency"),
                efficiency,
                value_format="percentage",
            ),
        ]

    def _get_maintenance_kpis(self, filters):
        Request = self.env["maintenance.request"]
        Equipment = self.env["maintenance.equipment"]
        domains = self._maintenance_domains(filters)

        return [
            self._kpi(
                "total_maintenance_requests",
                _("Total Maintenance Requests"),
                Request.search_count(domains["total"]),
            ),
            self._kpi(
                "maintenance_scheduled",
                _("Scheduled Maintenance Requests"),
                Request.search_count(domains["scheduled"]),
            ),
            self._kpi(
                "maintenance_delayed",
                _("Delayed Maintenance Requests"),
                Request.search_count(domains["delayed"]),
            ),
            self._kpi(
                "maintenance_in_progress",
                _("In Progress Maintenance Requests"),
                Request.search_count(domains["in_progress"]),
            ),
            self._kpi(
                "maintenance_done",
                _("Done Maintenance Requests"),
                Request.search_count(domains["done"]),
            ),
            self._kpi(
                "maintenance_breakdowns",
                _("Current Breakdown Requests"),
                Request.search_count(domains["breakdowns"]),
            ),
            self._kpi(
                "maintenance_total_equipment",
                _("Total Equipment"),
                Equipment.search_count(self._equipment_domain(filters)),
            ),
            self._kpi(
                "maintenance_equipment_open",
                _("Equipment With Open Maintenance"),
                len(self._equipment_with_open_maintenance_ids(filters)),
            ),
            self._kpi(
                "maintenance_mttr",
                _("Average Repair Time / MTTR (days)"),
                self._maintenance_mttr(filters),
                value_format="float",
            ),
            self._kpi(
                "maintenance_downtime_rate",
                _("Downtime Rate"),
                self._maintenance_downtime_rate(filters),
                value_format="percentage",
            ),
            self._kpi(
                "maintenance_preventive",
                _("Preventive Maintenance Requests"),
                Request.search_count(domains["preventive"]),
            ),
            self._kpi(
                "maintenance_corrective",
                _("Corrective Maintenance Requests"),
                Request.search_count(domains["corrective"]),
            ),
        ]

    # -------------------------------------------------------------------------
    # Tables
    # -------------------------------------------------------------------------

    def _get_delayed_sales(self, filters, limit=100):
        SaleOrder = self.env["sale.order"]
        domains = self._sales_domains(filters)
        today = fields.Date.context_today(self)
        rows = []

        orders = (
            SaleOrder.search(domains["delayed_quotations"], limit=limit, order="validity_date asc, date_order desc")
            | SaleOrder.search(domains["delayed_sales_orders"], limit=limit, order="commitment_date asc, date_order desc")
        )
        state_labels = self._selection_labels("sale.order", "state")

        for order in orders[: limit * 2]:
            is_quote = order.state in self._sale_quotation_states()
            expected_date = (
                order.validity_date
                if is_quote
                else self._datetime_to_user_date(order, order.commitment_date)
            )
            if not expected_date:
                continue
            rows.append(
                {
                    "id": order.id,
                    "name": order.name,
                    "type": _("Quotation") if is_quote else _("Sales Order"),
                    "partner": order.partner_id.display_name,
                    "salesperson": order.user_id.display_name or "",
                    "order_date": self._datetime_to_user_date_string(order, order.date_order),
                    "expected_date": fields.Date.to_string(expected_date),
                    "delay_days": max((today - expected_date).days, 0),
                    "amount_total": order.amount_total,
                    "state": order.state,
                    "state_label": state_labels.get(order.state, order.state),
                }
            )

        rows.sort(key=lambda row: (-row["delay_days"], row["expected_date"], row["name"]))
        return rows[:limit]

    def _get_pipeline_summary(self, filters):
        Lead = self.env["crm.lead"]
        domain = self._crm_base_domain(filters) + [("type", "=", "opportunity")]
        groups = Lead.read_group(
            domain,
            ["expected_revenue:sum"],
            ["stage_id", "team_id"],
            lazy=False,
        )

        rows = []
        for group in groups:
            stage = group.get("stage_id")
            team = group.get("team_id")
            stage_id = stage[0] if stage else False
            team_id = team[0] if team else False
            row_domain = domain + [("stage_id", "=", stage_id)]
            if team_id:
                row_domain.append(("team_id", "=", team_id))
            else:
                row_domain.append(("team_id", "=", False))
            rows.append(
                {
                    "stage_id": stage_id,
                    "stage": stage[1] if stage else _("No Stage"),
                    "team_id": team_id,
                    "team": team[1] if team else _("No Team"),
                    "count": group.get("__count", 0),
                    "expected_revenue": group.get("expected_revenue", 0) or 0,
                    "won_count": Lead.search_count(row_domain + [("won_status", "=", "won")]),
                }
            )
        rows.sort(key=lambda row: (row["stage"], row["team"]))
        return rows

    def _get_missing_materials(self, filters, limit=50):
        rows = []
        move_rows = self._missing_move_rows(filters, limit)
        rows.extend(move_rows)
        if len(rows) < limit:
            rows.extend(self._below_orderpoint_rows(filters, limit - len(rows)))
        rows.sort(key=lambda row: (-row["shortage_qty"], row["product"]))
        return rows[:limit]

    def _missing_move_rows(self, filters, limit):
        Move = self.env["stock.move"]
        moves = Move.search(
            self._missing_move_domain(filters),
            limit=limit * 4,
            order="date_deadline asc, date asc, id desc",
        )
        rows = []
        for move in moves:
            required_qty = move.product_qty or move.product_uom_qty
            available_qty = move.forecast_availability
            if available_qty is False:
                available_qty = move.availability
            if move.state == "assigned":
                available_qty = max(available_qty or 0, move.quantity or 0)
            shortage_qty = max(required_qty - max(available_qty or 0, 0), 0)
            if not shortage_qty:
                continue
            picking = move.picking_id
            activity_model = "stock.picking" if picking else "product.template"
            activity_id = picking.id if picking else move.product_id.product_tmpl_id.id
            responsible = picking.user_id or move.create_uid
            rows.append(
                {
                    "key": f"move-{move.id}",
                    "product_id": move.product_id.id,
                    "product": move.product_id.display_name,
                    "required_qty": required_qty,
                    "available_qty": max(available_qty or 0, 0),
                    "shortage_qty": shortage_qty,
                    "uom": move.product_id.uom_id.display_name,
                    "related_document": picking.name or move.reference or move.display_name,
                    "document_type": _("Delivery"),
                    "related_model": "stock.picking" if picking else "stock.move",
                    "related_id": picking.id or move.id,
                    "activity_model": activity_model,
                    "activity_id": activity_id,
                    "responsible_user_id": responsible.id if responsible else False,
                    "responsible_user": responsible.display_name if responsible else "",
                    "suggested_vendor": self._suggested_vendor_name(move.product_id, filters),
                }
            )
            if len(rows) >= limit:
                break
        return rows

    def _below_orderpoint_rows(self, filters, limit):
        Orderpoint = self.env["stock.warehouse.orderpoint"]
        orderpoints = Orderpoint.search(
            self._orderpoint_domain(filters) + [("qty_to_order", ">", 0)],
            limit=limit,
            order="deadline_date asc, id desc",
        )
        rows = []
        for orderpoint in orderpoints:
            shortage_qty = orderpoint.qty_to_order or max(orderpoint.product_min_qty - orderpoint.qty_forecast, 0)
            if not shortage_qty:
                continue
            rows.append(
                {
                    "key": f"orderpoint-{orderpoint.id}",
                    "product_id": orderpoint.product_id.id,
                    "product": orderpoint.product_id.display_name,
                    "required_qty": orderpoint.product_min_qty,
                    "available_qty": orderpoint.qty_forecast,
                    "shortage_qty": shortage_qty,
                    "uom": orderpoint.product_uom.display_name,
                    "related_document": orderpoint.name,
                    "document_type": _("Reordering Rule"),
                    "related_model": "stock.warehouse.orderpoint",
                    "related_id": orderpoint.id,
                    "activity_model": "product.template",
                    "activity_id": orderpoint.product_id.product_tmpl_id.id,
                    "responsible_user_id": self.env.user.id,
                    "responsible_user": self.env.user.display_name,
                    "suggested_vendor": self._suggested_vendor_name(orderpoint.product_id, filters),
                }
            )
        return rows

    def _get_pending_receipts(self, filters, limit=50):
        PurchaseOrder = self.env["purchase.order"]
        amount_field = self._purchase_amount_field()
        status_labels = self._selection_labels("purchase.order", "receipt_status") if self._has_field("purchase.order", "receipt_status") else {}
        today = fields.Date.context_today(self)
        orders = PurchaseOrder.search(
            self._purchase_domains(filters)["not_fully_received"],
            limit=limit,
            order="date_planned asc, date_order desc",
        )
        rows = []
        for order in orders:
            pending_pickings = (
                order.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
                if self._has_field("purchase.order", "picking_ids")
                else self.env["stock.picking"]
            )
            if filters["warehouse_id"]:
                pending_pickings = pending_pickings.filtered(
                    lambda p: p.picking_type_id.warehouse_id.id == filters["warehouse_id"]
                )
            receipt = pending_pickings[:1]
            expected_date = self._datetime_to_user_date(order, order.date_planned)
            receipt_status = order.receipt_status if self._has_field("purchase.order", "receipt_status") else False
            rows.append(
                {
                    "id": order.id,
                    "purchase_order": order.name,
                    "vendor": order.partner_id.display_name,
                    "expected_date": fields.Date.to_string(expected_date) if expected_date else "",
                    "delay_days": max((today - expected_date).days, 0) if expected_date else 0,
                    "total_amount": getattr(order, amount_field),
                    "receipt_status": status_labels.get(receipt_status, receipt_status or _("No Receipt")),
                    "buyer": order.user_id.display_name or "",
                    "picking_id": receipt.id if receipt else False,
                    "picking_name": receipt.name if receipt else "",
                }
            )
        return rows

    def _get_vendor_performance(self, filters, limit=20):
        PurchaseOrder = self.env["purchase.order"]
        amount_field = self._purchase_amount_field()
        domain = self._purchase_domains(filters)["total_purchase_orders"]
        groups = PurchaseOrder.read_group(
            domain,
            [f"{amount_field}:sum"],
            ["partner_id"],
            lazy=False,
        )
        rows = []
        for group in groups:
            partner = group.get("partner_id")
            if not partner:
                continue
            vendor_id = partner[0]
            vendor_filter = filters.copy()
            vendor_filter["vendor_id"] = vendor_id
            rows.append(
                {
                    "vendor_id": vendor_id,
                    "vendor": partner[1],
                    "purchase_orders_count": group.get("__count", 0),
                    "total_purchase_amount": group.get(amount_field, 0) or group.get(f"{amount_field}_sum", 0) or 0,
                    "on_time_delivery": self._vendor_on_time_delivery(filters, vendor_id),
                    "quantity_fulfillment": self._vendor_quantity_fulfillment(filters, vendor_id),
                    "average_delay_days": self._vendor_average_delay(filters, vendor_id),
                    "delayed_orders_count": PurchaseOrder.search_count(
                        self._purchase_domains(vendor_filter)["delayed_purchase_orders"]
                    ),
                    "open_vendor_orders": PurchaseOrder.search_count(
                        self._purchase_domains(vendor_filter)["open_purchase_orders"]
                    ),
                }
            )
        rows.sort(key=lambda row: row["total_purchase_amount"], reverse=True)
        return rows[:limit]

    def _get_manufacturing_orders(self, filters, limit=100):
        Production = self.env["mrp.production"]
        today = fields.Date.context_today(self)
        state_labels = self._selection_labels("mrp.production", "state")
        orders = Production.search(
            self._manufacturing_domains(filters)["total"],
            limit=limit,
            order="date_deadline asc, date_start desc, id desc",
        )
        rows = []
        for order in orders:
            progress = self._manufacturing_progress(order)
            deadline = self._datetime_to_user_date(order, order.date_deadline)
            delay_days = (
                max((today - deadline).days, 0)
                if deadline and order.state not in ("done", "cancel")
                else 0
            )
            rows.append(
                {
                    "id": order.id,
                    "name": order.name,
                    "product": order.product_id.display_name,
                    "qty_to_produce": order.product_qty,
                    "qty_produced": order.qty_produced,
                    "progress": progress,
                    "start_date": self._datetime_to_user_date_string(order, order.date_start),
                    "deadline": fields.Date.to_string(deadline) if deadline else "",
                    "delay_days": delay_days,
                    "state": order.state,
                    "state_label": state_labels.get(order.state, order.state),
                    "responsible": order.user_id.display_name or "",
                }
            )
        return rows

    def _get_manufacturing_shortages(self, filters, limit=50):
        Move = self.env["stock.move"]
        moves = Move.search(
            self._manufacturing_shortage_domain(filters),
            limit=limit * 4,
            order="date_deadline asc, date asc, id desc",
        )
        rows = []
        for move in moves:
            production = move.raw_material_production_id
            required_qty = move.product_qty or move.product_uom_qty
            reserved_qty = move.quantity or 0
            available_qty = move.forecast_availability
            if available_qty is False:
                available_qty = move.availability
            if available_qty is False:
                available_qty = move.product_virtual_available or move.product_qty_available
            if move.state == "assigned":
                available_qty = max(available_qty or 0, reserved_qty)
            shortage_qty = max(required_qty - max(available_qty or 0, reserved_qty), 0)
            if not shortage_qty:
                continue
            responsible = production.user_id or self.env.user
            rows.append(
                {
                    "key": f"mrp-move-{move.id}",
                    "move_id": move.id,
                    "mo_id": production.id,
                    "manufacturing_order": production.name,
                    "product_id": move.product_id.id,
                    "raw_material": move.product_id.display_name,
                    "required_qty": required_qty,
                    "available_qty": max(available_qty or 0, 0),
                    "reserved_qty": reserved_qty,
                    "shortage_qty": shortage_qty,
                    "uom": move.product_id.uom_id.display_name,
                    "responsible_user_id": responsible.id if responsible else False,
                    "responsible": responsible.display_name if responsible else "",
                    "suggested_vendor": self._suggested_vendor_name(move.product_id, filters),
                    "activity_model": "mrp.production",
                    "activity_id": production.id,
                }
            )
            if len(rows) >= limit:
                break
        rows.sort(key=lambda row: (-row["shortage_qty"], row["manufacturing_order"], row["raw_material"]))
        return rows[:limit]

    def _get_workcenter_performance(self, filters, limit=50):
        Workcenter = self.env["mrp.workcenter"]
        Workorder = self.env["mrp.workorder"]
        workcenters = Workcenter.search(
            self._workcenter_domain(filters),
            limit=limit,
            order="sequence, name, id",
        )
        if not workcenters:
            return []

        workorder_base = self._workorder_base_domain(filters) + [
            ("workcenter_id", "in", workcenters.ids),
        ]
        grouped = Workorder.read_group(
            workorder_base,
            ["duration_expected:sum", "duration:sum", "qty_produced:sum"],
            ["workcenter_id", "state"],
            lazy=False,
        )
        counts = defaultdict(lambda: defaultdict(int))
        expected = defaultdict(float)
        real = defaultdict(float)
        produced = defaultdict(float)
        for group in grouped:
            workcenter = group.get("workcenter_id")
            if not workcenter:
                continue
            workcenter_id = workcenter[0]
            state = group.get("state")
            count = group.get("__count", 0)
            counts[workcenter_id][state] += count
            expected[workcenter_id] += group.get("duration_expected", 0) or group.get("duration_expected_sum", 0) or 0
            real[workcenter_id] += group.get("duration", 0) or group.get("duration_sum", 0) or 0
            produced[workcenter_id] += group.get("qty_produced", 0) or group.get("qty_produced_sum", 0) or 0

        delayed_groups = Workorder.read_group(
            self._workorder_domains(filters)["delayed"] + [("workcenter_id", "in", workcenters.ids)],
            ["workcenter_id"],
            ["workcenter_id"],
            lazy=False,
        )
        delayed_counts = {
            group["workcenter_id"][0]: group.get("__count", 0)
            for group in delayed_groups
            if group.get("workcenter_id")
        }

        rows = []
        for workcenter in workcenters:
            real_duration = real[workcenter.id]
            efficiency = round((expected[workcenter.id] / real_duration) * 100, 1) if real_duration else 0
            rows.append(
                {
                    "workcenter_id": workcenter.id,
                    "workcenter": workcenter.display_name,
                    "active_work_orders": counts[workcenter.id].get("progress", 0),
                    "done_work_orders": counts[workcenter.id].get("done", 0),
                    "produced_qty": produced[workcenter.id],
                    "expected_duration": expected[workcenter.id],
                    "real_duration": real_duration,
                    "efficiency": efficiency,
                    "delayed_work_orders": delayed_counts.get(workcenter.id, 0),
                }
            )
        rows.sort(key=lambda row: (row["efficiency"] == 0, -row["efficiency"], row["workcenter"]))
        return rows

    def _get_maintenance_requests(self, filters, limit=100):
        Request = self.env["maintenance.request"]
        today = fields.Date.context_today(self)
        priority_labels = self._selection_labels("maintenance.request", "priority")
        requests = Request.search(
            self._maintenance_domains(filters)["total"],
            limit=limit,
            order="schedule_date asc, request_date desc, id desc",
        )
        rows = []
        for request in requests:
            scheduled_date = self._datetime_to_user_date(request, request.schedule_date)
            reference_date = scheduled_date or request.request_date
            delay_days = (
                max((today - reference_date).days, 0)
                if reference_date and not request.stage_id.done
                else 0
            )
            rows.append(
                {
                    "id": request.id,
                    "name": request.name,
                    "equipment": request.equipment_id.display_name or "",
                    "category": request.category_id.display_name or "",
                    "maintenance_team": request.maintenance_team_id.display_name or "",
                    "responsible": request.user_id.display_name or "",
                    "scheduled_date": fields.Date.to_string(scheduled_date) if scheduled_date else "",
                    "close_date": fields.Date.to_string(request.close_date) if request.close_date else "",
                    "delay_days": delay_days,
                    "stage": request.stage_id.display_name or "",
                    "stage_done": bool(request.stage_id.done),
                    "priority": priority_labels.get(request.priority, request.priority or ""),
                }
            )
        return rows

    def _get_equipment_status(self, filters, limit=100):
        Equipment = self.env["maintenance.equipment"]
        Request = self.env["maintenance.request"]
        equipment_records = Equipment.search(
            self._equipment_domain(filters),
            limit=limit,
            order="name, id",
        )
        if not equipment_records:
            return []

        open_groups = Request.read_group(
            self._maintenance_domains(filters)["in_progress"] + [
                ("equipment_id", "in", equipment_records.ids),
            ],
            ["equipment_id"],
            ["equipment_id"],
            lazy=False,
        )
        open_counts = {
            group["equipment_id"][0]: group.get("__count", 0)
            for group in open_groups
            if group.get("equipment_id")
        }

        rows = []
        for equipment in equipment_records:
            done_request = Request.search(
                self._maintenance_request_base_domain(filters, include_date=False)
                + [
                    ("equipment_id", "=", equipment.id),
                    ("stage_id.done", "=", True),
                    ("close_date", "!=", False),
                ],
                limit=1,
                order="close_date desc, id desc",
            )
            next_preventive = Request.search(
                self._maintenance_request_base_domain(filters, include_date=False)
                + [
                    ("equipment_id", "=", equipment.id),
                    ("maintenance_type", "=", "preventive"),
                    ("stage_id.done", "=", False),
                    ("archive", "=", False),
                    ("schedule_date", "!=", False),
                ],
                limit=1,
                order="schedule_date asc, id asc",
            )
            open_count = open_counts.get(equipment.id, 0)
            # Odoo 19 maintenance does not store explicit downtime hours on the
            # default equipment/request models, so the dashboard exposes 0 rather
            # than deriving downtime from scheduled maintenance windows.
            downtime_hours = 0
            rows.append(
                {
                    "equipment_id": equipment.id,
                    "equipment": equipment.display_name,
                    "technician": equipment.technician_user_id.display_name or "",
                    "maintenance_team": equipment.maintenance_team_id.display_name or "",
                    "current_open_requests": open_count,
                    "last_maintenance_date": fields.Date.to_string(done_request.close_date) if done_request else "",
                    "next_preventive_maintenance": self._datetime_to_user_date_string(next_preventive, next_preventive.schedule_date) if next_preventive else "",
                    "downtime_hours": downtime_hours,
                    "status": _("Open Maintenance") if open_count else _("Operational"),
                    "status_key": "open" if open_count else "operational",
                }
            )
        return rows

    # -------------------------------------------------------------------------
    # HR and Helpdesk
    # -------------------------------------------------------------------------

    def _get_hr_meta(self):
        return {
            "has_hr": self._can_read_model("hr.employee"),
            "has_attendance": self._can_read_model("hr.attendance"),
            "has_leaves": self._can_read_model("hr.leave"),
            "has_contracts": self._can_read_model("hr.contract"),
            "has_appraisals": self._can_read_model("hr.appraisal"),
        }

    def _get_helpdesk_meta(self):
        return {
            "has_helpdesk": self._can_read_model("helpdesk.ticket"),
            "has_sla": self._has_field("helpdesk.ticket", "sla_reached_late")
            or self._has_field("helpdesk.ticket", "sla_deadline"),
        }

    def _get_hr_kpis(self, filters):
        Employee = (
            self.env["hr.employee"].with_context(active_test=False)
            if self._can_read_model("hr.employee")
            else False
        )
        employee_domain = self._hr_employee_domain(filters) if Employee else [("id", "=", 0)]
        employee_total = Employee.search_count(employee_domain) if Employee else 0
        active_employees = (
            Employee.search_count(employee_domain + [("active", "=", True)])
            if Employee and self._has_field("hr.employee", "active")
            else employee_total
        )
        inactive_employees = (
            Employee.search_count(employee_domain + [("active", "=", False)])
            if Employee and self._has_field("hr.employee", "active")
            else 0
        )
        new_employees = (
            Employee.search_count(self._hr_employee_new_domain(filters)) if Employee else 0
        )

        attendance_available = self._can_read_model("hr.attendance")
        present_ids = self._hr_present_employee_ids_today(filters) if attendance_available else []
        late_ids = self._hr_late_employee_ids_today(filters) if attendance_available else []
        absent_today = max(active_employees - len(present_ids), 0) if attendance_available else 0
        attendance_rate = (
            round((len(present_ids) / active_employees) * 100, 1)
            if attendance_available and active_employees
            else 0
        )

        leave_domains = self._hr_leave_domains(filters) if self._can_read_model("hr.leave") else {}
        Leave = self.env["hr.leave"] if leave_domains else False
        contracts = self._hr_contract_domains(filters) if self._can_read_model("hr.contract") else {}
        Contract = self.env["hr.contract"] if contracts else False

        kpis = [
            self._kpi("hr_total_employees", _("Total Employees"), employee_total),
            self._kpi("hr_active_employees", _("Active Employees"), active_employees),
            self._kpi("hr_inactive_employees", _("Inactive Employees"), inactive_employees),
            self._kpi("hr_new_employees", _("New Employees During Selected Period"), new_employees),
            self._kpi("hr_present_today", _("Present Today"), len(present_ids)),
            self._kpi("hr_absent_today", _("Absent Today"), absent_today),
            self._kpi("hr_late_today", _("Late Employees Today"), len(late_ids)),
            self._kpi(
                "hr_total_leaves",
                _("Total Leave Requests"),
                Leave.search_count(leave_domains["total"]) if Leave else 0,
            ),
            self._kpi(
                "hr_approved_leaves",
                _("Approved Leaves"),
                Leave.search_count(leave_domains["approved"]) if Leave else 0,
            ),
            self._kpi(
                "hr_pending_leaves",
                _("Pending Leaves"),
                Leave.search_count(leave_domains["pending"]) if Leave else 0,
            ),
            self._kpi(
                "hr_refused_leaves",
                _("Refused Leaves"),
                Leave.search_count(leave_domains["refused"]) if Leave else 0,
            ),
            self._kpi(
                "hr_current_leave",
                _("Employees Currently on Leave"),
                len(self._hr_current_leave_employee_ids(filters)) if Leave else 0,
            ),
            self._kpi(
                "hr_contracts_expiring",
                _("Contracts Expiring Soon"),
                Contract.search_count(contracts["expiring"]) if Contract else 0,
            ),
            self._kpi(
                "hr_expired_contracts",
                _("Expired Contracts"),
                Contract.search_count(contracts["expired"]) if Contract else 0,
            ),
            self._kpi(
                "hr_average_attendance_rate",
                _("Average Attendance Rate"),
                attendance_rate,
                value_format="percentage",
            ),
        ]
        if self._can_read_model("hr.appraisal"):
            kpis.append(
                self._kpi(
                    "hr_open_appraisals",
                    _("Open Appraisals"),
                    self._hr_open_appraisal_count(filters),
                )
            )
        return kpis

    def _get_hr_employees_overview(self, filters, limit=50):
        if not self._can_read_model("hr.employee"):
            return []
        Employee = self.env["hr.employee"].with_context(active_test=False)
        employees = Employee.search(
            self._hr_employee_domain(filters),
            limit=limit,
            order="name, id",
        )
        if not employees:
            return []

        attendance_info = self._hr_today_attendance_info(filters, employee_ids=employees.ids)
        current_leave_ids = set(self._hr_current_leave_employee_ids(filters))
        open_leave_counts = defaultdict(int)
        if self._can_read_model("hr.leave"):
            groups = self.env["hr.leave"].read_group(
                self._hr_leave_base_domain(filters, include_date=False)
                + [
                    ("employee_id", "in", employees.ids),
                    ("state", "in", ("confirm", "validate1")),
                ],
                ["employee_id"],
                ["employee_id"],
                lazy=False,
            )
            open_leave_counts = {
                group["employee_id"][0]: group.get("__count", 0)
                for group in groups
                if group.get("employee_id")
            }

        rows = []
        for employee in employees:
            active = bool(getattr(employee, "active", True))
            if not active:
                status_key = "inactive"
                status = _("Inactive")
            elif employee.id in current_leave_ids:
                status_key = "leave"
                status = _("On Leave")
            elif employee.id in attendance_info["present_ids"]:
                status_key = "present"
                status = _("Present")
            else:
                status_key = "absent"
                status = _("Absent")
            rows.append(
                {
                    "id": employee.id,
                    "employee": employee.display_name,
                    "department": employee.department_id.display_name
                    if self._has_field("hr.employee", "department_id")
                    else "",
                    "job_position": employee.job_id.display_name
                    if self._has_field("hr.employee", "job_id")
                    else "",
                    "manager": employee.parent_id.display_name
                    if self._has_field("hr.employee", "parent_id")
                    else "",
                    "attendance_status": status,
                    "attendance_status_key": status_key,
                    "late_hours": attendance_info["late_hours"].get(employee.id, 0),
                    "open_leave_requests": open_leave_counts.get(employee.id, 0),
                }
            )
        return rows

    def _get_hr_leave_requests(self, filters, limit=50):
        if not self._can_read_model("hr.leave"):
            return []
        Leave = self.env["hr.leave"]
        state_labels = self._selection_labels("hr.leave", "state")
        leaves = Leave.search(
            self._hr_leave_domains(filters)["total"],
            limit=limit,
            order="date_from desc, id desc",
        )
        rows = []
        for leave in leaves:
            manager = leave.first_approver_id or leave.second_approver_id
            if not manager and leave.employee_id.parent_id:
                manager = leave.employee_id.parent_id
            rows.append(
                {
                    "id": leave.id,
                    "employee": leave.employee_id.display_name or "",
                    "leave_type": leave.holiday_status_id.display_name or "",
                    "date_from": self._datetime_to_user_date_string(leave, leave.date_from),
                    "date_to": self._datetime_to_user_date_string(leave, leave.date_to),
                    "duration": leave.duration_display
                    if self._has_field("hr.leave", "duration_display")
                    else leave.number_of_days,
                    "state": leave.state,
                    "state_label": state_labels.get(leave.state, leave.state or ""),
                    "responsible_manager": manager.display_name if manager else "",
                }
            )
        return rows

    def _get_hr_contracts_expiring(self, filters, limit=50):
        if not self._can_read_model("hr.contract"):
            return []
        Contract = self.env["hr.contract"]
        end_field = self._hr_contract_end_field()
        if not end_field:
            return []
        today = fields.Date.context_today(self)
        state_labels = self._selection_labels("hr.contract", "state")
        contracts = Contract.search(
            self._hr_contract_domains(filters)["expiring"],
            limit=limit,
            order=f"{end_field} asc, id desc",
        )
        rows = []
        for contract in contracts:
            employee = contract.employee_id if self._has_field("hr.contract", "employee_id") else False
            date_end = getattr(contract, end_field)
            date_start = (
                getattr(contract, self._hr_contract_start_field())
                if self._hr_contract_start_field()
                else False
            )
            department = (
                contract.department_id
                if self._has_field("hr.contract", "department_id")
                else employee.department_id
                if employee and self._has_field("hr.employee", "department_id")
                else False
            )
            state = contract.state if self._has_field("hr.contract", "state") else ""
            rows.append(
                {
                    "id": contract.id,
                    "employee": employee.display_name if employee else "",
                    "contract": contract.display_name,
                    "department": department.display_name if department else "",
                    "date_start": fields.Date.to_string(date_start) if date_start else "",
                    "date_end": fields.Date.to_string(date_end) if date_end else "",
                    "remaining_days": max((date_end - today).days, 0) if date_end else 0,
                    "state": state,
                    "state_label": state_labels.get(state, state or ""),
                }
            )
        return rows

    def _get_hr_charts(self, filters):
        return {
            "charts": [
                self._hr_employees_department_chart(filters),
                self._hr_attendance_status_chart(filters),
                self._hr_leaves_type_chart(filters),
                self._hr_monthly_new_employees_chart(filters),
                self._hr_leave_status_chart(filters),
                self._hr_employees_job_chart(filters),
            ]
        }

    def _get_helpdesk_kpis(self, filters):
        if not self._can_read_model("helpdesk.ticket"):
            return [
                self._kpi("helpdesk_total_tickets", _("Total Tickets"), 0),
                self._kpi("helpdesk_open_tickets", _("Open Tickets"), 0),
                self._kpi("helpdesk_closed_tickets", _("Closed Tickets"), 0),
                self._kpi("helpdesk_delayed_tickets", _("Delayed Tickets"), 0),
            ]
        Ticket = self.env["helpdesk.ticket"]
        domains = self._helpdesk_domains(filters)
        stage_count = len(
            Ticket.read_group(domains["total"], ["stage_id"], ["stage_id"], lazy=False)
        )
        team_count = len(
            Ticket.read_group(domains["total"], ["team_id"], ["team_id"], lazy=False)
        )
        user_count = len(
            Ticket.read_group(
                domains["total"] + [("user_id", "!=", False)],
                ["user_id"],
                ["user_id"],
                lazy=False,
            )
        )
        return [
            self._kpi("helpdesk_total_tickets", _("Total Tickets"), Ticket.search_count(domains["total"])),
            self._kpi("helpdesk_open_tickets", _("Open Tickets"), Ticket.search_count(domains["open"])),
            self._kpi("helpdesk_closed_tickets", _("Closed Tickets"), Ticket.search_count(domains["closed"])),
            self._kpi("helpdesk_delayed_tickets", _("Delayed Tickets"), Ticket.search_count(domains["delayed"])),
            self._kpi(
                "helpdesk_installation_tickets",
                _("Installation Tickets"),
                Ticket.search_count(self._helpdesk_ticket_keyword_domain(filters, ["installation", "install"])),
            ),
            self._kpi(
                "helpdesk_technical_tickets",
                _("Technical Support Tickets"),
                Ticket.search_count(self._helpdesk_ticket_keyword_domain(filters, ["technical", "support"])),
            ),
            self._kpi(
                "helpdesk_sales_support_tickets",
                _("Sales Support Tickets"),
                Ticket.search_count(self._helpdesk_ticket_keyword_domain(filters, ["sales"])),
            ),
            self._kpi("helpdesk_stage_count", _("Ticket Stages With Tickets"), stage_count),
            self._kpi("helpdesk_team_count", _("Teams With Tickets"), team_count),
            self._kpi("helpdesk_responsible_count", _("Responsible Users With Tickets"), user_count),
            self._kpi(
                "helpdesk_sla_breached",
                _("SLA Breached Tickets"),
                Ticket.search_count(self._helpdesk_sla_breached_domain(filters))
                if self._has_field("helpdesk.ticket", "sla_reached_late")
                else 0,
            ),
            self._kpi(
                "helpdesk_avg_resolution_time",
                _("Average Resolution Time"),
                self._avg(Ticket, domains["closed"], "close_hours")
                if self._has_field("helpdesk.ticket", "close_hours")
                else 0,
                value_format="float",
            ),
            self._kpi(
                "helpdesk_avg_first_response_time",
                _("Average First Response Time"),
                self._avg(Ticket, domains["total"], "assign_hours")
                if self._has_field("helpdesk.ticket", "assign_hours")
                else 0,
                value_format="float",
            ),
        ]

    def _get_helpdesk_tickets_overview(self, filters, limit=50):
        if not self._can_read_model("helpdesk.ticket"):
            return []
        return self._helpdesk_ticket_rows(
            self._helpdesk_domains(filters)["total"],
            limit=limit,
        )

    def _get_helpdesk_delayed_tickets(self, filters, limit=50):
        if not self._can_read_model("helpdesk.ticket"):
            return []
        return self._helpdesk_ticket_rows(
            self._helpdesk_domains(filters)["delayed"],
            limit=limit,
        )

    def _get_helpdesk_team_performance(self, filters, limit=50):
        if not self._can_read_model("helpdesk.team") or not self._can_read_model("helpdesk.ticket"):
            return []
        Team = self.env["helpdesk.team"]
        Ticket = self.env["helpdesk.ticket"]
        teams = Team.search(self._helpdesk_team_domain(filters), limit=limit, order="name, id")
        rows = []
        for team in teams:
            team_filters = filters.copy()
            team_filters["helpdesk_team_id"] = team.id
            domains = self._helpdesk_domains(team_filters)
            rows.append(
                {
                    "team_id": team.id,
                    "team": team.display_name,
                    "total_tickets": Ticket.search_count(domains["total"]),
                    "closed_tickets": Ticket.search_count(domains["closed"]),
                    "open_tickets": Ticket.search_count(domains["open"]),
                    "average_resolution_time": self._avg(Ticket, domains["closed"], "close_hours")
                    if self._has_field("helpdesk.ticket", "close_hours")
                    else 0,
                    "delayed_tickets": Ticket.search_count(domains["delayed"]),
                }
            )
        rows.sort(key=lambda row: (-row["total_tickets"], row["team"]))
        return rows

    def _helpdesk_ticket_rows(self, domain, limit=50):
        Ticket = self.env["helpdesk.ticket"]
        today = fields.Date.context_today(self)
        priority_labels = self._selection_labels("helpdesk.ticket", "priority")
        order = "priority desc, create_date desc, id desc"
        if self._has_field("helpdesk.ticket", "sla_deadline"):
            order = "sla_deadline asc, priority desc, create_date desc, id desc"
        tickets = Ticket.search(domain, limit=limit, order=order)
        rows = []
        for ticket in tickets:
            deadline = ticket.sla_deadline if self._has_field("helpdesk.ticket", "sla_deadline") else False
            deadline_date = self._datetime_to_user_date(ticket, deadline)
            delay_days = (
                max((today - deadline_date).days, 0)
                if deadline_date and not ticket.fold
                else 0
            )
            rows.append(
                {
                    "id": ticket.id,
                    "ticket": ticket.display_name,
                    "customer": ticket.partner_id.display_name
                    if ticket.partner_id
                    else getattr(ticket, "partner_name", "") or "",
                    "team": ticket.team_id.display_name or "",
                    "assigned_user": ticket.user_id.display_name or "",
                    "stage": ticket.stage_id.display_name or "",
                    "stage_fold": bool(ticket.fold),
                    "priority": priority_labels.get(ticket.priority, ticket.priority or ""),
                    "priority_key": ticket.priority or "0",
                    "create_date": self._datetime_to_user_date_string(ticket, ticket.create_date),
                    "deadline": fields.Date.to_string(deadline_date) if deadline_date else "",
                    "delay_days": delay_days,
                }
            )
        return rows

    def _get_helpdesk_charts(self, filters):
        return {
            "charts": [
                self._helpdesk_stage_chart(filters),
                self._helpdesk_team_chart(filters),
                self._helpdesk_user_chart(filters),
                self._helpdesk_monthly_ticket_chart(filters),
                self._helpdesk_delayed_team_chart(filters),
                self._helpdesk_priority_chart(filters),
            ]
        }

    def _hr_employees_department_chart(self, filters):
        data = []
        if self._can_read_model("hr.employee") and self._has_field("hr.employee", "department_id"):
            groups = self.env["hr.employee"].with_context(active_test=False).read_group(
                self._hr_employee_domain(filters),
                ["department_id"],
                ["department_id"],
                lazy=False,
            )
            for group in groups:
                department = group.get("department_id")
                data.append(
                    {
                        "label": department[1] if department else _("No Department"),
                        "value": group.get("__count", 0),
                        "extra": {"department_id": department[0] if department else False},
                    }
                )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "hr_employees_by_department",
            "action_key": "chart_hr_department",
            "title": _("Employees by Department"),
            "kind": "bar",
            "horizontal": True,
            "metric": "integer",
            "data": data[:10],
        }

    def _hr_attendance_status_chart(self, filters):
        active_employees = 0
        if self._can_read_model("hr.employee"):
            active_employees = self.env["hr.employee"].search_count(
                self._hr_employee_domain(filters) + [("active", "=", True)]
            )
        present_ids = self._hr_present_employee_ids_today(filters) if self._can_read_model("hr.attendance") else []
        late_ids = self._hr_late_employee_ids_today(filters) if self._can_read_model("hr.attendance") else []
        absent_count = max(active_employees - len(present_ids), 0) if self._can_read_model("hr.attendance") else 0
        return {
            "key": "hr_attendance_status",
            "action_key": "chart_hr_attendance_status",
            "title": _("Attendance Status Overview"),
            "kind": "doughnut",
            "metric": "integer",
            "data": [
                {"label": _("Present"), "value": len(present_ids), "extra": {"segment": "present"}},
                {"label": _("Absent"), "value": absent_count, "extra": {"segment": "absent"}},
                {"label": _("Late"), "value": len(late_ids), "extra": {"segment": "late"}},
            ],
        }

    def _hr_leaves_type_chart(self, filters):
        data = []
        if self._can_read_model("hr.leave"):
            groups = self.env["hr.leave"].read_group(
                self._hr_leave_domains(filters)["total"],
                ["holiday_status_id"],
                ["holiday_status_id"],
                lazy=False,
            )
            for group in groups:
                leave_type = group.get("holiday_status_id")
                data.append(
                    {
                        "label": leave_type[1] if leave_type else _("No Type"),
                        "value": group.get("__count", 0),
                        "extra": {"leave_type_id": leave_type[0] if leave_type else False},
                    }
                )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "hr_leaves_by_type",
            "action_key": "chart_hr_leave_type",
            "title": _("Leaves by Type"),
            "kind": "bar",
            "horizontal": True,
            "metric": "integer",
            "data": data[:10],
        }

    def _hr_monthly_new_employees_chart(self, filters):
        data = []
        if self._can_read_model("hr.employee"):
            Employee = self.env["hr.employee"].with_context(active_test=False)
            for period in self._month_periods(filters):
                period_domain = self._hr_employee_domain(filters, include_date=False)
                period_domain += self._datetime_range_domain("create_date", period["date_from"], period["date_to"])
                data.append(
                    {
                        "label": period["label"],
                        "value": Employee.search_count(period_domain),
                        "extra": period["extra"],
                    }
                )
        return {
            "key": "hr_monthly_new_employees",
            "action_key": "chart_hr_monthly_new_employees",
            "title": _("Monthly New Employees"),
            "kind": "line",
            "metric": "integer",
            "data": data,
        }

    def _hr_leave_status_chart(self, filters):
        data = []
        state_labels = self._selection_labels("hr.leave", "state")
        if self._can_read_model("hr.leave"):
            groups = self.env["hr.leave"].read_group(
                self._hr_leave_domains(filters)["total"],
                ["state"],
                ["state"],
                lazy=False,
            )
            for group in groups:
                state = group.get("state")
                data.append(
                    {
                        "label": state_labels.get(state, state or _("No Status")),
                        "value": group.get("__count", 0),
                        "extra": {"state": state or False},
                    }
                )
        return {
            "key": "hr_leave_requests_by_status",
            "action_key": "chart_hr_leave_status",
            "title": _("Leave Requests by Status"),
            "kind": "doughnut",
            "metric": "integer",
            "data": data,
        }

    def _hr_employees_job_chart(self, filters):
        data = []
        if self._can_read_model("hr.employee") and self._has_field("hr.employee", "job_id"):
            groups = self.env["hr.employee"].with_context(active_test=False).read_group(
                self._hr_employee_domain(filters),
                ["job_id"],
                ["job_id"],
                lazy=False,
            )
            for group in groups:
                job = group.get("job_id")
                data.append(
                    {
                        "label": job[1] if job else _("No Job Position"),
                        "value": group.get("__count", 0),
                        "extra": {"job_id": job[0] if job else False},
                    }
                )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "hr_employees_by_job",
            "action_key": "chart_hr_job",
            "title": _("Employees by Job Position"),
            "kind": "bar",
            "horizontal": True,
            "metric": "integer",
            "data": data[:10],
        }

    def _helpdesk_stage_chart(self, filters):
        data = []
        if self._can_read_model("helpdesk.ticket"):
            groups = self.env["helpdesk.ticket"].read_group(
                self._helpdesk_domains(filters)["total"],
                ["stage_id"],
                ["stage_id"],
                lazy=False,
            )
            for group in groups:
                stage = group.get("stage_id")
                data.append(
                    {
                        "label": stage[1] if stage else _("No Stage"),
                        "value": group.get("__count", 0),
                        "extra": {"stage_id": stage[0] if stage else False},
                    }
                )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "helpdesk_tickets_by_stage",
            "action_key": "chart_helpdesk_stage",
            "title": _("Tickets by Stage"),
            "kind": "doughnut",
            "metric": "integer",
            "data": data,
        }

    def _helpdesk_team_chart(self, filters):
        data = []
        if self._can_read_model("helpdesk.ticket"):
            groups = self.env["helpdesk.ticket"].read_group(
                self._helpdesk_domains(filters)["total"],
                ["team_id"],
                ["team_id"],
                lazy=False,
            )
            for group in groups:
                team = group.get("team_id")
                data.append(
                    {
                        "label": team[1] if team else _("No Team"),
                        "value": group.get("__count", 0),
                        "extra": {"team_id": team[0] if team else False},
                    }
                )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "helpdesk_tickets_by_team",
            "action_key": "chart_helpdesk_team",
            "title": _("Tickets by Team"),
            "kind": "bar",
            "horizontal": True,
            "metric": "integer",
            "data": data[:10],
        }

    def _helpdesk_user_chart(self, filters):
        data = []
        if self._can_read_model("helpdesk.ticket"):
            groups = self.env["helpdesk.ticket"].read_group(
                self._helpdesk_domains(filters)["total"],
                ["user_id"],
                ["user_id"],
                lazy=False,
            )
            for group in groups:
                user = group.get("user_id")
                data.append(
                    {
                        "label": user[1] if user else _("Unassigned"),
                        "value": group.get("__count", 0),
                        "extra": {"user_id": user[0] if user else False},
                    }
                )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "helpdesk_tickets_by_user",
            "action_key": "chart_helpdesk_user",
            "title": _("Tickets by Assigned User"),
            "kind": "bar",
            "horizontal": True,
            "metric": "integer",
            "data": data[:10],
        }

    def _helpdesk_monthly_ticket_chart(self, filters):
        data = []
        if self._can_read_model("helpdesk.ticket"):
            Ticket = self.env["helpdesk.ticket"]
            for period in self._month_periods(filters):
                domain = (
                    self._helpdesk_ticket_base_domain(filters, include_date=False)
                    + self._datetime_range_domain("create_date", period["date_from"], period["date_to"])
                )
                data.append(
                    {
                        "label": period["label"],
                        "value": Ticket.search_count(domain),
                        "extra": period["extra"],
                    }
                )
        return {
            "key": "helpdesk_monthly_tickets",
            "action_key": "chart_helpdesk_monthly_tickets",
            "title": _("Monthly Tickets Trend"),
            "kind": "line",
            "metric": "integer",
            "data": data,
        }

    def _helpdesk_delayed_team_chart(self, filters):
        data = []
        if self._can_read_model("helpdesk.ticket"):
            groups = self.env["helpdesk.ticket"].read_group(
                self._helpdesk_domains(filters)["delayed"],
                ["team_id"],
                ["team_id"],
                lazy=False,
            )
            for group in groups:
                team = group.get("team_id")
                data.append(
                    {
                        "label": team[1] if team else _("No Team"),
                        "value": group.get("__count", 0),
                        "extra": {"team_id": team[0] if team else False},
                    }
                )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "helpdesk_delayed_tickets_by_team",
            "action_key": "chart_helpdesk_delayed_team",
            "title": _("Delayed Tickets by Team"),
            "kind": "bar",
            "horizontal": True,
            "metric": "integer",
            "data": data[:10],
        }

    def _helpdesk_priority_chart(self, filters):
        data = []
        priority_labels = self._selection_labels("helpdesk.ticket", "priority")
        if self._can_read_model("helpdesk.ticket"):
            groups = self.env["helpdesk.ticket"].read_group(
                self._helpdesk_domains(filters)["total"],
                ["priority"],
                ["priority"],
                lazy=False,
            )
            for group in groups:
                priority = group.get("priority")
                data.append(
                    {
                        "label": priority_labels.get(priority, priority or _("No Priority")),
                        "value": group.get("__count", 0),
                        "extra": {"priority": priority or False},
                    }
                )
        return {
            "key": "helpdesk_ticket_priority_distribution",
            "action_key": "chart_helpdesk_priority",
            "title": _("Ticket Priority Distribution"),
            "kind": "doughnut",
            "metric": "integer",
            "data": data,
        }

    def _get_pos_meta(self):
        return {
            "has_pos": self._can_read_model("pos.order"),
            "has_pos_payments": self._can_read_model("pos.payment"),
            "has_pos_invoices": self._has_field("pos.order", "account_move"),
        }

    def _get_website_meta(self):
        return {
            "has_website_sale": self._has_field("sale.order", "website_id"),
            "has_abandoned_cart": self._has_field("sale.order", "is_abandoned_cart"),
            "has_visitors": self._can_read_model("website.visitor"),
        }

    def _get_pos_kpis(self, filters):
        if not self._can_read_model("pos.order"):
            return [
                self._kpi("pos_total_orders", _("Total POS Orders"), 0),
                self._kpi("pos_total_revenue", _("Total POS Revenue"), 0, value_format="monetary"),
            ]
        Order = self.env["pos.order"]
        Payment = self.env["pos.payment"] if self._can_read_model("pos.payment") else False
        order_domain = self._pos_order_domain(filters)
        payment_domain = self._pos_payment_domain(filters)
        order_count = Order.search_count(order_domain)
        revenue = self._sum(Order, order_domain, "amount_total")
        best_pos = self._pos_best_group(filters, "config_id")
        best_cashier = self._pos_best_group(filters, "user_id")
        top_product = self._pos_top_product(filters)
        refund_domain = self._pos_refund_order_domain(filters)
        cash_domain = payment_domain + [("payment_method_id.is_cash_count", "=", True)]
        card_domain = payment_domain + [("payment_method_id.journal_id.type", "=", "bank")]
        return [
            self._kpi("pos_total_orders", _("Total POS Orders"), order_count),
            self._kpi("pos_total_revenue", _("Total POS Revenue"), revenue, value_format="monetary"),
            self._kpi(
                "pos_average_order_value",
                _("Average Order Value"),
                revenue / order_count if order_count else 0,
                value_format="monetary",
            ),
            self._kpi(
                "pos_total_invoices",
                _("Total POS Invoices"),
                Order.search_count(order_domain + [("account_move", "!=", False)])
                if self._has_field("pos.order", "account_move")
                else 0,
            ),
            self._kpi("pos_open_sessions", _("Open Sessions"), self.env["pos.session"].search_count(self._pos_session_domains(filters)["open"]) if self._can_read_model("pos.session") else 0),
            self._kpi("pos_closed_sessions", _("Closed Sessions"), self.env["pos.session"].search_count(self._pos_session_domains(filters)["closed"]) if self._can_read_model("pos.session") else 0),
            self._kpi("pos_active_sessions_today", _("Active Sessions Today"), self.env["pos.session"].search_count(self._pos_session_domains(filters)["active_today"]) if self._can_read_model("pos.session") else 0),
            self._kpi("pos_best_branch", _("Best Performing POS / Branch"), best_pos["value"], value_format="monetary", display_value=best_pos["name"] or _("None")),
            self._kpi("pos_best_cashier", _("Best Cashier"), best_cashier["value"], value_format="monetary", display_value=best_cashier["name"] or _("None")),
            self._kpi("pos_top_product", _("Top Selling POS Product"), top_product["quantity"], value_format="float", display_value=top_product["name"] or _("None")),
            self._kpi("pos_refund_amount", _("Total Refund Amount"), abs(self._sum(Order, refund_domain, "amount_total")), value_format="monetary"),
            self._kpi("pos_refund_orders", _("Refund Orders Count"), Order.search_count(refund_domain)),
            self._kpi("pos_cash_payments", _("Cash Payments"), self._sum(Payment, cash_domain, "amount") if Payment else 0, value_format="monetary"),
            self._kpi("pos_card_payments", _("Card Payments"), self._sum(Payment, card_domain, "amount") if Payment else 0, value_format="monetary"),
            self._kpi("pos_other_payments", _("Other Payment Methods"), self._pos_other_payment_amount(filters) if Payment else 0, value_format="monetary"),
        ]

    def _get_pos_sessions_table(self, filters, limit=50):
        if not self._can_read_model("pos.session"):
            return []
        Session = self.env["pos.session"]
        Order = self.env["pos.order"] if self._can_read_model("pos.order") else False
        state_labels = self._selection_labels("pos.session", "state")
        sessions = Session.search(self._pos_session_domain(filters), limit=limit, order="start_at desc, id desc")
        order_summary = defaultdict(lambda: {"count": 0, "amount": 0})
        if sessions and Order:
            groups = Order.read_group(
                self._pos_order_domain(filters, include_date=False) + [("session_id", "in", sessions.ids)],
                ["amount_total:sum"],
                ["session_id"],
                lazy=False,
            )
            for group in groups:
                session = group.get("session_id")
                if session:
                    order_summary[session[0]] = {
                        "count": group.get("__count", 0),
                        "amount": group.get("amount_total", 0) or group.get("amount_total_sum", 0) or 0,
                    }
        rows = []
        for session in sessions:
            summary = order_summary[session.id]
            rows.append(
                {
                    "id": session.id,
                    "session": session.display_name,
                    "pos": session.config_id.display_name or "",
                    "cashier": session.user_id.display_name or "",
                    "opening_date": self._datetime_to_user_date_string(session, session.start_at),
                    "closing_date": self._datetime_to_user_date_string(session, session.stop_at),
                    "orders_count": summary["count"],
                    "total_sales": summary["amount"],
                    "state": session.state,
                    "state_label": state_labels.get(session.state, session.state or ""),
                }
            )
        return rows

    def _get_pos_orders_table(self, filters, limit=50):
        if not self._can_read_model("pos.order"):
            return []
        Order = self.env["pos.order"]
        state_labels = self._selection_labels("pos.order", "state")
        orders = Order.search(self._pos_order_domain(filters), limit=limit, order="date_order desc, id desc")
        rows = []
        for order in orders:
            rows.append(
                {
                    "id": order.id,
                    "order": order.display_name,
                    "pos": order.config_id.display_name or "",
                    "customer": order.partner_id.display_name or "",
                    "cashier": order.user_id.display_name or "",
                    "order_date": self._datetime_to_user_date_string(order, order.date_order),
                    "amount": order.amount_total,
                    "payment_method": ", ".join(order.payment_ids.mapped("payment_method_id.name")) if self._has_field("pos.order", "payment_ids") else "",
                    "state": order.state,
                    "state_label": state_labels.get(order.state, order.state or ""),
                }
            )
        return rows

    def _get_pos_products_table(self, filters, limit=50):
        if not self._can_read_model("pos.order.line"):
            return []
        Line = self.env["pos.order.line"]
        groups = Line.read_group(
            self._pos_line_domain(filters),
            ["qty:sum", "price_subtotal_incl:sum"],
            ["product_id"],
            lazy=False,
        )
        refund_groups = Line.read_group(
            self._pos_line_domain(filters) + [("qty", "<", 0)],
            ["qty:sum"],
            ["product_id"],
            lazy=False,
        )
        refund_qty = {
            group["product_id"][0]: abs(group.get("qty", 0) or group.get("qty_sum", 0) or 0)
            for group in refund_groups
            if group.get("product_id")
        }
        rows = []
        for group in groups:
            product = group.get("product_id")
            if not product:
                continue
            rows.append(
                {
                    "product_id": product[0],
                    "product": product[1],
                    "sold_quantity": group.get("qty", 0) or group.get("qty_sum", 0) or 0,
                    "revenue": group.get("price_subtotal_incl", 0) or group.get("price_subtotal_incl_sum", 0) or 0,
                    "refund_quantity": refund_qty.get(product[0], 0),
                    "orders_count": self._pos_line_distinct_order_count(filters, product[0]),
                }
            )
        rows.sort(key=lambda row: row["revenue"], reverse=True)
        return rows[:limit]

    def _get_pos_charts(self, filters):
        return {
            "charts": [
                self._pos_revenue_trend_chart(filters),
                self._pos_sales_branch_chart(filters),
                self._pos_sales_cashier_chart(filters),
                self._pos_sales_payment_method_chart(filters),
                self._pos_top_products_chart(filters),
                self._pos_refund_trend_chart(filters),
            ]
        }

    def _get_website_kpis(self, filters):
        if not self._has_field("sale.order", "website_id"):
            return [
                self._kpi("website_orders_count", _("Website Orders Count"), 0),
                self._kpi("website_revenue", _("Website Revenue"), 0, value_format="monetary"),
            ]
        SaleOrder = self.env["sale.order"]
        domains = self._website_order_domains(filters)
        total_count = SaleOrder.search_count(domains["total"])
        confirmed_count = SaleOrder.search_count(domains["confirmed"])
        revenue = self._sum(SaleOrder, domains["confirmed"], "amount_total")
        top_product = self._website_top_product(filters, metric="revenue")
        most_ordered = self._website_top_product(filters, metric="quantity")
        customers = self._website_customer_ids(filters)
        new_customers = self._website_customer_ids(filters, selected_period=True)
        conversion_base = total_count or confirmed_count
        return [
            self._kpi("website_orders_count", _("Website Orders Count"), total_count),
            self._kpi("website_revenue", _("Website Revenue"), revenue, value_format="monetary"),
            self._kpi("website_average_order_value", _("Average Website Order Value"), revenue / confirmed_count if confirmed_count else 0, value_format="monetary"),
            self._kpi("website_confirmed_orders", _("Confirmed Website Orders"), confirmed_count),
            self._kpi("website_cancelled_orders", _("Cancelled Website Orders"), SaleOrder.search_count(domains["cancelled"])),
            self._kpi("website_registered_customers", _("Website Registered Customers"), len(customers)),
            self._kpi("website_new_customers", _("New Website Customers During Selected Period"), len(new_customers)),
            self._kpi("website_top_product", _("Top Selling Online Product"), top_product["value"], value_format="monetary", display_value=top_product["name"] or _("None")),
            self._kpi("website_most_ordered_product", _("Most Ordered Online Product"), most_ordered["quantity"], value_format="float", display_value=most_ordered["name"] or _("None")),
            self._kpi("website_pending_orders", _("Pending Website Orders"), SaleOrder.search_count(domains["pending"])),
            self._kpi("website_draft_carts", _("Draft Website Orders / Carts"), SaleOrder.search_count(domains["draft"])),
            self._kpi("website_abandoned_carts", _("Abandoned Carts"), SaleOrder.search_count(domains["abandoned"]) if self._has_field("sale.order", "is_abandoned_cart") else 0),
            self._kpi("website_conversion_rate", _("Conversion Rate"), round((confirmed_count / conversion_base) * 100, 1) if conversion_base else 0, value_format="percentage"),
        ]

    def _get_website_orders_table(self, filters, limit=50):
        if not self._has_field("sale.order", "website_id"):
            return []
        SaleOrder = self.env["sale.order"]
        state_labels = self._selection_labels("sale.order", "state")
        orders = SaleOrder.search(self._website_order_domains(filters)["total"], limit=limit, order="date_order desc, id desc")
        rows = []
        for order in orders:
            rows.append(
                {
                    "id": order.id,
                    "order": order.name,
                    "customer": order.partner_id.display_name or "",
                    "website": order.website_id.display_name or "",
                    "order_date": self._datetime_to_user_date_string(order, order.date_order),
                    "amount": order.amount_total,
                    "state": order.state,
                    "state_label": state_labels.get(order.state, order.state or ""),
                    "salesperson": order.user_id.display_name or "",
                }
            )
        return rows

    def _get_website_products_table(self, filters, limit=50):
        if not self._has_field("sale.order", "website_id"):
            return []
        Line = self.env["sale.order.line"]
        groups = Line.read_group(
            self._website_line_domain(filters),
            ["product_uom_qty:sum", "price_total:sum"],
            ["product_id"],
            lazy=False,
        )
        rows = []
        for group in groups:
            product = group.get("product_id")
            if not product:
                continue
            rows.append(
                {
                    "product_id": product[0],
                    "product": product[1],
                    "sold_quantity": group.get("product_uom_qty", 0) or group.get("product_uom_qty_sum", 0) or 0,
                    "revenue": group.get("price_total", 0) or group.get("price_total_sum", 0) or 0,
                    "orders_count": self._website_line_distinct_order_count(filters, product[0]),
                }
            )
        rows.sort(key=lambda row: row["revenue"], reverse=True)
        return rows[:limit]

    def _get_website_customers_table(self, filters, limit=50):
        if not self._has_field("sale.order", "website_id"):
            return []
        SaleOrder = self.env["sale.order"]
        partner_ids = self._website_customer_ids(filters)[:limit]
        rows = []
        for partner in self.env["res.partner"].browse(partner_ids):
            partner_filters = filters.copy()
            partner_filters["website_customer_id"] = partner.id
            orders = SaleOrder.search(self._website_order_domains(partner_filters)["confirmed"], order="date_order desc, id desc")
            rows.append(
                {
                    "partner_id": partner.id,
                    "customer": partner.display_name,
                    "registration_date": fields.Date.to_string(partner.create_date.date()) if partner.create_date else "",
                    "orders_count": len(orders),
                    "total_revenue": sum(orders.mapped("amount_total")),
                    "last_order_date": self._datetime_to_user_date_string(orders[:1], orders[:1].date_order) if orders else "",
                }
            )
        rows.sort(key=lambda row: row["total_revenue"], reverse=True)
        return rows

    def _get_website_charts(self, filters):
        return {
            "charts": [
                self._website_revenue_trend_chart(filters),
                self._website_orders_by_website_chart(filters),
                self._website_orders_state_chart(filters),
                self._website_top_products_chart(filters),
                self._website_customer_growth_chart(filters),
                self._online_vs_pos_revenue_chart(filters),
            ]
        }

    def _pos_revenue_trend_chart(self, filters):
        data = []
        if self._can_read_model("pos.order"):
            Order = self.env["pos.order"]
            for period in self._month_periods(filters):
                domain = (
                    self._pos_order_domain(filters, include_date=False)
                    + self._datetime_range_domain("date_order", period["date_from"], period["date_to"])
                )
                data.append({"label": period["label"], "value": self._sum(Order, domain, "amount_total"), "extra": period["extra"]})
        return {"key": "pos_revenue_trend", "action_key": "chart_pos_revenue_trend", "title": _("POS Revenue Trend"), "kind": "line", "metric": "monetary", "data": data}

    def _pos_sales_branch_chart(self, filters):
        data = []
        if self._can_read_model("pos.order"):
            groups = self.env["pos.order"].read_group(self._pos_order_domain(filters), ["amount_total:sum"], ["config_id"], lazy=False)
            for group in groups:
                config = group.get("config_id")
                data.append({"label": config[1] if config else _("No POS"), "value": group.get("amount_total", 0) or group.get("amount_total_sum", 0) or 0, "extra": {"config_id": config[0] if config else False}})
        data.sort(key=lambda item: item["value"], reverse=True)
        return {"key": "pos_sales_by_branch", "action_key": "chart_pos_branch", "title": _("Sales by POS / Branch"), "kind": "bar", "horizontal": True, "metric": "monetary", "data": data[:10]}

    def _pos_sales_cashier_chart(self, filters):
        data = []
        if self._can_read_model("pos.order"):
            groups = self.env["pos.order"].read_group(self._pos_order_domain(filters), ["amount_total:sum"], ["user_id"], lazy=False)
            for group in groups:
                user = group.get("user_id")
                data.append({"label": user[1] if user else _("No Cashier"), "value": group.get("amount_total", 0) or group.get("amount_total_sum", 0) or 0, "extra": {"user_id": user[0] if user else False}})
        data.sort(key=lambda item: item["value"], reverse=True)
        return {"key": "pos_sales_by_cashier", "action_key": "chart_pos_cashier", "title": _("Sales by Cashier"), "kind": "bar", "horizontal": True, "metric": "monetary", "data": data[:10]}

    def _pos_sales_payment_method_chart(self, filters):
        data = []
        if self._can_read_model("pos.payment"):
            groups = self.env["pos.payment"].read_group(self._pos_payment_domain(filters), ["amount:sum"], ["payment_method_id"], lazy=False)
            for group in groups:
                payment_method = group.get("payment_method_id")
                data.append({"label": payment_method[1] if payment_method else _("No Method"), "value": group.get("amount", 0) or group.get("amount_sum", 0) or 0, "extra": {"payment_method_id": payment_method[0] if payment_method else False}})
        data.sort(key=lambda item: item["value"], reverse=True)
        return {"key": "pos_sales_by_payment_method", "action_key": "chart_pos_payment_method", "title": _("Sales by Payment Method"), "kind": "bar", "horizontal": True, "metric": "monetary", "data": data[:10]}

    def _pos_top_products_chart(self, filters):
        data = []
        for row in self._get_pos_products_table(filters, limit=10):
            data.append({"label": row["product"], "value": row["revenue"], "extra": {"product_id": row["product_id"]}})
        return {"key": "pos_top_products", "action_key": "chart_pos_top_product", "title": _("Top POS Products"), "kind": "bar", "horizontal": True, "metric": "monetary", "data": data}

    def _pos_refund_trend_chart(self, filters):
        data = []
        if self._can_read_model("pos.order"):
            Order = self.env["pos.order"]
            for period in self._month_periods(filters):
                domain = (
                    self._pos_refund_order_domain(filters, include_date=False)
                    + self._datetime_range_domain("date_order", period["date_from"], period["date_to"])
                )
                data.append({"label": period["label"], "value": abs(self._sum(Order, domain, "amount_total")), "extra": period["extra"]})
        return {"key": "pos_refund_trend", "action_key": "chart_pos_refund_trend", "title": _("Refund Trend"), "kind": "line", "metric": "monetary", "data": data}

    def _website_revenue_trend_chart(self, filters):
        data = []
        if self._has_field("sale.order", "website_id"):
            SaleOrder = self.env["sale.order"]
            for period in self._month_periods(filters):
                domain = (
                    self._website_order_domains(filters, include_date=False)["confirmed"]
                    + self._datetime_range_domain("date_order", period["date_from"], period["date_to"])
                )
                data.append({"label": period["label"], "value": self._sum(SaleOrder, domain, "amount_total"), "extra": period["extra"]})
        return {"key": "website_revenue_trend", "action_key": "chart_website_revenue_trend", "title": _("Website Revenue Trend"), "kind": "line", "metric": "monetary", "data": data}

    def _website_orders_by_website_chart(self, filters):
        data = []
        if self._has_field("sale.order", "website_id"):
            groups = self.env["sale.order"].read_group(self._website_order_domains(filters)["total"], ["website_id"], ["website_id"], lazy=False)
            for group in groups:
                website = group.get("website_id")
                data.append({"label": website[1] if website else _("No Website"), "value": group.get("__count", 0), "extra": {"website_id": website[0] if website else False}})
        data.sort(key=lambda item: item["value"], reverse=True)
        return {"key": "website_orders_by_website", "action_key": "chart_website_orders_by_website", "title": _("Orders by Website"), "kind": "bar", "horizontal": True, "metric": "integer", "data": data[:10]}

    def _website_orders_state_chart(self, filters):
        data = []
        state_labels = self._selection_labels("sale.order", "state")
        if self._has_field("sale.order", "website_id"):
            groups = self.env["sale.order"].read_group(self._website_order_domains(filters)["total"], ["state"], ["state"], lazy=False)
            for group in groups:
                state = group.get("state")
                data.append({"label": state_labels.get(state, state or _("No State")), "value": group.get("__count", 0), "extra": {"state": state or False}})
        return {"key": "website_orders_by_state", "action_key": "chart_website_orders_state", "title": _("Website Orders by State"), "kind": "doughnut", "metric": "integer", "data": data}

    def _website_top_products_chart(self, filters):
        data = []
        for row in self._get_website_products_table(filters, limit=10):
            data.append({"label": row["product"], "value": row["revenue"], "extra": {"product_id": row["product_id"]}})
        return {"key": "website_top_products", "action_key": "chart_website_top_product", "title": _("Top Online Products"), "kind": "bar", "horizontal": True, "metric": "monetary", "data": data}

    def _website_customer_growth_chart(self, filters):
        data = []
        if self._has_field("sale.order", "website_id"):
            Partner = self.env["res.partner"]
            for period in self._month_periods(filters):
                partner_ids = self._website_customer_ids(filters, selected_period=False)
                domain = [("id", "in", partner_ids)] + self._datetime_range_domain("create_date", period["date_from"], period["date_to"])
                data.append({"label": period["label"], "value": Partner.search_count(domain), "extra": period["extra"]})
        return {"key": "website_customer_growth", "action_key": "chart_website_customer_growth", "title": _("Online Customers Growth"), "kind": "line", "metric": "integer", "data": data}

    def _online_vs_pos_revenue_chart(self, filters):
        website_revenue = 0
        pos_revenue = 0
        if self._has_field("sale.order", "website_id"):
            website_revenue = self._sum(self.env["sale.order"], self._website_order_domains(filters)["confirmed"], "amount_total")
        if self._can_read_model("pos.order"):
            pos_revenue = self._sum(self.env["pos.order"], self._pos_order_domain(filters), "amount_total")
        return {
            "key": "online_vs_pos_revenue",
            "action_key": "chart_online_vs_pos_revenue",
            "title": _("Online vs POS Revenue Comparison"),
            "kind": "doughnut",
            "metric": "monetary",
            "data": [
                {"label": _("Online"), "value": website_revenue, "extra": {"segment": "online"}},
                {"label": _("POS"), "value": pos_revenue, "extra": {"segment": "pos"}},
            ],
        }

    # -------------------------------------------------------------------------
    # Alerts
    # -------------------------------------------------------------------------

    def _get_alert_rows(self, filters, limit=100, department=False, severity=False):
        rows = []
        per_type_limit = max(min(limit, 25), 1)
        collectors = [
            self._alert_delayed_quotations,
            self._alert_delayed_sales_orders,
            self._alert_out_of_stock_products,
            self._alert_low_stock_products,
            self._alert_pending_receipts,
            self._alert_delayed_purchase_orders,
            self._alert_manufacturing_shortages,
            self._alert_delayed_manufacturing_orders,
            self._alert_delayed_workorders,
            self._alert_delayed_maintenance_requests,
            self._alert_equipment_open_maintenance,
        ]
        for collector in collectors:
            rows.extend(collector(filters, per_type_limit))

        department = department or filters.get("department")
        severity = severity or filters.get("severity")
        if department:
            rows = [row for row in rows if row["department_key"] == department]
        if severity:
            rows = [row for row in rows if row["severity_key"] == severity]
        if filters.get("responsible_user_id"):
            rows = [
                row
                for row in rows
                if row.get("responsible_user_id") == filters["responsible_user_id"]
            ]

        rows.sort(
            key=lambda row: (
                self._alert_severity_rank(row["severity_key"]),
                -row.get("delay_days", 0),
                row["alert_type"],
                row["related_document"],
            )
        )
        return rows[:limit]

    def _alert_delayed_quotations(self, filters, limit):
        today = fields.Date.context_today(self)
        orders = self.env["sale.order"].search(
            self._sales_domains(filters)["delayed_quotations"],
            limit=limit,
            order="validity_date asc, date_order desc",
        )
        rows = []
        for order in orders:
            delay_days = self._delay_days(today, order.validity_date)
            rows.append(
                self._alert_row(
                    key=f"delayed-quotation-{order.id}",
                    alert_type=_("Delayed Quotations"),
                    severity_key="high" if delay_days <= 14 else "critical",
                    department_key="sales",
                    related_model="sale.order",
                    related_id=order.id,
                    related_document=order.name,
                    responsible=order.user_id,
                    delay_days=delay_days,
                    message=_("Quotation validity date has passed."),
                )
            )
        return rows

    def _alert_delayed_sales_orders(self, filters, limit):
        today = fields.Date.context_today(self)
        orders = self.env["sale.order"].search(
            self._sales_domains(filters)["delayed_sales_orders"],
            limit=limit,
            order="commitment_date asc, date_order desc",
        )
        rows = []
        for order in orders:
            expected_date = self._datetime_to_user_date(order, order.commitment_date)
            delay_days = self._delay_days(today, expected_date)
            rows.append(
                self._alert_row(
                    key=f"delayed-sale-order-{order.id}",
                    alert_type=_("Delayed Sales Orders"),
                    severity_key="high" if delay_days <= 14 else "critical",
                    department_key="sales",
                    related_model="sale.order",
                    related_id=order.id,
                    related_document=order.name,
                    responsible=order.user_id,
                    delay_days=delay_days,
                    message=_("Sales order commitment date has passed."),
                )
            )
        return rows

    def _alert_out_of_stock_products(self, filters, limit):
        Product = self.env["product.product"].with_context(**self._stock_context(filters))
        products = Product.search(
            self._stockable_product_domain(filters) + [("qty_available", "<=", 0)],
            limit=limit,
            order="name, id",
        )
        return [
            self._alert_row(
                key=f"out-of-stock-{product.id}",
                alert_type=_("Out of Stock Products"),
                severity_key="critical",
                department_key="inventory",
                related_model="product.product",
                related_id=product.id,
                related_document=product.display_name,
                responsible=False,
                delay_days=0,
                message=_("Product has no available stock."),
            )
            for product in products
        ]

    def _alert_low_stock_products(self, filters, limit):
        Product = self.env["product.product"].with_context(**self._stock_context(filters))
        low_domain = self._low_stock_action_domain(filters)
        products = Product.search(low_domain + [("qty_available", ">", 0)], limit=limit, order="name, id")
        return [
            self._alert_row(
                key=f"low-stock-{product.id}",
                alert_type=_("Low Stock Products"),
                severity_key="medium",
                department_key="inventory",
                related_model="product.product",
                related_id=product.id,
                related_document=product.display_name,
                responsible=False,
                delay_days=0,
                message=_("Product is below reorder or forecast threshold."),
            )
            for product in products
        ]

    def _alert_pending_receipts(self, filters, limit):
        orders = self.env["purchase.order"].search(
            self._purchase_domains(filters)["not_fully_received"],
            limit=limit,
            order="date_planned asc, date_order desc",
        )
        rows = []
        for order in orders:
            rows.append(
                self._alert_row(
                    key=f"pending-receipt-{order.id}",
                    alert_type=_("Pending Receipts"),
                    severity_key="low",
                    department_key="purchase",
                    related_model="purchase.order",
                    related_id=order.id,
                    related_document=order.name,
                    responsible=order.user_id,
                    delay_days=0,
                    message=_("Purchase order is not fully received."),
                )
            )
        return rows

    def _alert_delayed_purchase_orders(self, filters, limit):
        today = fields.Date.context_today(self)
        orders = self.env["purchase.order"].search(
            self._purchase_domains(filters)["delayed_purchase_orders"],
            limit=limit,
            order="date_planned asc, date_order desc",
        )
        rows = []
        for order in orders:
            planned_date = self._datetime_to_user_date(order, order.date_planned)
            delay_days = self._delay_days(today, planned_date)
            rows.append(
                self._alert_row(
                    key=f"delayed-purchase-{order.id}",
                    alert_type=_("Delayed Purchase Orders"),
                    severity_key="high" if delay_days <= 14 else "critical",
                    department_key="purchase",
                    related_model="purchase.order",
                    related_id=order.id,
                    related_document=order.name,
                    responsible=order.user_id,
                    delay_days=delay_days,
                    message=_("Purchase order planned receipt date has passed."),
                )
            )
        return rows

    def _alert_manufacturing_shortages(self, filters, limit):
        productions = self.env["mrp.production"].search(
            self._manufacturing_domains(filters)["missing_materials"],
            limit=limit,
            order="date_deadline asc, date_start desc, id desc",
        )
        return [
            self._alert_row(
                key=f"manufacturing-shortage-{production.id}",
                alert_type=_("Manufacturing Orders Blocked by Shortages"),
                severity_key="critical",
                department_key="manufacturing",
                related_model="mrp.production",
                related_id=production.id,
                related_document=production.name,
                responsible=production.user_id,
                delay_days=0,
                message=_("Manufacturing order is blocked by missing raw materials."),
                can_create_activity=True,
            )
            for production in productions
        ]

    def _alert_delayed_manufacturing_orders(self, filters, limit):
        today = fields.Date.context_today(self)
        productions = self.env["mrp.production"].search(
            self._manufacturing_domains(filters)["delayed"],
            limit=limit,
            order="date_deadline asc, date_start desc, id desc",
        )
        rows = []
        for production in productions:
            deadline = self._datetime_to_user_date(production, production.date_deadline)
            delay_days = self._delay_days(today, deadline)
            rows.append(
                self._alert_row(
                    key=f"delayed-manufacturing-{production.id}",
                    alert_type=_("Delayed Manufacturing Orders"),
                    severity_key="high" if delay_days <= 14 else "critical",
                    department_key="manufacturing",
                    related_model="mrp.production",
                    related_id=production.id,
                    related_document=production.name,
                    responsible=production.user_id,
                    delay_days=delay_days,
                    message=_("Manufacturing order deadline has passed."),
                )
            )
        return rows

    def _alert_delayed_workorders(self, filters, limit):
        today = fields.Date.context_today(self)
        workorders = self.env["mrp.workorder"].search(
            self._workorder_domains(filters)["delayed"],
            limit=limit,
            order="date_finished asc, date_start desc, id desc",
        )
        rows = []
        for workorder in workorders:
            deadline = self._datetime_to_user_date(workorder, workorder.date_finished)
            delay_days = self._delay_days(today, deadline)
            rows.append(
                self._alert_row(
                    key=f"delayed-workorder-{workorder.id}",
                    alert_type=_("Delayed Work Orders"),
                    severity_key="high" if delay_days <= 14 else "critical",
                    department_key="manufacturing",
                    related_model="mrp.workorder",
                    related_id=workorder.id,
                    related_document=workorder.display_name,
                    responsible=workorder.production_id.user_id,
                    delay_days=delay_days,
                    message=_("Work order planned finish date has passed."),
                )
            )
        return rows

    def _alert_delayed_maintenance_requests(self, filters, limit):
        today = fields.Date.context_today(self)
        requests = self.env["maintenance.request"].search(
            self._maintenance_domains(filters)["delayed"],
            limit=limit,
            order="schedule_date asc, request_date desc, id desc",
        )
        rows = []
        for request in requests:
            scheduled_date = self._datetime_to_user_date(request, request.schedule_date)
            reference_date = scheduled_date or request.request_date
            delay_days = self._delay_days(today, reference_date)
            rows.append(
                self._alert_row(
                    key=f"delayed-maintenance-{request.id}",
                    alert_type=_("Delayed Maintenance Requests"),
                    severity_key="high" if delay_days <= 14 else "critical",
                    department_key="maintenance",
                    related_model="maintenance.request",
                    related_id=request.id,
                    related_document=request.name,
                    responsible=request.user_id,
                    delay_days=delay_days,
                    message=_("Maintenance request is overdue."),
                )
            )
        return rows

    def _alert_equipment_open_maintenance(self, filters, limit):
        equipment_ids = self._equipment_with_open_maintenance_ids(filters)
        equipment_records = self.env["maintenance.equipment"].browse(equipment_ids[:limit]).exists()
        return [
            self._alert_row(
                key=f"equipment-open-maintenance-{equipment.id}",
                alert_type=_("Equipment with Open Maintenance"),
                severity_key="medium",
                department_key="maintenance",
                related_model="maintenance.equipment",
                related_id=equipment.id,
                related_document=equipment.display_name,
                responsible=equipment.technician_user_id,
                delay_days=0,
                message=_("Equipment has open maintenance requests."),
            )
            for equipment in equipment_records
        ]

    def _alert_row(
        self,
        key,
        alert_type,
        severity_key,
        department_key,
        related_model,
        related_id,
        related_document,
        responsible,
        delay_days,
        message,
        can_create_activity=False,
    ):
        department_labels = self._alert_department_labels()
        severity_labels = self._alert_severity_labels()
        return {
            "id": key,
            "alert_type": alert_type,
            "severity_key": severity_key,
            "severity": severity_labels.get(severity_key, severity_key),
            "related_model": related_model,
            "related_id": related_id,
            "related_document": related_document,
            "department_key": department_key,
            "department": department_labels.get(department_key, department_key),
            "responsible_user_id": responsible.id if responsible else False,
            "responsible_user": responsible.display_name if responsible else "",
            "delay_days": delay_days or 0,
            "message": message,
            "can_create_activity": can_create_activity,
        }

    def _get_alert_summary(self, alerts):
        summary = {
            "total": len(alerts),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for alert in alerts:
            key = alert.get("severity_key")
            if key in summary:
                summary[key] += 1
        return summary

    def _get_smart_alert_rows(self, filters, limit=100):
        domain = [
            ("company_id", "in", filters.get("company_ids") or self.env.companies.ids),
        ]
        if filters.get("severity"):
            domain.append(("severity", "=", filters["severity"]))
        if filters.get("responsible_user_id"):
            domain.append(("responsible_user_id", "=", filters["responsible_user_id"]))
        if filters.get("alert_status"):
            domain.append(("status", "=", filters["alert_status"]))
        else:
            domain.append(("status", "in", ["new", "in_progress", "escalated"]))
        if filters.get("alert_dashboard_key"):
            domain.append(("dashboard_key", "=", filters["alert_dashboard_key"]))
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        if date_from:
            domain.append(("triggered_datetime", ">=", datetime.combine(date_from, time.min)))
        if date_to:
            domain.append(("triggered_datetime", "<=", datetime.combine(date_to, time.max)))

        alerts = self.env["executive.dashboard.alert.history"].search(
            domain,
            limit=limit,
            order="severity DESC, triggered_datetime DESC, id DESC",
        )
        dashboard_labels = self._smart_alert_dashboard_labels()
        status_labels = self._smart_alert_status_labels()
        rows = []
        for alert in alerts:
            rows.append(
                {
                    "id": "smart-%s" % alert.id,
                    "smart_alert_id": alert.id,
                    "rule_id": alert.rule_id.id,
                    "rule_name": alert.rule_id.display_name or "",
                    "dashboard_key": alert.dashboard_key,
                    "dashboard": dashboard_labels.get(alert.dashboard_key, alert.dashboard_key),
                    "metric_key": alert.metric_key,
                    "metric_label": alert.metric_label,
                    "measured_value": alert.measured_value,
                    "operator": alert.operator,
                    "threshold_value": alert.threshold_value,
                    "severity_key": alert.severity,
                    "severity": dict(alert._fields["severity"].selection).get(alert.severity, alert.severity),
                    "status": alert.status,
                    "status_label": status_labels.get(alert.status, alert.status),
                    "responsible_user": alert.responsible_user_id.display_name or "",
                    "responsible_user_id": alert.responsible_user_id.id,
                    "triggered_datetime": fields.Datetime.to_string(alert.triggered_datetime) or "",
                    "message": alert.message or "",
                    "related_model": alert.related_model,
                    "related_id": alert.related_res_id,
                    "related_document": alert.related_record_name,
                    "can_open_related": bool(alert.related_model and alert.related_res_id),
                }
            )
        return rows

    def _get_smart_alert_summary(self, alerts):
        summary = {
            "total": len(alerts),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "escalated": 0,
        }
        for alert in alerts:
            severity = alert.get("severity_key")
            status = alert.get("status")
            if severity in summary:
                summary[severity] += 1
            if status == "escalated":
                summary["escalated"] += 1
        return summary

    def _critical_alert_count(self, filters):
        Product = self.env["product.product"].with_context(**self._stock_context(filters))
        product_domain = self._stockable_product_domain(filters)
        return (
            Product.search_count(product_domain + [("qty_available", "<=", 0)])
            + self.env["stock.picking"].search_count(self._blocked_delivery_domain(filters))
            + self.env["mrp.production"].search_count(self._manufacturing_domains(filters)["missing_materials"])
        )

    def _create_alert_activity(self, data):
        model_name = data.get("related_model")
        record_id = self._parse_int(data.get("related_id"))
        user_id = self._parse_int(data.get("responsible_user_id")) or self.env.user.id
        if not model_name or not record_id:
            raise UserError(_("The alert does not include a valid related record."))
        try:
            record = self.env[model_name].browse(record_id).exists()
        except KeyError:
            record = False
        if not record:
            raise UserError(_("The related record is no longer available."))
        if not hasattr(record, "activity_schedule"):
            raise UserError(_("Activities are not available on this record."))
        user = self.env["res.users"].browse(user_id).exists() or self.env.user
        record.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=user.id,
            summary=_("Dashboard alert: %s", data.get("alert_type") or record.display_name),
            note=data.get("message") or _("Please review this dashboard alert."),
        )
        return {"message": _("Activity created.")}

    def _delay_days(self, today, date_value):
        if not date_value:
            return 0
        if isinstance(date_value, datetime):
            date_value = date_value.date()
        return max((today - fields.Date.to_date(date_value)).days, 0)

    def _alert_department_labels(self):
        return {
            "sales": _("Sales"),
            "crm": _("CRM"),
            "inventory": _("Inventory"),
            "purchase": _("Purchase"),
            "manufacturing": _("Manufacturing"),
            "maintenance": _("Maintenance"),
        }

    def _alert_department_keys(self):
        return list(self._alert_department_labels())

    def _alert_severity_labels(self):
        return {
            "critical": _("Critical"),
            "high": _("High"),
            "medium": _("Medium"),
            "low": _("Low"),
        }

    def _alert_severity_keys(self):
        return list(self._alert_severity_labels())

    def _smart_alert_status_labels(self):
        return {
            "new": _("New"),
            "in_progress": _("In Progress"),
            "resolved": _("Resolved"),
            "ignored": _("Ignored"),
            "escalated": _("Escalated"),
        }

    def _smart_alert_status_keys(self):
        return list(self._smart_alert_status_labels())

    def _smart_alert_dashboard_labels(self):
        return dict(self.env["executive.dashboard.alert.rule"].DASHBOARD_SELECTION)

    def _smart_alert_dashboard_keys(self):
        return list(self._smart_alert_dashboard_labels())

    def _alert_severity_rank(self, severity_key):
        return {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }.get(severity_key, 99)

    def _last_updated_label(self):
        return fields.Datetime.to_string(
            fields.Datetime.context_timestamp(self, fields.Datetime.now())
        )

    def _create_shortage_activity(self, data):
        model_name = data.get("activity_model") or data.get("related_model")
        record_id = self._parse_int(data.get("activity_id") or data.get("related_id"))
        user_id = self._parse_int(data.get("responsible_user_id")) or self.env.user.id
        if not model_name or not record_id:
            raise UserError(_("The shortage row does not include a valid activity target."))
        try:
            record = self.env[model_name].browse(record_id).exists()
        except KeyError:
            record = False
        if not record:
            raise UserError(_("The related document is no longer available."))
        if not hasattr(record, "activity_schedule"):
            raise UserError(_("Activities are not available on this document."))
        user = self.env["res.users"].browse(user_id).exists() or self.env.user
        product = data.get("product") or _("Unknown Product")
        shortage_qty = data.get("shortage_qty") or 0
        document = data.get("related_document") or record.display_name
        note = _(
            "Please provide missing material: %(product)s\nShortage Qty: %(qty)s\nRelated Document: %(document)s",
            product=product,
            qty=shortage_qty,
            document=document,
        )
        record.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=user.id,
            summary=_("Missing material: %s", product),
            note=note,
        )
        return {"message": _("Activity created.")}

    def _create_manufacturing_shortage_activity(self, data):
        production_id = self._parse_int(data.get("mo_id") or data.get("activity_id"))
        if not production_id:
            raise UserError(_("The shortage row does not include a valid manufacturing order."))
        production = self.env["mrp.production"].browse(production_id).exists()
        if not production:
            raise UserError(_("The manufacturing order is no longer available."))
        product = data.get("raw_material") or data.get("product") or _("Unknown Product")
        shortage_qty = data.get("shortage_qty") or 0
        user = production.user_id or self.env.user
        note = _(
            "Please provide missing raw material: %(product)s\nShortage Qty: %(qty)s\nManufacturing Order: %(mo)s",
            product=product,
            qty=shortage_qty,
            mo=production.display_name,
        )
        production.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=user.id,
            summary=_("Missing raw material: %s", product),
            note=note,
        )
        return {"message": _("Manufacturing shortage activity created.")}

    # -------------------------------------------------------------------------
    # Charts
    # -------------------------------------------------------------------------

    def _get_chart_data(self, filters):
        return {
            "charts": [
                self._monthly_sales_chart(filters),
                self._quotations_vs_sales_chart(filters),
                self._salesperson_performance_chart(filters),
                self._crm_pipeline_stage_chart(filters),
            ]
        }

    def _get_sales_charts(self, filters):
        return {
            "charts": [
                self._monthly_sales_chart(filters),
                self._quotations_vs_sales_chart(filters),
                self._salesperson_performance_chart(filters),
            ]
        }

    def _get_crm_charts(self, filters):
        return {"charts": [self._crm_pipeline_stage_chart(filters)]}

    def _get_inventory_purchase_charts(self, filters):
        return {
            "charts": [
                self._inventory_status_chart(filters),
                self._monthly_purchase_chart(filters),
                self._top_vendors_purchase_chart(filters),
                self._delayed_receipts_vendor_chart(filters),
            ]
        }

    def _get_inventory_charts(self, filters):
        return {"charts": [self._inventory_status_chart(filters)]}

    def _get_purchase_charts(self, filters):
        return {
            "charts": [
                self._monthly_purchase_chart(filters),
                self._top_vendors_purchase_chart(filters),
                self._delayed_receipts_vendor_chart(filters),
            ]
        }

    def _get_manufacturing_charts(self, filters):
        return {
            "charts": [
                self._manufacturing_orders_state_chart(filters),
                self._production_quantity_product_chart(filters),
                self._delayed_manufacturing_responsible_chart(filters),
                self._workcenter_efficiency_chart(filters),
                self._monthly_production_trend_chart(filters),
            ]
        }

    def _get_maintenance_charts(self, filters):
        return {
            "charts": [
                self._maintenance_requests_stage_chart(filters),
                self._maintenance_requests_team_chart(filters),
                self._delayed_maintenance_equipment_chart(filters),
                self._downtime_equipment_chart(filters),
                self._maintenance_monthly_trend_chart(filters),
            ]
        }

    def _manufacturing_orders_state_chart(self, filters):
        Production = self.env["mrp.production"]
        state_labels = self._selection_labels("mrp.production", "state")
        groups = Production.read_group(
            self._manufacturing_base_domain(filters),
            ["state"],
            ["state"],
            lazy=False,
        )
        data = []
        for group in groups:
            state = group.get("state")
            data.append(
                {
                    "label": state_labels.get(state, state or _("No State")),
                    "value": group.get("__count", 0),
                    "extra": {"state": state or False},
                }
            )
        return {
            "key": "manufacturing_orders_by_state",
            "action_key": "chart_mrp_orders_state",
            "title": _("Manufacturing Orders by State"),
            "kind": "doughnut",
            "metric": "integer",
            "data": data,
        }

    def _production_quantity_product_chart(self, filters):
        Production = self.env["mrp.production"]
        groups = Production.read_group(
            self._manufacturing_base_domain(filters),
            ["product_qty:sum"],
            ["product_id"],
            lazy=False,
        )
        data = []
        for group in groups:
            product = group.get("product_id")
            if not product:
                continue
            data.append(
                {
                    "label": product[1],
                    "value": group.get("product_qty", 0) or group.get("product_qty_sum", 0) or 0,
                    "extra": {"product_id": product[0]},
                }
            )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "production_quantity_by_product",
            "action_key": "chart_mrp_product_qty",
            "title": _("Production Quantity by Product"),
            "kind": "bar",
            "horizontal": True,
            "metric": "float",
            "data": data[:10],
        }

    def _delayed_manufacturing_responsible_chart(self, filters):
        Production = self.env["mrp.production"]
        groups = Production.read_group(
            self._manufacturing_domains(filters)["delayed"],
            ["user_id"],
            ["user_id"],
            lazy=False,
        )
        data = []
        for group in groups:
            user = group.get("user_id")
            data.append(
                {
                    "label": user[1] if user else _("No Responsible"),
                    "value": group.get("__count", 0),
                    "extra": {"user_id": user[0] if user else False},
                }
            )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "delayed_manufacturing_by_responsible",
            "action_key": "chart_mrp_delayed_responsible",
            "title": _("Delayed Manufacturing Orders by Responsible"),
            "kind": "bar",
            "horizontal": True,
            "metric": "integer",
            "data": data[:10],
        }

    def _workcenter_efficiency_chart(self, filters):
        data = []
        for row in self._get_workcenter_performance(filters, limit=10):
            data.append(
                {
                    "label": row["workcenter"],
                    "value": row["efficiency"],
                    "extra": {"workcenter_id": row["workcenter_id"]},
                }
            )
        return {
            "key": "workcenter_efficiency",
            "action_key": "chart_workcenter_efficiency",
            "title": _("Work Center Efficiency"),
            "kind": "bar",
            "horizontal": True,
            "metric": "percentage",
            "data": data,
        }

    def _monthly_production_trend_chart(self, filters):
        Production = self.env["mrp.production"]
        data = []
        for period in self._month_periods(filters):
            domain = (
                self._manufacturing_base_domain(filters, include_date=False)
                + [("state", "=", "done")]
                + self._datetime_range_domain("date_finished", period["date_from"], period["date_to"])
            )
            data.append(
                {
                    "label": period["label"],
                    "value": self._sum(Production, domain, "product_qty"),
                    "extra": period["extra"],
                }
            )
        return {
            "key": "monthly_production_trend",
            "action_key": "chart_monthly_production_trend",
            "title": _("Monthly Production Trend"),
            "kind": "line",
            "metric": "float",
            "data": data,
        }

    def _maintenance_requests_stage_chart(self, filters):
        Request = self.env["maintenance.request"]
        groups = Request.read_group(
            self._maintenance_request_base_domain(filters),
            ["stage_id"],
            ["stage_id"],
            lazy=False,
        )
        data = []
        for group in groups:
            stage = group.get("stage_id")
            data.append(
                {
                    "label": stage[1] if stage else _("No Stage"),
                    "value": group.get("__count", 0),
                    "extra": {"stage_id": stage[0] if stage else False},
                }
            )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "maintenance_requests_by_stage",
            "action_key": "chart_maintenance_stage",
            "title": _("Maintenance Requests by Stage"),
            "kind": "doughnut",
            "metric": "integer",
            "data": data,
        }

    def _maintenance_requests_team_chart(self, filters):
        Request = self.env["maintenance.request"]
        groups = Request.read_group(
            self._maintenance_request_base_domain(filters),
            ["maintenance_team_id"],
            ["maintenance_team_id"],
            lazy=False,
        )
        data = []
        for group in groups:
            team = group.get("maintenance_team_id")
            data.append(
                {
                    "label": team[1] if team else _("No Team"),
                    "value": group.get("__count", 0),
                    "extra": {"team_id": team[0] if team else False},
                }
            )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "maintenance_requests_by_team",
            "action_key": "chart_maintenance_team",
            "title": _("Maintenance Requests by Team"),
            "kind": "bar",
            "horizontal": True,
            "metric": "integer",
            "data": data[:10],
        }

    def _delayed_maintenance_equipment_chart(self, filters):
        Request = self.env["maintenance.request"]
        groups = Request.read_group(
            self._maintenance_domains(filters)["delayed"],
            ["equipment_id"],
            ["equipment_id"],
            lazy=False,
        )
        data = []
        for group in groups:
            equipment = group.get("equipment_id")
            data.append(
                {
                    "label": equipment[1] if equipment else _("No Equipment"),
                    "value": group.get("__count", 0),
                    "extra": {"equipment_id": equipment[0] if equipment else False},
                }
            )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "delayed_maintenance_by_equipment",
            "action_key": "chart_delayed_maintenance_equipment",
            "title": _("Delayed Maintenance by Equipment"),
            "kind": "bar",
            "horizontal": True,
            "metric": "integer",
            "data": data[:10],
        }

    def _downtime_equipment_chart(self, filters):
        # The default Odoo 19 maintenance models expose scheduled duration, MTBF,
        # and MTTR, but no explicit equipment downtime duration. Returning an
        # empty chart avoids presenting scheduled hours as operational downtime.
        return {
            "key": "downtime_by_equipment",
            "action_key": "chart_downtime_equipment",
            "title": _("Downtime by Equipment"),
            "kind": "bar",
            "horizontal": True,
            "metric": "float",
            "data": [],
        }

    def _maintenance_monthly_trend_chart(self, filters):
        Request = self.env["maintenance.request"]
        data = []
        for period in self._month_periods(filters):
            domain = (
                self._maintenance_request_base_domain(filters, include_date=False)
                + self._date_range_domain("request_date", period["date_from"], period["date_to"])
            )
            data.append(
                {
                    "label": period["label"],
                    "value": Request.search_count(domain),
                    "extra": period["extra"],
                }
            )
        return {
            "key": "maintenance_monthly_trend",
            "action_key": "chart_maintenance_monthly_trend",
            "title": _("Maintenance Monthly Trend"),
            "kind": "line",
            "metric": "integer",
            "data": data,
        }

    def _inventory_status_chart(self, filters):
        Product = self.env["product.product"].with_context(**self._stock_context(filters))
        product_domain = self._stockable_product_domain(filters)
        total_count = Product.search_count(product_domain)
        out_count = Product.search_count(product_domain + [("qty_available", "<=", 0)])
        below_rule_count = len(self._below_reordering_product_ids(filters))
        low_count = below_rule_count or Product.search_count(product_domain + [("virtual_available", "<=", 0)])
        available_count = max(total_count - out_count - low_count, 0)
        return {
            "key": "inventory_status",
            "action_key": "chart_inventory_status",
            "title": _("Inventory Status"),
            "kind": "doughnut",
            "metric": "integer",
            "data": [
                {"label": _("Available"), "value": available_count, "extra": {"segment": "available"}},
                {"label": _("Low Stock"), "value": low_count, "extra": {"segment": "low"}},
                {"label": _("Out of Stock"), "value": out_count, "extra": {"segment": "out"}},
            ],
        }

    def _monthly_purchase_chart(self, filters):
        PurchaseOrder = self.env["purchase.order"]
        amount_field = self._purchase_amount_field()
        data = []
        for period in self._month_periods(filters):
            domain = (
                self._purchase_base_domain(filters, include_date=False)
                + [("state", "in", self._purchase_order_states())]
                + self._datetime_range_domain("date_order", period["date_from"], period["date_to"])
            )
            data.append(
                {
                    "label": period["label"],
                    "value": self._sum(PurchaseOrder, domain, amount_field),
                    "extra": period["extra"],
                }
            )
        return {
            "key": "monthly_purchase_amount",
            "action_key": "chart_monthly_purchase_amount",
            "title": _("Monthly Purchase Amount"),
            "kind": "bar",
            "metric": "monetary",
            "data": data,
        }

    def _top_vendors_purchase_chart(self, filters):
        PurchaseOrder = self.env["purchase.order"]
        amount_field = self._purchase_amount_field()
        groups = PurchaseOrder.read_group(
            self._purchase_domains(filters)["total_purchase_orders"],
            [f"{amount_field}:sum"],
            ["partner_id"],
            lazy=False,
        )
        data = []
        for group in groups:
            partner = group.get("partner_id")
            if partner:
                data.append(
                    {
                        "label": partner[1],
                        "value": group.get(amount_field, 0) or group.get(f"{amount_field}_sum", 0) or 0,
                        "extra": {"vendor_id": partner[0]},
                    }
                )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "top_vendors_purchase_amount",
            "action_key": "chart_top_vendor_purchase_amount",
            "title": _("Top Vendors by Purchase Amount"),
            "kind": "bar",
            "horizontal": True,
            "metric": "monetary",
            "data": data[:10],
        }

    def _delayed_receipts_vendor_chart(self, filters):
        PurchaseOrder = self.env["purchase.order"]
        groups = PurchaseOrder.read_group(
            self._purchase_domains(filters)["delayed_purchase_orders"],
            ["partner_id"],
            ["partner_id"],
            lazy=False,
        )
        data = []
        for group in groups:
            partner = group.get("partner_id")
            if partner:
                data.append(
                    {
                        "label": partner[1],
                        "value": group.get("__count", 0),
                        "extra": {"vendor_id": partner[0]},
                    }
                )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "delayed_receipts_by_vendor",
            "action_key": "chart_delayed_receipts_vendor",
            "title": _("Delayed Receipts by Vendor"),
            "kind": "bar",
            "horizontal": True,
            "metric": "integer",
            "data": data[:10],
        }

    def _monthly_sales_chart(self, filters):
        SaleOrder = self.env["sale.order"]
        data = []
        for period in self._month_periods(filters):
            domain = (
                self._sale_base_domain(filters, include_date=False)
                + [("state", "in", self._sale_confirmed_states())]
                + self._datetime_range_domain(
                    "date_order", period["date_from"], period["date_to"]
                )
            )
            data.append(
                {
                    "label": period["label"],
                    "value": self._sum(SaleOrder, domain, "amount_total"),
                    "extra": period["extra"],
                }
            )
        return {
            "key": "monthly_sales_amount",
            "action_key": "chart_monthly_sales",
            "title": _("Monthly Sales Amount"),
            "kind": "bar",
            "metric": "monetary",
            "data": data,
        }

    def _quotations_vs_sales_chart(self, filters):
        SaleOrder = self.env["sale.order"]
        labels = []
        metadata = []
        quotation_values = []
        sales_values = []
        for period in self._month_periods(filters):
            labels.append(period["label"])
            metadata.append({"label": period["label"], "extra": period["extra"]})
            month_domain = self._sale_base_domain(filters, include_date=False) + self._datetime_range_domain(
                "date_order", period["date_from"], period["date_to"]
            )
            quotation_values.append(
                SaleOrder.search_count(
                    month_domain + [("state", "in", self._sale_quotation_states())]
                )
            )
            sales_values.append(
                SaleOrder.search_count(
                    month_domain + [("state", "in", self._sale_confirmed_states())]
                )
            )
        return {
            "key": "quotations_vs_sales",
            "action_key": "chart_quotations_vs_sales",
            "title": _("Quotations vs Sales Orders"),
            "kind": "bar",
            "metric": "integer",
            "labels": labels,
            "data": metadata,
            "datasets": [
                {
                    "key": "quotations",
                    "label": _("Quotations"),
                    "values": quotation_values,
                    "color": "#4f46e5",
                },
                {
                    "key": "sales_orders",
                    "label": _("Sales Orders"),
                    "values": sales_values,
                    "color": "#059669",
                },
            ],
        }

    def _salesperson_performance_chart(self, filters):
        SaleOrder = self.env["sale.order"]
        domain = self._sale_base_domain(filters) + [
            ("state", "in", self._sale_confirmed_states())
        ]
        groups = SaleOrder.read_group(
            domain, ["amount_total:sum"], ["user_id"], lazy=False
        )
        data = []
        for group in groups:
            user = group.get("user_id")
            data.append(
                {
                    "label": user[1] if user else _("No Salesperson"),
                    "value": group.get("amount_total", 0) or 0,
                    "count": group.get("__count", 0),
                    "extra": {"salesperson_id": user[0] if user else False},
                }
            )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "salesperson_performance",
            "action_key": "chart_salesperson_performance",
            "title": _("Salesperson Performance"),
            "kind": "bar",
            "horizontal": True,
            "metric": "monetary",
            "data": data[:10],
        }

    def _crm_pipeline_stage_chart(self, filters):
        Lead = self.env["crm.lead"]
        domain = self._crm_base_domain(filters) + [("type", "=", "opportunity")]
        groups = Lead.read_group(
            domain, ["expected_revenue:sum"], ["stage_id"], lazy=False
        )
        data = []
        for group in groups:
            stage = group.get("stage_id")
            data.append(
                {
                    "label": stage[1] if stage else _("No Stage"),
                    "value": group.get("__count", 0),
                    "amount": group.get("expected_revenue", 0) or 0,
                    "extra": {"stage_id": stage[0] if stage else False},
                }
            )
        data.sort(key=lambda item: item["value"], reverse=True)
        return {
            "key": "crm_pipeline_stage",
            "action_key": "chart_crm_pipeline_stage",
            "title": _("CRM Pipeline by Stage"),
            "kind": "doughnut",
            "metric": "integer",
            "data": data,
        }

    # -------------------------------------------------------------------------
    # Domains
    # -------------------------------------------------------------------------

    def _hr_employee_domain(self, filters, include_date=False):
        domain = []
        if self._has_field("hr.employee", "company_id"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("hr_department_id") and self._has_field("hr.employee", "department_id"):
            domain.append(("department_id", "child_of", filters["hr_department_id"]))
        if filters.get("hr_employee_id"):
            domain.append(("id", "=", filters["hr_employee_id"]))
        if filters.get("hr_manager_id") and self._has_field("hr.employee", "parent_id"):
            domain.append(("parent_id", "=", filters["hr_manager_id"]))
        if filters.get("hr_job_id") and self._has_field("hr.employee", "job_id"):
            domain.append(("job_id", "=", filters["hr_job_id"]))
        if include_date:
            domain += self._hr_employee_new_date_domain(filters)
        return domain

    def _hr_employee_new_domain(self, filters):
        return self._hr_employee_domain(filters, include_date=False) + self._hr_employee_new_date_domain(filters)

    def _hr_employee_new_date_domain(self, filters):
        # hr.employee.date_start is HR-manager restricted in Odoo 19. Use
        # create_date so the dashboard respects non-manager HR access safely.
        return self._datetime_range_domain("create_date", filters["date_from"], filters["date_to"])

    def _hr_attendance_domain(self, filters, today=False, include_date=True):
        domain = []
        if self._has_field("hr.attendance", "employee_id"):
            domain.append(("employee_id.company_id", "in", filters["company_ids"]))
            if filters.get("hr_employee_id"):
                domain.append(("employee_id", "=", filters["hr_employee_id"]))
            if filters.get("hr_department_id"):
                domain.append(("employee_id.department_id", "child_of", filters["hr_department_id"]))
            if filters.get("hr_manager_id"):
                domain.append(("employee_id.parent_id", "=", filters["hr_manager_id"]))
            if filters.get("hr_job_id"):
                domain.append(("employee_id.job_id", "=", filters["hr_job_id"]))
        if today:
            domain.append(("date", "=", fields.Date.to_string(fields.Date.context_today(self))))
        elif include_date:
            domain += self._date_range_domain("date", filters["date_from"], filters["date_to"])
        return domain

    def _hr_leave_base_domain(self, filters, include_date=True):
        domain = []
        if self._has_field("hr.leave", "company_id"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("hr_employee_id") and self._has_field("hr.leave", "employee_id"):
            domain.append(("employee_id", "=", filters["hr_employee_id"]))
        if filters.get("hr_department_id") and self._has_field("hr.leave", "department_id"):
            domain.append(("department_id", "child_of", filters["hr_department_id"]))
        if filters.get("hr_manager_id") and self._has_field("hr.leave", "employee_id"):
            domain.append(("employee_id.parent_id", "=", filters["hr_manager_id"]))
        if filters.get("hr_job_id") and self._has_field("hr.leave", "employee_id"):
            domain.append(("employee_id.job_id", "=", filters["hr_job_id"]))
        if include_date:
            if filters["date_from"]:
                domain.append(
                    (
                        "date_to",
                        ">=",
                        fields.Datetime.to_string(datetime.combine(filters["date_from"], time.min)),
                    )
                )
            if filters["date_to"]:
                domain.append(
                    (
                        "date_from",
                        "<=",
                        fields.Datetime.to_string(datetime.combine(filters["date_to"], time.max)),
                    )
                )
        return domain

    def _hr_leave_domains(self, filters):
        base = self._hr_leave_base_domain(filters)
        now = fields.Datetime.to_string(fields.Datetime.now())
        return {
            "total": base,
            "approved": base + [("state", "=", "validate")],
            "pending": base + [("state", "in", ("confirm", "validate1"))],
            "refused": base + [("state", "=", "refuse")],
            "current": self._hr_leave_base_domain(filters, include_date=False)
            + [
                ("state", "=", "validate"),
                ("date_from", "<=", now),
                ("date_to", ">=", now),
            ],
        }

    def _hr_contract_base_domain(self, filters):
        domain = []
        if self._has_field("hr.contract", "company_id"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("hr_employee_id") and self._has_field("hr.contract", "employee_id"):
            domain.append(("employee_id", "=", filters["hr_employee_id"]))
        if filters.get("hr_department_id"):
            if self._has_field("hr.contract", "department_id"):
                domain.append(("department_id", "child_of", filters["hr_department_id"]))
            elif self._has_field("hr.contract", "employee_id"):
                domain.append(("employee_id.department_id", "child_of", filters["hr_department_id"]))
        if filters.get("hr_manager_id") and self._has_field("hr.contract", "employee_id"):
            domain.append(("employee_id.parent_id", "=", filters["hr_manager_id"]))
        if filters.get("hr_job_id"):
            if self._has_field("hr.contract", "job_id"):
                domain.append(("job_id", "=", filters["hr_job_id"]))
            elif self._has_field("hr.contract", "employee_id"):
                domain.append(("employee_id.job_id", "=", filters["hr_job_id"]))
        return domain

    def _hr_contract_domains(self, filters):
        base = self._hr_contract_base_domain(filters)
        end_field = self._hr_contract_end_field()
        if not end_field:
            empty = base + [("id", "=", 0)]
            return {"total": base, "expiring": empty, "expired": empty}
        today = fields.Date.context_today(self)
        notice_date = today + timedelta(days=30)
        return {
            "total": base,
            "expiring": base
            + [
                (end_field, "!=", False),
                (end_field, ">=", fields.Date.to_string(today)),
                (end_field, "<=", fields.Date.to_string(notice_date)),
            ],
            "expired": base
            + [
                (end_field, "!=", False),
                (end_field, "<", fields.Date.to_string(today)),
            ],
        }

    def _helpdesk_domains(self, filters):
        base = self._helpdesk_ticket_base_domain(filters)
        open_domain = base + self._helpdesk_open_domain()
        return {
            "total": base,
            "open": open_domain,
            "closed": base + self._helpdesk_closed_domain(),
            "delayed": self._helpdesk_delayed_domain(filters, base_domain=open_domain),
        }

    def _helpdesk_ticket_base_domain(self, filters, include_date=True):
        domain = []
        if self._has_field("helpdesk.ticket", "company_id"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("helpdesk_team_id") and self._has_field("helpdesk.ticket", "team_id"):
            domain.append(("team_id", "=", filters["helpdesk_team_id"]))
        if filters.get("helpdesk_user_id") and self._has_field("helpdesk.ticket", "user_id"):
            domain.append(("user_id", "=", filters["helpdesk_user_id"]))
        if filters.get("helpdesk_stage_id") and self._has_field("helpdesk.ticket", "stage_id"):
            domain.append(("stage_id", "=", filters["helpdesk_stage_id"]))
        if filters.get("helpdesk_priority") and self._has_field("helpdesk.ticket", "priority"):
            domain.append(("priority", "=", filters["helpdesk_priority"]))
        if include_date:
            domain += self._datetime_range_domain("create_date", filters["date_from"], filters["date_to"])
        return domain

    def _helpdesk_team_domain(self, filters):
        domain = []
        if self._has_field("helpdesk.team", "company_id"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("helpdesk_team_id"):
            domain.append(("id", "=", filters["helpdesk_team_id"]))
        return domain

    def _helpdesk_open_domain(self):
        if self._has_field("helpdesk.ticket", "fold"):
            return [("fold", "=", False)]
        if self._has_field("helpdesk.ticket", "stage_id"):
            return [("stage_id.fold", "=", False)]
        return []

    def _helpdesk_closed_domain(self):
        if self._has_field("helpdesk.ticket", "fold"):
            return [("fold", "=", True)]
        if self._has_field("helpdesk.ticket", "stage_id"):
            return [("stage_id.fold", "=", True)]
        return [("id", "=", 0)]

    def _helpdesk_delayed_domain(self, filters, base_domain=False):
        base = list(base_domain if base_domain is not False else self._helpdesk_ticket_base_domain(filters))
        now = fields.Datetime.to_string(fields.Datetime.now())
        if self._has_field("helpdesk.ticket", "sla_reached_late") and self._has_field("helpdesk.ticket", "sla_deadline"):
            return base + [
                "|",
                ("sla_reached_late", "=", True),
                "&",
                ("sla_deadline", "!=", False),
                ("sla_deadline", "<", now),
            ]
        if self._has_field("helpdesk.ticket", "sla_reached_late"):
            return base + [("sla_reached_late", "=", True)]
        if self._has_field("helpdesk.ticket", "sla_deadline"):
            return base + [
                ("sla_deadline", "!=", False),
                ("sla_deadline", "<", now),
            ]
        return base + [("id", "=", 0)]

    def _helpdesk_sla_breached_domain(self, filters):
        if not self._has_field("helpdesk.ticket", "sla_reached_late"):
            return self._helpdesk_ticket_base_domain(filters) + [("id", "=", 0)]
        return self._helpdesk_ticket_base_domain(filters) + [("sla_reached_late", "=", True)]

    def _helpdesk_ticket_keyword_domain(self, filters, keywords):
        conditions = []
        if self._has_field("helpdesk.ticket", "ticket_type_id"):
            conditions += [("ticket_type_id.name", "ilike", keyword) for keyword in keywords]
        if self._has_field("helpdesk.ticket", "tag_ids"):
            conditions += [("tag_ids.name", "ilike", keyword) for keyword in keywords]
        if not conditions:
            return self._helpdesk_ticket_base_domain(filters) + [("id", "=", 0)]
        return self._helpdesk_ticket_base_domain(filters) + self._or_domain(conditions)

    def _pos_order_domain(self, filters, include_date=True):
        domain = []
        if self._has_field("pos.order", "company_id"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("pos_config_id") and self._has_field("pos.order", "config_id"):
            domain.append(("config_id", "=", filters["pos_config_id"]))
        if filters.get("pos_cashier_id") and self._has_field("pos.order", "user_id"):
            domain.append(("user_id", "=", filters["pos_cashier_id"]))
        if filters.get("pos_payment_method_id") and self._has_field("pos.order", "payment_ids"):
            domain.append(("payment_ids.payment_method_id", "=", filters["pos_payment_method_id"]))
        if filters.get("pos_session_state") and self._has_field("pos.order", "session_id"):
            domain.append(("session_id.state", "=", filters["pos_session_state"]))
        if include_date:
            domain += self._datetime_range_domain("date_order", filters["date_from"], filters["date_to"])
        return domain

    def _pos_refund_order_domain(self, filters, include_date=True):
        return self._pos_order_domain(filters, include_date=include_date) + [("amount_total", "<", 0)]

    def _pos_session_domain(self, filters, include_date=True):
        domain = []
        if self._has_field("pos.session", "company_id"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("pos_config_id") and self._has_field("pos.session", "config_id"):
            domain.append(("config_id", "=", filters["pos_config_id"]))
        if filters.get("pos_cashier_id") and self._has_field("pos.session", "user_id"):
            domain.append(("user_id", "=", filters["pos_cashier_id"]))
        if filters.get("pos_session_state") and self._has_field("pos.session", "state"):
            domain.append(("state", "=", filters["pos_session_state"]))
        if include_date:
            domain += self._datetime_range_domain("start_at", filters["date_from"], filters["date_to"])
        return domain

    def _pos_session_domains(self, filters):
        base = self._pos_session_domain(filters)
        today = fields.Date.context_today(self)
        start_today = fields.Datetime.to_string(datetime.combine(today, time.min))
        end_today = fields.Datetime.to_string(datetime.combine(today, time.max))
        return {
            "total": base,
            "open": base + [("state", "!=", "closed")],
            "closed": base + [("state", "=", "closed")],
            "active_today": self._pos_session_domain(filters, include_date=False)
            + [
                ("state", "!=", "closed"),
                ("start_at", ">=", start_today),
                ("start_at", "<=", end_today),
            ],
        }

    def _pos_payment_domain(self, filters, include_date=True):
        domain = []
        if self._has_field("pos.payment", "company_id"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("pos_config_id"):
            domain.append(("session_id.config_id", "=", filters["pos_config_id"]))
        if filters.get("pos_cashier_id"):
            domain.append(("pos_order_id.user_id", "=", filters["pos_cashier_id"]))
        if filters.get("pos_payment_method_id"):
            domain.append(("payment_method_id", "=", filters["pos_payment_method_id"]))
        if filters.get("pos_session_state"):
            domain.append(("session_id.state", "=", filters["pos_session_state"]))
        if include_date:
            domain += self._datetime_range_domain("payment_date", filters["date_from"], filters["date_to"])
        return domain

    def _pos_line_domain(self, filters, include_date=True):
        domain = []
        if self._has_field("pos.order.line", "company_id"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("pos_config_id"):
            domain.append(("order_id.config_id", "=", filters["pos_config_id"]))
        if filters.get("pos_cashier_id"):
            domain.append(("order_id.user_id", "=", filters["pos_cashier_id"]))
        if filters.get("pos_payment_method_id"):
            domain.append(("order_id.payment_ids.payment_method_id", "=", filters["pos_payment_method_id"]))
        if filters.get("pos_session_state"):
            domain.append(("order_id.session_id.state", "=", filters["pos_session_state"]))
        if include_date:
            domain += self._datetime_range_domain("order_id.date_order", filters["date_from"], filters["date_to"])
        return domain

    def _website_order_base_domain(self, filters, include_date=True):
        domain = [("website_id", "!=", False)]
        if self._has_field("sale.order", "company_id"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("website_id"):
            domain.append(("website_id", "=", filters["website_id"]))
        if filters.get("website_customer_id"):
            domain.append(("partner_id", "=", filters["website_customer_id"]))
        if filters.get("product_category_id"):
            domain.append(("order_line.product_id.categ_id", "child_of", filters["product_category_id"]))
        if filters.get("website_order_state"):
            domain.append(("state", "=", filters["website_order_state"]))
        if include_date:
            domain += self._datetime_range_domain("date_order", filters["date_from"], filters["date_to"])
        return domain

    def _website_order_domains(self, filters, include_date=True):
        base = self._website_order_base_domain(filters, include_date=include_date)
        return {
            "total": base,
            "confirmed": base + [("state", "=", "sale")],
            "cancelled": base + [("state", "=", "cancel")],
            "pending": base + [("state", "=", "sent")],
            "draft": base + [("state", "=", "draft")],
            "abandoned": base + [("is_abandoned_cart", "=", True)]
            if self._has_field("sale.order", "is_abandoned_cart")
            else base + [("id", "=", 0)],
        }

    def _website_line_domain(self, filters, include_date=True):
        domain = [("order_id.website_id", "!=", False), ("display_type", "=", False)]
        if self._has_field("sale.order.line", "company_id"):
            domain.append(("company_id", "in", filters["company_ids"]))
        if filters.get("website_id"):
            domain.append(("order_id.website_id", "=", filters["website_id"]))
        if filters.get("website_customer_id"):
            domain.append(("order_id.partner_id", "=", filters["website_customer_id"]))
        if filters.get("product_category_id"):
            domain.append(("product_id.categ_id", "child_of", filters["product_category_id"]))
        if filters.get("website_order_state"):
            domain.append(("order_id.state", "=", filters["website_order_state"]))
        else:
            domain.append(("order_id.state", "=", "sale"))
        if include_date:
            domain += self._datetime_range_domain("order_id.date_order", filters["date_from"], filters["date_to"])
        return domain

    def _sales_domains(self, filters):
        base = self._sale_base_domain(filters)
        quote_states = self._sale_quotation_states()
        confirmed_states = self._sale_confirmed_states()
        today = fields.Date.context_today(self)
        start_today = fields.Datetime.to_string(datetime.combine(today, time.min))
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = today.replace(day=1)
        month_end = month_start + relativedelta(months=1) - timedelta(days=1)

        total_quotations = base + [("state", "in", quote_states)]
        total_sales_orders = base + [("state", "in", confirmed_states)]
        confirmed_sales_orders = base + [("state", "=", "sale")]
        delayed_quotations = total_quotations + [
            ("validity_date", "!=", False),
            ("validity_date", "<", fields.Date.to_string(today)),
        ]
        delayed_sales_orders = total_sales_orders + [
            ("commitment_date", "!=", False),
            ("commitment_date", "<", start_today),
        ]
        if self._has_field("sale.order", "delivery_status"):
            delayed_sales_orders += self._delivery_status_domain(delivered=False)
        # If sale_stock is not installed there is no default delivery completion
        # flag on sale.order. In that case, delayed sales fall back to the promised
        # commitment date only instead of guessing delivery completion from stock.

        return {
            "total_quotations": total_quotations,
            "open_quotations": total_quotations
            + [
                "|",
                ("validity_date", "=", False),
                ("validity_date", ">=", fields.Date.to_string(today)),
            ],
            "delayed_quotations": delayed_quotations,
            "quotations_converted": total_sales_orders,
            "total_sales_orders": total_sales_orders,
            "confirmed_sales_orders": confirmed_sales_orders,
            "delivered_sales_orders": total_sales_orders
            + self._delivery_status_domain(delivered=True),
            "undelivered_sales_orders": total_sales_orders
            + self._delivery_status_domain(delivered=False),
            "delayed_sales_orders": delayed_sales_orders,
            "orders_delivery_today": total_sales_orders
            + self._datetime_range_domain("commitment_date", today, today),
            "orders_delivery_week": total_sales_orders
            + self._datetime_range_domain("commitment_date", week_start, week_end),
            "orders_delivery_month": total_sales_orders
            + self._datetime_range_domain("commitment_date", month_start, month_end),
            "sent_quotations_crm": base
            + [
                ("state", "=", "sent"),
                ("opportunity_id", "!=", False),
            ],
        }

    def _crm_domains(self, filters):
        base = self._crm_base_domain(filters)
        opportunities = base + [("type", "=", "opportunity")]
        return {
            "total_leads": base + [("type", "=", "lead")],
            "total_opportunities": opportunities,
            "won_opportunities": opportunities + [("won_status", "=", "won")],
            "lost_opportunities": opportunities + [("won_status", "=", "lost")],
            "closed_opportunities": opportunities
            + [("won_status", "in", ["won", "lost"])],
            "pipeline_opportunities": opportunities
            + [
                ("active", "=", True),
                ("won_status", "=", "pending"),
            ],
        }

    def _sale_base_domain(self, filters, include_date=True):
        domain = [("company_id", "in", filters["company_ids"])]
        if filters["salesperson_id"]:
            domain.append(("user_id", "=", filters["salesperson_id"]))
        if include_date:
            domain += self._datetime_range_domain(
                "date_order", filters["date_from"], filters["date_to"]
            )
        return domain

    def _crm_base_domain(self, filters, include_date=True):
        domain = []
        if filters["company_id"]:
            domain.append(("company_id", "=", filters["company_id"]))
        else:
            domain += [
                "|",
                ("company_id", "=", False),
                ("company_id", "in", filters["company_ids"]),
            ]
        if filters["salesperson_id"]:
            domain.append(("user_id", "=", filters["salesperson_id"]))
        if filters["sales_team_id"]:
            domain.append(("team_id", "=", filters["sales_team_id"]))
        if include_date:
            domain += self._datetime_range_domain(
                "create_date", filters["date_from"], filters["date_to"]
            )
        return domain

    def _partner_domain(self, filters):
        domain = [("customer_rank", ">", 0)]
        if filters["company_id"]:
            domain += [
                "|",
                ("company_id", "=", False),
                ("company_id", "=", filters["company_id"]),
            ]
        else:
            domain += [
                "|",
                ("company_id", "=", False),
                ("company_id", "in", filters["company_ids"]),
            ]
        if filters["salesperson_id"]:
            domain.append(("user_id", "=", filters["salesperson_id"]))
        domain += self._datetime_range_domain(
            "create_date", filters["date_from"], filters["date_to"]
        )
        return domain

    def _stock_context(self, filters):
        context = {"allowed_company_ids": filters["company_ids"]}
        if filters["warehouse_id"]:
            context["warehouse_id"] = filters["warehouse_id"]
        return context

    def _stockable_product_domain(self, filters):
        domain = [
            ("is_storable", "=", True),
            "|",
            ("product_tmpl_id.company_id", "=", False),
            ("product_tmpl_id.company_id", "in", filters["company_ids"]),
        ]
        if filters["product_category_id"]:
            domain.append(("categ_id", "child_of", filters["product_category_id"]))
        if filters["product_id"]:
            domain.append(("id", "=", filters["product_id"]))
        return domain

    def _orderpoint_domain(self, filters):
        domain = [
            ("company_id", "in", filters["company_ids"]),
            ("product_id.is_storable", "=", True),
        ]
        if filters["warehouse_id"]:
            domain.append(("warehouse_id", "=", filters["warehouse_id"]))
        if filters["product_category_id"]:
            domain.append(("product_id.categ_id", "child_of", filters["product_category_id"]))
        if filters["product_id"]:
            domain.append(("product_id", "=", filters["product_id"]))
        return domain

    def _stock_picking_domain(self, filters, picking_code=None, include_date=True, pending=True):
        domain = [("company_id", "in", filters["company_ids"])]
        if pending:
            domain.append(("state", "not in", ("done", "cancel")))
        if picking_code:
            domain.append(("picking_type_id.code", "=", picking_code))
        if filters["warehouse_id"]:
            domain.append(("picking_type_id.warehouse_id", "=", filters["warehouse_id"]))
        if filters["vendor_id"] and picking_code == "incoming":
            domain.append(("partner_id", "=", filters["vendor_id"]))
        if filters["product_category_id"]:
            domain.append(("move_ids.product_id.categ_id", "child_of", filters["product_category_id"]))
        if filters["product_id"]:
            domain.append(("move_ids.product_id", "=", filters["product_id"]))
        if include_date:
            domain += self._datetime_range_domain(
                "scheduled_date", filters["date_from"], filters["date_to"]
            )
        return domain

    def _delayed_delivery_domain(self, filters):
        today = fields.Date.context_today(self)
        return (
            self._stock_picking_domain(filters, "outgoing")
            + [("scheduled_date", "<", fields.Datetime.to_string(datetime.combine(today, time.min)))]
        )

    def _blocked_delivery_domain(self, filters):
        # Odoo 19 computes products_availability_state from stock.move.forecast_availability.
        # Using the searchable picking field avoids loading all pending moves just to detect shortages.
        return self._stock_picking_domain(filters, "outgoing") + [
            ("products_availability_state", "=", "late")
        ]

    def _missing_move_domain(self, filters):
        domain = [
            ("company_id", "in", filters["company_ids"]),
            ("state", "in", ("waiting", "confirmed", "partially_available", "assigned")),
            ("picking_type_id.code", "=", "outgoing"),
            ("product_id.is_storable", "=", True),
        ]
        if filters["warehouse_id"]:
            domain.append(("picking_type_id.warehouse_id", "=", filters["warehouse_id"]))
        if filters["product_category_id"]:
            domain.append(("product_id.categ_id", "child_of", filters["product_category_id"]))
        if filters["product_id"]:
            domain.append(("product_id", "=", filters["product_id"]))
        domain += self._datetime_range_domain("date", filters["date_from"], filters["date_to"])
        return domain

    def _purchase_domains(self, filters):
        base = self._purchase_base_domain(filters)
        rfq_states = self._purchase_rfq_states()
        po_states = self._purchase_order_states()
        not_full_domain = self._purchase_not_full_domain()
        today = fields.Date.context_today(self)
        start_today = fields.Datetime.to_string(datetime.combine(today, time.min))
        total_rfqs = base + [("state", "in", rfq_states)]
        total_purchase_orders = base + [("state", "in", po_states)]
        not_fully_received = total_purchase_orders + not_full_domain
        return {
            "total_rfqs": total_rfqs,
            "open_rfqs": total_rfqs,
            "total_purchase_orders": total_purchase_orders,
            "open_purchase_orders": not_fully_received,
            "not_fully_received": not_fully_received,
            "delayed_purchase_orders": not_fully_received
            + [
                ("date_planned", "!=", False),
                ("date_planned", "<", start_today),
            ],
        }

    def _purchase_base_domain(self, filters, include_date=True):
        domain = [("company_id", "in", filters["company_ids"])]
        if filters["vendor_id"]:
            domain.append(("partner_id", "=", filters["vendor_id"]))
        if filters["warehouse_id"] and self._has_field("purchase.order", "picking_type_id"):
            domain.append(("picking_type_id.warehouse_id", "=", filters["warehouse_id"]))
        if filters["product_category_id"]:
            domain.append(("order_line.product_id.categ_id", "child_of", filters["product_category_id"]))
        if filters["product_id"]:
            domain.append(("order_line.product_id", "=", filters["product_id"]))
        if include_date:
            domain += self._datetime_range_domain(
                "date_order", filters["date_from"], filters["date_to"]
            )
        return domain

    def _purchase_not_full_domain(self):
        if self._has_field("purchase.order", "receipt_status"):
            return ["|", ("receipt_status", "=", False), ("receipt_status", "!=", "full")]
        # purchase_stock adds receipt_status. If it is unavailable, keep a conservative
        # fallback that only treats confirmed purchase orders as still open.
        return []

    def _purchase_receipt_picking_domain(self, filters, pending=True):
        domain = self._stock_picking_domain(filters, "incoming", pending=pending)
        if self._has_field("stock.picking", "purchase_id"):
            domain.append(("purchase_id", "!=", False))
        return domain

    def _vendor_domain(self, filters):
        domain = [
            ("supplier_rank", ">", 0),
            "|",
            ("company_id", "=", False),
            ("company_id", "in", filters["company_ids"]),
        ]
        if filters["vendor_id"]:
            domain.append(("id", "=", filters["vendor_id"]))
        return domain

    def _purchase_line_domain(self, filters, vendor_id=False):
        domain = [
            ("order_id.company_id", "in", filters["company_ids"]),
            ("order_id.state", "in", self._purchase_order_states()),
            ("display_type", "=", False),
        ]
        if vendor_id:
            domain.append(("order_id.partner_id", "=", vendor_id))
        elif filters["vendor_id"]:
            domain.append(("order_id.partner_id", "=", filters["vendor_id"]))
        if filters["warehouse_id"] and self._has_field("purchase.order", "picking_type_id"):
            domain.append(("order_id.picking_type_id.warehouse_id", "=", filters["warehouse_id"]))
        if filters["product_category_id"]:
            domain.append(("product_id.categ_id", "child_of", filters["product_category_id"]))
        if filters["product_id"]:
            domain.append(("product_id", "=", filters["product_id"]))
        domain += self._datetime_range_domain(
            "order_id.date_order", filters["date_from"], filters["date_to"]
        )
        return domain

    def _manufacturing_domains(self, filters):
        base = self._manufacturing_base_domain(filters)
        today = fields.Date.context_today(self)
        start_today = fields.Datetime.to_string(datetime.combine(today, time.min))
        return {
            "total": base,
            "in_progress": base + [("state", "=", "progress")],
            "planned": base + [
                ("is_planned", "=", True),
                ("state", "not in", ("done", "cancel")),
            ],
            "done": base + [("state", "=", "done")],
            "cancelled": base + [("state", "=", "cancel")],
            "delayed": base + [
                ("state", "not in", ("done", "cancel")),
                ("date_deadline", "!=", False),
                ("date_deadline", "<", start_today),
            ],
            "missing_materials": base + [
                ("state", "in", ("confirmed", "progress", "to_close")),
                ("components_availability_state", "in", ["unavailable"]),
            ],
        }

    def _manufacturing_base_domain(self, filters, include_date=True):
        domain = [("company_id", "in", filters["company_ids"])]
        if filters["product_id"]:
            domain.append(("product_id", "=", filters["product_id"]))
        if filters["manufacturing_user_id"]:
            domain.append(("user_id", "=", filters["manufacturing_user_id"]))
        if filters["workcenter_id"]:
            domain.append(("workorder_ids.workcenter_id", "=", filters["workcenter_id"]))
        if filters["manufacturing_state"]:
            domain.append(("state", "=", filters["manufacturing_state"]))
        if filters["warehouse_id"]:
            domain.append(("picking_type_id.warehouse_id", "=", filters["warehouse_id"]))
        if filters["product_category_id"]:
            domain.append(("product_id.categ_id", "child_of", filters["product_category_id"]))
        if include_date:
            domain += self._datetime_range_domain(
                "date_start", filters["date_from"], filters["date_to"]
            )
        return domain

    def _manufacturing_shortage_domain(self, filters):
        domain = [
            ("raw_material_production_id", "!=", False),
            ("raw_material_production_id.company_id", "in", filters["company_ids"]),
            ("raw_material_production_id.state", "not in", ("done", "cancel")),
            ("state", "not in", ("done", "cancel")),
            ("product_id.is_storable", "=", True),
        ]
        if filters["product_id"]:
            domain.append(("raw_material_production_id.product_id", "=", filters["product_id"]))
        if filters["manufacturing_user_id"]:
            domain.append(("raw_material_production_id.user_id", "=", filters["manufacturing_user_id"]))
        if filters["workcenter_id"]:
            domain.append(("raw_material_production_id.workorder_ids.workcenter_id", "=", filters["workcenter_id"]))
        if filters["manufacturing_state"]:
            domain.append(("raw_material_production_id.state", "=", filters["manufacturing_state"]))
        if filters["warehouse_id"]:
            domain.append(("raw_material_production_id.picking_type_id.warehouse_id", "=", filters["warehouse_id"]))
        if filters["product_category_id"]:
            domain.append(("product_id.categ_id", "child_of", filters["product_category_id"]))
        domain += self._datetime_range_domain(
            "raw_material_production_id.date_start", filters["date_from"], filters["date_to"]
        )
        return domain

    def _workcenter_domain(self, filters):
        domain = [
            "|",
            ("company_id", "=", False),
            ("company_id", "in", filters["company_ids"]),
        ]
        if filters["workcenter_id"]:
            domain.append(("id", "=", filters["workcenter_id"]))
        return domain

    def _workorder_domains(self, filters):
        base = self._workorder_base_domain(filters)
        today = fields.Date.context_today(self)
        start_today = fields.Datetime.to_string(datetime.combine(today, time.min))
        return {
            "total": base,
            "in_progress": base + [("state", "=", "progress")],
            "done": base + [("state", "=", "done")],
            "delayed": base + [
                ("state", "not in", ("done", "cancel")),
                ("date_finished", "!=", False),
                ("date_finished", "<", start_today),
            ],
        }

    def _workorder_base_domain(self, filters, include_date=True):
        domain = [("company_id", "in", filters["company_ids"])]
        if filters["product_id"]:
            domain.append(("product_id", "=", filters["product_id"]))
        if filters["manufacturing_user_id"]:
            domain.append(("production_id.user_id", "=", filters["manufacturing_user_id"]))
        if filters["workcenter_id"]:
            domain.append(("workcenter_id", "=", filters["workcenter_id"]))
        if filters["manufacturing_state"]:
            domain.append(("production_id.state", "=", filters["manufacturing_state"]))
        if filters["warehouse_id"]:
            domain.append(("production_id.picking_type_id.warehouse_id", "=", filters["warehouse_id"]))
        if filters["product_category_id"]:
            domain.append(("product_id.categ_id", "child_of", filters["product_category_id"]))
        if include_date:
            domain += self._datetime_range_domain(
                "date_start", filters["date_from"], filters["date_to"]
            )
        return domain

    def _maintenance_domains(self, filters):
        base = self._maintenance_request_base_domain(filters)
        today = fields.Date.context_today(self)
        today_string = fields.Date.to_string(today)
        start_today = fields.Datetime.to_string(datetime.combine(today, time.min))
        delayed_date_domain = [
            "|",
            "&",
            ("schedule_date", "!=", False),
            ("schedule_date", "<", start_today),
            "&",
            ("schedule_date", "=", False),
            ("request_date", "<", today_string),
        ]
        return {
            "total": base,
            "scheduled": base + [
                ("stage_id.done", "=", False),
                ("archive", "=", False),
                ("schedule_date", "!=", False),
            ],
            "delayed": base + [
                ("stage_id.done", "=", False),
                ("archive", "=", False),
            ] + delayed_date_domain,
            "in_progress": base + [
                ("stage_id.done", "=", False),
                ("archive", "=", False),
            ],
            "done": base + [("stage_id.done", "=", True)],
            "breakdowns": base + [
                ("stage_id.done", "=", False),
                ("archive", "=", False),
                ("maintenance_type", "=", "corrective"),
            ],
            "preventive": base + [("maintenance_type", "=", "preventive")],
            "corrective": base + [("maintenance_type", "=", "corrective")],
        }

    def _maintenance_request_base_domain(self, filters, include_date=True):
        domain = [("company_id", "in", filters["company_ids"])]
        if filters["maintenance_team_id"]:
            domain.append(("maintenance_team_id", "=", filters["maintenance_team_id"]))
        if filters["equipment_id"]:
            domain.append(("equipment_id", "=", filters["equipment_id"]))
        if filters["technician_id"]:
            domain.append(("user_id", "=", filters["technician_id"]))
        if filters["maintenance_stage_id"]:
            domain.append(("stage_id", "=", filters["maintenance_stage_id"]))
        if include_date:
            domain += self._date_range_domain(
                "request_date", filters["date_from"], filters["date_to"]
            )
        return domain

    def _equipment_domain(self, filters):
        domain = [
            "|",
            ("company_id", "=", False),
            ("company_id", "in", filters["company_ids"]),
        ]
        if filters["maintenance_team_id"]:
            domain.append(("maintenance_team_id", "=", filters["maintenance_team_id"]))
        if filters["equipment_id"]:
            domain.append(("id", "=", filters["equipment_id"]))
        if filters["technician_id"]:
            domain.append(("technician_user_id", "=", filters["technician_id"]))
        return domain

    def _datetime_range_domain(self, field_name, date_from=False, date_to=False):
        domain = []
        if date_from:
            domain.append(
                (
                    field_name,
                    ">=",
                    fields.Datetime.to_string(datetime.combine(date_from, time.min)),
                )
            )
        if date_to:
            domain.append(
                (
                    field_name,
                    "<=",
                    fields.Datetime.to_string(datetime.combine(date_to, time.max)),
                )
            )
        return domain

    def _date_range_domain(self, field_name, date_from=False, date_to=False):
        domain = []
        if date_from:
            domain.append((field_name, ">=", fields.Date.to_string(date_from)))
        if date_to:
            domain.append((field_name, "<=", fields.Date.to_string(date_to)))
        return domain

    def _delivery_status_domain(self, delivered):
        if self._has_field("sale.order", "delivery_status"):
            if delivered:
                return [("delivery_status", "=", "full")]
            return [("delivery_status", "in", [False, "pending", "started", "partial"])]
        # Safe fallback when sale_stock is not installed: base sale.order has no
        # stock delivery status. Invoice status is not a delivery metric, but it is
        # the closest stored order-level completion signal available in sale.
        if delivered:
            return [("invoice_status", "=", "invoiced")]
        return [("invoice_status", "!=", "invoiced")]

    # -------------------------------------------------------------------------
    # Action helpers
    # -------------------------------------------------------------------------

    def _window_action(self, name, model, domain, context=None, views=None):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model,
            "view_mode": "list,form",
            "views": views or [[False, "list"], [False, "form"]],
            "domain": domain,
            "context": context or {},
            "target": "current",
        }

    def _safe_window_action(self, name, model, domain, context=None, views=None):
        if not self._can_read_model(model):
            return self._unavailable_action(
                _("You do not have access to %(model)s or the app is not installed.", model=model)
            )
        return self._window_action(name, model, domain, context=context, views=views)

    def _unavailable_action(self, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "warning",
                "message": message,
            },
        }

    def _open_sale_order(self, order_id):
        order_id = self._parse_int(order_id)
        if not order_id:
            return False
        action = self._window_action(
            _("Sales Order"),
            "sale.order",
            [("id", "=", order_id)],
            views=[[False, "form"]],
        )
        action["view_mode"] = "form"
        action["res_id"] = order_id
        return action

    def _pipeline_stage_action(self, filters, extra):
        stage_id = self._parse_int(extra.get("stage_id"))
        team_id = self._parse_int(extra.get("team_id"))
        domain = self._crm_base_domain(filters) + [("type", "=", "opportunity")]
        domain.append(("stage_id", "=", stage_id or False))
        if team_id:
            domain.append(("team_id", "=", team_id))
        elif "team_id" in extra:
            domain.append(("team_id", "=", False))
        return self._window_action(_("CRM Pipeline"), "crm.lead", domain)

    def _chart_monthly_sales_action(self, filters, extra):
        domain = (
            self._sale_base_domain(filters, include_date=False)
            + [("state", "in", self._sale_confirmed_states())]
            + self._extra_date_domain("date_order", extra)
        )
        return self._window_action(_("Monthly Sales Amount"), "sale.order", domain)

    def _chart_quotations_vs_sales_action(self, filters, extra):
        segment = extra.get("segment")
        states = (
            self._sale_quotation_states()
            if segment == "quotations"
            else self._sale_confirmed_states()
        )
        domain = (
            self._sale_base_domain(filters, include_date=False)
            + [("state", "in", states)]
            + self._extra_date_domain("date_order", extra)
        )
        return self._window_action(_("Quotations vs Sales Orders"), "sale.order", domain)

    def _chart_salesperson_action(self, filters, extra):
        user_id = self._parse_int(extra.get("salesperson_id"))
        domain = self._sale_base_domain(filters) + [
            ("state", "in", self._sale_confirmed_states())
        ]
        domain.append(("user_id", "=", user_id or False))
        return self._window_action(_("Salesperson Performance"), "sale.order", domain)

    def _chart_crm_stage_action(self, filters, extra):
        stage_id = self._parse_int(extra.get("stage_id"))
        domain = self._crm_base_domain(filters) + [
            ("type", "=", "opportunity"),
            ("stage_id", "=", stage_id or False),
        ]
        return self._window_action(_("CRM Pipeline by Stage"), "crm.lead", domain)

    def _get_inventory_purchase_action(self, action_key, filters, extra):
        product_domain = self._stockable_product_domain(filters)
        picking_actions = {
            "open_internal_transfers": (_("Open Internal Transfers"), self._stock_picking_domain(filters, "internal")),
            "pending_receipts": (_("Pending Receipts"), self._stock_picking_domain(filters, "incoming")),
            "pending_deliveries": (_("Pending Deliveries"), self._stock_picking_domain(filters, "outgoing")),
            "delayed_deliveries": (_("Delayed Deliveries"), self._delayed_delivery_domain(filters)),
            "orders_blocked_missing_materials": (_("Orders Blocked Due to Missing Materials"), self._blocked_delivery_domain(filters)),
            "pending_warehouse_receipts": (_("Pending Warehouse Receipts"), self._purchase_receipt_picking_domain(filters)),
        }
        purchase_domains = self._purchase_domains(filters)
        purchase_actions = {
            "total_rfqs": (_("Total RFQs"), purchase_domains["total_rfqs"]),
            "open_rfqs": (_("Open RFQs"), purchase_domains["open_rfqs"]),
            "total_purchase_orders": (_("Total Purchase Orders"), purchase_domains["total_purchase_orders"]),
            "open_purchase_orders": (_("Open Purchase Orders"), purchase_domains["open_purchase_orders"]),
            "delayed_purchase_orders": (_("Delayed Purchase Orders"), purchase_domains["delayed_purchase_orders"]),
            "purchase_orders_not_fully_received": (_("Purchase Orders Not Fully Received"), purchase_domains["not_fully_received"]),
            "total_purchase_amount": (_("Total Purchase Amount"), purchase_domains["total_purchase_orders"]),
        }
        if action_key == "total_stockable_products":
            return self._window_action(_("Total Stockable Products"), "product.product", product_domain)
        if action_key == "out_of_stock_products":
            return self._window_action(
                _("Out of Stock Products"),
                "product.product",
                product_domain + [("qty_available", "<=", 0)],
            )
        if action_key == "low_stock_products":
            return self._window_action(
                _("Low Stock Products"),
                "product.product",
                self._low_stock_action_domain(filters),
            )
        if action_key == "products_below_reordering_rules":
            product_ids = self._below_reordering_product_ids(filters)
            return self._window_action(
                _("Products Below Reordering Rules"),
                "product.product",
                [("id", "in", product_ids)] if product_ids else [("id", "=", 0)],
            )
        if action_key == "current_inventory_value":
            return self._window_action(_("Current Inventory Value"), "product.product", product_domain)
        if action_key in picking_actions:
            name, domain = picking_actions[action_key]
            return self._window_action(name, "stock.picking", domain)
        if action_key == "total_vendors":
            return self._window_action(_("Total Vendors"), "res.partner", self._vendor_domain(filters))
        if action_key in purchase_actions:
            name, domain = purchase_actions[action_key]
            return self._window_action(name, "purchase.order", domain)
        if action_key == "most_used_vendor":
            vendor = self._most_used_vendor(filters)
            if vendor["id"]:
                vendor_filters = filters.copy()
                vendor_filters["vendor_id"] = vendor["id"]
                return self._window_action(
                    _("Most Used Vendor"),
                    "purchase.order",
                    self._purchase_domains(vendor_filters)["total_purchase_orders"],
                )
            return self._window_action(_("Most Used Vendor"), "purchase.order", [("id", "=", 0)])
        if action_key == "shortage_product":
            return self._open_record_action("product.product", extra.get("product_id"), _("Product"))
        if action_key == "shortage_related_document":
            return self._open_record_action(
                extra.get("related_model"),
                extra.get("related_id"),
                _("Related Document"),
            )
        if action_key == "pending_receipt_po":
            return self._open_record_action("purchase.order", extra.get("purchase_order_id"), _("Purchase Order"))
        if action_key == "pending_receipt_picking":
            return self._open_record_action("stock.picking", extra.get("picking_id"), _("Receipt"))
        if action_key == "vendor_performance":
            vendor_id = self._parse_int(extra.get("vendor_id"))
            vendor_filters = filters.copy()
            vendor_filters["vendor_id"] = vendor_id
            return self._window_action(
                _("Vendor Purchase Orders"),
                "purchase.order",
                self._purchase_domains(vendor_filters)["total_purchase_orders"],
            )
        if action_key == "chart_inventory_status":
            return self._chart_inventory_status_action(filters, extra)
        if action_key == "chart_monthly_purchase_amount":
            return self._chart_monthly_purchase_action(filters, extra)
        if action_key == "chart_top_vendor_purchase_amount":
            return self._chart_top_vendor_purchase_action(filters, extra)
        if action_key == "chart_delayed_receipts_vendor":
            return self._chart_delayed_receipts_vendor_action(filters, extra)
        return False

    def _get_manufacturing_action(self, action_key, filters, extra):
        manufacturing_domains = self._manufacturing_domains(filters)
        workorder_domains = self._workorder_domains(filters)
        production_actions = {
            "total_manufacturing_orders": (_("Total Manufacturing Orders"), manufacturing_domains["total"]),
            "manufacturing_in_progress": (_("In Progress Manufacturing Orders"), manufacturing_domains["in_progress"]),
            "manufacturing_planned": (_("Planned Manufacturing Orders"), manufacturing_domains["planned"]),
            "manufacturing_done": (_("Done Manufacturing Orders"), manufacturing_domains["done"]),
            "manufacturing_cancelled": (_("Cancelled Manufacturing Orders"), manufacturing_domains["cancelled"]),
            "manufacturing_delayed": (_("Delayed Manufacturing Orders"), manufacturing_domains["delayed"]),
            "manufacturing_missing_materials": (_("Manufacturing Orders Blocked Due to Missing Materials"), manufacturing_domains["missing_materials"]),
            "manufacturing_avg_progress": (_("Manufacturing Orders"), manufacturing_domains["total"]),
            "manufacturing_qty_to_produce": (_("Manufacturing Orders"), manufacturing_domains["total"]),
            "manufacturing_qty_produced": (_("Manufacturing Orders"), manufacturing_domains["total"]),
            "manufacturing_qty_remaining": (_("Manufacturing Orders"), manufacturing_domains["total"]),
            "manufacturing_delivery_commitment": (_("Done Manufacturing Orders"), manufacturing_domains["done"]),
        }
        workorder_actions = {
            "work_orders_in_progress": (_("Work Orders In Progress"), workorder_domains["in_progress"]),
            "work_orders_delayed": (_("Delayed Work Orders"), workorder_domains["delayed"]),
            "workcenter_work_orders_in_progress": (_("Work Orders In Progress"), workorder_domains["in_progress"]),
            "workcenter_done_work_orders": (_("Done Work Orders"), workorder_domains["done"]),
            "workcenter_delayed_work_orders": (_("Delayed Work Orders"), workorder_domains["delayed"]),
            "workcenter_avg_efficiency": (_("Done Work Orders"), workorder_domains["done"]),
        }
        if action_key in production_actions:
            name, domain = production_actions[action_key]
            return self._window_action(name, "mrp.production", domain)
        if action_key in workorder_actions:
            name, domain = workorder_actions[action_key]
            return self._window_action(name, "mrp.workorder", domain)
        if action_key == "workcenters_total":
            return self._window_action(_("Total Work Centers"), "mrp.workcenter", self._workcenter_domain(filters))
        if action_key == "workcenters_active":
            return self._window_action(_("Active Work Centers"), "mrp.workcenter", self._workcenter_domain(filters) + [("active", "=", True)])
        if action_key in ("manufacturing_order_row", "manufacturing_shortage_mo"):
            return self._open_record_action("mrp.production", extra.get("mo_id"), _("Manufacturing Order"))
        if action_key == "manufacturing_shortage_product":
            return self._open_record_action("product.product", extra.get("product_id"), _("Product"))
        if action_key in ("workcenter_row", "chart_workcenter_efficiency"):
            return self._open_record_action("mrp.workcenter", extra.get("workcenter_id"), _("Work Center"))
        if action_key == "chart_mrp_orders_state":
            state = extra.get("state") or False
            domain = self._manufacturing_base_domain(filters) + [("state", "=", state)]
            return self._window_action(_("Manufacturing Orders by State"), "mrp.production", domain)
        if action_key == "chart_mrp_product_qty":
            product_id = self._parse_int(extra.get("product_id"))
            domain = self._manufacturing_base_domain(filters) + [("product_id", "=", product_id or False)]
            return self._window_action(_("Production Quantity by Product"), "mrp.production", domain)
        if action_key == "chart_mrp_delayed_responsible":
            user_id = self._parse_int(extra.get("user_id"))
            domain = manufacturing_domains["delayed"] + [("user_id", "=", user_id or False)]
            return self._window_action(_("Delayed Manufacturing Orders by Responsible"), "mrp.production", domain)
        if action_key == "chart_monthly_production_trend":
            domain = (
                self._manufacturing_base_domain(filters, include_date=False)
                + [("state", "=", "done")]
                + self._extra_date_domain("date_finished", extra)
            )
            return self._window_action(_("Monthly Production Trend"), "mrp.production", domain)
        return False

    def _get_maintenance_action(self, action_key, filters, extra):
        maintenance_domains = self._maintenance_domains(filters)
        request_actions = {
            "total_maintenance_requests": (_("Total Maintenance Requests"), maintenance_domains["total"]),
            "maintenance_scheduled": (_("Scheduled Maintenance Requests"), maintenance_domains["scheduled"]),
            "maintenance_delayed": (_("Delayed Maintenance Requests"), maintenance_domains["delayed"]),
            "maintenance_in_progress": (_("In Progress Maintenance Requests"), maintenance_domains["in_progress"]),
            "maintenance_done": (_("Done Maintenance Requests"), maintenance_domains["done"]),
            "maintenance_breakdowns": (_("Current Breakdown Requests"), maintenance_domains["breakdowns"]),
            "maintenance_mttr": (_("Done Maintenance Requests"), maintenance_domains["done"]),
            "maintenance_downtime_rate": (_("Maintenance Requests"), maintenance_domains["total"]),
            "maintenance_preventive": (_("Preventive Maintenance Requests"), maintenance_domains["preventive"]),
            "maintenance_corrective": (_("Corrective Maintenance Requests"), maintenance_domains["corrective"]),
        }
        if action_key in request_actions:
            name, domain = request_actions[action_key]
            return self._window_action(name, "maintenance.request", domain)
        if action_key == "maintenance_total_equipment":
            return self._window_action(_("Total Equipment"), "maintenance.equipment", self._equipment_domain(filters))
        if action_key == "maintenance_equipment_open":
            equipment_ids = self._equipment_with_open_maintenance_ids(filters)
            return self._window_action(
                _("Equipment With Open Maintenance"),
                "maintenance.equipment",
                [("id", "in", equipment_ids)] if equipment_ids else [("id", "=", 0)],
            )
        if action_key == "maintenance_request_row":
            return self._open_record_action("maintenance.request", extra.get("request_id"), _("Maintenance Request"))
        if action_key == "equipment_row":
            return self._open_record_action("maintenance.equipment", extra.get("equipment_id"), _("Equipment"))
        if action_key == "chart_maintenance_stage":
            stage_id = self._parse_int(extra.get("stage_id"))
            domain = self._maintenance_request_base_domain(filters) + [("stage_id", "=", stage_id or False)]
            return self._window_action(_("Maintenance Requests by Stage"), "maintenance.request", domain)
        if action_key == "chart_maintenance_team":
            team_id = self._parse_int(extra.get("team_id"))
            domain = self._maintenance_request_base_domain(filters) + [("maintenance_team_id", "=", team_id or False)]
            return self._window_action(_("Maintenance Requests by Team"), "maintenance.request", domain)
        if action_key == "chart_delayed_maintenance_equipment":
            equipment_id = self._parse_int(extra.get("equipment_id"))
            domain = maintenance_domains["delayed"] + [("equipment_id", "=", equipment_id or False)]
            return self._window_action(_("Delayed Maintenance by Equipment"), "maintenance.request", domain)
        if action_key == "chart_downtime_equipment":
            equipment_id = self._parse_int(extra.get("equipment_id"))
            if equipment_id:
                return self._open_record_action("maintenance.equipment", equipment_id, _("Equipment"))
            return self._window_action(_("Downtime by Equipment"), "maintenance.equipment", self._equipment_domain(filters))
        if action_key == "chart_maintenance_monthly_trend":
            domain = (
                self._maintenance_request_base_domain(filters, include_date=False)
                + self._date_range_domain(
                    "request_date",
                    self._parse_date(extra.get("date_from")),
                    self._parse_date(extra.get("date_to")),
                )
            )
            return self._window_action(_("Maintenance Monthly Trend"), "maintenance.request", domain)
        return False

    def _get_hr_action(self, action_key, filters, extra):
        if not action_key or not action_key.startswith(("hr_", "chart_hr_")):
            return False
        if action_key in ("hr_total_employees", "hr_average_attendance_rate"):
            return self._safe_window_action(_("Employees"), "hr.employee", self._hr_employee_domain(filters), context={"active_test": False})
        if action_key == "hr_active_employees":
            return self._safe_window_action(_("Active Employees"), "hr.employee", self._hr_employee_domain(filters) + [("active", "=", True)])
        if action_key == "hr_inactive_employees":
            return self._safe_window_action(_("Inactive Employees"), "hr.employee", self._hr_employee_domain(filters) + [("active", "=", False)], context={"active_test": False})
        if action_key == "hr_new_employees":
            return self._safe_window_action(_("New Employees"), "hr.employee", self._hr_employee_new_domain(filters), context={"active_test": False})
        if action_key == "hr_present_today":
            return self._safe_window_action(_("Present Today"), "hr.attendance", self._hr_attendance_domain(filters, today=True))
        if action_key == "hr_absent_today":
            present_ids = self._hr_present_employee_ids_today(filters)
            domain = self._hr_employee_domain(filters) + [("active", "=", True)]
            if present_ids:
                domain.append(("id", "not in", present_ids))
            return self._safe_window_action(_("Absent Today"), "hr.employee", domain)
        if action_key == "hr_late_today":
            late_ids = self._hr_late_employee_ids_today(filters)
            return self._safe_window_action(
                _("Late Employees Today"),
                "hr.employee",
                [("id", "in", late_ids)] if late_ids else [("id", "=", 0)],
            )
        if action_key in (
            "hr_total_leaves",
            "hr_approved_leaves",
            "hr_pending_leaves",
            "hr_refused_leaves",
            "hr_current_leave",
        ):
            leave_domains = self._hr_leave_domains(filters)
            keys = {
                "hr_total_leaves": (_("Leave Requests"), "total"),
                "hr_approved_leaves": (_("Approved Leaves"), "approved"),
                "hr_pending_leaves": (_("Pending Leaves"), "pending"),
                "hr_refused_leaves": (_("Refused Leaves"), "refused"),
                "hr_current_leave": (_("Employees Currently on Leave"), "current"),
            }
            name, domain_key = keys[action_key]
            return self._safe_window_action(name, "hr.leave", leave_domains[domain_key])
        if action_key in ("hr_contracts_expiring", "hr_expired_contracts"):
            contract_domains = self._hr_contract_domains(filters)
            name = _("Contracts Expiring Soon") if action_key == "hr_contracts_expiring" else _("Expired Contracts")
            domain_key = "expiring" if action_key == "hr_contracts_expiring" else "expired"
            return self._safe_window_action(name, "hr.contract", contract_domains[domain_key])
        if action_key == "hr_open_appraisals":
            return self._safe_window_action(_("Open Appraisals"), "hr.appraisal", self._hr_appraisal_domain(filters))
        if action_key == "hr_employee_row":
            return self._open_record_action("hr.employee", extra.get("employee_id"), _("Employee"))
        if action_key == "hr_leave_row":
            return self._open_record_action("hr.leave", extra.get("leave_id"), _("Leave Request"))
        if action_key == "hr_contract_row":
            return self._open_record_action("hr.contract", extra.get("contract_id"), _("Contract"))
        if action_key == "chart_hr_department":
            department_id = self._parse_int(extra.get("department_id"))
            domain = self._hr_employee_domain(filters) + [("department_id", "=", department_id or False)]
            return self._safe_window_action(_("Employees by Department"), "hr.employee", domain, context={"active_test": False})
        if action_key == "chart_hr_attendance_status":
            segment = extra.get("segment")
            if segment == "present":
                return self._safe_window_action(_("Present Today"), "hr.attendance", self._hr_attendance_domain(filters, today=True))
            if segment == "late":
                late_ids = self._hr_late_employee_ids_today(filters)
                return self._safe_window_action(
                    _("Late Employees Today"),
                    "hr.employee",
                    [("id", "in", late_ids)] if late_ids else [("id", "=", 0)],
                )
            present_ids = self._hr_present_employee_ids_today(filters)
            domain = self._hr_employee_domain(filters) + [("active", "=", True)]
            if present_ids:
                domain.append(("id", "not in", present_ids))
            return self._safe_window_action(_("Absent Today"), "hr.employee", domain)
        if action_key == "chart_hr_leave_type":
            leave_type_id = self._parse_int(extra.get("leave_type_id"))
            return self._safe_window_action(
                _("Leaves by Type"),
                "hr.leave",
                self._hr_leave_domains(filters)["total"] + [("holiday_status_id", "=", leave_type_id or False)],
            )
        if action_key == "chart_hr_monthly_new_employees":
            domain = self._hr_employee_domain(filters, include_date=False)
            domain += self._extra_date_domain("create_date", extra)
            return self._safe_window_action(_("Monthly New Employees"), "hr.employee", domain, context={"active_test": False})
        if action_key == "chart_hr_leave_status":
            state = extra.get("state") or False
            return self._safe_window_action(
                _("Leave Requests by Status"),
                "hr.leave",
                self._hr_leave_domains(filters)["total"] + [("state", "=", state)],
            )
        if action_key == "chart_hr_job":
            job_id = self._parse_int(extra.get("job_id"))
            return self._safe_window_action(
                _("Employees by Job Position"),
                "hr.employee",
                self._hr_employee_domain(filters) + [("job_id", "=", job_id or False)],
                context={"active_test": False},
            )
        return False

    def _get_helpdesk_action(self, action_key, filters, extra):
        if not action_key or not action_key.startswith(("helpdesk_", "chart_helpdesk_")):
            return False
        domains = self._helpdesk_domains(filters)
        ticket_actions = {
            "helpdesk_total_tickets": (_("Total Tickets"), domains["total"]),
            "helpdesk_open_tickets": (_("Open Tickets"), domains["open"]),
            "helpdesk_closed_tickets": (_("Closed Tickets"), domains["closed"]),
            "helpdesk_delayed_tickets": (_("Delayed Tickets"), domains["delayed"]),
            "helpdesk_installation_tickets": (_("Installation Tickets"), self._helpdesk_ticket_keyword_domain(filters, ["installation", "install"])),
            "helpdesk_technical_tickets": (_("Technical Support Tickets"), self._helpdesk_ticket_keyword_domain(filters, ["technical", "support"])),
            "helpdesk_sales_support_tickets": (_("Sales Support Tickets"), self._helpdesk_ticket_keyword_domain(filters, ["sales"])),
            "helpdesk_sla_breached": (_("SLA Breached Tickets"), self._helpdesk_sla_breached_domain(filters)),
            "helpdesk_avg_resolution_time": (_("Closed Tickets"), domains["closed"]),
            "helpdesk_avg_first_response_time": (_("Tickets"), domains["total"]),
            "helpdesk_stage_count": (_("Tickets by Stage"), domains["total"]),
            "helpdesk_team_count": (_("Tickets by Team"), domains["total"]),
            "helpdesk_responsible_count": (_("Tickets by Responsible"), domains["total"]),
        }
        if action_key in ticket_actions:
            name, domain = ticket_actions[action_key]
            return self._safe_window_action(name, "helpdesk.ticket", domain)
        if action_key == "helpdesk_ticket_row":
            return self._open_record_action("helpdesk.ticket", extra.get("ticket_id"), _("Helpdesk Ticket"))
        if action_key == "helpdesk_team_row":
            return self._open_record_action("helpdesk.team", extra.get("team_id"), _("Helpdesk Team"))
        if action_key == "chart_helpdesk_stage":
            stage_id = self._parse_int(extra.get("stage_id"))
            return self._safe_window_action(
                _("Tickets by Stage"),
                "helpdesk.ticket",
                self._helpdesk_ticket_base_domain(filters) + [("stage_id", "=", stage_id or False)],
            )
        if action_key in ("chart_helpdesk_team", "chart_helpdesk_delayed_team"):
            team_id = self._parse_int(extra.get("team_id"))
            base = domains["delayed"] if action_key == "chart_helpdesk_delayed_team" else self._helpdesk_ticket_base_domain(filters)
            return self._safe_window_action(
                _("Tickets by Team"),
                "helpdesk.ticket",
                base + [("team_id", "=", team_id or False)],
            )
        if action_key == "chart_helpdesk_user":
            user_id = self._parse_int(extra.get("user_id"))
            return self._safe_window_action(
                _("Tickets by Assigned User"),
                "helpdesk.ticket",
                self._helpdesk_ticket_base_domain(filters) + [("user_id", "=", user_id or False)],
            )
        if action_key == "chart_helpdesk_monthly_tickets":
            return self._safe_window_action(
                _("Monthly Tickets"),
                "helpdesk.ticket",
                self._helpdesk_ticket_base_domain(filters, include_date=False)
                + self._extra_date_domain("create_date", extra),
            )
        if action_key == "chart_helpdesk_priority":
            priority = extra.get("priority") or False
            return self._safe_window_action(
                _("Tickets by Priority"),
                "helpdesk.ticket",
                self._helpdesk_ticket_base_domain(filters) + [("priority", "=", priority)],
            )
        return False

    def _get_pos_action(self, action_key, filters, extra):
        if not action_key or not action_key.startswith(("pos_", "chart_pos_")):
            return False
        order_domain = self._pos_order_domain(filters)
        session_domains = self._pos_session_domains(filters) if self._can_read_model("pos.session") else {}
        order_actions = {
            "pos_total_orders": (_("Total POS Orders"), order_domain),
            "pos_total_revenue": (_("Total POS Revenue"), order_domain),
            "pos_average_order_value": (_("POS Orders"), order_domain),
            "pos_total_invoices": (_("POS Invoices"), order_domain + [("account_move", "!=", False)]),
            "pos_refund_amount": (_("POS Refund Orders"), self._pos_refund_order_domain(filters)),
            "pos_refund_orders": (_("POS Refund Orders"), self._pos_refund_order_domain(filters)),
        }
        if action_key in order_actions:
            name, domain = order_actions[action_key]
            return self._safe_window_action(name, "pos.order", domain)
        session_actions = {
            "pos_open_sessions": (_("Open POS Sessions"), session_domains.get("open", [("id", "=", 0)])),
            "pos_closed_sessions": (_("Closed POS Sessions"), session_domains.get("closed", [("id", "=", 0)])),
            "pos_active_sessions_today": (_("Active Sessions Today"), session_domains.get("active_today", [("id", "=", 0)])),
        }
        if action_key in session_actions:
            name, domain = session_actions[action_key]
            return self._safe_window_action(name, "pos.session", domain)
        payment_actions = {
            "pos_cash_payments": (_("Cash Payments"), self._pos_payment_domain(filters) + [("payment_method_id.is_cash_count", "=", True)]),
            "pos_card_payments": (_("Card Payments"), self._pos_payment_domain(filters) + [("payment_method_id.journal_id.type", "=", "bank")]),
            "pos_other_payments": (_("Other Payment Methods"), self._pos_other_payment_domain(filters)),
        }
        if action_key in payment_actions:
            name, domain = payment_actions[action_key]
            return self._safe_window_action(name, "pos.payment", domain)
        if action_key == "pos_best_branch":
            best = self._pos_best_group(filters, "config_id")
            return self._safe_window_action(_("Best POS / Branch"), "pos.order", order_domain + [("config_id", "=", best["id"] or False)])
        if action_key == "pos_best_cashier":
            best = self._pos_best_group(filters, "user_id")
            return self._safe_window_action(_("Best Cashier"), "pos.order", order_domain + [("user_id", "=", best["id"] or False)])
        if action_key == "pos_top_product":
            top = self._pos_top_product(filters)
            return self._safe_window_action(_("Top POS Product Orders"), "pos.order", order_domain + [("lines.product_id", "=", top["id"] or False)])
        if action_key == "pos_session_row":
            return self._open_record_action("pos.session", extra.get("session_id"), _("POS Session"))
        if action_key == "pos_order_row":
            return self._open_record_action("pos.order", extra.get("order_id"), _("POS Order"))
        if action_key == "pos_product_row":
            return self._open_record_action("product.product", extra.get("product_id"), _("Product"))
        if action_key == "chart_pos_revenue_trend":
            return self._safe_window_action(_("POS Revenue Trend"), "pos.order", self._pos_order_domain(filters, include_date=False) + self._extra_date_domain("date_order", extra))
        if action_key == "chart_pos_branch":
            config_id = self._parse_int(extra.get("config_id"))
            return self._safe_window_action(_("Sales by POS / Branch"), "pos.order", order_domain + [("config_id", "=", config_id or False)])
        if action_key == "chart_pos_cashier":
            user_id = self._parse_int(extra.get("user_id"))
            return self._safe_window_action(_("Sales by Cashier"), "pos.order", order_domain + [("user_id", "=", user_id or False)])
        if action_key == "chart_pos_payment_method":
            payment_method_id = self._parse_int(extra.get("payment_method_id"))
            return self._safe_window_action(_("Sales by Payment Method"), "pos.payment", self._pos_payment_domain(filters) + [("payment_method_id", "=", payment_method_id or False)])
        if action_key == "chart_pos_top_product":
            product_id = self._parse_int(extra.get("product_id"))
            return self._safe_window_action(_("Top POS Product"), "pos.order", order_domain + [("lines.product_id", "=", product_id or False)])
        if action_key == "chart_pos_refund_trend":
            return self._safe_window_action(_("Refund Trend"), "pos.order", self._pos_refund_order_domain(filters, include_date=False) + self._extra_date_domain("date_order", extra))
        return False

    def _get_website_action(self, action_key, filters, extra):
        if not action_key or not action_key.startswith(("website_", "chart_website_", "chart_online_")):
            return False
        domains = self._website_order_domains(filters) if self._has_field("sale.order", "website_id") else {}
        order_actions = {
            "website_orders_count": (_("Website Orders"), domains.get("total", [("id", "=", 0)])),
            "website_revenue": (_("Website Revenue"), domains.get("confirmed", [("id", "=", 0)])),
            "website_average_order_value": (_("Website Orders"), domains.get("confirmed", [("id", "=", 0)])),
            "website_confirmed_orders": (_("Confirmed Website Orders"), domains.get("confirmed", [("id", "=", 0)])),
            "website_cancelled_orders": (_("Cancelled Website Orders"), domains.get("cancelled", [("id", "=", 0)])),
            "website_pending_orders": (_("Pending Website Orders"), domains.get("pending", [("id", "=", 0)])),
            "website_draft_carts": (_("Draft Website Orders / Carts"), domains.get("draft", [("id", "=", 0)])),
            "website_abandoned_carts": (_("Abandoned Carts"), domains.get("abandoned", [("id", "=", 0)])),
            "website_conversion_rate": (_("Website Orders"), domains.get("total", [("id", "=", 0)])),
        }
        if action_key in order_actions:
            name, domain = order_actions[action_key]
            return self._safe_window_action(name, "sale.order", domain)
        if action_key in ("website_registered_customers", "website_new_customers"):
            partner_ids = self._website_customer_ids(filters, selected_period=action_key == "website_new_customers")
            return self._safe_window_action(_("Website Customers"), "res.partner", [("id", "in", partner_ids)] if partner_ids else [("id", "=", 0)])
        if action_key in ("website_top_product", "website_most_ordered_product"):
            product = self._website_top_product(filters, metric="quantity" if action_key == "website_most_ordered_product" else "revenue")
            return self._open_record_action("product.product", product["id"], _("Online Product"))
        if action_key == "website_order_row":
            return self._open_record_action("sale.order", extra.get("order_id"), _("Website Order"))
        if action_key == "website_product_row":
            return self._open_record_action("product.product", extra.get("product_id"), _("Online Product"))
        if action_key == "website_customer_row":
            return self._open_record_action("res.partner", extra.get("partner_id"), _("Website Customer"))
        if action_key == "chart_website_revenue_trend":
            return self._safe_window_action(_("Website Revenue Trend"), "sale.order", self._website_order_domains(filters, include_date=False)["confirmed"] + self._extra_date_domain("date_order", extra))
        if action_key == "chart_website_orders_by_website":
            website_id = self._parse_int(extra.get("website_id"))
            return self._safe_window_action(_("Orders by Website"), "sale.order", domains.get("total", []) + [("website_id", "=", website_id or False)])
        if action_key == "chart_website_orders_state":
            state = extra.get("state") or False
            return self._safe_window_action(_("Website Orders by State"), "sale.order", domains.get("total", []) + [("state", "=", state)])
        if action_key == "chart_website_top_product":
            product_id = self._parse_int(extra.get("product_id"))
            return self._safe_window_action(_("Top Online Product"), "sale.order", domains.get("confirmed", []) + [("order_line.product_id", "=", product_id or False)])
        if action_key == "chart_website_customer_growth":
            partner_ids = self._website_customer_ids(filters)
            return self._safe_window_action(_("Online Customers Growth"), "res.partner", [("id", "in", partner_ids)] if partner_ids else [("id", "=", 0)])
        if action_key == "chart_online_vs_pos_revenue":
            segment = extra.get("segment")
            if segment == "pos":
                return self._safe_window_action(_("POS Revenue"), "pos.order", self._pos_order_domain(filters))
            return self._safe_window_action(_("Online Revenue"), "sale.order", domains.get("confirmed", [("id", "=", 0)]))
        return False

    def _low_stock_action_domain(self, filters):
        product_ids = self._below_reordering_product_ids(filters)
        if product_ids:
            return [("id", "in", product_ids)]
        return self._stockable_product_domain(filters) + [("virtual_available", "<=", 0)]

    def _open_record_action(self, model_name, record_id, name):
        record_id = self._parse_int(record_id)
        if not model_name or not record_id:
            return False
        try:
            self.env[model_name]
        except KeyError:
            return False
        action = self._window_action(
            name,
            model_name,
            [("id", "=", record_id)],
            views=[[False, "form"]],
        )
        action["view_mode"] = "form"
        action["res_id"] = record_id
        return action

    def _chart_inventory_status_action(self, filters, extra):
        segment = extra.get("segment")
        if segment == "out":
            domain = self._stockable_product_domain(filters) + [("qty_available", "<=", 0)]
        elif segment == "low":
            domain = self._low_stock_action_domain(filters)
        else:
            domain = self._stockable_product_domain(filters) + [("qty_available", ">", 0)]
        return self._window_action(_("Inventory Status"), "product.product", domain)

    def _chart_monthly_purchase_action(self, filters, extra):
        domain = (
            self._purchase_base_domain(filters, include_date=False)
            + [("state", "in", self._purchase_order_states())]
            + self._extra_date_domain("date_order", extra)
        )
        return self._window_action(_("Monthly Purchase Amount"), "purchase.order", domain)

    def _chart_top_vendor_purchase_action(self, filters, extra):
        vendor_id = self._parse_int(extra.get("vendor_id"))
        vendor_filters = filters.copy()
        vendor_filters["vendor_id"] = vendor_id
        return self._window_action(
            _("Top Vendors by Purchase Amount"),
            "purchase.order",
            self._purchase_domains(vendor_filters)["total_purchase_orders"],
        )

    def _chart_delayed_receipts_vendor_action(self, filters, extra):
        vendor_id = self._parse_int(extra.get("vendor_id"))
        vendor_filters = filters.copy()
        vendor_filters["vendor_id"] = vendor_id
        return self._window_action(
            _("Delayed Receipts by Vendor"),
            "purchase.order",
            self._purchase_domains(vendor_filters)["delayed_purchase_orders"],
        )

    def _extra_date_domain(self, field_name, extra):
        return self._datetime_range_domain(
            field_name,
            self._parse_date(extra.get("date_from")),
            self._parse_date(extra.get("date_to")),
        )

    # -------------------------------------------------------------------------
    # Aggregation helpers
    # -------------------------------------------------------------------------

    def _manufacturing_progress(self, production):
        if not production.product_qty:
            return 0
        return round(min((production.qty_produced / production.product_qty) * 100, 100), 1)

    def _manufacturing_quantity_summary(self, filters):
        Production = self.env["mrp.production"]
        domain = self._manufacturing_domains(filters)["total"]
        qty_to_produce = self._sum(Production, domain, "product_qty")
        count = Production.search_count(domain)
        # mrp.production.qty_produced is computed and not read_group-safe in
        # Odoo 19. Keep the dashboard bounded instead of loading an unlimited
        # production history for every refresh.
        sample = Production.search(domain, limit=2000, order="date_start desc, id desc")
        produced_qty = sum(sample.mapped("qty_produced"))
        progress_values = [self._manufacturing_progress(production) for production in sample if production.product_qty]
        average_progress = round(sum(progress_values) / len(progress_values), 1) if progress_values else 0
        if count > len(sample):
            # Conservative fallback for large datasets: to-produce remains exact
            # through read_group; produced/remaining/progress reflect the bounded
            # recent sample to avoid heavy computed-field loops.
            qty_remaining = max(qty_to_produce - produced_qty, 0)
        else:
            qty_remaining = sum(max(production.product_qty - production.qty_produced, 0) for production in sample)
        return {
            "qty_to_produce": qty_to_produce,
            "qty_produced": produced_qty,
            "qty_remaining": qty_remaining,
            "average_progress": average_progress,
        }

    def _manufacturing_delivery_commitment(self, filters):
        Production = self.env["mrp.production"]
        domain = self._manufacturing_domains(filters)["done"] + [
            ("date_deadline", "!=", False),
            ("date_finished", "!=", False),
        ]
        count = Production.search_count(domain)
        if not count:
            return 0
        # Odoo domains do not safely compare date_finished to date_deadline as
        # two fields. The bounded scan keeps this KPI conservative and prevents
        # large computed-field loops on busy manufacturing databases.
        productions = Production.search(domain, limit=2000, order="date_finished desc, id desc")
        on_time = sum(1 for production in productions if production.date_finished <= production.date_deadline)
        measured = len(productions)
        return round((on_time / measured) * 100, 1) if measured else 0

    def _workorder_efficiency(self, domain):
        result = self.env["mrp.workorder"].read_group(
            domain,
            ["duration_expected:sum", "duration:sum"],
            [],
        )
        if not result:
            return 0
        expected = result[0].get("duration_expected", 0) or result[0].get("duration_expected_sum", 0) or 0
        real = result[0].get("duration", 0) or result[0].get("duration_sum", 0) or 0
        return round((expected / real) * 100, 1) if real else 0

    def _equipment_with_open_maintenance_ids(self, filters):
        groups = self.env["maintenance.request"].read_group(
            self._maintenance_domains(filters)["in_progress"] + [("equipment_id", "!=", False)],
            ["equipment_id"],
            ["equipment_id"],
            lazy=False,
        )
        return [group["equipment_id"][0] for group in groups if group.get("equipment_id")]

    def _maintenance_mttr(self, filters):
        Request = self.env["maintenance.request"]
        domain = self._maintenance_domains(filters)["done"] + [
            ("close_date", "!=", False),
        ]
        # close_date/request_date are date fields in Odoo 19 maintenance; the
        # default module exposes MTTR in days, not hours.
        requests = Request.search(domain, limit=2000, order="close_date desc, id desc")
        durations = []
        for request in requests:
            start = request.request_date or request.create_date.date()
            if not start or not request.close_date:
                continue
            durations.append(max((request.close_date - start).days, 0))
        return round(sum(durations) / len(durations), 1) if durations else 0

    def _maintenance_downtime_rate(self, filters):
        # Odoo 19's default maintenance app does not include a stored downtime
        # duration or planned production availability denominator. Returning 0
        # is safer than inferring downtime from scheduled maintenance duration.
        return 0

    def _hr_present_employee_ids_today(self, filters):
        return self._hr_today_attendance_info(filters)["present_ids"]

    def _hr_late_employee_ids_today(self, filters):
        info = self._hr_today_attendance_info(filters)
        return list(info["late_hours"])

    def _hr_today_attendance_info(self, filters, employee_ids=False):
        if not self._can_read_model("hr.attendance"):
            return {"present_ids": [], "late_hours": {}}
        domain = self._hr_attendance_domain(filters, today=True)
        if employee_ids:
            domain.append(("employee_id", "in", employee_ids))
        attendances = self.env["hr.attendance"].search(
            domain,
            limit=5000,
            order="employee_id, check_in",
        )
        present_ids = []
        late_hours = {}
        seen = set()
        for attendance in attendances:
            employee = attendance.employee_id
            if not employee or employee.id in seen:
                continue
            seen.add(employee.id)
            present_ids.append(employee.id)
            # Default HR attendance has no stored "late" flag. Use the first
            # check-in after 09:00 local time as a conservative operational signal.
            if attendance.check_in:
                local_check_in = fields.Datetime.context_timestamp(attendance, attendance.check_in)
                late = max(local_check_in.hour + (local_check_in.minute / 60.0) - 9.0, 0)
                if late:
                    late_hours[employee.id] = round(late, 2)
        return {"present_ids": present_ids, "late_hours": late_hours}

    def _hr_current_leave_employee_ids(self, filters):
        if not self._can_read_model("hr.leave"):
            return []
        groups = self.env["hr.leave"].read_group(
            self._hr_leave_domains(filters)["current"] + [("employee_id", "!=", False)],
            ["employee_id"],
            ["employee_id"],
            lazy=False,
        )
        return [group["employee_id"][0] for group in groups if group.get("employee_id")]

    def _hr_open_appraisal_count(self, filters):
        if not self._can_read_model("hr.appraisal"):
            return 0
        return self.env["hr.appraisal"].search_count(self._hr_appraisal_domain(filters))

    def _hr_appraisal_domain(self, filters):
        domain = []
        if self._has_field("hr.appraisal", "employee_id"):
            domain.append(("employee_id.company_id", "in", filters["company_ids"]))
            if filters.get("hr_employee_id"):
                domain.append(("employee_id", "=", filters["hr_employee_id"]))
            if filters.get("hr_department_id"):
                domain.append(("employee_id.department_id", "child_of", filters["hr_department_id"]))
            if filters.get("hr_manager_id"):
                domain.append(("employee_id.parent_id", "=", filters["hr_manager_id"]))
            if filters.get("hr_job_id"):
                domain.append(("employee_id.job_id", "=", filters["hr_job_id"]))
        if self._has_field("hr.appraisal", "date_close"):
            domain += self._date_range_domain("date_close", filters["date_from"], filters["date_to"])
        states = self._selection_values("hr.appraisal", "state")
        if "done" in states:
            domain.append(("state", "!=", "done"))
        return domain

    def _hr_contract_start_field(self):
        for field_name in ("date_start", "contract_date_start"):
            if self._has_field("hr.contract", field_name):
                return field_name
        return False

    def _hr_contract_end_field(self):
        for field_name in ("date_end", "contract_date_end"):
            if self._has_field("hr.contract", field_name):
                return field_name
        return False

    def _pos_best_group(self, filters, group_field):
        if not self._can_read_model("pos.order") or not self._has_field("pos.order", group_field):
            return {"id": False, "name": "", "value": 0}
        groups = self.env["pos.order"].read_group(
            self._pos_order_domain(filters),
            ["amount_total:sum"],
            [group_field],
            lazy=False,
        )
        groups = [group for group in groups if group.get(group_field)]
        if not groups:
            return {"id": False, "name": "", "value": 0}
        group = max(groups, key=lambda item: item.get("amount_total", 0) or item.get("amount_total_sum", 0) or 0)
        value = group.get("amount_total", 0) or group.get("amount_total_sum", 0) or 0
        return {"id": group[group_field][0], "name": group[group_field][1], "value": value}

    def _pos_top_product(self, filters):
        if not self._can_read_model("pos.order.line"):
            return {"id": False, "name": "", "quantity": 0, "value": 0}
        groups = self.env["pos.order.line"].read_group(
            self._pos_line_domain(filters) + [("qty", ">", 0)],
            ["qty:sum", "price_subtotal_incl:sum"],
            ["product_id"],
            lazy=False,
        )
        groups = [group for group in groups if group.get("product_id")]
        if not groups:
            return {"id": False, "name": "", "quantity": 0, "value": 0}
        group = max(groups, key=lambda item: item.get("qty", 0) or item.get("qty_sum", 0) or 0)
        return {
            "id": group["product_id"][0],
            "name": group["product_id"][1],
            "quantity": group.get("qty", 0) or group.get("qty_sum", 0) or 0,
            "value": group.get("price_subtotal_incl", 0) or group.get("price_subtotal_incl_sum", 0) or 0,
        }

    def _pos_other_payment_amount(self, filters):
        if not self._can_read_model("pos.payment"):
            return 0
        return self._sum(self.env["pos.payment"], self._pos_other_payment_domain(filters), "amount")

    def _pos_other_payment_domain(self, filters):
        if not self._can_read_model("pos.payment.method"):
            return self._pos_payment_domain(filters) + [("id", "=", 0)]
        method_domain = []
        if self._has_field("pos.payment.method", "company_id"):
            method_domain.append(("company_id", "in", filters["company_ids"]))
        methods = self.env["pos.payment.method"].search(method_domain)
        other_method_ids = [
            method.id
            for method in methods
            if not method.is_cash_count and method.journal_id.type != "bank"
        ]
        return self._pos_payment_domain(filters) + (
            [("payment_method_id", "in", other_method_ids)]
            if other_method_ids
            else [("id", "=", 0)]
        )

    def _pos_line_distinct_order_count(self, filters, product_id):
        if not self._can_read_model("pos.order.line"):
            return 0
        groups = self.env["pos.order.line"].read_group(
            self._pos_line_domain(filters) + [("product_id", "=", product_id), ("order_id", "!=", False)],
            ["order_id"],
            ["order_id"],
            lazy=False,
        )
        return len([group for group in groups if group.get("order_id")])

    def _website_top_product(self, filters, metric="revenue"):
        if not self._has_field("sale.order", "website_id"):
            return {"id": False, "name": "", "quantity": 0, "value": 0}
        groups = self.env["sale.order.line"].read_group(
            self._website_line_domain(filters),
            ["product_uom_qty:sum", "price_total:sum"],
            ["product_id"],
            lazy=False,
        )
        groups = [group for group in groups if group.get("product_id")]
        if not groups:
            return {"id": False, "name": "", "quantity": 0, "value": 0}
        value_key = "product_uom_qty" if metric == "quantity" else "price_total"
        group = max(groups, key=lambda item: item.get(value_key, 0) or item.get(f"{value_key}_sum", 0) or 0)
        return {
            "id": group["product_id"][0],
            "name": group["product_id"][1],
            "quantity": group.get("product_uom_qty", 0) or group.get("product_uom_qty_sum", 0) or 0,
            "value": group.get("price_total", 0) or group.get("price_total_sum", 0) or 0,
        }

    def _website_line_distinct_order_count(self, filters, product_id):
        if not self._has_field("sale.order", "website_id"):
            return 0
        groups = self.env["sale.order.line"].read_group(
            self._website_line_domain(filters) + [("product_id", "=", product_id), ("order_id", "!=", False)],
            ["order_id"],
            ["order_id"],
            lazy=False,
        )
        return len([group for group in groups if group.get("order_id")])

    def _website_customer_ids(self, filters, selected_period=False):
        if not self._has_field("sale.order", "website_id"):
            return []
        domain = self._website_order_domains(filters, include_date=not selected_period)["confirmed"] + [("partner_id", "!=", False)]
        if selected_period:
            domain += self._datetime_range_domain("partner_id.create_date", filters["date_from"], filters["date_to"])
        groups = self.env["sale.order"].read_group(domain, ["partner_id"], ["partner_id"], lazy=False)
        return [group["partner_id"][0] for group in groups if group.get("partner_id")]

    def _avg(self, model, domain, field_name):
        result = model.read_group(domain, [f"{field_name}:avg"], [])
        if not result:
            return 0.0
        return (
            result[0].get(field_name)
            or result[0].get(f"{field_name}_avg")
            or 0.0
        )

    def _sum(self, model, domain, field_name):
        result = model.read_group(domain, [f"{field_name}:sum"], [])
        if not result:
            return 0.0
        return (
            result[0].get(field_name)
            or result[0].get(f"{field_name}_sum")
            or 0.0
        )

    def _sale_distinct_partner_count(self, domain):
        return len(self._sale_partner_ids(domain))

    def _sale_partner_ids(self, domain):
        groups = self.env["sale.order"].read_group(
            domain + [("partner_id", "!=", False)],
            ["partner_id"],
            ["partner_id"],
            lazy=False,
        )
        return [group["partner_id"][0] for group in groups if group.get("partner_id")]

    def _partner_ids_domain(self, partner_ids):
        return [("id", "in", partner_ids)] if partner_ids else [("id", "=", 0)]

    def _or_domain(self, conditions):
        conditions = [condition for condition in conditions if condition]
        if not conditions:
            return []
        if len(conditions) == 1:
            return conditions
        return ["|"] * (len(conditions) - 1) + conditions

    def _below_reordering_product_ids(self, filters):
        groups = self.env["stock.warehouse.orderpoint"].read_group(
            self._orderpoint_domain(filters) + [("qty_to_order", ">", 0)],
            ["product_id"],
            ["product_id"],
            lazy=False,
        )
        return [group["product_id"][0] for group in groups if group.get("product_id")]

    def _current_inventory_value(self, filters):
        if not self._can_read_inventory_value():
            return None
        Product = self.env["product.product"].with_context(**self._stock_context(filters))
        domain = self._stockable_product_domain(filters)
        product_count = Product.search_count(domain)
        if product_count > 2000:
            # product.total_value is computed, not a read_group-safe stored aggregate.
            # Avoid loading very large product sets for a dashboard KPI.
            return None
        return sum(Product.search(domain).mapped("total_value"))

    def _can_read_inventory_value(self):
        return self._has_field("product.product", "total_value") and self.env.user.has_group(
            "stock.group_stock_manager"
        )

    def _purchase_amount_field(self):
        return "amount_total_cc" if self._has_field("purchase.order", "amount_total_cc") else "amount_total"

    def _purchase_rfq_states(self):
        states = self._selection_values("purchase.order", "state")
        return [state for state in ["draft", "sent"] if state in states]

    def _purchase_order_states(self):
        states = self._selection_values("purchase.order", "state")
        confirmed = [state for state in ["purchase", "done"] if state in states]
        return confirmed or ["purchase"]

    def _most_used_vendor(self, filters):
        groups = self.env["purchase.order"].read_group(
            self._purchase_domains(filters)["total_purchase_orders"],
            ["partner_id"],
            ["partner_id"],
            lazy=False,
        )
        groups = [group for group in groups if group.get("partner_id")]
        if not groups:
            return {"id": False, "name": "", "count": 0}
        group = max(groups, key=lambda item: item.get("__count", 0))
        return {
            "id": group["partner_id"][0],
            "name": group["partner_id"][1],
            "count": group.get("__count", 0),
        }

    def _vendor_on_time_delivery(self, filters, vendor_id):
        vendor_filters = filters.copy()
        vendor_filters["vendor_id"] = vendor_id
        pickings = self.env["stock.picking"].search(
            self._purchase_receipt_picking_domain(vendor_filters, pending=False)
            + [("state", "=", "done")],
            limit=1000,
            order="date_done desc",
        )
        if not pickings:
            return 0
        on_time = 0
        measured = 0
        for picking in pickings:
            expected = (
                picking.date_deadline
                or picking.scheduled_date
                or (picking.purchase_id.date_planned if picking.purchase_id else False)
            )
            if not expected or not picking.date_done:
                continue
            measured += 1
            if self._datetime_to_user_date(picking, picking.date_done) <= self._datetime_to_user_date(picking, expected):
                on_time += 1
        return round((on_time / measured) * 100, 1) if measured else 0

    def _vendor_quantity_fulfillment(self, filters, vendor_id):
        if not self._has_field("purchase.order.line", "qty_received"):
            return 0
        result = self.env["purchase.order.line"].read_group(
            self._purchase_line_domain(filters, vendor_id=vendor_id),
            ["product_qty:sum", "qty_received:sum"],
            [],
        )
        if not result:
            return 0
        ordered_qty = result[0].get("product_qty", 0) or result[0].get("product_qty_sum", 0) or 0
        received_qty = result[0].get("qty_received", 0) or result[0].get("qty_received_sum", 0) or 0
        return round(min((received_qty / ordered_qty) * 100, 100), 1) if ordered_qty else 0

    def _vendor_average_delay(self, filters, vendor_id):
        vendor_filters = filters.copy()
        vendor_filters["vendor_id"] = vendor_id
        pickings = self.env["stock.picking"].search(
            self._purchase_receipt_picking_domain(vendor_filters, pending=False)
            + [("state", "=", "done")],
            limit=1000,
            order="date_done desc",
        )
        delays = []
        for picking in pickings:
            expected = (
                picking.date_deadline
                or picking.scheduled_date
                or (picking.purchase_id.date_planned if picking.purchase_id else False)
            )
            if not expected or not picking.date_done:
                continue
            delay = (
                self._datetime_to_user_date(picking, picking.date_done)
                - self._datetime_to_user_date(picking, expected)
            ).days
            delays.append(max(delay, 0))
        return round(sum(delays) / len(delays), 1) if delays else 0

    def _suggested_vendor_name(self, product, filters):
        sellers = product.product_tmpl_id.seller_ids.filtered(
            lambda seller: (
                (not seller.company_id or seller.company_id.id in filters["company_ids"])
                and (not seller.product_id or seller.product_id == product)
            )
        )
        if filters["vendor_id"]:
            sellers = sellers.filtered(lambda seller: seller.partner_id.id == filters["vendor_id"])
        seller = sellers[:1]
        return seller.partner_id.display_name if seller else ""

    def _month_periods(self, filters):
        today = fields.Date.context_today(self)
        end_month = (filters["date_to"] or today).replace(day=1)
        start_month = (filters["date_from"] or (end_month - relativedelta(months=11))).replace(day=1)
        periods = []
        current = start_month
        while current <= end_month:
            next_month = current + relativedelta(months=1)
            month_end = next_month - timedelta(days=1)
            periods.append(
                {
                    "label": current.strftime("%b %Y"),
                    "date_from": current,
                    "date_to": month_end,
                    "extra": {
                        "date_from": fields.Date.to_string(current),
                        "date_to": fields.Date.to_string(month_end),
                    },
                }
            )
            current = next_month
        return periods[-12:]

    # -------------------------------------------------------------------------
    # Field helpers
    # -------------------------------------------------------------------------

    def _has_model(self, model_name):
        try:
            self.env[model_name]
        except KeyError:
            return False
        return True

    def _can_read_model(self, model_name):
        if not self._has_model(model_name):
            return False
        try:
            return self.env[model_name].check_access_rights("read", raise_exception=False)
        except AccessError:
            return False

    def _has_field(self, model_name, field_name):
        return self._has_model(model_name) and field_name in self.env[model_name]._fields

    def _selection_values(self, model_name, field_name):
        if not self._has_field(model_name, field_name):
            return []
        field = self.env[model_name]._fields[field_name]
        return list(field.get_values(self.env))

    def _selection_labels(self, model_name, field_name):
        if not self._has_field(model_name, field_name):
            return {}
        return dict(self.env[model_name].fields_get([field_name])[field_name]["selection"])

    def _sale_quotation_states(self):
        states = self._selection_values("sale.order", "state")
        return [state for state in ["draft", "sent"] if state in states]

    def _sale_confirmed_states(self):
        states = self._selection_values("sale.order", "state")
        confirmed = [state for state in ["sale", "done"] if state in states]
        return confirmed or ["sale"]

    def _datetime_to_user_date(self, record, value):
        if not value:
            return False
        return fields.Datetime.context_timestamp(record, value).date()

    def _datetime_to_user_date_string(self, record, value):
        user_date = self._datetime_to_user_date(record, value)
        return fields.Date.to_string(user_date) if user_date else ""
