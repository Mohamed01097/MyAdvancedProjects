from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ExecutiveDashboardReportSendWizard(models.TransientModel):
    _name = "executive.dashboard.report.send.wizard"
    _description = "Send Dashboard Report Wizard"

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

    dashboard_key = fields.Selection(DASHBOARD_SELECTION, string="Dashboard", required=True)
    dashboard_name = fields.Char(
        string="Dashboard Name",
        compute="_compute_dashboard_name",
        readonly=True,
    )
    format = fields.Selection(
        [("pdf", "PDF"), ("excel", "Excel"), ("both", "PDF & Excel")],
        string="Format",
        required=True,
        default="pdf",
    )
    recipient_ids = fields.Many2many(
        "res.partner",
        string="Recipients",
        domain=[("email", "!=", False)],
        default=lambda self: self._default_recipient_ids(),
    )
    recipient_emails = fields.Char(
        string="Additional Emails",
        help="Comma-separated email addresses.",
    )
    subject = fields.Char(
        string="Subject",
        required=True,
        default=lambda self: _("Dashboard Report"),
    )
    message = fields.Html(
        string="Message",
        default=lambda self: _("<p>Please find attached the requested dashboard report.</p>"),
    )
    include_kpis = fields.Boolean(default=lambda self: self._default_include("include_kpis"))
    include_tables = fields.Boolean(default=lambda self: self._default_include("include_tables"))
    include_charts = fields.Boolean(default=lambda self: self._default_include("include_charts"))
    filters_json = fields.Json(string="Filters", default=dict)

    @api.depends("dashboard_key")
    def _compute_dashboard_name(self):
        for record in self:
            record.dashboard_name = self.env["executive.dashboard.export"].get_dashboard_title(
                record.dashboard_key
            )

    @api.model
    def _default_recipient_ids(self):
        recipient_ids = self.env["executive.dashboard.export"].get_report_settings()[
            "default_recipient_ids"
        ]
        return [(6, 0, recipient_ids)] if recipient_ids else False

    @api.model
    def _default_include(self, key):
        return self.env["executive.dashboard.export"].get_report_settings()[key]

    def action_send_report(self):
        self.ensure_one()
        export_service = self.env["executive.dashboard.export"]
        recipients = self._get_recipient_emails()
        attachments = self.env["ir.attachment"]
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
                    "title": self.subject,
                    "filename_suffix": "shared",
                },
            )
            export_service.send_report_email(
                recipients,
                self.subject,
                self.message or _("<p>Please find attached the requested dashboard report.</p>"),
                attachments,
            )

            log = export_service.create_report_log(
                {
                    "name": "%s - Share" % self.dashboard_name,
                    "dashboard_key": self.dashboard_key,
                    "dashboard_name": self.dashboard_name,
                    "report_type": "share",
                    "format": self.format,
                    "recipients": ", ".join(recipients),
                    "status": "success",
                    "attachment_ids": [(6, 0, attachments.ids)],
                    "filters_json": self.filters_json,
                }
            )
            attachments.write(
                {"res_model": "executive.dashboard.report.log", "res_id": log.id}
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Report Sent"),
                    "message": _("Dashboard report sent successfully."),
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        except Exception as error:
            log_values = {
                "name": "%s - Share (Failed)" % (self.dashboard_name or _("Dashboard")),
                "dashboard_key": self.dashboard_key,
                "dashboard_name": self.dashboard_name,
                "report_type": "share",
                "format": self.format,
                "recipients": ", ".join(recipients),
                "status": "failed",
                "error_message": str(error),
                "filters_json": self.filters_json,
            }
            if attachments:
                log_values["attachment_ids"] = [(6, 0, attachments.ids)]
            export_service.create_report_log(log_values)
            raise

    def _get_recipient_emails(self):
        recipients = [partner.email for partner in self.recipient_ids if partner.email]
        if self.recipient_emails:
            recipients += self.env["executive.dashboard.export"]._normalize_recipients(
                self.recipient_emails
            )
        return recipients
