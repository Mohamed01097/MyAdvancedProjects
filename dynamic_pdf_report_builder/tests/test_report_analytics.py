from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from ..const import REPORT_TEMPLATE_XML_ID


@tagged("post_install", "-at_install")
class TestDynamicPdfReportAnalytics(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report_model = cls.env["dynamic.pdf.report"]
        cls.log_model = cls.env["dynamic.pdf.report.print.log"]
        cls.partner_model = cls.env["ir.model"].search([("model", "=", "res.partner")], limit=1)
        cls.partner_name_field = cls.env["ir.model.fields"].search(
            [("model_id", "=", cls.partner_model.id), ("name", "=", "name")],
            limit=1,
        )

    def _create_partner_report(self):
        report = self.report_model.create({
            "name": "Analytics Partner Report",
            "model_id": self.partner_model.id,
            "field_line_ids": [
                (0, 0, {"field_id": self.partner_name_field.id, "sequence": 10}),
            ],
        })
        report.action_create_report()
        return report

    def test_rendering_dynamic_report_creates_print_log(self):
        report = self._create_partner_report()
        partner = self.env["res.partner"].create({"name": "Analytics Partner"})

        self.env["ir.actions.report"].with_context(
            dynamic_pdf_report_id=report.id,
            dynamic_pdf_report_source="preview",
        )._render_qweb_pdf(REPORT_TEMPLATE_XML_ID, partner.ids)

        log = self.log_model.search([("report_id", "=", report.id)], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.user_id, self.env.user)
        self.assertEqual(log.model_name, "res.partner")
        self.assertEqual(log.record_count, 1)
        self.assertEqual(log.source, "preview")
        self.assertEqual(report.print_count, 1)
        self.assertEqual(report.last_printed_by, self.env.user)
        self.assertTrue(report.last_printed_on)

    def test_cleanup_old_logs_uses_retention_parameter(self):
        report = self._create_partner_report()
        old_log = self.log_model.create({
            "report_id": report.id,
            "user_id": self.env.user.id,
            "model_name": report.model_name,
            "record_count": 1,
            "printed_on": fields.Datetime.now() - timedelta(days=400),
            "source": "unknown",
        })
        recent_log = self.log_model.create({
            "report_id": report.id,
            "user_id": self.env.user.id,
            "model_name": report.model_name,
            "record_count": 1,
            "printed_on": fields.Datetime.now(),
            "source": "unknown",
        })

        self.env["ir.config_parameter"].sudo().set_param(
            "dynamic_pdf_report_builder.log_retention_days",
            "365",
        )
        deleted_count = self.log_model._cron_clean_old_logs()

        self.assertEqual(deleted_count, 1)
        self.assertFalse(old_log.exists())
        self.assertTrue(recent_log.exists())
