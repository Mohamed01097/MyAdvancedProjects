/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { onPatched, onWillStart, useEffect } from "@odoo/owl";

const EMPTY_RESTRICTIONS = Object.freeze({
    prevent_create: false,
    prevent_edit: false,
    prevent_delete: false,
    prevent_duplicate: false,
    prevent_export: false,
    prevent_import: false,
    prevent_archive: false,
});

const ACTION_FIELDS = [
    "prevent_create",
    "prevent_edit",
    "prevent_delete",
    "prevent_duplicate",
    "prevent_export",
    "prevent_import",
    "prevent_archive",
];

const STATIC_ACTIONS = {
    archive: "prevent_archive",
    unarchive: "prevent_archive",
    duplicate: "prevent_duplicate",
    delete: "prevent_delete",
    export: "prevent_export",
    import: "prevent_import",
};

const restrictionsByModel = new Map();

function normalizeRestrictions(restrictions) {
    const normalized = { ...EMPTY_RESTRICTIONS, ...(restrictions || {}) };
    for (const fieldName of ACTION_FIELDS) {
        normalized[fieldName] = Boolean(normalized[fieldName]);
    }
    return normalized;
}

function setModelRestrictions(modelName, restrictions) {
    const normalized = normalizeRestrictions(restrictions);
    if (modelName) {
        restrictionsByModel.set(modelName, normalized);
    }
    return normalized;
}

function getModelRestrictions(modelName) {
    return normalizeRestrictions(restrictionsByModel.get(modelName));
}

function isPrevented(restrictions, fieldName) {
    const normalized = normalizeRestrictions(restrictions);
    return normalized[fieldName];
}

function getControllerModelName(controller) {
    const props = controller.props || {};
    const model = controller.model || {};
    return props.resModel || (model.root && model.root.resModel) || false;
}

function getControllerRecordIds(controller) {
    const props = controller.props || {};
    const root = controller.model && controller.model.root;
    if (root && root.selection && root.selection.length) {
        return root.selection.map((record) => record.resId).filter(Boolean);
    }
    const resId = (root && root.resId) || props.resId || false;
    return resId ? [resId] : [];
}

function getCogModelName(cogMenu) {
    const props = cogMenu.props || {};
    const env = cogMenu.env || {};
    return props.resModel || (env.searchModel && env.searchModel.resModel) || false;
}

async function loadUiRestrictions(controller) {
    const modelName = getControllerModelName(controller);
    if (!modelName) {
        return setModelRestrictions(modelName, EMPTY_RESTRICTIONS);
    }

    try {
        const restrictions = await controller.orm.call(
            "user.restrict",
            "get_ui_restrictions",
            [modelName, getControllerRecordIds(controller)]
        );
        return setModelRestrictions(modelName, restrictions);
    } catch (error) {
        console.warn("dynamic_restriction: failed to load UI restrictions", error);
        return setModelRestrictions(modelName, EMPTY_RESTRICTIONS);
    }
}

function restrictStaticActionItems(items, restrictions) {
    const normalized = normalizeRestrictions(restrictions);
    const restrictedItems = { ...items };
    for (const [actionName, fieldName] of Object.entries(STATIC_ACTIONS)) {
        if (!restrictedItems[actionName]) {
            continue;
        }
        const originalIsAvailable = restrictedItems[actionName].isAvailable;
        restrictedItems[actionName] = {
            ...restrictedItems[actionName],
            isAvailable: () =>
                !normalized[fieldName] &&
                (originalIsAvailable === undefined || originalIsAvailable()),
        };
    }
    return restrictedItems;
}

function isActionItemPrevented(item, restrictions) {
    const fieldName = item && item.key && STATIC_ACTIONS[item.key];
    return Boolean(fieldName && isPrevented(restrictions, fieldName));
}

function isCogItemPrevented(item, restrictions) {
    const itemKey = item && (item.key || (item.Component && item.Component.name));
    return (
        (itemKey === "ExportAll" && isPrevented(restrictions, "prevent_export")) ||
        (itemKey === "ImportRecords" && isPrevented(restrictions, "prevent_import"))
    );
}

patch(CogMenu.prototype, {
    get cogItems() {
        const restrictions = getModelRestrictions(getCogModelName(this));
        return super.cogItems.filter((item) => !isCogItemPrevented(item, restrictions));
    },
});

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.uiRestrictions = setModelRestrictions(this.props.resModel, EMPTY_RESTRICTIONS);
        this.baseCanCreate = this.canCreate;
        this.baseCanEdit = this.canEdit;

        onWillStart(async () => {
            await this.loadDynamicUiRestrictions(false);
        });

        useEffect(
            () => {
                this.loadDynamicUiRestrictions(true);
            },
            () => [(this.model.root && this.model.root.resId) || false]
        );

        onPatched(() => this.applyDynamicUiFallbacks());
    },

    getUiRestrictionResId() {
        return (this.model.root && this.model.root.resId) || this.props.resId || false;
    },

    async loadDynamicUiRestrictions(shouldRender) {
        this.uiRestrictions = await loadUiRestrictions(this);
        this.applyDynamicUiState();
        if (shouldRender) {
            this.render();
        }
    },

    applyDynamicUiState() {
        this.canCreate = this.baseCanCreate && !isPrevented(this.uiRestrictions, "prevent_create");
        this.canEdit = this.baseCanEdit && !isPrevented(this.uiRestrictions, "prevent_edit");

        const root = this.model && this.model.root;
        if (
            root &&
            root.switchMode &&
            !root.isNew &&
            root.isInEdition &&
            isPrevented(this.uiRestrictions, "prevent_edit")
        ) {
            root.switchMode("readonly");
        }
    },

    applyDynamicUiFallbacks() {
        const rootEl = this.rootRef && this.rootRef.el;
        if (!rootEl) {
            return;
        }
        rootEl
            .querySelectorAll(".o_form_button_create")
            .forEach((button) =>
                button.classList.toggle(
                    "d-none",
                    isPrevented(this.uiRestrictions, "prevent_create")
                )
            );
        rootEl
            .querySelectorAll(".o_form_status_indicator")
            .forEach((button) =>
                button.classList.toggle(
                    "d-none",
                    isPrevented(this.uiRestrictions, "prevent_edit")
                )
            );
    },

    getStaticActionMenuItems() {
        return restrictStaticActionItems(
            super.getStaticActionMenuItems(),
            this.uiRestrictions
        );
    },

    async shouldExecuteAction(item) {
        if (isActionItemPrevented(item, this.uiRestrictions)) {
            return false;
        }
        return super.shouldExecuteAction(item);
    },

    async create(...args) {
        if (isPrevented(this.uiRestrictions, "prevent_create")) {
            return;
        }
        return super.create(...args);
    },

    async duplicateRecord(...args) {
        if (isPrevented(this.uiRestrictions, "prevent_duplicate")) {
            return;
        }
        return super.duplicateRecord(...args);
    },

    async deleteRecord(...args) {
        if (isPrevented(this.uiRestrictions, "prevent_delete")) {
            return;
        }
        return super.deleteRecord(...args);
    },
});

patch(ListController.prototype, {
    setup() {
        super.setup();
        this.uiRestrictions = setModelRestrictions(this.props.resModel, EMPTY_RESTRICTIONS);
        this.baseActiveActions = { ...this.activeActions };
        this.baseEditable = this.editable;

        onWillStart(async () => {
            await this.loadDynamicUiRestrictions(false);
        });

        useEffect(
            () => {
                this.loadDynamicUiRestrictions(true);
            },
            () => [
                this.props.resModel,
                this.model.root.selection.map((record) => record.resId).join(","),
                this.model.root.isDomainSelected,
            ]
        );

        onPatched(() => this.applyDynamicUiFallbacks());
    },

    async loadDynamicUiRestrictions(shouldRender) {
        this.uiRestrictions = await loadUiRestrictions(this);
        this.applyDynamicUiState();
        if (shouldRender) {
            this.render();
        }
    },

    applyDynamicUiState() {
        this.activeActions = {
            ...this.baseActiveActions,
            create:
                this.baseActiveActions.create &&
                !isPrevented(this.uiRestrictions, "prevent_create"),
            edit:
                this.baseActiveActions.edit &&
                !isPrevented(this.uiRestrictions, "prevent_edit"),
            delete:
                this.baseActiveActions.delete &&
                !isPrevented(this.uiRestrictions, "prevent_delete"),
            duplicate:
                this.baseActiveActions.duplicate &&
                !isPrevented(this.uiRestrictions, "prevent_duplicate"),
        };
        this.editable = isPrevented(this.uiRestrictions, "prevent_edit")
            ? false
            : this.baseEditable;
    },

    applyDynamicUiFallbacks() {
        const rootEl = this.rootRef && this.rootRef.el;
        if (!rootEl) {
            return;
        }
        rootEl
            .querySelectorAll(".o_list_button_add")
            .forEach((button) =>
                button.classList.toggle(
                    "d-none",
                    isPrevented(this.uiRestrictions, "prevent_create")
                )
            );
    },

    getStaticActionMenuItems() {
        return restrictStaticActionItems(
            super.getStaticActionMenuItems(),
            this.uiRestrictions
        );
    },

    async onClickCreate(...args) {
        if (isPrevented(this.uiRestrictions, "prevent_create")) {
            return;
        }
        return super.onClickCreate(...args);
    },

    async createRecord(...args) {
        if (isPrevented(this.uiRestrictions, "prevent_create")) {
            return;
        }
        return super.createRecord(...args);
    },

    async onExportData(...args) {
        if (isPrevented(this.uiRestrictions, "prevent_export")) {
            return;
        }
        return super.onExportData(...args);
    },

    async onDirectExportData(...args) {
        if (isPrevented(this.uiRestrictions, "prevent_export")) {
            return;
        }
        return super.onDirectExportData(...args);
    },

    async toggleArchiveState(...args) {
        if (isPrevented(this.uiRestrictions, "prevent_archive")) {
            return;
        }
        return super.toggleArchiveState(...args);
    },

    async duplicateRecords(...args) {
        if (isPrevented(this.uiRestrictions, "prevent_duplicate")) {
            return;
        }
        return super.duplicateRecords(...args);
    },

    async onDeleteSelectedRecords(...args) {
        if (isPrevented(this.uiRestrictions, "prevent_delete")) {
            return;
        }
        return super.onDeleteSelectedRecords(...args);
    },
});
