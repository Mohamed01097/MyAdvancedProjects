import base64
import io
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

try:
    import xlsxwriter

    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False


_logger = logging.getLogger(__name__)


class ExecutiveDashboardExport(models.AbstractModel):
    _name = "executive.dashboard.export"
    _description = "Executive Dashboard Export Service"

    REPORT_TEMPLATE_XMLID = "executive_dashboard.dashboard_report_document"
    REPORT_ACTION_XMLID = "executive_dashboard.action_dashboard_report_pdf"

    DASHBOARD_METHODS = {
        "overview": "get_overview_data",
        "sales": "get_sales_dashboard_data",
        "crm": "get_crm_dashboard_data",
        "inventory": "get_inventory_dashboard_data",
        "purchase": "get_purchase_dashboard_data",
        "manufacturing": "get_manufacturing_dashboard_data",
        "maintenance": "get_maintenance_dashboard_data",
        "hr": "get_hr_dashboard_data",
        "helpdesk": "get_helpdesk_dashboard_data",
        "pos": "get_pos_dashboard_data",
        "website": "get_website_dashboard_data",
        "alerts": "get_alerts_data",
    }

    DASHBOARD_TITLES = {
        "overview": "Executive Overview",
        "sales": "Sales Dashboard",
        "crm": "CRM Dashboard",
        "inventory": "Inventory Dashboard",
        "purchase": "Purchase Dashboard",
        "manufacturing": "Manufacturing Dashboard",
        "maintenance": "Maintenance Dashboard",
        "hr": "HR Dashboard",
        "helpdesk": "Helpdesk Dashboard",
        "pos": "POS Dashboard",
        "website": "Website Dashboard",
        "alerts": "Alerts Center",
    }

    FILTER_LABELS = {
        "date_from": _("Date From"),
        "date_to": _("Date To"),
        "salesperson_id": _("Salesperson"),
        "sales_team_id": _("Sales Team"),
        "company_id": _("Company"),
        "warehouse_id": _("Warehouse"),
        "vendor_id": _("Vendor"),
        "product_category_id": _("Product Category"),
        "product_id": _("Product"),
        "manufacturing_user_id": _("Manufacturing Responsible"),
        "workcenter_id": _("Work Center"),
        "manufacturing_state": _("Manufacturing State"),
        "maintenance_team_id": _("Maintenance Team"),
        "equipment_id": _("Equipment"),
        "technician_id": _("Technician"),
        "maintenance_stage_id": _("Maintenance Stage"),
        "hr_department_id": _("HR Department"),
        "hr_employee_id": _("Employee"),
        "hr_manager_id": _("Manager"),
        "hr_job_id": _("Job Position"),
        "helpdesk_team_id": _("Helpdesk Team"),
        "helpdesk_user_id": _("Assigned User"),
        "helpdesk_stage_id": _("Ticket Stage"),
        "helpdesk_priority": _("Priority"),
        "pos_config_id": _("POS / Branch"),
        "pos_cashier_id": _("Cashier"),
        "pos_payment_method_id": _("Payment Method"),
        "pos_session_state": _("Session State"),
        "website_id": _("Website"),
        "website_customer_id": _("Website Customer"),
        "website_order_state": _("Website Order State"),
        "department": _("Department"),
        "severity": _("Severity"),
        "responsible_user_id": _("Responsible User"),
    }

    FILTER_OPTION_MAP = {
        "company_id": ("companies", "name"),
        "salesperson_id": ("salespersons", "name"),
        "sales_team_id": ("sales_teams", "name"),
        "warehouse_id": ("warehouses", "name"),
        "vendor_id": ("vendors", "name"),
        "product_category_id": ("product_categories", "complete_name"),
        "product_id": ("products", "display_name"),
        "manufacturing_user_id": ("manufacturing_users", "name"),
        "workcenter_id": ("workcenters", "name"),
        "manufacturing_state": ("manufacturing_states", "name"),
        "maintenance_team_id": ("maintenance_teams", "name"),
        "equipment_id": ("equipment", "display_name"),
        "technician_id": ("technicians", "name"),
        "maintenance_stage_id": ("maintenance_stages", "name"),
        "hr_department_id": ("hr_departments", "complete_name"),
        "hr_employee_id": ("hr_employees", "display_name"),
        "hr_manager_id": ("hr_managers", "display_name"),
        "hr_job_id": ("hr_jobs", "name"),
        "helpdesk_team_id": ("helpdesk_teams", "name"),
        "helpdesk_user_id": ("helpdesk_users", "name"),
        "helpdesk_stage_id": ("helpdesk_stages", "name"),
        "helpdesk_priority": ("helpdesk_priorities", "name"),
        "pos_config_id": ("pos_configs", "name"),
        "pos_cashier_id": ("pos_cashiers", "name"),
        "pos_payment_method_id": ("pos_payment_methods", "name"),
        "pos_session_state": ("pos_session_states", "name"),
        "website_id": ("websites", "name"),
        "website_customer_id": ("website_customers", "display_name"),
        "website_order_state": ("website_order_states", "name"),
        "department": ("alert_departments", "name"),
        "severity": ("alert_severities", "name"),
        "responsible_user_id": ("responsible_users", "name"),
    }

    @api.model
    def get_dashboard_title(self, dashboard_key):
        dashboard_key = dashboard_key if isinstance(dashboard_key, str) else ""
        return self.DASHBOARD_TITLES.get(dashboard_key, _("Dashboard Report"))

    @api.model
    def get_report_settings(self):
        # sudo: ir.config_parameter stores technical reporting defaults, not business data.
        params = self.env["ir.config_parameter"].sudo()
        default_frequency = params.get_param(
            "executive_dashboard.reporting.default_frequency", "daily"
        )
        if default_frequency not in ("daily", "weekly", "monthly"):
            default_frequency = "daily"
        default_recipient_ids = self.env["res.partner"].browse(
            self._parse_int_list(
                params.get_param("executive_dashboard.reporting.default_recipient_ids", "")
            )
        ).exists().ids
        return {
            "default_recipient_ids": default_recipient_ids,
            "default_frequency": default_frequency,
            "default_export_max_rows": self._clamp_int(
                params.get_param("executive_dashboard.reporting.default_export_max_rows", "500"),
                1,
                5000,
                500,
            ),
            "include_charts": self._to_bool(
                params.get_param("executive_dashboard.reporting.include_charts", "True"), True
            ),
            "include_tables": self._to_bool(
                params.get_param("executive_dashboard.reporting.include_tables", "True"), True
            ),
            "include_kpis": self._to_bool(
                params.get_param("executive_dashboard.reporting.include_kpis", "True"), True
            ),
            "pdf_footer_text": params.get_param(
                "executive_dashboard.reporting.pdf_footer_text",
                _("Generated by Executive Dashboard"),
            ),
            "use_company_logo": self._to_bool(
                params.get_param("executive_dashboard.reporting.use_company_logo", "True"), True
            ),
        }

    @api.model
    def get_dashboard_report_data(self, dashboard_key, filters=None, options=None):
        dashboard_key = dashboard_key if isinstance(dashboard_key, str) else ""
        filters = self._as_dict(filters)
        options = self._as_dict(options)
        method_name = self.DASHBOARD_METHODS.get(dashboard_key)
        if not method_name:
            raise UserError(_("Invalid dashboard key: %s") % (dashboard_key or ""))

        dashboard_service = self.env["executive.dashboard.service"]
        method = getattr(dashboard_service, method_name, None)
        if not method:
            raise UserError(_("Dashboard service method is not available: %s") % method_name)
        return method(filters)

    @api.model
    def export_dashboard_excel(self, dashboard_key, filters=None, options=None):
        if not HAS_XLSXWRITER:
            raise UserError(_("xlsxwriter is required for Excel export. Install it with pip."))

        report = self._prepare_report_context(dashboard_key, filters, options)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        title_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 16,
                "font_color": "white",
                "bg_color": "#1f4e79",
                "align": "center",
                "valign": "vcenter",
            }
        )
        section_format = workbook.add_format(
            {"bold": True, "font_color": "white", "bg_color": "#2563eb"}
        )
        label_format = workbook.add_format({"bold": True, "bg_color": "#eef2ff"})
        header_format = workbook.add_format({"bold": True, "bg_color": "#dbeafe", "border": 1})
        cell_format = workbook.add_format({"border": 1})
        note_format = workbook.add_format({"italic": True, "font_color": "#6b7280"})

        self._write_excel_summary(
            workbook,
            report,
            title_format,
            section_format,
            label_format,
            cell_format,
            note_format,
        )
        self._write_excel_tables(
            workbook,
            report,
            section_format,
            header_format,
            cell_format,
            note_format,
        )
        self._write_excel_charts(
            workbook,
            report,
            section_format,
            header_format,
            cell_format,
            note_format,
        )

        workbook.close()
        output.seek(0)
        return output.getvalue()

    @api.model
    def export_dashboard_pdf(self, dashboard_key, filters=None, options=None):
        report = self._prepare_report_context(dashboard_key, filters, options)
        report_action = self._get_or_create_pdf_report_action()
        pdf_content, _report_format = self.env["ir.actions.report"]._render_qweb_pdf(
            report_action,
            [report["company_id"]],
            data={"report_data": report},
        )
        return pdf_content

    @api.model
    def print_dashboard_snapshot(self, dashboard_key, filters=None, options=None):
        options = dict(self._as_dict(options))
        options["snapshot_mode"] = True
        options.setdefault("title", _("Snapshot - %s") % self.get_dashboard_title(dashboard_key))
        return self.export_dashboard_pdf(dashboard_key, filters, options)

    @api.model
    def share_dashboard_snapshot(self, data):
        data = self._as_dict(data)
        dashboard_key = data.get("dashboard_key")
        dashboard_name = self.get_dashboard_title(dashboard_key)
        filters = self._as_dict(data.get("filters_json")) or self._as_dict(data.get("filters"))
        settings = self.get_report_settings()
        recipient_ids = settings["default_recipient_ids"]
        return {
            "name": _("Send Dashboard Report"),
            "type": "ir.actions.act_window",
            "res_model": "executive.dashboard.report.send.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_dashboard_key": dashboard_key,
                "default_format": "pdf",
                "default_recipient_ids": [(6, 0, recipient_ids)] if recipient_ids else False,
                "default_subject": _("Dashboard Snapshot: %s") % dashboard_name,
                "default_message": _(
                    "<p>Please find attached the requested dashboard snapshot.</p>"
                ),
                "default_include_kpis": settings["include_kpis"],
                "default_include_tables": settings["include_tables"],
                "default_include_charts": settings["include_charts"],
                "default_filters_json": filters,
            },
        }

    @api.model
    def create_report_log(self, values):
        vals = dict(self._as_dict(values))
        vals.setdefault("generated_by", self.env.user.id)
        vals.setdefault("generated_datetime", fields.Datetime.now())
        vals.setdefault("company_id", self.env.company.id)
        if vals.get("dashboard_key") and not vals.get("dashboard_name"):
            vals["dashboard_name"] = self.get_dashboard_title(vals["dashboard_key"])
        return self.env["executive.dashboard.report.log"].create(vals)

    @api.model
    def generate_report_attachment(self, dashboard_key, filters=None, format="pdf", options=None):
        filters = self._as_dict(filters)
        options = dict(self._as_dict(options))
        export_format = self._normalize_format(format)
        dashboard_name = self.get_dashboard_title(dashboard_key)
        timestamp = fields.Datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = options.get("filename_suffix")
        suffix = "_%s" % suffix if suffix else ""
        attachments = self.env["ir.attachment"]

        if export_format in ("pdf", "both"):
            pdf_data = self.export_dashboard_pdf(dashboard_key, filters, options)
            attachments |= self._create_report_attachment(
                "%s%s_%s.pdf" % (self._filename_slug(dashboard_name), suffix, timestamp),
                pdf_data,
                "application/pdf",
                options,
            )

        if export_format in ("excel", "both"):
            excel_data = self.export_dashboard_excel(dashboard_key, filters, options)
            attachments |= self._create_report_attachment(
                "%s%s_%s.xlsx" % (self._filename_slug(dashboard_name), suffix, timestamp),
                excel_data,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                options,
            )

        return attachments

    @api.model
    def generate_report_download_action(
        self, dashboard_key, filters=None, format="pdf", report_type="export", options=None
    ):
        filters = self._as_dict(filters)
        options = dict(self._as_dict(options))
        export_format = self._normalize_format(format)
        dashboard_name = self.get_dashboard_title(dashboard_key)
        try:
            attachments = self.generate_report_attachment(
                dashboard_key, filters, export_format, options
            )
            log = self.create_report_log(
                {
                    "name": "%s - %s" % (dashboard_name, report_type.title()),
                    "dashboard_key": dashboard_key,
                    "dashboard_name": dashboard_name,
                    "report_type": report_type,
                    "format": export_format,
                    "status": "success",
                    "attachment_ids": [(6, 0, attachments.ids)],
                    "filters_json": filters,
                }
            )
            attachments.write(
                {"res_model": "executive.dashboard.report.log", "res_id": log.id}
            )
            return self._download_action(attachments[0])
        except Exception as error:
            self._safe_create_failed_log(
                dashboard_key,
                dashboard_name,
                report_type,
                export_format,
                filters,
                error,
            )
            raise

    @api.model
    def send_report_email(self, recipients, subject, body, attachments=None):
        recipient_list = self._normalize_recipients(recipients)
        if not recipient_list:
            raise UserError(_("No valid recipients configured."))

        attachments = attachments or self.env["ir.attachment"]
        mail = self.env["mail.mail"].create(
            {
                "subject": subject or _("Dashboard Report"),
                "body_html": body or _("<p>Please find the dashboard report attached.</p>"),
                "email_to": ", ".join(recipient_list),
                "email_from": self.env.user.email_formatted or self.env.company.email or False,
                "attachment_ids": [(6, 0, attachments.ids)],
                "auto_delete": False,
            }
        )
        mail.send()
        return mail

    def _prepare_report_context(self, dashboard_key, filters=None, options=None):
        filters = self._as_dict(filters)
        options = self._prepare_options(options)
        raw_data = self.get_dashboard_report_data(dashboard_key, filters, options)
        data = self._normalize_dashboard_report_data(raw_data, options["max_rows"])
        dashboard_name = self.get_dashboard_title(dashboard_key)
        report_filters = data["filters"] or self._as_dict(filters)
        filter_options = data["filter_options"]
        selected_company = self._get_report_company(report_filters)
        generated_datetime = fields.Datetime.context_timestamp(self, fields.Datetime.now())

        return {
            "title": options.get("title") or dashboard_name,
            "dashboard_key": dashboard_key,
            "dashboard_name": dashboard_name,
            "company_id": selected_company.id,
            "company_name": selected_company.display_name,
            "generated_by": self.env.user.display_name,
            "generated_datetime": generated_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "filters": self._format_filters(report_filters, filter_options),
            "kpis": data["kpis"] if options["include_kpis"] else [],
            "tables": data["tables"] if options["include_tables"] else [],
            "charts": data["charts"] if options["include_charts"] else [],
            "footer_text": options["pdf_footer_text"],
            "use_company_logo": options["use_company_logo"],
            "max_rows": options["max_rows"],
            "snapshot_mode": bool(options.get("snapshot_mode")),
        }

    def _prepare_options(self, options=None):
        settings = self.get_report_settings()
        options = dict(self._as_dict(options))
        return {
            "title": options.get("title"),
            "snapshot_mode": options.get("snapshot_mode"),
            "include_kpis": options.get("include_kpis", settings["include_kpis"]),
            "include_tables": options.get("include_tables", settings["include_tables"]),
            "include_charts": options.get("include_charts", settings["include_charts"]),
            "pdf_footer_text": options.get("pdf_footer_text", settings["pdf_footer_text"]),
            "use_company_logo": options.get("use_company_logo", settings["use_company_logo"]),
            "max_rows": self._clamp_int(
                options.get("max_rows", settings["default_export_max_rows"]),
                1,
                5000,
                settings["default_export_max_rows"],
            ),
            "filename_suffix": options.get("filename_suffix"),
        }

    def _normalize_dashboard_report_data(self, raw_data, max_rows=500):
        data = raw_data if isinstance(raw_data, dict) else {}
        normalized = {
            "title": "",
            "filters": self._as_dict(data.get("filters")) if isinstance(data, dict) else {},
            "filter_options": self._as_dict(data.get("filter_options"))
            if isinstance(data, dict)
            else {},
            "kpis": [],
            "tables": [],
            "charts": [],
        }

        normalized["kpis"] = self._extract_kpis(raw_data)
        normalized["tables"] = self._extract_tables(raw_data, max_rows)
        normalized["charts"] = self._extract_charts(raw_data, max_rows)
        return normalized

    def _extract_kpis(self, data):
        kpis = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and self._looks_like_kpi(item):
                    self._append_kpi(kpis, item)
            return kpis

        if not isinstance(data, dict):
            return []

        if self._looks_like_kpi(data):
            self._append_kpi(kpis, data)

        for key, value in data.items():
            if key == "kpis" or key.endswith("_kpis"):
                self._append_kpi_collection(kpis, value)
            elif key == "summary":
                self._append_summary_kpis(kpis, value)
            elif isinstance(value, dict) and key not in self._report_metadata_keys():
                kpis.extend(self._extract_kpis(value))
        return kpis

    def _extract_tables(self, data, max_rows):
        tables = []

        if isinstance(data, list):
            table = self._table_from_value(_("Raw Data"), data, max_rows)
            return [table] if table else []

        if not isinstance(data, dict):
            table = self._table_from_value(_("Raw Data"), data, max_rows)
            return [table] if table else []

        for key, value in data.items():
            if key in self._report_metadata_keys() or key.endswith("_kpis"):
                continue
            if key == "tables":
                self._append_table_collection(tables, value, max_rows)
            elif isinstance(value, list):
                table = self._table_from_value(key.replace("_", " ").title(), value, max_rows)
                if table:
                    tables.append(table)
            elif isinstance(value, dict):
                table = self._table_from_mapping(key.replace("_", " ").title(), value, max_rows)
                if table:
                    tables.append(table)
                else:
                    tables.extend(self._extract_tables(value, max_rows))
        return tables

    def _extract_charts(self, data, max_rows):
        charts = self._collect_chart_definitions(data)

        chart_sections = []
        for chart in charts:
            if not isinstance(chart, dict):
                continue
            rows = []
            headers = [_("Label"), _("Value")]
            points = chart.get("data") or []
            if not isinstance(points, list):
                points = []
            labels = chart.get("labels") or []
            if not points and isinstance(labels, list):
                points = labels
            datasets = chart.get("datasets") or []
            if not isinstance(datasets, list):
                datasets = []
            if datasets and not points:
                dataset_lengths = [
                    len(dataset.get("values") or dataset.get("data") or [])
                    for dataset in datasets
                    if isinstance(dataset, dict)
                    and isinstance(dataset.get("values") or dataset.get("data") or [], list)
                ]
                points = list(range(1, (max(dataset_lengths) if dataset_lengths else 0) + 1))
            if datasets:
                headers = [_("Label"), _("Series"), _("Value")]
                for index, point in enumerate(points):
                    label = point.get("label") if isinstance(point, dict) else point
                    for dataset in datasets:
                        if not isinstance(dataset, dict):
                            continue
                        values = dataset.get("values") or dataset.get("data") or []
                        if not isinstance(values, list):
                            values = []
                        value = values[index] if index < len(values) else ""
                        rows.append(
                            [
                                self._format_cell(label),
                                self._format_cell(dataset.get("label") or dataset.get("key")),
                                self._format_cell(value),
                            ]
                        )
            else:
                for point in points:
                    if isinstance(point, dict):
                        rows.append(
                            [
                                self._format_cell(point.get("label")),
                                self._format_cell(point.get("value")),
                            ]
                        )
                    else:
                        rows.append([self._format_cell(point), ""])

            chart_sections.append(
                {
                    "title": self._format_cell(chart.get("title") or chart.get("key")),
                    "headers": headers,
                    "rows": rows[:max_rows],
                    "limited": len(rows) > max_rows,
                    "limit": max_rows,
                }
            )
        return chart_sections

    def _append_kpi_collection(self, kpis, value):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    if self._looks_like_kpi(item):
                        self._append_kpi(kpis, item)
                    else:
                        kpis.extend(self._extract_kpis(item))
        elif isinstance(value, dict):
            if self._looks_like_kpi(value):
                self._append_kpi(kpis, value)
            else:
                for key, metric in value.items():
                    if isinstance(metric, dict) and self._looks_like_kpi(metric):
                        item = dict(metric)
                        item.setdefault("label", key)
                        self._append_kpi(kpis, item)
                    elif not isinstance(metric, (dict, list, tuple)):
                        kpis.append(
                            {
                                "label": self._format_cell(key).replace("_", " ").title(),
                                "value": self._format_cell(metric),
                            }
                        )

    def _append_kpi(self, kpis, kpi):
        if not isinstance(kpi, dict):
            return
        display_value = kpi.get("display_value")
        value = display_value if display_value not in (None, False, "") else kpi.get("value")
        kpis.append(
            {
                "label": self._format_cell(kpi.get("label") or kpi.get("key") or _("KPI")),
                "value": self._format_cell(value),
            }
        )

    def _append_summary_kpis(self, kpis, summary):
        if not isinstance(summary, dict):
            return
        summary_labels = {
            "total": _("Total Alerts"),
            "critical": _("Critical Alerts"),
            "high": _("High Alerts"),
            "medium": _("Medium Alerts"),
            "low": _("Low Alerts"),
        }
        for key, value in summary.items():
            if isinstance(value, (dict, list, tuple)):
                continue
            kpis.append(
                {
                    "label": summary_labels.get(key, key.replace("_", " ").title()),
                    "value": self._format_cell(value),
                }
            )

    def _looks_like_kpi(self, value):
        return isinstance(value, dict) and (
            "value" in value or "display_value" in value
        ) and ("label" in value or "key" in value)

    def _append_table_collection(self, tables, value, max_rows):
        if isinstance(value, list):
            for index, table_value in enumerate(value, 1):
                title = _("Table %s") % index
                table = self._table_from_mapping(title, table_value, max_rows)
                if not table:
                    table = self._table_from_value(title, table_value, max_rows)
                if table:
                    tables.append(table)
        elif isinstance(value, dict):
            for key, table_value in value.items():
                title = key.replace("_", " ").title()
                table = self._table_from_mapping(title, table_value, max_rows)
                if not table:
                    table = self._table_from_value(title, table_value, max_rows)
                if table:
                    tables.append(table)

    def _table_from_mapping(self, title, value, max_rows):
        if not isinstance(value, dict):
            return False
        headers = value.get("headers")
        rows = value.get("rows")
        records = value.get("records") or value.get("data")
        if isinstance(headers, list) and isinstance(rows, list):
            safe_rows = [
                [self._format_cell(cell) for cell in row]
                if isinstance(row, (list, tuple))
                else [self._format_cell(row)]
                for row in rows[:max_rows]
            ]
            return {
                "title": title,
                "headers": [self._format_cell(header) for header in headers],
                "rows": safe_rows,
                "limited": len(rows) > max_rows,
                "limit": max_rows,
            }
        if isinstance(records, list):
            return self._table_from_value(title, records, max_rows)
        return False

    def _table_from_value(self, title, value, max_rows):
        if value in (None, False, ""):
            return False
        if not isinstance(value, list):
            return {
                "title": title,
                "headers": [_("Value")],
                "rows": [[self._format_cell(value)]],
                "limited": False,
                "limit": max_rows,
            }

        if not value:
            return False

        records = [row for row in value if isinstance(row, dict)]
        if records:
            headers = self._table_headers(records)
            if not headers:
                return False
            rows = [
                [self._format_cell(record.get(header)) for header in headers]
                for record in records[:max_rows]
            ]
            return {
                "title": title,
                "headers": [header.replace("_", " ").title() for header in headers],
                "rows": rows,
                "limited": len(records) > max_rows,
                "limit": max_rows,
            }

        rows = [[self._format_cell(item)] for item in value[:max_rows]]
        return {
            "title": title,
            "headers": [_("Value")],
            "rows": rows,
            "limited": len(value) > max_rows,
            "limit": max_rows,
        }

    def _collect_chart_definitions(self, data):
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict) and self._looks_like_chart(item)]
        if not isinstance(data, dict):
            return []

        charts = []
        chart_data = data.get("chart_data")
        if isinstance(chart_data, dict):
            chart_values = chart_data.get("charts")
            if isinstance(chart_values, list):
                charts.extend(chart_values)
        elif isinstance(chart_data, list):
            charts.extend(chart_data)

        direct_charts = data.get("charts")
        if isinstance(direct_charts, list):
            charts.extend(direct_charts)
        elif isinstance(direct_charts, dict):
            charts.append(direct_charts)

        if self._looks_like_chart(data):
            charts.append(data)

        for key, value in data.items():
            if key in self._report_metadata_keys() or key in ("chart_data", "charts"):
                continue
            if isinstance(value, dict):
                charts.extend(self._collect_chart_definitions(value))
            elif isinstance(value, list):
                charts.extend(
                    item for item in value if isinstance(item, dict) and self._looks_like_chart(item)
                )
        return charts

    def _looks_like_chart(self, value):
        return isinstance(value, dict) and (
            isinstance(value.get("data"), list) or isinstance(value.get("datasets"), list)
        ) and ("title" in value or "key" in value)

    def _report_metadata_keys(self):
        return {
            "filters",
            "filter_options",
            "currency_id",
            "meta",
            "last_updated",
            "summary",
            "chart_data",
            "charts",
            "kpis",
        }

    def _write_excel_summary(
        self,
        workbook,
        report,
        title_format,
        section_format,
        label_format,
        cell_format,
        note_format,
    ):
        sheet = workbook.add_worksheet(_("Summary")[:31])
        sheet.set_column("A:A", 28)
        sheet.set_column("B:D", 35)
        row = 0
        sheet.merge_range(row, 0, row, 3, report["title"], title_format)
        row += 2

        row = self._write_excel_pairs(
            sheet,
            row,
            _("Report Information"),
            [
                (_("Dashboard"), report["dashboard_name"]),
                (_("Company"), report["company_name"]),
                (_("Generated By"), report["generated_by"]),
                (_("Generated Date/Time"), report["generated_datetime"]),
            ],
            section_format,
            label_format,
            cell_format,
        )

        filters = report["filters"] or [{"label": _("Filters"), "value": _("No filters applied")}]
        row = self._write_excel_pairs(
            sheet,
            row + 1,
            _("Applied Filters"),
            [(item["label"], item["value"]) for item in filters],
            section_format,
            label_format,
            cell_format,
        )

        if report["kpis"]:
            row += 1
            sheet.write(row, 0, _("Key Performance Indicators"), section_format)
            row += 1
            sheet.write(row, 0, _("KPI"), label_format)
            sheet.write(row, 1, _("Value"), label_format)
            row += 1
            for kpi in report["kpis"]:
                sheet.write(row, 0, kpi["label"], cell_format)
                sheet.write(row, 1, kpi["value"], cell_format)
                row += 1
        else:
            sheet.write(row + 1, 0, _("No KPI data available."), note_format)

    def _write_excel_tables(self, workbook, report, section_format, header_format, cell_format, note_format):
        sheet = workbook.add_worksheet(_("Tables")[:31])
        sheet.set_column("A:Z", 22)
        row = 0
        if not report["tables"]:
            sheet.write(row, 0, _("No table data available."), note_format)
            return
        for table in report["tables"]:
            row = self._write_excel_table(sheet, row, table, section_format, header_format, cell_format, note_format)
            row += 2

    def _write_excel_charts(self, workbook, report, section_format, header_format, cell_format, note_format):
        sheet = workbook.add_worksheet(_("Chart Data")[:31])
        sheet.set_column("A:Z", 22)
        row = 0
        if not report["charts"]:
            sheet.write(row, 0, _("No chart data available."), note_format)
            return
        for chart in report["charts"]:
            row = self._write_excel_table(sheet, row, chart, section_format, header_format, cell_format, note_format)
            row += 2

    def _write_excel_pairs(self, sheet, row, title, pairs, section_format, label_format, cell_format):
        sheet.write(row, 0, title, section_format)
        row += 1
        for label, value in pairs:
            sheet.write(row, 0, label, label_format)
            sheet.write(row, 1, self._format_cell(value), cell_format)
            row += 1
        return row

    def _write_excel_table(self, sheet, row, table, section_format, header_format, cell_format, note_format):
        sheet.write(row, 0, table["title"], section_format)
        row += 1
        for col, header in enumerate(table["headers"]):
            sheet.write(row, col, header, header_format)
        row += 1
        if table["rows"]:
            for record in table["rows"]:
                for col, value in enumerate(record):
                    sheet.write(row, col, value, cell_format)
                row += 1
        else:
            sheet.write(row, 0, _("No data available."), note_format)
            row += 1
        if table["limited"]:
            sheet.write(row, 0, _("Data limited to first %s rows.") % table["limit"], note_format)
            row += 1
        return row

    def _create_report_attachment(self, filename, content, mimetype, options):
        options = self._as_dict(options)
        vals = {
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(content),
            "mimetype": mimetype,
            "res_model": options.get("res_model") or False,
            "res_id": options.get("res_id") or 0,
        }
        if "company_id" in self.env["ir.attachment"]._fields:
            vals["company_id"] = self.env.company.id
        return self.env["ir.attachment"].create(vals)

    def _get_or_create_pdf_report_action(self):
        self._ensure_pdf_report_template()
        Report = self.env["ir.actions.report"].sudo()
        report = self.env.ref(self.REPORT_ACTION_XMLID, raise_if_not_found=False)
        if report and report._name == "ir.actions.report":
            if (
                report.report_name != self.REPORT_TEMPLATE_XMLID
                or report.report_file != self.REPORT_TEMPLATE_XMLID
            ):
                report.sudo().write(
                    {
                        "report_name": self.REPORT_TEMPLATE_XMLID,
                        "report_file": self.REPORT_TEMPLATE_XMLID,
                    }
                )
            return report

        report = Report.search(
            [("report_name", "=", self.REPORT_TEMPLATE_XMLID)],
            limit=1,
        )
        if report:
            return report

        # sudo: this is a technical report action used to render the current user's data.
        return Report.create(
            {
                "name": "Executive Dashboard Report",
                "model": "res.company",
                "report_type": "qweb-pdf",
                "report_name": self.REPORT_TEMPLATE_XMLID,
                "report_file": self.REPORT_TEMPLATE_XMLID,
            }
        )

    def _ensure_pdf_report_template(self):
        view = self.env["ir.ui.view"].sudo().search(
            [("key", "=", self.REPORT_TEMPLATE_XMLID), ("type", "=", "qweb")],
            limit=1,
        )
        if not view:
            view = self.env.ref(self.REPORT_TEMPLATE_XMLID, raise_if_not_found=False)
        if not view:
            raise UserError(
                _(
                    "Executive Dashboard PDF template is not loaded. Upgrade the "
                    "executive_dashboard module so reports/dashboard_report_templates.xml "
                    "is installed."
                )
            )
        return view

    def _safe_create_failed_log(
        self, dashboard_key, dashboard_name, report_type, export_format, filters, error
    ):
        try:
            self.create_report_log(
                {
                    "name": "%s - %s (Failed)" % (dashboard_name, report_type.title()),
                    "dashboard_key": dashboard_key,
                    "dashboard_name": dashboard_name,
                    "report_type": report_type,
                    "format": export_format,
                    "status": "failed",
                    "error_message": str(error),
                    "filters_json": filters,
                }
            )
        except Exception:
            _logger.exception("Unable to create executive dashboard failed export log.")

    def _download_action(self, attachment):
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def _format_filters(self, filters, filter_options):
        filters = self._as_dict(filters)
        filter_options = self._as_dict(filter_options)
        rows = []
        for key, value in (filters or {}).items():
            if key == "company_ids" or value in (False, None, "", []):
                continue
            rows.append(
                {
                    "label": self.FILTER_LABELS.get(key, key.replace("_", " ").title()),
                    "value": self._filter_display_value(key, value, filter_options),
                }
            )
        return rows

    def _filter_display_value(self, key, value, filter_options):
        filter_options = self._as_dict(filter_options)
        option_info = self.FILTER_OPTION_MAP.get(key)
        if not option_info:
            return self._format_cell(value)
        options_key, label_field = option_info
        options = filter_options.get(options_key, [])
        if not isinstance(options, list):
            options = []
        for option in options:
            if not isinstance(option, dict):
                continue
            if str(option.get("id")) == str(value):
                return self._format_cell(
                    option.get(label_field) or option.get("name") or option.get("display_name")
                )
        return self._format_cell(value)

    def _get_report_company(self, filters):
        filters = self._as_dict(filters)
        company_id = self._parse_int(filters.get("company_id"))
        if company_id and company_id in self.env.companies.ids:
            return self.env["res.company"].browse(company_id)
        return self.env.company

    def _as_dict(self, value):
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    def _table_headers(self, records):
        headers = []
        for record in records:
            if not isinstance(record, dict):
                continue
            for key in record:
                if key not in headers:
                    headers.append(key)
        return headers

    def _format_cell(self, value):
        if value in (False, None):
            return ""
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return str(value)

    def _filename_slug(self, value):
        return "".join(char if char.isalnum() else "_" for char in value).strip("_") or "dashboard"

    def _normalize_format(self, value):
        if value not in ("pdf", "excel", "both"):
            raise UserError(_("Invalid report format: %s") % (value or ""))
        return value

    def _normalize_recipients(self, recipients):
        if isinstance(recipients, str):
            raw_recipients = recipients.replace(";", ",").split(",")
        else:
            raw_recipients = recipients or []
        return [email.strip() for email in raw_recipients if email and email.strip()]

    def _parse_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return False

    def _parse_int_list(self, value):
        ids = []
        for item in (value or "").replace(";", ",").split(","):
            parsed = self._parse_int(item.strip())
            if parsed:
                ids.append(parsed)
        return ids

    def _to_bool(self, value, default=False):
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return default
        return str(value).lower() in ("1", "true", "yes", "y", "on")

    def _clamp_int(self, value, minimum, maximum, default):
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = default
        return max(minimum, min(maximum, value))
