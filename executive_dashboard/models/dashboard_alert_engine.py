import logging
from datetime import datetime, time, timedelta
from string import Template

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


_logger = logging.getLogger(__name__)


class ExecutiveDashboardAlertEngine(models.AbstractModel):
    _name = "executive.dashboard.alert.engine"
    _description = "Executive Dashboard Smart Alert Engine"

    DASHBOARD_METHODS = {
        "overview": "get_overview_data",
        "sales": "get_sales_dashboard_data",
        "crm": "get_crm_dashboard_data",
        "inventory": "get_inventory_dashboard_data",
        "purchase": "get_purchase_dashboard_data",
        "manufacturing": "get_manufacturing_dashboard_data",
        "maintenance": "get_maintenance_dashboard_data",
        "hr": "get_hr_dashboard_data",
        "helpdesk": "get_helpdesk_dashboard_data",
        "pos": "get_pos_dashboard_data",
        "website": "get_website_dashboard_data",
        "alerts": "get_alerts_data",
    }

    @api.model
    def get_available_alert_metrics(self):
        return {
            "overview": {
                "label": _("Executive Overview"),
                "metrics": [
                    self._metric("overview_sales_revenue", _("Sales Revenue"), "amount"),
                    self._metric("overview_inventory_shortages", _("Inventory Shortage Alerts")),
                    self._metric("overview_delayed_sales_orders", _("Delayed Sales Orders")),
                    self._metric("overview_delayed_purchase_orders", _("Delayed Purchase Orders")),
                    self._metric("overview_critical_alerts", _("Critical Alerts")),
                ],
            },
            "sales": {
                "label": _("Sales Dashboard"),
                "metrics": [
                    self._metric("sales_revenue", _("Sales Revenue"), "amount"),
                    self._metric("total_sales_orders", _("Total Sales Orders")),
                    self._metric("delayed_sales_orders", _("Delayed Sales Orders")),
                    self._metric("total_quotations", _("Total Quotations")),
                    self._metric("delayed_quotations", _("Delayed Quotations")),
                ],
            },
            "crm": {
                "label": _("CRM Dashboard"),
                "metrics": [
                    self._metric("total_leads", _("Total Leads")),
                    self._metric("total_opportunities", _("Total Opportunities")),
                    self._metric("won_opportunities", _("Won Opportunities")),
                    self._metric("conversion_rate", _("Conversion Rate"), "percentage"),
                    self._metric("expected_revenue", _("Expected Revenue"), "amount"),
                ],
            },
            "inventory": {
                "label": _("Inventory Dashboard"),
                "metrics": [
                    self._metric("low_stock_products", _("Low Stock Products")),
                    self._metric("out_of_stock_products", _("Out of Stock Products")),
                    self._metric("pending_receipts", _("Pending Receipts")),
                    self._metric("delayed_deliveries", _("Delayed Deliveries")),
                ],
            },
            "purchase": {
                "label": _("Purchase Dashboard"),
                "metrics": [
                    self._metric("total_purchase_orders", _("Total Purchase Orders")),
                    self._metric("delayed_purchase_orders", _("Delayed Purchase Orders")),
                    self._metric("pending_warehouse_receipts", _("Pending Warehouse Receipts")),
                    self._metric("total_purchase_amount", _("Total Purchase Amount"), "amount"),
                ],
            },
            "manufacturing": {
                "label": _("Manufacturing Dashboard"),
                "metrics": [
                    self._metric("total_manufacturing_orders", _("Total Manufacturing Orders")),
                    self._metric("manufacturing_delayed", _("Delayed Manufacturing Orders")),
                    self._metric("manufacturing_missing_materials", _("Manufacturing Shortages")),
                    self._metric("work_orders_delayed", _("Delayed Work Orders")),
                ],
            },
            "maintenance": {
                "label": _("Maintenance Dashboard"),
                "metrics": [
                    self._metric("total_maintenance_requests", _("Total Maintenance Requests")),
                    self._metric("maintenance_delayed", _("Delayed Maintenance Requests")),
                    self._metric("maintenance_equipment_open", _("Equipment With Open Maintenance")),
                    self._metric("maintenance_downtime_rate", _("Downtime Rate"), "percentage"),
                ],
            },
            "hr": {
                "label": _("HR Dashboard"),
                "metrics": [
                    self._metric("hr_absent_today", _("Absent Today")),
                    self._metric("hr_late_today", _("Late Employees Today")),
                    self._metric("hr_pending_leaves", _("Pending Leave Requests")),
                    self._metric("hr_contracts_expiring", _("Contracts Expiring Soon")),
                ],
            },
            "helpdesk": {
                "label": _("Helpdesk Dashboard"),
                "metrics": [
                    self._metric("helpdesk_open_tickets", _("Open Tickets")),
                    self._metric("helpdesk_delayed_tickets", _("Delayed Tickets")),
                    self._metric("helpdesk_sla_breached", _("SLA Breached Tickets")),
                ],
            },
            "pos": {
                "label": _("POS Dashboard"),
                "metrics": [
                    self._metric("pos_total_orders", _("Total POS Orders")),
                    self._metric("pos_total_revenue", _("Total POS Revenue"), "amount"),
                    self._metric("pos_refund_orders", _("Refund Orders Count")),
                    self._metric("pos_refund_amount", _("Total Refund Amount"), "amount"),
                ],
            },
            "website": {
                "label": _("Website Dashboard"),
                "metrics": [
                    self._metric("website_orders_count", _("Website Orders Count")),
                    self._metric("website_revenue", _("Website Revenue"), "amount"),
                    self._metric("website_abandoned_carts", _("Abandoned Carts")),
                    self._metric("website_conversion_rate", _("Conversion Rate"), "percentage"),
                ],
            },
            "alerts": {
                "label": _("Alerts Center"),
                "metrics": [
                    self._metric("total", _("Total Operational Alerts")),
                    self._metric("critical", _("Critical Operational Alerts")),
                    self._metric("high", _("High Operational Alerts")),
                ],
            },
        }

    @api.model
    def evaluate_all_rules(self):
        now = fields.Datetime.now()
        rules = self.env["executive.dashboard.alert.rule"].search(
            [
                ("active", "=", True),
                "|",
                ("next_allowed_datetime", "=", False),
                ("next_allowed_datetime", "<=", now),
            ],
            order="dashboard_key, company_id, id",
        )
        cache = {}
        for rule in rules:
            try:
                self.evaluate_rule(rule, cache=cache)
            except Exception as error:
                _logger.exception("Executive dashboard alert rule failed: %s", rule.display_name)
                self._log_rule_error(rule, error)
        return True

    @api.model
    def evaluate_rule(self, rule, cache=None):
        rule.ensure_one()
        now = fields.Datetime.now()
        if not rule.active:
            return False
        if rule.next_allowed_datetime and rule.next_allowed_datetime > now:
            return False

        measured_value = self.get_metric_value(rule, cache=cache)
        matched = self.compare_value(measured_value, rule.operator, rule.threshold_value)
        if not matched:
            return False

        open_alert = self.env["executive.dashboard.alert.history"].search(
            [
                ("rule_id", "=", rule.id),
                ("metric_key", "=", rule.metric_key),
                ("status", "in", ["new", "in_progress", "escalated"]),
            ],
            limit=1,
        )
        message = self._default_alert_message(rule, measured_value)
        if open_alert:
            open_alert.write({"measured_value": measured_value, "message": message})
            self._update_rule_cooldown(rule, now)
            return open_alert

        alert = self.create_alert_history(rule, measured_value, message)
        self.execute_rule_actions(rule, alert)
        self._update_rule_cooldown(rule, now)
        return alert

    @api.model
    def get_metric_value(self, rule, cache=None):
        cache = cache if isinstance(cache, dict) else {}
        dashboard_key = rule.dashboard_key
        method_name = self.DASHBOARD_METHODS.get(dashboard_key)
        if not method_name:
            raise UserError(_("Invalid dashboard key: %s") % dashboard_key)

        service = self.env["executive.dashboard.service"]
        if rule.company_id:
            service = service.with_company(rule.company_id)
        method = getattr(service, method_name, None)
        if not method:
            raise UserError(_("Dashboard method is not available: %s") % method_name)

        filters = self._rule_filters(rule)
        cache_key = (
            dashboard_key,
            rule.company_id.id or self.env.company.id,
            filters.get("date_from") or "",
            filters.get("date_to") or "",
        )
        if cache_key not in cache:
            cache[cache_key] = method(filters)
        data = cache[cache_key]
        metric = self._find_metric(data, rule.metric_key)
        if metric is None:
            raise UserError(
                _("Metric %(metric)s was not found in %(dashboard)s dashboard data.")
                % {
                    "metric": rule.metric_key,
                    "dashboard": dict(rule.DASHBOARD_SELECTION).get(dashboard_key, dashboard_key),
                }
            )
        return self._to_float(metric.get("value"))

    @api.model
    def compare_value(self, measured_value, operator, threshold_value):
        measured = self._to_float(measured_value)
        threshold = self._to_float(threshold_value)
        if operator == ">":
            return measured > threshold
        if operator == ">=":
            return measured >= threshold
        if operator == "<":
            return measured < threshold
        if operator == "<=":
            return measured <= threshold
        if operator == "=":
            return measured == threshold
        if operator == "!=":
            return measured != threshold
        raise UserError(_("Unsupported alert operator: %s") % operator)

    @api.model
    def create_alert_history(self, rule, measured_value, message, related_record=None):
        values = {
            "rule_id": rule.id,
            "dashboard_key": rule.dashboard_key,
            "metric_key": rule.metric_key,
            "metric_label": rule.metric_label or rule.metric_key,
            "measured_value": measured_value,
            "operator": rule.operator,
            "threshold_value": rule.threshold_value,
            "severity": rule.severity,
            "status": "new",
            "company_id": (rule.company_id or self.env.company).id,
            "responsible_user_id": (rule.responsible_user_id or self.env.user).id,
            "triggered_datetime": fields.Datetime.now(),
            "message": message,
            "filters_json": self._rule_filters(rule),
        }
        if related_record:
            values.update(
                {
                    "related_model": related_record._name,
                    "related_res_id": related_record.id,
                    "related_record_name": related_record.display_name,
                }
            )
        alert = self.env["executive.dashboard.alert.history"].create(values)
        if rule.action_create_log:
            alert.message_post(body=escape(message))
        return alert

    @api.model
    def execute_rule_actions(self, rule, alert):
        action_notes = []
        if rule.action_send_email:
            try:
                self.send_alert_email(rule, alert)
                alert.email_sent = True
                action_notes.append(_("email sent"))
            except Exception as error:
                alert.error_message = self._append_error(alert.error_message, error)
        if rule.action_create_activity:
            try:
                self.create_alert_activity(rule, alert)
                alert.activity_created = True
                action_notes.append(_("activity created"))
            except Exception as error:
                alert.error_message = self._append_error(alert.error_message, error)
        if rule.action_notify_user:
            try:
                self.notify_alert_users(rule, alert)
                alert.notification_sent = True
                action_notes.append(_("notification posted"))
            except Exception as error:
                alert.error_message = self._append_error(alert.error_message, error)
        alert.write(
            {
                "last_notification_datetime": fields.Datetime.now(),
                "action_taken": ", ".join(action_notes),
            }
        )
        return True

    @api.model
    def send_alert_email(self, rule, alert):
        recipients = self._alert_recipients(rule)
        if not recipients:
            return False
        subject = self._render_template(
            rule.email_subject or _("Dashboard Alert: ${metric_label}"),
            rule,
            alert,
        )
        body = self._render_template(
            rule.email_body or self._default_email_body(),
            rule,
            alert,
        )
        mail = self.env["mail.mail"].create(
            {
                "subject": subject,
                "body_html": body,
                "email_to": ", ".join(recipients),
                "email_from": self.env.user.email_formatted or self.env.company.email or False,
                "auto_delete": False,
            }
        )
        mail.send()
        return mail

    @api.model
    def create_alert_activity(self, rule, alert):
        user = rule.activity_user_id or rule.responsible_user_id or alert.responsible_user_id or self.env.user
        activity_type = rule.activity_type_id or self.env.ref(
            "mail.mail_activity_data_todo", raise_if_not_found=False
        )
        summary = self._render_template(
            rule.activity_summary or _("Dashboard alert: ${metric_label}"),
            rule,
            alert,
        )
        note = self._render_template(
            rule.activity_note or self._default_activity_note(),
            rule,
            alert,
        )
        record = self._activity_target(alert)
        if hasattr(record, "activity_schedule"):
            record.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                user_id=user.id,
                summary=summary,
                note=note,
            )
            return True
        model = self.env["ir.model"]._get(alert._name)
        self.env["mail.activity"].create(
            {
                "res_model_id": model.id,
                "res_id": alert.id,
                "activity_type_id": activity_type.id if activity_type else False,
                "user_id": user.id,
                "summary": summary,
                "note": note,
                "date_deadline": fields.Date.context_today(self),
                "automated": True,
            }
        )
        return True

    @api.model
    def notify_alert_users(self, rule, alert):
        body = self._render_template(
            _("Smart dashboard alert triggered: ${metric_label} ${operator} ${threshold_value}."),
            rule,
            alert,
        )
        partner_ids = (
            rule.recipient_partner_ids
            | rule.recipient_user_ids.partner_id
            | rule.responsible_user_id.partner_id
        ).ids
        alert.message_post(body=escape(body), partner_ids=partner_ids)
        return True

    @api.model
    def process_escalations(self):
        now = fields.Datetime.now()
        alerts = self.env["executive.dashboard.alert.history"].search(
            [
                ("status", "in", ["new", "in_progress"]),
                ("escalation_sent", "=", False),
                ("rule_id.escalation_enabled", "=", True),
            ]
        )
        for alert in alerts:
            try:
                rule = alert.rule_id
                if not rule:
                    continue
                deadline = alert.triggered_datetime + timedelta(
                    hours=rule.escalation_after_hours or 0
                )
                if deadline > now:
                    continue
                self._send_escalation(rule, alert)
                alert.write(
                    {
                        "status": "escalated",
                        "escalated_datetime": now,
                        "escalation_sent": True,
                        "last_notification_datetime": now,
                        "action_taken": self._append_action(alert.action_taken, _("escalated")),
                    }
                )
            except Exception as error:
                _logger.exception("Executive dashboard alert escalation failed: %s", alert.name)
                alert.error_message = self._append_error(alert.error_message, error)
        return True

    @api.model
    def resolve_alert(self, alert, reason=None):
        alert.write(
            {
                "status": "resolved",
                "resolved_datetime": fields.Datetime.now(),
                "action_taken": self._append_action(alert.action_taken, reason or _("resolved")),
            }
        )
        alert.message_post(body=escape(reason or _("Alert resolved.")))
        return True

    @api.model
    def ignore_alert(self, alert, reason=None):
        alert.write(
            {
                "status": "ignored",
                "resolved_datetime": fields.Datetime.now(),
                "action_taken": self._append_action(alert.action_taken, reason or _("ignored")),
            }
        )
        alert.message_post(body=escape(reason or _("Alert ignored.")))
        return True

    def _metric(self, key, label, threshold_type="number"):
        return {"key": key, "label": label, "threshold_type": threshold_type}

    def _rule_filters(self, rule):
        today = fields.Date.context_today(self)
        date_from = False
        date_to = False
        if rule.period_type == "today":
            date_from = date_to = today
        elif rule.period_type == "this_week":
            date_from = today - timedelta(days=today.weekday())
            date_to = date_from + timedelta(days=6)
        elif rule.period_type == "this_month":
            date_from = today.replace(day=1)
            next_month = date_from.replace(day=28) + timedelta(days=4)
            date_to = next_month.replace(day=1) - timedelta(days=1)
        elif rule.period_type == "this_year":
            date_from = today.replace(month=1, day=1)
            date_to = today.replace(month=12, day=31)
        elif rule.period_type == "custom":
            date_from = rule.date_from
            date_to = rule.date_to
        filters = {
            "company_id": rule.company_id.id if rule.company_id else False,
            "date_from": fields.Date.to_string(date_from) if date_from else False,
            "date_to": fields.Date.to_string(date_to) if date_to else False,
        }
        return filters

    def _find_metric(self, data, metric_key):
        if not data:
            return None
        if isinstance(data, dict):
            if data.get("key") == metric_key and "value" in data:
                return data
            summary = data.get("summary")
            if isinstance(summary, dict) and metric_key in summary:
                return {"key": metric_key, "label": metric_key, "value": summary[metric_key]}
            for value in data.values():
                found = self._find_metric(value, metric_key)
                if found is not None:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = self._find_metric(item, metric_key)
                if found is not None:
                    return found
        return None

    def _update_rule_cooldown(self, rule, now):
        cooldown = max(rule.cooldown_hours or 0, 0)
        rule.write(
            {
                "last_triggered_datetime": now,
                "next_allowed_datetime": now + timedelta(hours=cooldown) if cooldown else False,
            }
        )

    def _default_alert_message(self, rule, measured_value):
        return _(
            "%(metric)s is %(measured)s and breached %(operator)s %(threshold)s.",
            metric=rule.metric_label or rule.metric_key,
            measured=self._format_number(measured_value),
            operator=rule.operator,
            threshold=self._format_number(rule.threshold_value),
        )

    def _default_email_body(self):
        return Markup(
            """
            <p>Dashboard alert <strong>${rule_name}</strong> was triggered.</p>
            <ul>
                <li>Dashboard: ${dashboard}</li>
                <li>Metric: ${metric_label}</li>
                <li>Measured Value: ${measured_value}</li>
                <li>Threshold: ${operator} ${threshold_value}</li>
                <li>Severity: ${severity}</li>
                <li>Company: ${company}</li>
                <li>Triggered: ${triggered_datetime}</li>
            </ul>
            <p><a href="${alert_url}">Open alert history</a></p>
            """
        )

    def _default_activity_note(self):
        return Markup(
            """
            <p>${message}</p>
            <p><strong>Dashboard:</strong> ${dashboard}<br/>
            <strong>Metric:</strong> ${metric_label}<br/>
            <strong>Measured:</strong> ${measured_value}<br/>
            <strong>Threshold:</strong> ${operator} ${threshold_value}</p>
            """
        )

    def _render_template(self, template_value, rule, alert):
        values = self._template_values(rule, alert)
        return Template(str(template_value or "")).safe_substitute(values)

    def _template_values(self, rule, alert):
        dashboard_label = dict(rule.DASHBOARD_SELECTION).get(rule.dashboard_key, rule.dashboard_key)
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", default="")
        alert_url = "%s/web#id=%s&model=executive.dashboard.alert.history&view_type=form" % (
            base_url,
            alert.id,
        )
        return {
            "rule_name": rule.name or "",
            "dashboard": dashboard_label or "",
            "metric_label": alert.metric_label or rule.metric_label or rule.metric_key or "",
            "measured_value": self._format_number(alert.measured_value),
            "operator": rule.operator or "",
            "threshold_value": self._format_number(rule.threshold_value),
            "severity": alert.severity or "",
            "company": alert.company_id.display_name or "",
            "triggered_datetime": fields.Datetime.to_string(alert.triggered_datetime) or "",
            "message": alert.message or "",
            "alert_url": alert_url,
        }

    def _alert_recipients(self, rule):
        recipients = set()
        for partner in rule.recipient_partner_ids | rule.recipient_user_ids.partner_id:
            if partner.email:
                recipients.add(partner.email.strip())
        for email in (rule.recipient_emails or "").replace(";", ",").split(","):
            if email.strip():
                recipients.add(email.strip())
        return sorted(recipients)

    def _send_escalation(self, rule, alert):
        recipients = set()
        for partner in rule.escalation_partner_ids | rule.escalation_user_ids.partner_id:
            if partner.email:
                recipients.add(partner.email.strip())
        if not recipients:
            return False
        subject = self._render_template(
            rule.escalation_email_subject or _("Escalated Dashboard Alert: ${metric_label}"),
            rule,
            alert,
        )
        body = self._render_template(rule.escalation_email_body or self._default_email_body(), rule, alert)
        mail = self.env["mail.mail"].create(
            {
                "subject": subject,
                "body_html": body,
                "email_to": ", ".join(sorted(recipients)),
                "email_from": self.env.user.email_formatted or self.env.company.email or False,
                "auto_delete": False,
            }
        )
        mail.send()
        return mail

    def _activity_target(self, alert):
        if alert.related_model and alert.related_res_id:
            try:
                record = self.env[alert.related_model].browse(alert.related_res_id).exists()
            except (KeyError, AccessError):
                record = False
            if record and hasattr(record, "activity_schedule"):
                return record
        return alert

    def _log_rule_error(self, rule, error):
        body = escape(_("Alert rule evaluation failed: %s") % error)
        try:
            rule.message_post(body=body)
        except Exception:
            _logger.exception("Unable to post alert rule error message.")

    def _append_error(self, current, error):
        message = str(error)
        return "%s\n%s" % (current, message) if current else message

    def _append_action(self, current, action):
        return "%s, %s" % (current, action) if current else str(action)

    def _to_float(self, value):
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _format_number(self, value):
        return ("%0.2f" % self._to_float(value)).rstrip("0").rstrip(".")
