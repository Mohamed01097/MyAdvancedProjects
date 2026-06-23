/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { onMounted, onPatched, onWillStart, onWillUnmount } from "@odoo/owl";

const HIDDEN_DATASET_KEY = "dynamicViewElementRestrictionHidden";
const HIDDEN_ATTRIBUTE = "data-dynamic-view-element-restriction-hidden";
const TAB_NAV_SELECTOR = [
    ".nav-link",
    ".o_notebook .nav-link",
    'button[role="tab"]',
    'a[role="tab"]',
    ".o_notebook_headers a",
    ".o_notebook_headers button",
].join(",");

const EMPTY_RESTRICTIONS = Object.freeze({
    buttons: Object.freeze([]),
    tabs: Object.freeze([]),
    buttonLabels: Object.freeze({}),
});

function escapeAttributeValue(value) {
    return String(value || "")
        .replace(/\\/g, "\\\\")
        .replace(/"/g, '\\"');
}

function normalizeLabelText(value) {
    return String(value || "")
        .replace(/\s+/g, " ")
        .trim();
}

function uniquePush(target, seen, value) {
    const name = String(value || "").trim();
    if (!name || seen.has(name)) {
        return;
    }
    seen.add(name);
    target.push(name);
}

function normalizeLabelMap(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
        return {};
    }
    return Object.fromEntries(
        Object.entries(value)
            .filter((entry) => entry[0] && entry[1])
            .map(([key, label]) => [String(key), String(label)])
    );
}

function normalizeNameList(value, labelMap, nameKeys, labelKeys) {
    const names = [];
    const seen = new Set();
    if (!Array.isArray(value)) {
        return names;
    }
    for (const item of value) {
        if (typeof item === "string") {
            uniquePush(names, seen, item);
            continue;
        }
        if (!item || typeof item !== "object") {
            continue;
        }
        const name = nameKeys.map((key) => item[key]).find(Boolean);
        uniquePush(names, seen, name);
        const label = labelKeys.map((key) => item[key]).find(Boolean);
        if (name && label) {
            labelMap[String(name)] = String(label);
        }
    }
    return names;
}

function normalizeTabList(value, labelMap) {
    const tabs = [];
    const seen = new Set();
    if (!Array.isArray(value)) {
        return tabs;
    }
    for (const item of value) {
        let name = false;
        let label = false;
        if (typeof item === "string") {
            name = item;
            label = labelMap[item] || item;
        } else if (item && typeof item === "object") {
            name = item.name || item.tab_name;
            label = item.label || item.tab_label || labelMap[name] || name;
        }
        name = String(name || "").trim();
        label = String(label || "").trim();
        if (!name || seen.has(name)) {
            continue;
        }
        seen.add(name);
        tabs.push({ name, label });
    }
    return tabs;
}

function normalizeRestrictions(result) {
    const buttonLabels = normalizeLabelMap(result && result.button_labels);
    const tabLabels = normalizeLabelMap(result && result.tab_labels);
    return {
        buttons: normalizeNameList(
            result && result.buttons,
            buttonLabels,
            ["name", "button_name"],
            ["label", "button_label"]
        ),
        tabs: normalizeTabList(result && result.tabs, tabLabels),
        buttonLabels,
    };
}

function getControllerModelName(controller) {
    const root = controller.model && controller.model.root;
    const props = controller.props || {};
    const env = controller.env || {};
    return (
        (root && root.resModel) ||
        props.resModel ||
        (env.searchModel && env.searchModel.resModel) ||
        false
    );
}

function queryAllSafe(root, selector) {
    if (!root || !root.querySelectorAll) {
        return [];
    }
    try {
        return Array.from(root.querySelectorAll(selector));
    } catch (error) {
        console.warn("[Dynamic View Element Restrictions Odoo19] invalid selector", selector, error);
        return [];
    }
}

function setElementHidden(element, hidden) {
    if (!element || !element.classList) {
        return;
    }
    if (hidden) {
        element.classList.add("d-none");
        element.setAttribute("aria-hidden", "true");
        element.dataset[HIDDEN_DATASET_KEY] = "1";
    } else if (element.dataset[HIDDEN_DATASET_KEY] === "1") {
        element.classList.remove("d-none");
        element.style.display = "";
        element.removeAttribute("aria-hidden");
        delete element.dataset[HIDDEN_DATASET_KEY];
    }
}

function setTabElementHidden(element, hidden) {
    setElementHidden(element, hidden);
    if (hidden && element) {
        element.style.display = "none";
    }
}

function clearPreviouslyHiddenElements(root) {
    for (const element of queryAllSafe(root, `[${HIDDEN_ATTRIBUTE}="1"]`)) {
        setElementHidden(element, false);
    }
}

function hideRestrictedButtons(root, buttonNames) {
    for (const buttonName of buttonNames) {
        const escapedName = escapeAttributeValue(buttonName);
        for (const button of queryAllSafe(
            root,
            `button[name="${escapedName}"], .btn[name="${escapedName}"]`
        )) {
            setElementHidden(button, true);
        }
    }
}

function isNotebookTabLink(element) {
    return Boolean(
        element &&
            element.matches &&
            (element.matches(".nav-link") ||
                element.matches(".o_notebook .nav-link") ||
                element.matches(".tab-link") ||
                element.matches('button[role="tab"]') ||
                element.matches('a[role="tab"]') ||
                element.matches(".o_notebook_headers a") ||
                element.matches(".o_notebook_headers button") ||
                element.matches('[role="tab"]'))
    );
}

function getTabLinkFromElement(element) {
    if (!element) {
        return false;
    }
    if (isNotebookTabLink(element)) {
        return element;
    }
    return (
        element.closest &&
        element.closest(`${TAB_NAV_SELECTOR}, .tab-link, [role="tab"]`)
    );
}

function isHiddenByThisFeature(element) {
    return Boolean(
        element &&
            element.dataset &&
            element.dataset[HIDDEN_DATASET_KEY] === "1"
    );
}

function isVisibleTabCandidate(link) {
    const container = link.closest(".nav-item") || link;
    return (
        !isHiddenByThisFeature(container) &&
        !container.classList.contains("d-none") &&
        !link.classList.contains("disabled") &&
        link.getAttribute("aria-disabled") !== "true"
    );
}

function activateVisibleSiblingTab(link) {
    const notebook = link.closest(".o_notebook");
    if (!notebook) {
        return false;
    }
    for (const candidate of queryAllSafe(notebook, ".o_notebook_headers .nav-link, [role=\"tab\"]")) {
        if (candidate !== link && isVisibleTabCandidate(candidate)) {
            candidate.click();
            return true;
        }
    }
    return false;
}

function hideActiveNotebookContent(link) {
    const notebook = link.closest(".o_notebook");
    const activePane = notebook && notebook.querySelector(".o_notebook_content .tab-pane.active");
    if (activePane) {
        setTabElementHidden(activePane, true);
    }
}

function getElementDocument(element) {
    return (element && element.ownerDocument) || (typeof document !== "undefined" && document);
}

function getHashTargetId(value) {
    if (!value) {
        return false;
    }
    const hashIndex = value.indexOf("#");
    if (hashIndex < 0) {
        return false;
    }
    return value.slice(hashIndex + 1).split(/[?&]/)[0];
}

function addContentPaneById(targets, doc, targetId) {
    if (!doc || !targetId) {
        return;
    }
    for (const id of String(targetId).split(/\s+/).filter(Boolean)) {
        const element = doc.getElementById(id);
        if (element) {
            targets.add(element);
        }
    }
}

function collectTabContentPanes(root, link, tabName) {
    const targets = new Set();
    const doc = getElementDocument(link);
    addContentPaneById(targets, doc, link.getAttribute("aria-controls"));
    addContentPaneById(targets, doc, getHashTargetId(link.getAttribute("href")));
    addContentPaneById(targets, doc, getHashTargetId(link.getAttribute("data-bs-target")));

    if (link.id) {
        const escapedId = escapeAttributeValue(link.id);
        for (const pane of queryAllSafe(root, `[aria-labelledby="${escapedId}"]`)) {
            targets.add(pane);
        }
    }
    if (tabName) {
        const escapedName = escapeAttributeValue(tabName);
        const selectors = [
            `.tab-pane[name="${escapedName}"]`,
            `.tab-pane[data-name="${escapedName}"]`,
            `[role="tabpanel"][name="${escapedName}"]`,
            `[role="tabpanel"][data-name="${escapedName}"]`,
            `[data-tab="${escapedName}"]`,
            `[data-page="${escapedName}"]`,
        ];
        for (const selector of selectors) {
            for (const pane of queryAllSafe(root, selector)) {
                targets.add(pane);
            }
        }
    }
    if (link.classList.contains("active")) {
        const notebook = link.closest(".o_notebook");
        const activePane =
            notebook && notebook.querySelector(".o_notebook_content .tab-pane.active");
        if (activePane) {
            targets.add(activePane);
        }
    }
    return targets;
}

function hideTabLink(root, link, tabName) {
    const container = link.closest(".nav-item") || link;
    const wasActive = link.classList.contains("active");
    const contentPanes = collectTabContentPanes(root, link, tabName);
    setTabElementHidden(link, true);
    setTabElementHidden(container, true);
    for (const pane of contentPanes) {
        setTabElementHidden(pane, true);
    }
    if (!wasActive) {
        return;
    }
    if (!activateVisibleSiblingTab(link)) {
        hideActiveNotebookContent(link);
    }
}

function isTabContentCandidate(element) {
    return Boolean(
        element &&
            element.matches &&
            (element.matches(".tab-pane") ||
                element.matches('[role="tabpanel"]') ||
                element.matches(".o_notebook_page") ||
                element.closest(".o_notebook_content"))
    );
}

function collectTabElementsByName(root, tabName) {
    const escapedName = escapeAttributeValue(tabName);
    const escapedHash = escapeAttributeValue(`#${tabName}`);
    const selectors = [
        `[name="${escapedName}"]`,
        `[data-name="${escapedName}"]`,
        `[data-tab="${escapedName}"]`,
        `[aria-controls*="${escapedName}"]`,
        `[href*="${escapedName}"]`,
        `[data-page="${escapedName}"]`,
        `[data-key="${escapedName}"]`,
        `[href="${escapedHash}"]`,
        `[data-bs-target="${escapedHash}"]`,
    ];
    const elements = new Set();
    for (const selector of selectors) {
        for (const element of queryAllSafe(root, selector)) {
            elements.add(element);
        }
    }
    return elements;
}

function collectTabLinksByName(root, tabName) {
    const links = new Set();
    for (const element of collectTabElementsByName(root, tabName)) {
        const link = getTabLinkFromElement(element);
        if (link) {
            links.add(link);
        }
    }
    return links;
}

function collectTabLinksByLabel(root, tabLabel) {
    const normalizedLabel = normalizeLabelText(tabLabel);
    const links = new Set();
    if (!normalizedLabel) {
        return links;
    }
    for (const link of queryAllSafe(root, `${TAB_NAV_SELECTOR}, .tab-link`)) {
        if (normalizeLabelText(link.textContent) === normalizedLabel) {
            links.add(link);
        }
    }
    return links;
}

function collectFallbackElementsByLabel(root, tabLabel) {
    const normalizedLabel = normalizeLabelText(tabLabel);
    const elements = new Set();
    if (!normalizedLabel) {
        return elements;
    }
    for (const element of queryAllSafe(root, `${TAB_NAV_SELECTOR}, .tab-link`)) {
        if (normalizeLabelText(element.textContent) === normalizedLabel) {
            elements.add(element);
        }
    }
    return elements;
}

function hideRestrictedTabs(root, restrictions) {
    for (const tab of restrictions.tabs) {
        const tabName = tab.name;
        const tabLabel = tab.label;
        const links = collectTabLinksByName(root, tabName);
        if (tabLabel) {
            for (const link of collectTabLinksByLabel(root, tabLabel)) {
                links.add(link);
            }
        }
        for (const element of collectTabElementsByName(root, tabName)) {
            const link = getTabLinkFromElement(element);
            if (link) {
                links.add(link);
            } else if (isTabContentCandidate(element)) {
                setTabElementHidden(element, true);
            }
        }
        for (const link of links) {
            hideTabLink(root, link, tabName);
        }
        for (const element of collectFallbackElementsByLabel(root, tabLabel)) {
            const link = getTabLinkFromElement(element);
            if (link) {
                hideTabLink(root, link, tabName);
            } else {
                setTabElementHidden(element, true);
            }
        }
    }
}

function getButtonRestrictionRoot(controller) {
    const root = controller.rootRef && controller.rootRef.el;
    if (root) {
        return root;
    }
    if (typeof document !== "undefined" && document.body) {
        return document.body;
    }
    return false;
}

function getTabRestrictionRoot() {
    if (typeof document !== "undefined" && document.body) {
        return document.body;
    }
    return false;
}

patch(FormController.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.viewElementRestrictions = EMPTY_RESTRICTIONS;
        this.viewElementRestrictionModelName = false;
        this.viewElementRestrictionObserver = false;
        this.viewElementRestrictionTimer = false;
        this.viewElementRestrictionClickHandler = false;

        onWillStart(async () => {
            await this.loadViewElementRestrictions();
        });

        onMounted(() => {
            this.applyViewElementRestrictions();
            this.startViewElementRestrictionObserver();
            this.startViewElementRestrictionClickListener();
        });

        onPatched(() => {
            this.scheduleViewElementRestrictionCleanup();
            this.startViewElementRestrictionObserver();
            this.startViewElementRestrictionClickListener();
        });

        onWillUnmount(() => {
            this.stopViewElementRestrictionObserver();
            this.stopViewElementRestrictionClickListener();
        });
    },

    async loadViewElementRestrictions() {
        const modelName = getControllerModelName(this);
        this.viewElementRestrictionModelName = modelName;
        if (!modelName || !this.orm || !this.orm.call) {
            this.viewElementRestrictions = EMPTY_RESTRICTIONS;
            return;
        }
        try {
            const result = await this.orm.call("user.restrict", "get_view_ui_restrictions", [
                modelName,
            ]);
            this.viewElementRestrictions = normalizeRestrictions(result);
        } catch (error) {
            this.viewElementRestrictions = EMPTY_RESTRICTIONS;
            console.warn(
                "[Dynamic View Element Restrictions Odoo19] failed to load",
                modelName,
                error
            );
        }
    },

    applyViewElementRestrictions() {
        try {
            const restrictions = this.viewElementRestrictions || EMPTY_RESTRICTIONS;
            const cleanupRoot = getTabRestrictionRoot() || getButtonRestrictionRoot(this);
            if (cleanupRoot) {
                clearPreviouslyHiddenElements(cleanupRoot);
            }
            const buttonRoot = getButtonRestrictionRoot(this);
            if (buttonRoot) {
                hideRestrictedButtons(buttonRoot, restrictions.buttons);
            }
            const tabRoot = getTabRestrictionRoot();
            if (tabRoot) {
                hideRestrictedTabs(tabRoot, restrictions);
            }
        } catch (error) {
            console.warn("[Dynamic View Element Restrictions Odoo19] failed to apply", error);
        }
    },

    scheduleViewElementRestrictionCleanup() {
        if (typeof window === "undefined") {
            this.applyViewElementRestrictions();
            return;
        }
        window.clearTimeout(this.viewElementRestrictionTimer);
        this.viewElementRestrictionTimer = window.setTimeout(() => {
            this.applyViewElementRestrictions();
        }, 300);
    },

    startViewElementRestrictionObserver() {
        if (
            this.viewElementRestrictionObserver ||
            typeof MutationObserver === "undefined"
        ) {
            return;
        }
        const target = typeof document !== "undefined" && document.body;
        if (!target) {
            return;
        }
        try {
            this.viewElementRestrictionObserver = new MutationObserver(() => {
                this.scheduleViewElementRestrictionCleanup();
            });
            this.viewElementRestrictionObserver.observe(target, {
                childList: true,
                subtree: true,
            });
        } catch (error) {
            this.viewElementRestrictionObserver = false;
            console.warn(
                "[Dynamic View Element Restrictions Odoo19] failed to observe DOM",
                error
            );
        }
    },

    stopViewElementRestrictionObserver() {
        try {
            if (typeof window !== "undefined") {
                window.clearTimeout(this.viewElementRestrictionTimer);
            }
            if (this.viewElementRestrictionObserver) {
                this.viewElementRestrictionObserver.disconnect();
                this.viewElementRestrictionObserver = false;
            }
        } catch (error) {
            console.warn(
                "[Dynamic View Element Restrictions Odoo19] failed to stop observer",
                error
            );
        }
    },

    startViewElementRestrictionClickListener() {
        if (this.viewElementRestrictionClickHandler || typeof document === "undefined") {
            return;
        }
        this.viewElementRestrictionClickHandler = (event) => {
            const target = event.target;
            if (!target || !target.closest) {
                return;
            }
            if (target.closest(`${TAB_NAV_SELECTOR}, .tab-link, [role="tab"]`)) {
                this.scheduleViewElementRestrictionCleanup();
            }
        };
        document.addEventListener("click", this.viewElementRestrictionClickHandler, true);
    },

    stopViewElementRestrictionClickListener() {
        if (typeof document === "undefined" || !this.viewElementRestrictionClickHandler) {
            return;
        }
        document.removeEventListener("click", this.viewElementRestrictionClickHandler, true);
        this.viewElementRestrictionClickHandler = false;
    },
});
