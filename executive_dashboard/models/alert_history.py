from odoo import _, api, fields, models


class ExecutiveDashboardAlertHistory(models.Model):
    _name = "executive.dashboard.alert.history"
    _description = "Executive Dashboard Alert History"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "triggered_datetime DESC, id DESC"

    name = fields.Char(required=True)
    rule_id = fields.Many2one(
        "executive.dashboard.alert.rule",
        string="Rule",
        ondelete="set null",
        index=True,
    )
    dashboard_key = fields.Char(index=True)
    metric_key = fields.Char(index=True)
    metric_label = fields.Char()
    measured_value = fields.Float()
    operator = fields.Char()
    threshold_value = fields.Float()
    severity = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
        index=True,
    )
    status = fields.Selection(
        [
            ("new", "New"),
            ("in_progress", "In Progress"),
            ("resolved", "Resolved"),
            ("ignored", "Ignored"),
            ("escalated", "Escalated"),
        ],
        default="new",
        required=True,
        tracking=True,
        index=True,
    )
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, index=True)
    responsible_user_id = fields.Many2one("res.users", index=True)
    triggered_datetime = fields.Datetime(default=fields.Datetime.now, index=True)
    resolved_datetime = fields.Datetime()
    escalated_datetime = fields.Datetime()
    last_notification_datetime = fields.Datetime()
    related_model = fields.Char(index=True)
    related_res_id = fields.Integer(index=True)
    related_record_name = fields.Char()
    message = fields.Text()
    action_taken = fields.Text()
    email_sent = fields.Boolean()
    activity_created = fields.Boolean()
    notification_sent = fields.Boolean()
    escalation_sent = fields.Boolean()
    error_message = fields.Text()
    filters_json = fields.Json(default=dict)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                metric_label = vals.get("metric_label") or vals.get("metric_key") or _("Alert")
                timestamp = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                vals["name"] = _("%(metric)s Alert - %(timestamp)s", metric=metric_label, timestamp=timestamp)
            vals.setdefault("triggered_datetime", fields.Datetime.now())
            vals.setdefault("company_id", self.env.company.id)
        return super().create(vals_list)

    def action_mark_in_progress(self):
        self.write({"status": "in_progress"})
        self._post_lifecycle_message(_("Alert marked in progress."))
        return True

    def action_mark_resolved(self):
        return self.env["executive.dashboard.alert.engine"].resolve_alert(self)

    def action_ignore(self):
        return self.env["executive.dashboard.alert.engine"].ignore_alert(self)

    def action_reopen(self):
        self.write({"status": "new", "resolved_datetime": False})
        self._post_lifecycle_message(_("Alert reopened."))
        return True

    def action_open_rule(self):
        self.ensure_one()
        if not self.rule_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "executive.dashboard.alert.rule",
            "res_id": self.rule_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_related_record(self):
        self.ensure_one()
        return self.env["executive.dashboard.service"]._open_record_action(
            self.related_model,
            self.related_res_id,
            self.related_record_name or _("Related Record"),
        )

    def action_create_activity(self):
        engine = self.env["executive.dashboard.alert.engine"]
        for alert in self:
            if alert.rule_id:
                engine.create_alert_activity(alert.rule_id, alert)
        return True

    def _post_lifecycle_message(self, body):
        for alert in self:
            alert.message_post(body=body)
