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
