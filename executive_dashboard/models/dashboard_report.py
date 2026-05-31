from odoo import api, models
from odoo.tools.image import image_data_uri


class ExecutiveDashboardReport(models.AbstractModel):
    _name = "report.executive_dashboard.dashboard_report_document"
    _description = "Executive Dashboard PDF Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data if isinstance(data, dict) else {}
        report_data = data.get("report_data") if isinstance(data.get("report_data"), dict) else {}
        company_id = report_data.get("company_id")
        company = self.env["res.company"].browse(company_id).exists() if company_id else self.env.company
        company = company or self.env.company
        report_data.setdefault("title", "Dashboard Report")
        report_data.setdefault("dashboard_name", "")
        report_data.setdefault("generated_by", self.env.user.display_name)
        report_data.setdefault("generated_datetime", "")
        report_data.setdefault("company_name", company.display_name)
        report_data.setdefault("filters", [])
        report_data.setdefault("kpis", [])
        report_data.setdefault("tables", [])
        report_data.setdefault("charts", [])
        report_data.setdefault("footer_text", "")
        for key in ("filters", "kpis", "tables", "charts"):
            value = report_data.get(key)
            report_data[key] = (
                [item for item in value if isinstance(item, dict)]
                if isinstance(value, list)
                else []
            )
        return {
            "doc_ids": docids,
            "doc_model": "res.company",
            "docs": company,
            "company": company,
            "image_data_uri": image_data_uri,
            "report": report_data,
        }
