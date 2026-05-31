from datetime import date, datetime
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date, format_datetime, html2plaintext

from ..const import ALLOWED_FIELD_TYPES, BLOCK_POSITIONS, REPORT_TEMPLATE_XML_ID


class ReportDynamicPdfReport(models.AbstractModel):
    _name = "report.dynamic_pdf_report_builder.dynamic_pdf_report_template"
    _description = "Dynamic PDF Report Template"

    @api.model
    def _get_report_values(self, docids, data=None):
        report_action = self.env["ir.actions.report"]._get_report_from_name(REPORT_TEMPLATE_XML_ID)
        report_config = report_action.dynamic_pdf_report_id
        if not report_config:
            report_config = self.env["dynamic.pdf.report"].sudo().search(
                [("report_action_id", "=", report_action.id)],
                limit=1,
            )
        if not report_config:
            raise UserError(_("Unable to find the dynamic report configuration for this report action."))
        if not report_config.model_name or report_config.model_name not in self.env:
            raise UserError(_("The configured model is not available in the registry."))

        field_lines = report_config.field_line_ids.filtered(
            lambda line: line.field_id and line.field_type in ALLOWED_FIELD_TYPES
        ).sorted("sequence")
        if not field_lines:
            raise UserError(_("This dynamic report has no printable fields configured."))

        docs = self.env[report_config.model_name].browse(docids)
        report_rows = self._get_record_rows(docs)
        line_section_data = self._get_line_section_data(report_config)
        active_blocks = report_config.block_ids.filtered("is_active").sorted("sequence")
        blocks_by_position = self._get_blocks_by_position(active_blocks)

        return {
            "doc_ids": docids,
            "doc_model": report_config.model_name,
            "docs": docs,
            "primary_doc": docs[:1],
            "report_rows": report_rows,
            "report_config": report_config,
            "field_lines": field_lines,
            "line_section_data": line_section_data,
            "blocks_by_position": blocks_by_position,
            "company": self.env.company,
            "print_date": format_datetime(self.env, fields.Datetime.now()),
            "template_preset_label": self._get_template_preset_label(report_config),
            "style": self._get_style_values(report_config),
            "format_value": self._format_value,
            "get_line_records": self._get_line_records,
            "get_record_rows": self._get_record_rows,
            "get_blocks": self._get_blocks,
            "get_block_title": self._get_block_title,
            "get_barcode_url": self._get_barcode_url,
        }

    @api.model
    def _get_blocks_by_position(self, blocks):
        return {
            position: blocks.filtered(lambda block, position=position: block.position == position)
            for position in BLOCK_POSITIONS
        }

    @api.model
    def _get_blocks(self, blocks_by_position, position):
        return blocks_by_position.get(position, self.env["dynamic.pdf.report.block"])

    @api.model
    def _get_block_title(self, block):
        if block.title:
            return block.title
        if block.block_type == "terms_conditions":
            return _("Terms & Conditions")
        if block.block_type == "note":
            return _("Notes")
        return ""

    @api.model
    def _get_block_value(self, block, record):
        source_type = block.source_type or "record_name"
        if source_type == "static_value":
            return block.static_value or ""
        if source_type == "custom_url":
            record_id = record[:1].id if record else ""
            return "%s%s" % (block.custom_url_prefix or "", record_id)
        if not record:
            return ""

        record = record[:1]
        if source_type == "record_name":
            return record.display_name or ""
        if source_type == "field_value":
            field = block.source_field_id
            if not field or field.name not in record._fields:
                return ""
            value = record[field.name]
            if field.ttype == "selection" and value:
                selection = dict(record._fields[field.name]._description_selection(self.env))
                return selection.get(value, value)
            return self._format_block_value(value)
        return ""

    @api.model
    def _format_block_value(self, value):
        if value is False or value is None:
            return ""
        if hasattr(value, "mapped") and hasattr(value, "_name"):
            return ", ".join(value.mapped("display_name"))
        if isinstance(value, datetime):
            return format_datetime(self.env, value)
        if isinstance(value, date):
            return format_date(self.env, value)
        return str(value)

    @api.model
    def _get_barcode_url(self, block, record, barcode_type):
        value = self._get_block_value(block, record)
        if not value:
            return ""
        size = max(block.size or 120, 1)
        return "/report/barcode/%s/%s?width=%d&height=%d" % (
            barcode_type,
            quote(str(value), safe=""),
            size,
            size,
        )

    @api.model
    def _get_template_preset_label(self, report_config):
        if not report_config.template_preset:
            return ""
        return dict(report_config._fields["template_preset"].selection).get(
            report_config.template_preset,
            report_config.template_preset,
        )

    @api.model
    def _get_line_section_data(self, report_config):
        line_section_data = []
        for section in report_config.line_section_ids.sorted("sequence"):
            if (
                not section.one2many_field_id
                or section.one2many_field_id.ttype != "one2many"
                or not section.related_model_name
                or section.related_model_name not in self.env
            ):
                continue

            field_lines = section.line_field_ids.filtered(
                lambda line: (
                    line.field_id
                    and line.field_type in ALLOWED_FIELD_TYPES
                    and line.field_id.model_id == section.related_model_id
                )
            ).sorted("sequence")
            if field_lines:
                line_section_data.append({
                    "section": section,
                    "field_lines": field_lines,
                })
        return line_section_data

    @api.model
    def _get_record_rows(self, records):
        return [(record, index % 2 == 1) for index, record in enumerate(records)]

    @api.model
    def _get_line_records(self, doc, section):
        field_name = section.one2many_field_name
        if not field_name or field_name not in doc._fields:
            if section.related_model_name and section.related_model_name in self.env:
                return self.env[section.related_model_name].browse()
            return doc.browse()
        return doc[field_name]

    @api.model
    def _format_value(self, record, field_line):
        field_name = field_line.field_name
        if not field_name or field_name not in record._fields:
            return ""

        field_type = field_line.field_type
        value = record[field_name]

        if field_type == "boolean":
            return _("Yes") if value else _("No")
        if field_type == "many2one":
            return value.display_name if value else ""
        if value is False or value is None:
            return ""
        if field_type == "date":
            return format_date(self.env, value)
        if field_type == "datetime":
            return format_datetime(self.env, value)
        if field_type == "selection":
            selection = dict(record._fields[field_name]._description_selection(self.env))
            return selection.get(value, value or "")
        if field_type == "html":
            return html2plaintext(value or "")
        return value

    @api.model
    def _get_style_values(self, report_config):
        text_align = "right" if report_config.direction == "rtl" else "left"
        font_size = max(report_config.font_size or 12, 1)
        title_font_size = max(report_config.title_font_size or 22, 1)
        cell_border = self._get_cell_border_style(report_config)
        header_border = cell_border
        if report_config.table_border_style == "none":
            header_border = "border: 0; border-bottom: 1px solid %s;" % report_config.border_color

        if report_config.layout_style == "modern":
            header_style = (
                "background-color: %s; color: #FFFFFF; padding: 12px 14px; "
                "border-radius: 6px; margin-bottom: 14px;"
            ) % report_config.primary_color
            header_text_style = "color: #FFFFFF;"
            table_wrapper_style = (
                "border: 1px solid %s; border-radius: 6px; padding: 8px; "
                "background-color: #FFFFFF;"
            ) % report_config.border_color
            footer_style = (
                "border-top: 1px solid %s; margin-top: 14px; padding-top: 8px; "
                "font-size: 10px; color: %s;"
            ) % (report_config.border_color, report_config.text_color)
        elif report_config.layout_style == "minimal":
            header_style = (
                "border-bottom: 1px solid %s; padding-bottom: 6px; margin-bottom: 12px;"
            ) % report_config.border_color
            header_text_style = "color: %s;" % report_config.text_color
            table_wrapper_style = ""
            footer_style = (
                "border-top: 1px solid %s; margin-top: 12px; padding-top: 6px; "
                "font-size: 10px; color: %s;"
            ) % (report_config.secondary_color, report_config.text_color)
        else:
            header_style = (
                "border-bottom: 2px solid %s; padding-bottom: 8px; margin-bottom: 14px;"
            ) % report_config.primary_color
            header_text_style = "color: %s;" % report_config.text_color
            table_wrapper_style = ""
            footer_style = (
                "border-top: 1px solid %s; margin-top: 14px; padding-top: 8px; "
                "font-size: 10px; color: %s;"
            ) % (report_config.border_color, report_config.text_color)

        return {
            "article": (
                "direction: %(direction)s; color: %(text_color)s; font-size: %(font_size)dpx; "
                "font-family: Arial, sans-serif;"
            ) % {
                "direction": report_config.direction,
                "text_color": report_config.text_color,
                "font_size": font_size,
            },
            "header": header_style,
            "header_text": header_text_style,
            "title": (
                "color: %(primary_color)s; font-size: %(title_font_size)dpx; "
                "font-weight: bold; margin: 0 0 12px 0; text-align: center;"
            ) % {
                "primary_color": report_config.primary_color,
                "title_font_size": title_font_size,
            },
            "table_wrapper": table_wrapper_style,
            "table": (
                "width: 100%%; border-collapse: collapse; color: %(text_color)s; "
                "font-size: %(font_size)dpx;"
            ) % {
                "text_color": report_config.text_color,
                "font_size": font_size,
            },
            "th": (
                "background-color: %(background)s; color: %(color)s; %(border)s "
                "padding: 7px 8px; text-align: %(text_align)s;"
            ) % {
                "background": report_config.table_header_bg_color,
                "color": report_config.table_header_text_color,
                "border": header_border,
                "text_align": text_align,
            },
            "td": "%s padding: 6px 8px; text-align: %s; vertical-align: top;" % (cell_border, text_align),
            "zebra_row": "background-color: %s;" % report_config.secondary_color,
            "footer": footer_style,
            "logo": "display: block; max-height: 70px; max-width: 120px; margin: 0 auto 12px auto;",
            "doc_block": "clear: both; margin-bottom: 28px;",
            "line_section": "clear: both; margin-top: 18px;",
            "line_section_title": (
                "color: %(primary_color)s; font-size: %(section_font_size)dpx; "
                "font-weight: bold; margin: 0 0 8px 0; text-align: %(text_align)s;"
            ) % {
                "primary_color": report_config.primary_color,
                "section_font_size": font_size + 2,
                "text_align": text_align,
            },
            "block": (
                "clear: both; margin: 12px 0; color: %(text_color)s; "
                "font-size: %(font_size)dpx; page-break-inside: avoid;"
            ) % {
                "text_color": report_config.text_color,
                "font_size": font_size,
            },
            "block_title": (
                "color: %(primary_color)s; font-size: %(title_size)dpx; "
                "font-weight: bold; margin: 0 0 6px 0;"
            ) % {
                "primary_color": report_config.primary_color,
                "title_size": font_size + 2,
            },
            "block_content": "line-height: 1.45;",
            "signature": (
                "display: inline-block; min-width: 220px; max-width: 100%%; "
                "color: %(text_color)s;"
            ) % {
                "text_color": report_config.text_color,
            },
            "signature_line": (
                "border-top: 1px solid %(border_color)s; width: 220px; "
                "height: 1px; margin: 28px 0 6px 0;"
            ) % {
                "border_color": report_config.border_color,
            },
            "watermark": (
                "clear: both; text-align: center; color: %(primary_color)s; "
                "font-size: %(watermark_size)dpx; "
                "font-weight: bold; line-height: 1.2; margin: 8px 0 14px 0; "
                "padding: 6px 0;"
            ) % {
                "primary_color": report_config.primary_color,
                "watermark_size": font_size + 26,
            },
        }

    @api.model
    def _get_cell_border_style(self, report_config):
        if report_config.table_border_style == "none":
            return "border: 0;"
        if report_config.table_border_style == "light" or report_config.layout_style == "minimal":
            return "border: 0; border-bottom: 1px solid %s;" % report_config.border_color
        return "border: 1px solid %s;" % report_config.border_color
