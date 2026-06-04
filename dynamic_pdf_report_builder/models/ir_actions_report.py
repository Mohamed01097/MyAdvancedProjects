from odoo import fields, models

from ..const import REPORT_TEMPLATE_XML_ID


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    context = fields.Char(default="{}")
    dynamic_pdf_report_id = fields.Many2one(
        "dynamic.pdf.report",
        string="Dynamic PDF Report",
        ondelete="cascade",
        readonly=True,
    )

    def _get_dynamic_pdf_report_action_from_context(self):
        report_config_id = self.env.context.get("dynamic_pdf_report_id")
        if not report_config_id:
            return self.env["ir.actions.report"]
        report_config = self.env["dynamic.pdf.report"].sudo().browse(report_config_id).exists()
        return report_config.report_action_id.sudo() if report_config else self.env["ir.actions.report"]

    def _get_report_from_name(self, report_name):
        if report_name == REPORT_TEMPLATE_XML_ID:
            action = self._get_dynamic_pdf_report_action_from_context()
            if action:
                return action
        return super()._get_report_from_name(report_name)

    def _get_report(self, report_ref):
        if report_ref == REPORT_TEMPLATE_XML_ID:
            action = self._get_dynamic_pdf_report_action_from_context()
            if action:
                return action
        return super()._get_report(report_ref)

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        result = super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        self._log_dynamic_pdf_report_print(report_ref, res_ids)
        return result

    def _log_dynamic_pdf_report_print(self, report_ref, res_ids=None):
        report_config = self._get_dynamic_pdf_report_config_for_logging(report_ref)
        if not report_config:
            return False

        record_count = self._get_dynamic_pdf_report_record_count(res_ids)
        source = self.env.context.get("dynamic_pdf_report_source") or "unknown"
        return self.env["dynamic.pdf.report.print.log"]._log_dynamic_report_print(
            report_config,
            record_count=record_count,
            source=source,
        )

    def _get_dynamic_pdf_report_config_for_logging(self, report_ref):
        report_action = self._get_report(report_ref)
        report_config = report_action.dynamic_pdf_report_id if report_action else self.env["dynamic.pdf.report"]
        if not report_config:
            report_config_id = self.env.context.get("dynamic_pdf_report_id")
            report_config = self.env["dynamic.pdf.report"].sudo().browse(report_config_id).exists()
        return report_config

    def _get_dynamic_pdf_report_record_count(self, res_ids=None):
        if not res_ids:
            return 0
        if isinstance(res_ids, int):
            return 1
        return len(res_ids)
