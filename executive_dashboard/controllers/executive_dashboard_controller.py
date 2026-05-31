import json

from odoo import http
from odoo.http import request


def _filters_dict(filters):
    if isinstance(filters, dict):
        return filters
    if isinstance(filters, str):
        try:
            parsed = json.loads(filters)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


class ExecutiveDashboardController(http.Controller):
    @http.route("/executive_dashboard/data", type="jsonrpc", auth="user", readonly=True)
    def dashboard_data(self, filters=None):
        return request.env["executive.dashboard.service"].get_dashboard_data(_filters_dict(filters))

    @http.route("/executive_dashboard/action", type="jsonrpc", auth="user", readonly=True)
    def dashboard_action(self, action_key, filters=None, extra_context=None):
        return request.env["executive.dashboard.service"].get_action(
            action_key, _filters_dict(filters), extra_context or {}
        )

    @http.route("/executive_dashboard/export_excel", type="jsonrpc", auth="user")
    def export_excel(self, dashboard_key, filters=None):
        return request.env["executive.dashboard.export"].generate_report_download_action(
            dashboard_key,
            _filters_dict(filters),
            "excel",
            report_type="export",
        )

    @http.route("/executive_dashboard/export_pdf", type="jsonrpc", auth="user")
    def export_pdf(self, dashboard_key, filters=None):
        return request.env["executive.dashboard.export"].generate_report_download_action(
            dashboard_key,
            _filters_dict(filters),
            "pdf",
            report_type="export",
        )

    @http.route("/executive_dashboard/print_snapshot", type="jsonrpc", auth="user")
    def print_snapshot(self, dashboard_key, filters=None):
        return request.env["executive.dashboard.export"].generate_report_download_action(
            dashboard_key,
            _filters_dict(filters),
            "pdf",
            report_type="snapshot",
            options={
                "snapshot_mode": True,
                "title": "Snapshot - %s"
                % request.env["executive.dashboard.export"].get_dashboard_title(dashboard_key),
                "filename_suffix": "snapshot",
            },
        )

    @http.route("/executive_dashboard/share_snapshot", type="jsonrpc", auth="user")
    def share_snapshot(self, dashboard_key, filters=None):
        return request.env["executive.dashboard.export"].share_dashboard_snapshot(
            {"dashboard_key": dashboard_key, "filters_json": _filters_dict(filters)}
        )
