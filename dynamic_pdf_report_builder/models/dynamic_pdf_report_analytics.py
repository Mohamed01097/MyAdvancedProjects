import logging
from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

LOG_RETENTION_DAYS_PARAM = "dynamic_pdf_report_builder.log_retention_days"
LOG_SOURCE_SELECTION = (
    ("print_menu", "Print Menu"),
    ("preview", "Preview"),
    ("builder", "Builder"),
    ("unknown", "Unknown"),
)


class DynamicPdfReportPrintLog(models.Model):
    _name = "dynamic.pdf.report.print.log"
    _description = "Dynamic PDF Report Print Log"
    _order = "printed_on desc, id desc"

    report_id = fields.Many2one(
        "dynamic.pdf.report",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    model_name = fields.Char(index=True)
    record_count = fields.Integer(default=0)
    print_quantity = fields.Integer(
        string="Prints",
        default=1,
        readonly=True,
    )
    printed_on = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
        index=True,
    )
    source = fields.Selection(
        LOG_SOURCE_SELECTION,
        default="unknown",
        required=True,
        index=True,
    )

    @api.model
    def _log_dynamic_report_print(self, report, record_count=0, source="unknown"):
        report = report.sudo().exists()
        if not report:
            return False

        try:
            with self.env.cr.savepoint():
                source = self._normalize_source(source)
                printed_on = fields.Datetime.now()
                self.sudo().create({
                    "report_id": report.id,
                    "user_id": self.env.user.id,
                    "model_name": report.model_name,
                    "record_count": record_count or 0,
                    "printed_on": printed_on,
                    "source": source,
                })
                report_vals = {}
                if "last_printed_on" in report._fields:
                    report_vals["last_printed_on"] = printed_on
                if "last_printed_by" in report._fields:
                    report_vals["last_printed_by"] = self.env.user.id
                if "print_count" in report._fields:
                    report_vals["print_count"] = (report.print_count or 0) + 1
                if report_vals:
                    report.sudo().write(report_vals)
        except Exception:
            _logger.exception("Unable to log dynamic PDF report print for report id %s.", report.id)
            return False
        return True

    @api.model
    def _normalize_source(self, source):
        valid_sources = {value for value, _label in LOG_SOURCE_SELECTION}
        return source if source in valid_sources else "unknown"

    @api.model
    def _cron_clean_old_logs(self):
        retention_days = self._get_log_retention_days()
        cutoff = fields.Datetime.now() - timedelta(days=retention_days)
        old_logs = self.sudo().search([("printed_on", "<", cutoff)])
        deleted_count = len(old_logs)
        old_logs.unlink()
        return deleted_count

    @api.model
    def _get_log_retention_days(self):
        raw_value = self.env["ir.config_parameter"].sudo().get_param(LOG_RETENTION_DAYS_PARAM, "365")
        try:
            retention_days = int(raw_value)
        except (TypeError, ValueError):
            retention_days = 365
        return max(retention_days, 0)


class DynamicPdfReportDashboard(models.Model):
    _name = "dynamic.pdf.report.dashboard"
    _description = "Dynamic PDF Report Dashboard"

    name = fields.Char(default="Dashboard", required=True)
    total_report_count = fields.Integer(compute="_compute_metrics")
    draft_report_count = fields.Integer(compute="_compute_metrics")
    done_report_count = fields.Integer(compute="_compute_metrics")
    total_print_count = fields.Integer(compute="_compute_metrics")
    printed_today_count = fields.Integer(compute="_compute_metrics")
    printed_this_month_count = fields.Integer(compute="_compute_metrics")

    def _compute_metrics(self):
        self._check_analytics_access()
        Report = self.env["dynamic.pdf.report"].sudo()
        Log = self.env["dynamic.pdf.report.print.log"].sudo()
        today_start = self._get_today_start()
        tomorrow_start = today_start + timedelta(days=1)
        month_start = today_start.replace(day=1)

        metrics = {
            "total_report_count": Report.search_count([]),
            "draft_report_count": Report.search_count([("state", "=", "draft")]),
            "done_report_count": Report.search_count([("state", "=", "done")]),
            "total_print_count": Log.search_count([]),
            "printed_today_count": Log.search_count([
                ("printed_on", ">=", today_start),
                ("printed_on", "<", tomorrow_start),
            ]),
            "printed_this_month_count": Log.search_count([
                ("printed_on", ">=", month_start),
                ("printed_on", "<", tomorrow_start),
            ]),
        }
        for dashboard in self:
            for field_name, value in metrics.items():
                dashboard[field_name] = value

    def action_open_reports(self):
        self._check_analytics_access()
        return self.env.ref("dynamic_pdf_report_builder.action_dynamic_pdf_report_builder").read()[0]

    def action_open_print_logs(self):
        self._check_analytics_access()
        return self.env.ref("dynamic_pdf_report_builder.action_dynamic_pdf_report_print_log").read()[0]

    def action_open_today_print_logs(self):
        action = self.action_open_print_logs()
        today_start = self._get_today_start()
        tomorrow_start = today_start + timedelta(days=1)
        action["domain"] = [
            ("printed_on", ">=", fields.Datetime.to_string(today_start)),
            ("printed_on", "<", fields.Datetime.to_string(tomorrow_start)),
        ]
        return action

    def action_open_month_print_logs(self):
        action = self.action_open_print_logs()
        today_start = self._get_today_start()
        month_start = today_start.replace(day=1)
        tomorrow_start = today_start + timedelta(days=1)
        action["domain"] = [
            ("printed_on", ">=", fields.Datetime.to_string(month_start)),
            ("printed_on", "<", fields.Datetime.to_string(tomorrow_start)),
        ]
        return action

    def _get_today_start(self):
        today = fields.Date.context_today(self)
        return datetime.combine(today, time.min)

    def _check_analytics_access(self):
        if not self.env.user.has_group("base.group_system"):
            raise UserError(_("Only Settings users can view dynamic report analytics."))
