from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ExecutiveDashboardAlertRule(models.Model):
    _name = "executive.dashboard.alert.rule"
    _description = "Executive Dashboard Alert Rule"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "active DESC, severity DESC, name"

    DASHBOARD_SELECTION = [
        ("overview", "Executive Overview"),
        ("sales", "Sales Dashboard"),
        ("crm", "CRM Dashboard"),
        ("inventory", "Inventory Dashboard"),
        ("purchase", "Purchase Dashboard"),
        ("manufacturing", "Manufacturing Dashboard"),
        ("maintenance", "Maintenance Dashboard"),
        ("hr", "HR Dashboard"),
        ("helpdesk", "Helpdesk Dashboard"),
        ("pos", "POS Dashboard"),
        ("website", "Website Dashboard"),
        ("alerts", "Alerts Center"),
    ]
    OPERATOR_SELECTION = [
        (">", ">"),
        (">=", ">="),
        ("<", "<"),
        ("<=", "<="),
        ("=", "="),
        ("!=", "!="),
    ]
    THRESHOLD_TYPE_SELECTION = [
        ("number", "Number"),
        ("percentage", "Percentage"),
        ("amount", "Amount"),
    ]
    PERIOD_TYPE_SELECTION = [
        ("current_filters", "Current Filters"),
        ("today", "Today"),
        ("this_week", "This Week"),
        ("this_month", "This Month"),
        ("this_year", "This Year"),
        ("custom", "Custom"),
    ]
    SEVERITY_SELECTION = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    dashboard_key = fields.Selection(DASHBOARD_SELECTION, required=True, tracking=True)
    metric_key = fields.Char(required=True, tracking=True)
    metric_label = fields.Char()
    operator = fields.Selection(OPERATOR_SELECTION, required=True, default=">", tracking=True)
    threshold_value = fields.Float(required=True, tracking=True)
    threshold_type = fields.Selection(
        THRESHOLD_TYPE_SELECTION,
        required=True,
        default="number",
        tracking=True,
    )
    period_type = fields.Selection(
        PERIOD_TYPE_SELECTION,
        required=True,
        default="current_filters",
        tracking=True,
    )
    date_from = fields.Date()
    date_to = fields.Date()
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    responsible_user_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    recipient_user_ids = fields.Many2many(
        "res.users",
        "executive_dashboard_alert_rule_user_rel",
        "rule_id",
        "user_id",
        string="Recipient Users",
    )
    recipient_partner_ids = fields.Many2many(
        "res.partner",
        "executive_dashboard_alert_rule_partner_rel",
        "rule_id",
        "partner_id",
        string="Recipient Partners",
        domain=[("email", "!=", False)],
    )
    recipient_emails = fields.Char(help="Comma-separated email addresses.")
    action_create_activity = fields.Boolean(default=True)
    action_send_email = fields.Boolean(default=False)
    action_notify_user = fields.Boolean(default=True)
    action_create_log = fields.Boolean(default=True)
    activity_user_id = fields.Many2one("res.users")
    activity_type_id = fields.Many2one(
        "mail.activity.type",
        default=lambda self: self.env.ref(
            "mail.mail_activity_data_todo", raise_if_not_found=False
        ),
    )
    activity_summary = fields.Char()
    activity_note = fields.Html()
    email_subject = fields.Char()
    email_body = fields.Html()
    severity = fields.Selection(SEVERITY_SELECTION, required=True, default="medium", tracking=True)
    cooldown_hours = fields.Float(default=24.0)
    escalation_enabled = fields.Boolean(default=False)
    escalation_after_hours = fields.Float(default=24.0)
    escalation_user_ids = fields.Many2many(
        "res.users",
        "executive_dashboard_alert_rule_escalation_user_rel",
        "rule_id",
        "user_id",
        string="Escalation Users",
    )
    escalation_partner_ids = fields.Many2many(
        "res.partner",
        "executive_dashboard_alert_rule_escalation_partner_rel",
        "rule_id",
        "partner_id",
        string="Escalation Partners",
        domain=[("email", "!=", False)],
    )
    escalation_email_subject = fields.Char()
    escalation_email_body = fields.Html()
    last_triggered_datetime = fields.Datetime(readonly=True)
    next_allowed_datetime = fields.Datetime(readonly=True)

    @api.constrains("cooldown_hours", "escalation_after_hours")
    def _check_non_negative_hours(self):
        for record in self:
            if record.cooldown_hours < 0:
                raise ValidationError(_("Cooldown hours cannot be negative."))
            if record.escalation_after_hours < 0:
                raise ValidationError(_("Escalation hours cannot be negative."))

    @api.onchange("dashboard_key", "metric_key")
    def _onchange_metric_label(self):
        registry = self.env["executive.dashboard.alert.engine"].get_available_alert_metrics()
        for record in self:
            if not record.dashboard_key or not record.metric_key:
                continue
            for metric in registry.get(record.dashboard_key, {}).get("metrics", []):
                if metric.get("key") == record.metric_key and not record.metric_label:
                    record.metric_label = metric.get("label")
                    record.threshold_type = metric.get("threshold_type") or record.threshold_type

    def action_evaluate_now(self):
        engine = self.env["executive.dashboard.alert.engine"]
        for rule in self:
            engine.evaluate_rule(rule)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Alert Rules"),
                "message": _("Selected alert rules were evaluated."),
                "type": "success",
            },
        }

    def action_open_history(self):
        self.ensure_one()
        return {
            "name": _("Alert History"),
            "type": "ir.actions.act_window",
            "res_model": "executive.dashboard.alert.history",
            "view_mode": "list,form",
            "domain": [("rule_id", "=", self.id)],
            "context": {"default_rule_id": self.id},
        }

    @api.model
    def _cron_evaluate_alert_rules(self):
        self.env["executive.dashboard.alert.engine"].evaluate_all_rules()
        self.env["executive.dashboard.alert.engine"].process_escalations()

    @api.model
    def get_available_alert_metrics(self):
        return self.env["executive.dashboard.alert.engine"].get_available_alert_metrics()
