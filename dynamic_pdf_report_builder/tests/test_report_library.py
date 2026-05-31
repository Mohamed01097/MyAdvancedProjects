import json

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDynamicPdfReportLibrary(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["ir.model"].search([("model", "=", "res.partner")], limit=1)
        cls.library_model = cls.env["dynamic.pdf.report.library"]

    def _create_library_template(self):
        payload = {
            "version": "1.0",
            "module": "dynamic_pdf_report_builder",
            "report": {
                "name": "Partner Library Template",
                "report_title": "Partner Report",
                "model": "res.partner",
                "styling": {
                    "layout_style": "classic",
                    "primary_color": "#111827",
                    "table_header_bg_color": "#111827",
                },
            },
            "fields": [
                {"sequence": 10, "field_name": "name", "show_label": True},
                {"sequence": 20, "field_name": "email", "show_label": True},
            ],
            "line_sections": [
                {
                    "sequence": 10,
                    "name": "Contacts",
                    "one2many_field_name": "child_ids",
                    "show_section_title": True,
                    "line_fields": [
                        {"sequence": 10, "field_name": "name", "show_label": True},
                        {"sequence": 20, "field_name": "email", "show_label": True},
                    ],
                }
            ],
            "blocks": [
                {
                    "sequence": 10,
                    "block_type": "note",
                    "title": "Notes",
                    "content": "<p>Partner summary.</p>",
                    "position": "after_main_table",
                    "alignment": "left",
                    "is_active": True,
                    "source_type": "record_name",
                }
            ],
            "formulas": [
                {
                    "sequence": 10,
                    "name": "Contact Label",
                    "code": "contact_label",
                    "scope": "main_record",
                    "formula_type": "concat",
                    "active": True,
                    "formula_expression": "name email",
                    "separator": " - ",
                    "output_label": "Contact Label",
                    "show_in_report": True,
                    "show_in_line_tables": True,
                }
            ],
            "groups": [
                {"sequence": 10, "field_name": "country_id"},
            ],
            "aggregates": [
                {"field_name": "name", "aggregate_type": "count"},
            ],
        }
        return self.library_model.create({
            "name": "Partner Library Template",
            "code": "partner_library_template",
            "category": "generic",
            "model_name": "res.partner",
            "template_json": json.dumps(payload),
        })

    def test_create_custom_copy_from_library_template(self):
        library_template = self._create_library_template()

        action = library_template.action_create_custom_copy()
        report = self.env["dynamic.pdf.report"].browse(action["res_id"])

        self.assertEqual(report.model_id, self.partner_model)
        self.assertEqual(report.state, "draft")
        self.assertEqual(report.field_line_ids.sorted("sequence").mapped("field_name"), ["name", "email"])
        self.assertEqual(report.line_section_ids.one2many_field_name, "child_ids")
        self.assertEqual(report.line_section_ids.line_field_ids.sorted("sequence").mapped("field_name"), ["name", "email"])
        self.assertEqual(report.block_ids.block_type, "note")
        self.assertEqual(report.formula_ids.code, "contact_label")
        self.assertEqual(report.group_ids.field_name, "country_id")
        self.assertEqual(report.aggregate_ids.aggregate_type, "count")

    def test_install_template_creates_report_action(self):
        library_template = self._create_library_template()

        action = library_template.action_install_template()
        report = self.env["dynamic.pdf.report"].browse(action["res_id"])

        self.assertEqual(report.state, "done")
        self.assertTrue(report.report_action_id)
