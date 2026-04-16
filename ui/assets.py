from __future__ import annotations

import gradio as gr

from .constants import APP_MODE_PUBLIC_DEMO, PUBLIC_DEMO_PRIVACY_NOTE


def build_custom_css() -> str:
    return """
    :root {
      color-scheme: light;
      --app-body-bg: #f4f7fb;
      --app-panel-bg: rgba(255, 255, 255, 0.96);
      --app-card-bg: rgba(248, 250, 252, 0.98);
      --app-soft-bg: rgba(241, 245, 249, 0.92);
      --app-overlay-bg: rgba(226, 232, 240, 0.42);
      --app-input-bg: rgba(255, 255, 255, 1);
      --app-input-soft-bg: rgba(248, 250, 252, 0.98);
      --app-table-bg: #f8fafc;
      --app-table-alt-odd: #f8fafc;
      --app-table-alt-even: #eef2ff;
      --app-table-index: #e2e8f0;
      --app-table-highlight: #dbeafe;
      --app-table-current: #e0e7ff;
      --app-table-current-index: #c7d2fe;
      --app-table-head: #dbeafe;
      --app-table-head-index: #cbd5e1;
      --app-text-strong: #0f172a;
      --app-text-main: #1e293b;
      --app-text-muted: #334155;
      --app-text-soft: #475569;
      --app-text-label: #64748b;
      --app-border: rgba(148, 163, 184, 0.22);
      --app-border-strong: rgba(148, 163, 184, 0.3);
      --app-shadow-lg: 0 18px 40px rgba(148, 163, 184, 0.16);
      --app-shadow-md: 0 12px 28px rgba(148, 163, 184, 0.12);
      --app-alert-bg: linear-gradient(180deg, rgba(254, 242, 242, 0.98), rgba(255, 241, 242, 0.96));
      --app-alert-border: rgba(248, 113, 113, 0.28);
      --app-alert-title: #b91c1c;
      --app-alert-body: #7f1d1d;
      --app-alert-impact: #991b1b;
      --app-tab-bg: rgba(255, 255, 255, 0.92);
      --app-tab-hover-bg: rgba(238, 242, 255, 0.94);
      --app-tab-selected-bg: rgba(79, 70, 229, 0.18);
      --app-tab-selected-border: rgba(79, 70, 229, 0.42);
      --app-tab-selected-accent: #4f46e5;
      --app-tab-selected-text: #ffffff;
      --app-tab-focus-ring: rgba(79, 70, 229, 0.18);
      --app-accordion-bg: rgba(248, 250, 252, 0.98);
      --app-accordion-hover-bg: rgba(239, 246, 255, 0.98);
      --app-divider-shadow: rgba(15,23,42,0.03);
      --app-accent: #4f46e5;
      --app-accent-hover: #4338ca;
      --app-accent-contrast: #eef2ff;
      --app-primary-gradient: linear-gradient(135deg, #4f46e5, #6366f1);
      --app-primary-shadow: 0 10px 22px rgba(79, 70, 229, 0.22);
    }
    .dark, .dark body, .dark .gradio-container {
        color-scheme: dark;
        --app-body-bg: #0b1220;
        --app-panel-bg: rgba(20, 30, 48, 0.9);
        --app-card-bg: rgba(32, 45, 68, 0.94);
        --app-soft-bg: rgba(15, 23, 42, 0.48);
        --app-overlay-bg: rgba(20, 30, 48, 0.44);
        --app-input-bg: rgba(58, 74, 101, 0.94);
        --app-input-soft-bg: rgba(20, 30, 48, 0.7);
        --app-table-bg: #1f2937;
        --app-table-alt-odd: #233149;
        --app-table-alt-even: #1f2b40;
        --app-table-index: #31415b;
        --app-table-highlight: #42517a;
        --app-table-current: #2e3d63;
        --app-table-current-index: #3b4c72;
        --app-table-head: #273449;
        --app-table-head-index: #334155;
        --app-text-strong: #f8fafc;
        --app-text-main: #dbe6ff;
        --app-text-muted: #c7d4ea;
        --app-text-soft: #b8c3d8;
        --app-text-label: #9fb2d1;
        --app-border: rgba(148, 163, 184, 0.18);
        --app-border-strong: rgba(148, 163, 184, 0.24);
        --app-shadow-lg: 10px 10px 24px rgba(5, 10, 22, 0.32), -6px -6px 18px rgba(255, 255, 255, 0.03);
        --app-shadow-md: 8px 8px 20px rgba(5, 10, 22, 0.26), -4px -4px 14px rgba(255, 255, 255, 0.025);
        --app-alert-bg: linear-gradient(180deg, rgba(127, 29, 29, 0.30), rgba(69, 10, 10, 0.18));
        --app-alert-border: rgba(248, 113, 113, 0.24);
        --app-alert-title: #fecaca;
        --app-alert-body: #fff1f2;
        --app-alert-impact: #fecdd3;
        --app-tab-bg: rgba(20, 30, 48, 0.88);
        --app-tab-hover-bg: rgba(32, 45, 68, 0.82);
        --app-tab-selected-bg: rgba(79, 70, 229, 0.3);
        --app-tab-selected-border: rgba(124, 131, 255, 0.45);
        --app-tab-selected-accent: #7c83ff;
        --app-tab-selected-text: #ffffff;
        --app-tab-focus-ring: rgba(124, 131, 255, 0.2);
        --app-accordion-bg: rgba(32, 45, 68, 0.94);
        --app-accordion-hover-bg: rgba(38, 54, 82, 0.96);
        --app-divider-shadow: rgba(255,255,255,0.03);
        --app-accent: #6366f1;
        --app-accent-hover: #7c83ff;
        --app-accent-contrast: #eef2ff;
        --app-primary-gradient: linear-gradient(135deg, #4f46e5, #6366f1);
        --app-primary-shadow: 0 12px 26px rgba(79, 70, 229, 0.3);
    }
    body { background: var(--app-body-bg) !important; color: var(--app-text-main) !important; }
    .gradio-container { background: var(--app-body-bg); color: var(--app-text-main); }
    .workspace-root { max-width: 1480px; margin: 0 auto; padding: 20px 0 36px; color: var(--app-text-main); }
    .panel { background: var(--app-panel-bg); border: 1px solid var(--app-border-strong); border-radius: 18px; padding: 18px; box-shadow: var(--app-shadow-lg); }
    .hero-card, .summary-card, .row-preview-card, .context-card, .dashboard-shell, .action-card, .reference-card { background: var(--app-card-bg); border: 1px solid var(--app-border); border-radius: 18px; padding: 18px; box-shadow: var(--app-shadow-md); }
    .hero-title { font-size: 1.45rem; font-weight: 700; line-height: 1.2; }
    .hero-subtitle { margin-top: 8px; font-size: 1rem; color: var(--app-text-main); }
    .welcome-project-link { margin: 12px 0 6px; font-size: 1.35rem; font-weight: 700; line-height: 1.3; }
    .welcome-project-link a { color: var(--app-accent); text-decoration: underline; text-underline-offset: 3px; }
    .welcome-project-link a:hover { color: var(--app-accent-hover); }
    .welcome-project-meta { margin: 0 0 16px; color: var(--app-text-soft); font-size: 1rem; line-height: 1.5; }
    .eyebrow { text-transform: uppercase; letter-spacing: .08em; font-size: .72rem; color: var(--app-text-label); margin-bottom: 8px; }
    .hero-row { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
    .hero-badges { display: flex; gap: 8px; flex-wrap: wrap; }
    .hero-meta { margin-top: 12px; color: var(--app-text-soft); font-size: .92rem; }
    .hero-alert { margin-top: 14px; padding: 14px 16px; border-radius: 16px; border: 1px solid var(--app-alert-border); background: var(--app-alert-bg); box-shadow: inset 0 1px 0 rgba(255,255,255,0.03); }
    .hero-alert-title { font-size: .84rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: var(--app-alert-title); margin-bottom: 8px; }
    .hero-alert-body { color: var(--app-alert-body); font-size: .98rem; line-height: 1.5; }
    .hero-alert-impact { margin-top: 8px; color: var(--app-alert-impact); font-size: .92rem; line-height: 1.45; }
    .badge { display: inline-flex; align-items: center; padding: 6px 10px; border-radius: 999px; font-size: .8rem; font-weight: 600; }
    .badge-pending { background: rgba(96, 165, 250, 0.14); color: var(--app-accent); }
    .badge-confirm { background: rgba(34, 197, 94, 0.14); color: #16a34a; }
    .badge-reject { background: rgba(248, 113, 113, 0.14); color: #dc2626; }
    .badge-ignore { background: rgba(148, 163, 184, 0.14); color: var(--app-text-soft); }
    .badge-anomaly { background: rgba(245, 158, 11, 0.14); color: #d97706; }
    .badge-data { background: rgba(14, 165, 233, 0.12); color: #0284c7; }
    .badge-neutral { background: rgba(148, 163, 184, 0.14); color: var(--app-text-soft); }
    .summary-title, .row-preview-title, .context-title, .action-title, .reference-title { font-size: 1.02rem; font-weight: 700; margin-bottom: 12px; }
    .metric-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .summary-inline-card { padding: 14px 16px; }
    .metric-strip { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
    .metric-chip { border-radius: 14px; padding: 10px 10px; border: 1px solid var(--app-border); background: var(--app-soft-bg); min-height: 64px; box-shadow: inset 1px 1px 0 rgba(255,255,255,0.03); }
    .metric-chip-value { font-size: 1.08rem; font-weight: 700; line-height: 1; }
    .metric-chip-label { margin-top: 5px; font-size: .76rem; line-height: 1.25; color: var(--app-text-soft); }
    .summary-footnote, .filter-hint, .row-preview-helper, .context-empty, .row-preview-empty, .action-helper, .reference-summary-copy { margin-top: 12px; color: var(--app-text-soft); font-size: .9rem; }
    .detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .reference-detail-card { background: var(--app-soft-bg); border: 1px solid var(--app-border); border-radius: 16px; padding: 16px; min-height: 124px; }
    .detail-title { font-size: .8rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: var(--app-text-label); margin-bottom: 8px; }
    .detail-body { font-size: 1rem; line-height: 1.5; color: var(--app-text-strong); }
    .action-card { border-color: rgba(96, 165, 250, 0.24); box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.08); padding: 14px 16px; }
    .action-body { font-size: .96rem; line-height: 1.45; color: var(--app-text-strong); }
    .reference-details { display: block; }
    .reference-summary { display: flex; justify-content: space-between; gap: 16px; align-items: center; cursor: pointer; list-style: none; }
    .reference-summary::-webkit-details-marker { display: none; }
    .reference-grid { margin-top: 14px; }
    .decision-panel { border-color: rgba(244, 114, 182, 0.18); }
    .module-intro { margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid var(--app-border); }
    .module-intro-title { font-size: 1.02rem; font-weight: 700; color: var(--app-text-strong); }
    .module-intro-copy { display: none; }
    .context-table, .row-preview-table { width: 100%; border-collapse: collapse; }
    .context-table th, .context-table td, .row-preview-table th, .row-preview-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--app-border); vertical-align: top; color: var(--app-text-main); }
    .context-table th, .row-preview-table th { color: var(--app-text-label); font-size: .82rem; text-transform: uppercase; letter-spacing: .04em; }
    .row-preview-table-wrap { overflow-x: auto; }
    .excel-sheet-wrap { margin-top: 12px; border: 1px solid var(--app-border-strong); border-radius: 10px; background: var(--app-table-bg); box-shadow: inset 0 1px 0 rgba(255,255,255,0.03); }
    .row-preview-table { font-family: Calibri, "Segoe UI", Arial, sans-serif; background: var(--app-table-bg); }
    .row-preview-table thead th { background: var(--app-table-head); color: var(--app-text-main); border-right: 1px solid var(--app-border-strong); border-bottom: 1px solid var(--app-border-strong); font-size: .78rem; font-weight: 700; letter-spacing: 0; }
    .row-preview-table thead th:first-child { background: var(--app-table-head-index); color: var(--app-text-strong); }
    .row-preview-table th, .row-preview-table td { padding: 8px 10px; font-size: .84rem; word-break: break-word; border-right: 1px solid var(--app-border); border-bottom: 1px solid var(--app-border); }
    .row-preview-table tbody tr:nth-child(odd) td { background: var(--app-table-alt-odd); }
    .row-preview-table tbody tr:nth-child(even) td { background: var(--app-table-alt-even); }
    .row-preview-table tbody td:first-child { background: var(--app-table-index); color: var(--app-text-strong); font-weight: 700; width: 72px; white-space: nowrap; }
    .current-row td { background: var(--app-table-current) !important; }
    .current-row td:first-child { background: var(--app-table-current-index) !important; }
    .flagged-cell { position: relative; background: var(--app-table-highlight) !important; font-weight: 700; box-shadow: inset 0 0 0 2px #22c55e; }
    .evidence-summary { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--app-border); }
    .evidence-summary-main { min-width: 0; }
    .evidence-summary-title { font-size: 1.35rem; font-weight: 700; line-height: 1.2; color: var(--app-text-strong); }
    .evidence-summary-subtitle { margin-top: 6px; color: var(--app-text-main); font-size: .98rem; }
    .evidence-action { margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--app-border); }
    .queue-subtitle { color: var(--app-text-soft); margin-top: 4px; margin-bottom: 12px; }
    .queue-filter-grid { display: grid; grid-template-columns: repeat(1, minmax(0, 1fr)); gap: 10px; margin-bottom: 10px; }
    .queue-table-wrap { margin-top: 10px; }
    .history-accordion { margin-top: 12px; }
    .review-shell { gap: 18px; align-items: flex-start; }
    .queue-panel, .review-flow-panel { gap: 14px; }
    .review-flow-panel { border-left: 1px solid var(--app-border-strong); padding-left: 22px; box-shadow: inset 1px 0 0 var(--app-divider-shadow); }
    .active-finding-panel { margin-bottom: 10px; }
    .secondary-accordion { margin-top: 12px; }
    .gradio-container .tab-wrapper, .gradio-container .tabs { border-bottom: 1px solid var(--app-border); margin-bottom: 18px; padding-bottom: 12px; box-shadow: inset 0 -1px 0 var(--app-divider-shadow); }
    .gradio-container .tab-nav { gap: 8px; padding: 6px; background: var(--app-tab-bg); border: 1px solid var(--app-border); border-radius: 16px; display: inline-flex; box-shadow: inset 0 1px 0 rgba(255,255,255,0.03); }
    .gradio-container .tab-nav button, .gradio-container button[role="tab"] { position: relative; padding: 10px 16px; border-radius: 12px; border: 1px solid transparent; color: var(--app-text-muted) !important; background: transparent !important; font-weight: 600; box-shadow: none; }
    .gradio-container .tab-nav button:hover, .gradio-container button[role="tab"]:hover { background: var(--app-tab-hover-bg) !important; color: var(--app-text-strong) !important; border-color: transparent; }
    .gradio-container .tab-nav button:focus-visible, .gradio-container button[role="tab"]:focus-visible { outline: none; box-shadow: 0 0 0 3px var(--app-tab-focus-ring); }
    .gradio-container .tab-nav button.selected, .gradio-container button[role="tab"][aria-selected="true"] { background: var(--app-tab-selected-bg) !important; color: var(--app-tab-selected-text) !important; border-color: var(--app-tab-selected-border) !important; box-shadow: inset 0 -2px 0 var(--app-tab-selected-accent), 0 8px 18px rgba(79, 70, 229, 0.14) !important; }
    .gradio-container .tab-nav button.selected *, .gradio-container button[role="tab"][aria-selected="true"] * { color: var(--app-tab-selected-text) !important; }
    .gradio-container .tab-nav button:not(.selected), .gradio-container button[role="tab"][aria-selected="false"] { opacity: 0.88; }
    .gradio-container button, .gradio-container [role="button"] { transition: background .18s ease, border-color .18s ease, box-shadow .18s ease; }
    .gradio-container .secondary-accordion button, .gradio-container .history-accordion button, .gradio-container .accordion button { background: var(--app-accordion-bg); border: 1px solid var(--app-border-strong); color: var(--app-text-strong); box-shadow: 6px 6px 14px rgba(5,10,22,0.18), -3px -3px 10px rgba(255,255,255,0.02); }
    .gradio-container .secondary-accordion button:hover, .gradio-container .history-accordion button:hover, .gradio-container .accordion button:hover { border-color: rgba(96, 165, 250, 0.42); background: var(--app-accordion-hover-bg); }
    .gradio-container .secondary-accordion button::after, .gradio-container .history-accordion button::after, .gradio-container .accordion button::after { content: "v"; margin-left: auto; color: var(--app-text-main); font-size: .9rem; }
    .gradio-container .wrap .form > *, .gradio-container .form > * { border-color: rgba(148, 163, 184, 0.18); }
    .gradio-container .queue-filter-grid .wrap, .gradio-container .queue-filter-grid .form, .gradio-container .queue-filter-grid input, .gradio-container .queue-filter-grid textarea, .gradio-container .queue-filter-grid button { box-shadow: none; }
    .gradio-container .queue-filter-grid .wrap, .gradio-container .queue-filter-grid .form { border-top: 1px solid var(--app-border); padding-top: 10px; }
    .gradio-container .queue-filter-grid > *:first-child .wrap, .gradio-container .queue-filter-grid > *:first-child .form { border-top: none; padding-top: 0; }
    .gradio-container .queue-filter-grid button, .gradio-container .queue-filter-grid input, .gradio-container .queue-filter-grid textarea { border: 1px solid var(--app-border-strong); background: var(--app-input-bg); color: var(--app-text-strong); }
    .gradio-container .queue-filter-grid button:hover, .gradio-container .queue-filter-grid input:hover, .gradio-container .queue-filter-grid textarea:hover { border-color: rgba(96, 165, 250, 0.4); }
    .gradio-container input, .gradio-container textarea, .gradio-container select { background: var(--app-input-bg); color: var(--app-text-strong); border-color: var(--app-border-strong); }
    .gradio-container input::placeholder, .gradio-container textarea::placeholder { color: var(--app-text-label); }
    .gradio-container button.primary, .gradio-container .primary {
      background: var(--app-primary-gradient) !important;
      color: var(--app-accent-contrast) !important;
      border: 1px solid transparent !important;
      box-shadow: var(--app-primary-shadow);
    }
    .gradio-container button.primary:hover, .gradio-container .primary:hover {
      filter: brightness(1.04);
      box-shadow: 0 14px 28px rgba(79, 70, 229, 0.28);
    }
    .gradio-container .secondary, .gradio-container button.secondary {
      background: var(--app-soft-bg) !important;
      color: var(--app-text-strong) !important;
      border: 1px solid var(--app-border) !important;
    }
    .gradio-container .queue-filter-grid label, .gradio-container .decision-panel label { color: var(--app-text-main); }
    .gradio-container .queue-filter-grid textarea, .gradio-container .queue-filter-grid input[type="text"] { min-height: 48px !important; height: 48px !important; line-height: 1.35; padding-top: 12px; padding-bottom: 12px; resize: none; overflow: hidden; }
    .gradio-container .queue-filter-grid textarea::placeholder, .gradio-container .queue-filter-grid input[type="text"]::placeholder { color: var(--app-text-label); }
    .gradio-container .queue-filter-grid .scroll-hide, .gradio-container .queue-filter-grid [class*="scroll"] { scrollbar-width: thin; }
    .gradio-container .queue-filter-grid .form { overflow: visible; }
    .gradio-container .decision-panel { padding: 10px 14px 14px; margin-top: 6px; }
    .gradio-container .decision-panel .wrap { border: 1px solid var(--app-border); border-radius: 14px; background: var(--app-input-soft-bg); }
    .gradio-container .decision-panel .wrap label { padding: 6px 10px; border-right: 1px solid var(--app-border); }
    .gradio-container .decision-panel .wrap label:last-child { border-right: none; }
    .gradio-container .decision-panel .wrap label:hover { background: rgba(79, 70, 229, 0.12); }
    .gradio-container .decision-panel .wrap label:has(input:checked) {
      background: var(--app-tab-selected-bg);
      color: var(--app-tab-selected-text);
      box-shadow: inset 0 0 0 1px var(--app-tab-selected-border);
    }
    .inline-icon { display: inline-flex; width: 16px; height: 16px; margin-right: 8px; flex: 0 0 16px; vertical-align: -3px; }
    .inline-icon svg { width: 16px; height: 16px; }
    .title-with-icon { display: inline-flex; align-items: center; gap: 8px; }
    .dashboard-title-row { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; }
    .dashboard-title { font-size: 1.35rem; font-weight: 700; color: var(--app-text-strong); }
    .dashboard-subtitle { margin-top: 8px; color: var(--app-text-muted); line-height: 1.55; }
    .dashboard-section-kicker { display: inline-flex; align-items: center; gap: 8px; padding: 5px 10px; border-radius: 999px; background: rgba(79, 70, 229, 0.14); border: 1px solid rgba(124, 131, 255, 0.24); color: var(--app-text-muted); font-size: .72rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    .dashboard-kpi-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }
    .dashboard-kpi-card { background: linear-gradient(180deg, var(--app-soft-bg), var(--app-card-bg)); border: 1px solid var(--app-border); border-radius: 16px; padding: 14px; min-height: 116px; }
    .dashboard-kpi-top { display: inline-flex; align-items: center; gap: 8px; color: var(--app-text-muted); font-size: .9rem; }
    .dashboard-kpi-value { margin-top: 16px; font-size: 1.9rem; font-weight: 700; color: var(--app-text-strong); }
    .dashboard-kpi-note { margin-top: 8px; color: var(--app-text-label); font-size: .84rem; line-height: 1.45; }
    .insight-shell { margin-top: 18px; padding: 18px; border: 1px solid var(--app-border); border-radius: 20px; background: var(--app-overlay-bg); }
    .insight-shell-header { display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; margin-bottom: 14px; }
    .insight-shell-title { margin-top: 10px; font-size: 1.08rem; font-weight: 700; color: var(--app-text-strong); }
    .insight-shell-copy { max-width: 420px; color: var(--app-text-label); line-height: 1.5; font-size: .9rem; }
    .insight-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .insight-card { background: var(--app-panel-bg); border: 1px solid var(--app-border); border-radius: 18px; padding: 16px; min-height: 122px; }
    .insight-card-focus { border-left: 3px solid rgba(245, 158, 11, 0.72); }
    .insight-card-status { border-left: 3px solid rgba(96, 165, 250, 0.72); }
    .insight-title { display: inline-flex; align-items: center; gap: 8px; color: var(--app-text-strong); font-size: .92rem; font-weight: 700; }
    .insight-body { margin-top: 12px; color: var(--app-text-muted); line-height: 1.55; }
    @media (max-width: 960px) {
      .detail-grid, .insight-grid, .dashboard-kpi-grid, .metric-grid, .metric-strip { grid-template-columns: repeat(1, minmax(0, 1fr)); }
      .hero-row, .dashboard-title-row { flex-direction: column; }
      .reference-summary { flex-direction: column; align-items: flex-start; }
      .review-flow-panel { border-left: none; padding-left: 0; }
      .insight-shell-header { flex-direction: column; }
      .welcome-project-link { font-size: 1.15rem; }
      .welcome-project-meta { font-size: .96rem; }
    }
    @media (min-width: 961px) {
      .queue-filter-grid { grid-template-columns: repeat(1, minmax(0, 1fr)); }
    }
    """


def build_heading(app_mode: str) -> str:
    heading = "# VAT Spreadsheet Review Centre"
    if app_mode == APP_MODE_PUBLIC_DEMO:
        heading += "\n\n_Limited public demo profile_"
    return heading


def build_welcome_markdown(app_mode: str) -> str:
    return (
        "This local-first prototype helps you analyse VAT-related spreadsheets, explain why records were flagged, and record a human review trail.\n\n"
        '<div class="welcome-project-link"><a href="https://github.com/ricardo-zihao-lin/ai-assisted-vat-prep-prototype" target="_blank" rel="noopener noreferrer">AI-Assisted VAT Prep Prototype @ GitHub</a></div>\n'
        '<div class="welcome-project-meta">Zihao Lin | Undergraduate Final Year Project | University of Huddersfield, UK</div>\n\n'
        "**Built with Gradio**\n"
        "- Browser UI shell: Gradio\n"
        "- Tabular processing: pandas\n"
        "- Figure output: Matplotlib\n\n"
        "**Architecture**\n"
        "- Same Python core is reused by source run, local GUI, Docker, Windows package, and the web demo shell.\n"
        "- The browser GUI is the current main interaction entry.\n"
        "- Deployment shells stay thin so evaluation logic can continue changing separately.\n\n"
        "**Workflow**\n"
        "1. Upload a CSV or Excel file.\n"
        "2. Run the analysis.\n"
        "3. Review flagged findings in the dual-pane Review Centre.\n"
        "4. Save decisions and export the review artefacts.\n"
        + (
            f"\n**Public Demo Boundary**\n- {PUBLIC_DEMO_PRIVACY_NOTE}\n"
            if app_mode == APP_MODE_PUBLIC_DEMO
            else "\n**Current Default Shape**\n- Run locally from source or a local package for demonstrations and dissertation work.\n"
        )
    )


def build_theme() -> gr.themes.Theme:
    return gr.themes.Soft(
        primary_hue="indigo",
        neutral_hue="slate",
        text_size="lg",
        spacing_size="lg",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    )
