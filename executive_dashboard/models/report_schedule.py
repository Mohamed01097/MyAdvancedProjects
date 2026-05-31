import logging
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


class ExecutiveDashboardReportSchedule(models.Model):
    _name = "executive.dashboard.report.schedule"
    _description = "Dashboard Report Schedule"
    _inherit = ["mail.thread", "mail.activity.mixin"]

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

    name = fields.Char(string="Schedule Name", required=True)
    active = fields.Boolean(default=True, tracking=True)
    dashboard_key = fields.Selection(DASHBOARD_SELECTION, string="Dashboard", required=True)
    dashboard_name = fields.Char(
        string="Dashboard Name",
        compute="_compute_dashboard_name",
        store=True,
    )
    frequency = fields.Selection(
        [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")],
        string="Frequency",
        required=True,
        default=lambda self: self._default_frequency(),
        tracking=True,
    )
    send_time = fields.Float(
        string="Send Time",
        help="Time in 24-hour format. Example: 14.5 means 14:30.",
        default=9.0,
        tracking=True,
    )
    day_of_week = fields.Selection(
        [
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        string="Day of Week",
        default="0",
    )
    day_of_month = fields.Integer(
        string="Day of Month",
        default=1,
        help="Use a value from 1 to 28 so every month has a valid run date.",
    )
    recipient_ids = fields.Many2many(
        "res.partner",
        string="Recipients",
        domain=[("email", "!=", False)],
        default=lambda self: self._default_recipient_ids(),
    )
    recipient_emails = fields.Char(
        string="Additional Email Addresses",
        help="Comma-separated email addresses.",
    )
    format = fields.Selection(
        [("pdf", "PDF"), ("excel", "Excel"), ("both", "PDF & Excel")],
        string="Format",
        required=True,
        default="pdf",
    )
    include_kpis = fields.Boolean(default=lambda self: self._default_include("include_kpis"))
    include_tables = fields.Boolean(default=lambda self: self._default_include("include_tables"))
    include_charts = fields.Boolean(default=lambda self: self._default_include("include_charts"))
    filters_json = fields.Json(string="Filters", default=dict)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsible User",
        default=lambda self: self.env.user,
        required=True,
    )
    last_run_datetime = fields.Datetime(string="Last Run", readonly=True)
    next_run_datetime = fields.Datetime(string="Next Run", readonly=True)
    state = fields.Selection(
        [("active", "Active"), ("inactive", "Inactive"), ("error", "Error")],
        default="active",
        tracking=True,
    )

    @api.depends("dashboard_key")
    def _compute_dashboard_name(self):
        dashboard_names = dict(self.DASHBOARD_SELECTION)
        for record in self:
            record.dashboard_name = dashboard_names.get(record.dashboard_key, "")

    @api.model
    def _default_frequency(self):
        return self.env["executive.dashboard.export"].get_report_settings()["default_frequency"]

    @api.model
    def _default_recipient_ids(self):
        recipient_ids = self.env["executive.dashboard.export"].get_report_settings()[
            "default_recipient_ids"
        ]
        return [(6, 0, recipient_ids)] if recipient_ids else False

    @api.model
    def _default_include(self, key):
        return self.env["executive.dashboard.export"].get_report_settings()[key]

    @api.constrains("send_time", "day_of_month")
    def _check_schedule_values(self):
        for record in self:
            if record.send_time < 0 or record.send_time >= 24:
                raise ValidationError(_("Send Time must be between 0.00 and 23.99."))
            if record.day_of_month < 1 or record.day_of_month > 28:
                raise ValidationError(_("Day of Month must be between 1 and 28."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_next_run_datetime()
        return records

    def write(self, vals):
        res = super().write(vals)
        schedule_fields = {
            "active",
            "frequency",
            "send_time",
            "day_of_week",
            "day_of_month",
        }
        if schedule_fields.intersection(vals) and not self.env.context.get("skip_next_run_update"):
            self._update_next_run_datetime()
        return res

    @api.onchange("active", "frequency", "send_time", "day_of_week", "day_of_month")
    def _onchange_schedule_fields(self):
        for record in self:
            record.next_run_datetime = record._get_next_run_datetime()
            if not record.active:
                record.state = "inactive"
            elif record.state == "inactive":
                record.state = "active"

    def action_run_now(self):
        for record in self:
            record._send_report(raise_on_error=True)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Scheduled Report"),
                "message": _("Report generated and emailed successfully."),
                "type": "success",
            },
        }

    def _send_report(self, raise_on_error=False):
        self.ensure_one()
        export_service = (
            self.env["executive.dashboard.export"]
            .with_user(self.user_id)
            .with_company(self.company_id)
        )
        recipients = self._get_recipient_emails()
        now = fields.Datetime.now()
        try:
            if not recipients:
                raise UserError(_("No valid recipients configured."))

            attachments = export_service.generate_report_attachment(
                self.dashboard_key,
                self.filters_json or {},
                self.format,
                {
                    "include_kpis": self.include_kpis,
                    "include_tables": self.include_tables,
                    "include_charts": self.include_charts,
                    "filename_suffix": "scheduled",
                    "res_model": self._name,
                    "res_id": self.id,
                },
            )
            subject = _("Scheduled Dashboard Report: %s") % self.dashboard_name
            body = _(
                "<p>Please find attached the scheduled <strong>%s</strong> report.</p>"
            ) % self.dashboard_name
            export_service.send_report_email(recipients, subject, body, attachments)

            attachments = self.env["ir.attachment"].browse(attachments.ids)
            log = self.env["executive.dashboard.report.log"].create(
                {
                    "name": "%s - Scheduled" % self.dashboard_name,
                    "dashboard_key": self.dashboard_key,
                    "dashboard_name": self.dashboard_name,
                    "report_type": "scheduled",
                    "format": self.format,
                    "generated_by": self.user_id.id,
                    "company_id": self.company_id.id,
                    "recipients": ", ".join(recipients),
                    "schedule_id": self.id,
                    "status": "success",
                    "attachment_ids": [(6, 0, attachments.ids)],
                    "filters_json": self.filters_json,
                }
            )
            attachments.write(
                {"res_model": "executive.dashboard.report.log", "res_id": log.id}
            )
            self.with_context(skip_next_run_update=True).write(
                {
                    "last_run_datetime": now,
                    "next_run_datetime": self._get_next_run_datetime(now),
                    "state": "active",
                }
            )
            return True
        except Exception as error:
            self.with_context(skip_next_run_update=True).write(
                {
                    "last_run_datetime": now,
                    "next_run_datetime": self._get_next_run_datetime(now),
                    "state": "error",
                }
            )
            self.env["executive.dashboard.report.log"].create(
                {
                    "name": "%s - Scheduled (Failed)" % (self.dashboard_name or self.name),
                    "dashboard_key": self.dashboard_key,
                    "dashboard_name": self.dashboard_name,
                    "report_type": "scheduled",
                    "format": self.format,
                    "generated_by": self.user_id.id,
                    "company_id": self.company_id.id,
                    "recipients": ", ".join(recipients),
                    "schedule_id": self.id,
                    "status": "failed",
                    "error_message": str(error),
                    "filters_json": self.filters_json,
                }
            )
            if raise_on_error:
                raise
            _logger.exception("Executive dashboard scheduled report failed: %s", self.name)
            return False

    @api.model
    def _run_scheduled_reports(self):
        now = fields.Datetime.now()
        schedules = self.search(
            [
                ("active", "=", True),
                ("next_run_datetime", "!=", False),
                ("next_run_datetime", "<=", now),
            ],
            order="next_run_datetime, id",
        )
        for schedule in schedules:
            try:
                schedule._send_report()
            except Exception:
                _logger.exception("Unexpected scheduled report failure: %s", schedule.name)

    def _update_next_run_datetime(self):
        for record in self:
            values = {
                "next_run_datetime": record._get_next_run_datetime(),
                "state": "active" if record.active else "inactive",
            }
            record.with_context(skip_next_run_update=True).write(values)

    def _get_next_run_datetime(self, base_datetime=None):
        self.ensure_one()
        if not self.active:
            return False

        base = fields.Datetime.to_datetime(base_datetime or fields.Datetime.now())
        hour = int(self.send_time)
        minute = int(round((self.send_time - hour) * 60))
        if minute >= 60:
            hour += 1
            minute = 0
        hour = min(hour, 23)

        candidate = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if self.frequency == "daily":
            if candidate <= base:
                candidate += timedelta(days=1)
        elif self.frequency == "weekly":
            target_day = int(self.day_of_week or "0")
            days_ahead = target_day - base.weekday()
            if days_ahead < 0 or (days_ahead == 0 and candidate <= base):
                days_ahead += 7
            candidate += timedelta(days=days_ahead)
        elif self.frequency == "monthly":
            target_day = min(max(self.day_of_month or 1, 1), 28)
            candidate = base.replace(
                day=target_day, hour=hour, minute=minute, second=0, microsecond=0
            )
            if candidate <= base:
                candidate += relativedelta(months=1)
        return candidate

    def _get_recipient_emails(self):
        recipients = [partner.email for partner in self.recipient_ids if partner.email]
        if self.recipient_emails:
            recipients += self.env["executive.dashboard.export"]._normalize_recipients(
                self.recipient_emails
            )
        return recipients
