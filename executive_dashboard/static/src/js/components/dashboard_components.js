import { Component, onWillUnmount, useEffect, useRef } from "@odoo/owl";
import { formatFloat, formatInteger, formatMonetary } from "@web/views/fields/formatters";

const CHART_COLORS = [
    "#2563eb",
    "#059669",
    "#d97706",
    "#dc2626",
    "#0891b2",
    "#7c3aed",
    "#65a30d",
    "#c2410c",
    "#0f766e",
    "#be123c",
];

export class DashboardChart extends Component {
    static template = "executive_dashboard.DashboardChart";
    static props = {
        chart: { type: Object },
        currencyId: { type: Number, optional: true },
        onOpen: { type: Function },
    };

    setup() {
        this.chartInstance = null;
        this.canvasRef = useRef("canvas");
        useEffect(() => {
            this.renderChart();
            return () => this.destroyChart();
        });
        onWillUnmount(() => this.destroyChart());
    }

    destroyChart() {
        if (this.chartInstance) {
            this.chartInstance.destroy();
            this.chartInstance = null;
        }
    }

    renderChart() {
        if (!this.canvasRef.el || typeof Chart === "undefined" || !this.hasData()) {
            return;
        }
        this.destroyChart();
        this.chartInstance = new Chart(this.canvasRef.el, this.getChartConfig());
    }

    hasData() {
        const chart = this.props.chart;
        if (chart.datasets && chart.datasets.length) {
            return chart.datasets.some((dataset) => dataset.values.some((value) => value));
        }
        return Boolean(chart.data && chart.data.some((point) => point.value));
    }

    getChartConfig() {
        const chart = this.props.chart;
        const hasDatasets = Boolean(chart.datasets && chart.datasets.length);
        const isDoughnut = chart.kind === "doughnut";
        return {
            type: chart.kind || "bar",
            data: hasDatasets ? this.getDatasetChartData(chart) : this.getSimpleChartData(chart),
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: chart.horizontal ? "y" : "x",
                plugins: {
                    legend: {
                        display: hasDatasets || isDoughnut,
                        position: "bottom",
                        labels: { usePointStyle: true, boxWidth: 8 },
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => this.getTooltipLabel(context),
                        },
                    },
                },
                scales: isDoughnut ? {} : this.getScales(chart),
                onClick: (event, elements) => this.onChartClick(elements),
            },
        };
    }

    getDatasetChartData(chart) {
        return {
            labels: chart.labels,
            datasets: chart.datasets.map((dataset, index) => ({
                label: dataset.label,
                data: dataset.values,
                backgroundColor: dataset.color || CHART_COLORS[index % CHART_COLORS.length],
                borderColor: dataset.color || CHART_COLORS[index % CHART_COLORS.length],
                borderWidth: 2,
                borderRadius: 4,
                tension: 0.35,
            })),
        };
    }

    getSimpleChartData(chart) {
        const isDoughnut = chart.kind === "doughnut";
        return {
            labels: chart.data.map((point) => point.label),
            datasets: [
                {
                    label: chart.title,
                    data: chart.data.map((point) => point.value),
                    backgroundColor: isDoughnut
                        ? chart.data.map((_, index) => CHART_COLORS[index % CHART_COLORS.length])
                        : "#0891b2",
                    borderColor: isDoughnut ? "#ffffff" : "#0e7490",
                    borderWidth: isDoughnut ? 2 : 1,
                    borderRadius: isDoughnut ? 0 : 4,
                    tension: 0.35,
                },
            ],
        };
    }

    getScales(chart) {
        const valueAxis = chart.horizontal ? "x" : "y";
        const categoryAxis = chart.horizontal ? "y" : "x";
        return {
            [valueAxis]: {
                beginAtZero: true,
                grid: { color: "rgba(15, 23, 42, 0.08)" },
                ticks: {
                    callback: (value) => this.compactValue(value, chart.metric),
                },
            },
            [categoryAxis]: { grid: { display: false } },
        };
    }

    getTooltipLabel(context) {
        const label = context.dataset.label ? `${context.dataset.label}: ` : "";
        const parsed = context.parsed || {};
        const value = parsed.y !== undefined
            ? parsed.y
            : parsed.x !== undefined
                ? parsed.x
                : context.raw || 0;
        return `${label}${this.formatChartValue(value, this.props.chart.metric)}`;
    }

    onChartClick(elements) {
        if (!elements.length || !this.props.chart.action_key) {
            return;
        }
        const element = elements[0];
        const chart = this.props.chart;
        let extra = {};
        if (chart.datasets && chart.datasets.length) {
            const point = chart.data[element.index] || {};
            const dataset = chart.datasets[element.datasetIndex] || {};
            extra = { ...(point.extra || {}), segment: dataset.key };
        } else {
            const point = chart.data[element.index] || {};
            extra = { ...(point.extra || {}) };
        }
        this.props.onOpen(chart.action_key, extra);
    }

    formatChartValue(value, metric) {
        if (metric === "monetary" && this.props.currencyId) {
            return formatMonetary(value || 0, { currencyId: this.props.currencyId });
        }
        if (metric === "percentage") {
            return `${formatFloat(value || 0, { digits: [false, 1] })}%`;
        }
        if (metric === "float") {
            return formatFloat(value || 0, { digits: [false, 1] });
        }
        return formatInteger(value || 0, { humanReadable: false });
    }

    compactValue(value, metric) {
        if (metric !== "monetary") {
            return value;
        }
        const amount = Number(value || 0);
        const absolute = Math.abs(amount);
        if (absolute >= 1000000) {
            return `${formatFloat(amount / 1000000, { digits: [false, 1] })}M`;
        }
        if (absolute >= 1000) {
            return `${formatFloat(amount / 1000, { digits: [false, 1] })}K`;
        }
        return formatInteger(amount, { humanReadable: false });
    }
}

export class KpiCard extends Component {
    static template = "executive_dashboard.KpiCard";
    static props = {
        kpi: { type: Object },
        formatKpi: { type: Function },
        onOpen: { type: Function },
    };

    get actionKey() {
        return this.props.kpi.action_key !== undefined ? this.props.kpi.action_key : this.props.kpi.key;
    }
}

export class DepartmentCard extends Component {
    static template = "executive_dashboard.DepartmentCard";
    static props = {
        card: { type: Object },
        formatValue: { type: Function },
        onOpen: { type: Function },
    };
}

export class DashboardFilters extends Component {
    static template = "executive_dashboard.DashboardFilters";
    static props = {
        filters: { type: Object },
        options: { type: Object },
        fields: { type: Array },
        onChange: { type: Function },
        onClear: { type: Function },
        hasActiveFilters: { type: Boolean },
    };

    getOptions(field) {
        return this.props.options[field.optionsKey] || [];
    }

    optionLabel(option, field) {
        return option[field.labelField || "name"];
    }

    onFilterChange(ev) {
        const filterName = ev.currentTarget.dataset.filter;
        const field = this.props.fields.find((item) => item.name === filterName) || {};
        let value = ev.currentTarget.value || false;
        if (field.valueType === "integer") {
            value = value ? Number(value) : false;
        }
        this.props.onChange(filterName, value);
    }
}

export class LoadingState extends Component {
    static template = "executive_dashboard.LoadingState";
    static props = {
        label: { type: String, optional: true },
    };
}

export class AlertPreview extends Component {
    static template = "executive_dashboard.AlertPreview";
    static props = {
        alerts: { type: Array },
        onOpen: { type: Function },
        onActivity: { type: Function, optional: true },
        compact: { type: Boolean, optional: true },
    };

    severityClass(severity) {
        const classes = {
            critical: "text-bg-danger",
            high: "text-bg-warning",
            medium: "text-bg-info",
            low: "text-bg-secondary",
        };
        return classes[severity] || "text-bg-light";
    }
}
