import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

import { ExecutiveDashboardBase, FILTER_FIELDS } from "./dashboard_base";

export class AlertsCenter extends ExecutiveDashboardBase {
    static template = "executive_dashboard.AlertsCenter";
    static dataMethod = "get_alerts_data";
    static actionMethod = "get_action";
    static usesCharts = false;
    static filterFields = [
        FILTER_FIELDS.alertDashboard,
        FILTER_FIELDS.alertStatus,
        FILTER_FIELDS.department,
        FILTER_FIELDS.severity,
        FILTER_FIELDS.responsibleUser,
        FILTER_FIELDS.dateFrom,
        FILTER_FIELDS.dateTo,
        FILTER_FIELDS.company,
    ];

    async openSmartAlert(row) {
        return this.openAlert({ smart_alert_id: row.smart_alert_id });
    }

    async openSmartRule(row) {
        if (!row.rule_id) {
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "executive.dashboard.alert.rule",
            res_id: row.rule_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openSmartRelated(row) {
        if (!row.can_open_related) {
            return;
        }
        return this.openAlert({
            related_model: row.related_model,
            related_id: row.related_id,
            related_document: row.related_document,
        });
    }

    async updateSmartAlert(row, method, successMessage) {
        if (!row.smart_alert_id) {
            return;
        }
        try {
            await this.orm.call("executive.dashboard.alert.history", method, [[row.smart_alert_id]]);
            this.notification.add(successMessage, { type: "success" });
            await this.refresh();
        } catch (error) {
            this.notification.add(error.message || _t("The smart alert could not be updated."), {
                type: "danger",
            });
        }
    }

    markSmartInProgress(row) {
        return this.updateSmartAlert(row, "action_mark_in_progress", _t("Alert marked in progress."));
    }

    resolveSmartAlert(row) {
        return this.updateSmartAlert(row, "action_mark_resolved", _t("Alert resolved."));
    }

    ignoreSmartAlert(row) {
        return this.updateSmartAlert(row, "action_ignore", _t("Alert ignored."));
    }
}

registry.category("actions").add("executive_dashboard.alerts", AlertsCenter);
