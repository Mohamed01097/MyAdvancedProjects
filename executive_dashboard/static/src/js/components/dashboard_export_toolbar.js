import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class DashboardExportToolbar extends Component {
    static template = "executive_dashboard.DashboardExportToolbar";
    static props = {
        dashboardKey: { type: String },
        dashboardTitle: { type: String },
        filters: { type: Object, optional: true },
    };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            excel: false,
            pdf: false,
            print: false,
            share: false,
        });
    }

    get filtersPayload() {
        const filters = this.props.filters;
        if (!filters || Array.isArray(filters) || typeof filters !== "object") {
            return {};
        }
        return { ...filters };
    }

    isLoading(key) {
        return Boolean(this.state[key]);
    }

    async onExportExcel() {
        await this.runAction(
            "excel",
            "/executive_dashboard/export_excel",
            _t("Excel export started."),
            _t("Excel export failed.")
        );
    }

    async onExportPDF() {
        await this.runAction(
            "pdf",
            "/executive_dashboard/export_pdf",
            _t("PDF export started."),
            _t("PDF export failed.")
        );
    }

    async onPrintSnapshot() {
        await this.runAction(
            "print",
            "/executive_dashboard/print_snapshot",
            _t("Snapshot is ready."),
            _t("Snapshot generation failed.")
        );
    }

    async onShareSnapshot() {
        await this.runAction(
            "share",
            "/executive_dashboard/share_snapshot",
            false,
            _t("Could not open the share wizard.")
        );
    }

    async runAction(stateKey, route, successMessage, errorMessage) {
        if (this.state[stateKey]) {
            return;
        }
        this.state[stateKey] = true;
        try {
            const result = await rpc(route, {
                dashboard_key: this.props.dashboardKey,
                filters: this.filtersPayload,
            });
            if (result) {
                await this.action.doAction(result);
            }
            if (successMessage) {
                this.notification.add(successMessage, { type: "success" });
            }
        } catch (error) {
            const message =
                (error && error.data && error.data.message) ||
                (error && error.message) ||
                errorMessage ||
                _t("Dashboard report action failed.");
            this.notification.add(message, { type: "danger" });
        } finally {
            this.state[stateKey] = false;
        }
    }
}
