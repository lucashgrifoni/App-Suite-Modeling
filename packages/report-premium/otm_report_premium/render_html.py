"""HTML + CSS for premium PDF — executive AppSec layout (English UI, xhtml2pdf-safe)."""

from __future__ import annotations

import html
import re
from typing import Literal

from otm_threat_engine.severity import severity_for_score

from .branding import report_logo_data_uri
from .enums import ReportLevel
from .models import PremiumReportPayload, TopRiskItem

# Tier / severity palette (aligned with product brief)
_COLOR_P1 = "#dc2626"
_COLOR_P2 = "#f97316"
_COLOR_P3 = "#eab308"
_COLOR_P4 = "#2563eb"

_S = (
    """
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 10pt;
  color: #0f172a;
  line-height: 1.45;
  margin: 0;
  padding: 0;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
h1 {
  font-size: 22pt;
  font-weight: 700;
  color: #020617;
  margin: 0 0 4px 0;
  line-height: 1.2;
  letter-spacing: -0.02em;
}
h2 {
  font-size: 13pt;
  font-weight: 700;
  color: #0f172a;
  margin: 22px 0 10px 0;
  padding-bottom: 6px;
  border-bottom: 2px solid #e2e8f0;
  line-height: 1.25;
  page-break-after: avoid;
}
h3 {
  font-size: 10.5pt;
  font-weight: 700;
  color: #334155;
  margin: 14px 0 8px 0;
  line-height: 1.3;
  page-break-after: avoid;
}
.section-divider {
  border: 0;
  height: 1px;
  background: linear-gradient(90deg, #cbd5e1, transparent);
  margin: 18px 0;
}
header.report-header {
  border-bottom: 3px solid #1e40af;
  padding-bottom: 14px;
  margin-bottom: 16px;
}
.product-line {
  font-size: 11pt;
  font-weight: 600;
  color: #1e40af;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 10px;
}
.subtitle-line {
  font-size: 10pt;
  color: #475569;
  margin-top: 6px;
  font-weight: 500;
}
.logo-wrap {
  margin: 12px 0 8px 0;
  text-align: left;
}
.logo-wrap img {
  max-height: 60px;
  width: auto;
  display: block;
}
.meta-grid {
  font-size: 9pt;
  color: #475569;
  margin-top: 10px;
  line-height: 1.5;
}
.meta-grid strong { color: #334155; }
.disclaimer {
  background: #fffbeb;
  border-left: 4px solid #f59e0b;
  padding: 10px 14px;
  margin: 14px 0;
  font-size: 9pt;
  color: #422006;
  line-height: 1.45;
}
.disclaimer ul { margin: 8px 0 0 18px; padding: 0; }
.exec-block {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 14px 16px;
  margin: 12px 0;
}
.exec-block ul {
  margin: 0;
  padding-left: 18px;
  list-style-type: disc;
}
.exec-block li { margin: 6px 0; line-height: 1.45; }
.hl { font-weight: 700; color: #0f172a; }
.tier-p1 { color: """
    + _COLOR_P1
    + """; font-weight: 700; }
.tier-p2 { color: """
    + _COLOR_P2
    + """; font-weight: 700; }
.tier-p3 { color: """
    + _COLOR_P3
    + """; font-weight: 700; }
.tier-p4 { color: """
    + _COLOR_P4
    + """; font-weight: 700; }
.badge-tier {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 8pt;
  font-weight: 700;
  color: #fff;
  min-width: 2em;
  text-align: center;
}
.bg-p1 { background: """
    + _COLOR_P1
    + """; }
.bg-p2 { background: """
    + _COLOR_P2
    + """; }
.bg-p3 { background: """
    + _COLOR_P3
    + """; }
.bg-p4 { background: """
    + _COLOR_P4
    + """; }
.sev-critical { color: """
    + _COLOR_P1
    + """; font-weight: 700; }
.sev-high { color: """
    + _COLOR_P2
    + """; font-weight: 700; }
.sev-medium { color: #ca8a04; font-weight: 700; }
.sev-low { color: """
    + _COLOR_P4
    + """; font-weight: 600; }
table.risk-table {
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
  margin: 10px 0 16px 0;
  font-size: 8.5pt;
}
table.risk-table th,
table.risk-table td {
  border: 1px solid #cbd5e1;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
  word-wrap: break-word;
  overflow-wrap: break-word;
  word-break: break-word;
  white-space: normal;
  line-height: 1.4;
}
table.risk-table th {
  background: #f1f5f9;
  color: #0f172a;
  font-weight: 700;
}
table.risk-table tr:nth-child(even) td { background: #f8fafc; }
.col-rank { width: 6%; }
.col-id { width: 14%; }
.col-title { width: 32%; }
.col-comp { width: 16%; }
.col-sev { width: 12%; }
.col-score { width: 10%; }
.col-tier { width: 10%; }
.root-grid { margin: 10px 0 16px 0; }
.root-row {
  width: 100%;
  margin-bottom: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  border-left: 4px solid #94a3b8;
  border-radius: 0 4px 4px 0;
  font-size: 9.5pt;
  line-height: 1.4;
}
.root-row.rc-p1 { border-left-color: """
    + _COLOR_P1
    + """; }
.root-row.rc-p2 { border-left-color: """
    + _COLOR_P2
    + """; }
.root-row.rc-p3 { border-left-color: """
    + _COLOR_P3
    + """; }
.root-row.rc-p4 { border-left-color: """
    + _COLOR_P4
    + """; }
.roadmap-block { margin: 12px 0 18px 0; }
.roadmap-block h3 { margin-top: 0; }
.roadmap-block ul { margin: 6px 0 0 18px; padding: 0; }
.roadmap-block li { margin: 4px 0; line-height: 1.45; word-wrap: break-word; }
.risk-meter {
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  margin: 6px 0 0 0;
  overflow: hidden;
  max-width: 220px;
}
.risk-meter-fill {
  height: 100%;
  border-radius: 4px;
}
.section { page-break-inside: avoid; }
footer {
  font-size: 8pt;
  color: #64748b;
  margin-top: 28px;
  border-top: 1px solid #e2e8f0;
  padding-top: 10px;
  line-height: 1.4;
}
.small-muted { font-size: 8.5pt; color: #64748b; }
"""
)


_UL_CLOSE = "</ul>"
_HR_DIVIDER = "<hr class='section-divider'/>"
_TABLE_SECTION_CLOSE = "</table></section>"


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _severity_band(score: float | None) -> tuple[str, str]:
    """(label, css_class) for table column — derived from the engine's canonical band."""
    if score is None:
        return "—", "sev-low"
    band = severity_for_score(score)
    return band.capitalize(), f"sev-{band}"


def _tier_badge_class(tier: str) -> str:
    if tier == "P1":
        return "bg-p1"
    if tier == "P2":
        return "bg-p2"
    return "bg-p3"


def _root_cause_row_class(index: int) -> str:
    return ("rc-p1", "rc-p2", "rc-p3", "rc-p4")[index % 4]


def _status_emoji(status: str) -> str:
    if status == "requires_immediate_attention":
        return "&#9888;&#65039;"  # warning
    if status == "action_recommended":
        return "&#9888;"  # ⚠ simple
    return "&#10003;"  # check


def _roadmap_heading(phase: Literal["immediate", "short", "medium"]) -> str:
    if phase == "immediate":
        return "Immediate (P1)"
    if phase == "short":
        return "Short term (P2)"
    return "Medium term"


def _top_risk_for_exec(rows: list[TopRiskItem]) -> TopRiskItem | None:
    return rows[0] if rows else None


def _band_css(band: str) -> str:
    b = (band or "").lower()
    if b == "critical":
        return "sev-critical"
    if b == "high":
        return "sev-high"
    if b == "medium":
        return "sev-medium"
    return "sev-low"


def _html_header(parts: list[str], payload: PremiumReportPayload) -> None:
    c = payload.cover
    logo_uri = report_logo_data_uri()
    subtitle_parts = []
    if c.model_id_hint:
        subtitle_parts.append(c.model_id_hint)
    subtitle_parts.append(f"{c.system_type} · {c.industry_sector}")
    subtitle = " — ".join(subtitle_parts) if subtitle_parts else f"{c.system_type} · {c.industry_sector}"

    parts.extend(
        [
            "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'/>",
            f"<title>{_esc(c.title)} — App Suite Modeling</title><style>{_S}</style></head><body>",
            "<header class='report-header'>",
            "<div class='product-line'>App Suite Modeling</div>",
        ]
    )
    if logo_uri:
        parts.append(f"<div class='logo-wrap'><img src='{_esc(logo_uri)}' alt='Logo'/></div>")
    parts.append(f"<h1>{_esc(c.title)}</h1>")
    parts.append(f"<p class='subtitle-line'>{_esc(subtitle)}</p>")
    parts.append("<div class='meta-grid'>")
    parts.append(
        f"<div><strong>Schema</strong> {_esc(c.schema_version)} &nbsp;|&nbsp; "
        f"<strong>Methodology</strong> {_esc(c.primary_methodology)} &nbsp;|&nbsp; "
        f"<strong>Analysis date</strong> {_esc(c.analysis_date_iso)} &nbsp;|&nbsp; "
        f"<strong>Product version</strong> {_esc(c.app_suite_version)}</div>"
    )
    parts.append(
        f"<div><strong>Overall status</strong> {_esc(c.overall_status_display)} &nbsp;|&nbsp; "
        f"<strong>Risk (heuristic)</strong> {_esc(c.overall_risk_label)}</div>"
    )
    parts.append("</div></header>")

    parts.append("<div class='disclaimer'>")
    parts.append("<strong>Inference notice</strong> — " + _esc(payload.disclaimer.summary))
    if payload.disclaimer.bullets:
        parts.append("<ul>")
        for bullet in payload.disclaimer.bullets:
            parts.append(f"<li>{_esc(bullet)}</li>")
        parts.append(_UL_CLOSE)
    parts.append("</div>")


def _html_risk_meter(parts: list[str], payload: PremiumReportPayload) -> None:
    top = _top_risk_for_exec(payload.top_risks)
    if not (top and (top.severity_score is not None or top.composite_score)):
        return
    score_raw = float(top.severity_score) if top.severity_score is not None else float(top.composite_score)
    pct = min(100.0, max(5.0, (score_raw / 25.0) * 100.0))
    if top.priority_tier == "P1":
        fill_color = _COLOR_P1
    elif top.priority_tier == "P2":
        fill_color = _COLOR_P2
    else:
        fill_color = _COLOR_P3
    parts.append("<p class='small-muted'><strong>Top risk score (visual)</strong></p>")
    parts.append(
        f"<div class='risk-meter'><div class='risk-meter-fill' style='width:{pct:.0f}%;background:{fill_color};'>"
        f"</div></div>"
    )


def _html_executive_summary(parts: list[str], payload: PremiumReportPayload) -> None:
    c = payload.cover
    es = payload.executive_summary
    parts.append(_HR_DIVIDER)
    parts.append("<section class='section'><h2>Executive summary</h2>")
    top = _top_risk_for_exec(payload.top_risks)
    tier_line = "No ranked heuristic threats"
    score_line = "—"
    if top:
        sev_lbl, _ = _severity_band(top.severity_score)
        tier_line = f"{top.priority_tier} ({sev_lbl})"
        if top.severity_score is not None:
            score_line = f"{top.severity_score:.1f}"
        elif top.composite_score:
            score_line = f"{top.composite_score:.2f} (composite)"
    status_icon = _status_emoji(c.overall_status)
    parts.append("<div class='exec-block'>")
    parts.append("<ul>")
    parts.append(f"<li><span class='hl'>Total threats:</span> {es.threat_count}</li>")
    parts.append(
        f"<li><span class='hl'>Highest priority:</span> "
        f"<span class='tier-p1'>&#128308;</span> {_esc(tier_line)} "
        f"&nbsp; <span class='hl'>Score:</span> {_esc(score_line)}</li>"
    )
    parts.append(f"<li><span class='hl'>Overall status:</span> {status_icon} {_esc(c.overall_status_display)}</li>")
    parts.append(f"<li><span class='hl'>Urgency:</span> {_esc(es.urgency_level)}</li>")
    parts.append(_UL_CLOSE)
    if es.top5_risk_titles:
        parts.append("<p class='small-muted' style='margin:10px 0 0 0;'><strong>Top risk themes:</strong></p><ul>")
        for t in es.top5_risk_titles[:5]:
            parts.append(f"<li>{_esc(t[:200])}</li>")
        parts.append(_UL_CLOSE)
    parts.append(f"<p style='margin-top:12px;font-size:9pt;color:#334155;'>{_esc(es.executive_conclusion)}</p>")
    _html_risk_meter(parts, payload)
    parts.append("<p class='small-muted'>" + _esc(es.business_impact_summary) + "</p>")
    if es.readiness_questions:
        parts.append("<p class='small-muted'><strong>Readiness checks:</strong></p><ul>")
        for q in es.readiness_questions[:5]:
            parts.append(f"<li>{_esc(q)}</li>")
        parts.append(_UL_CLOSE)
    parts.append("</div></section>")


def _html_severity_distribution(parts: list[str], payload: PremiumReportPayload) -> None:
    es = payload.executive_summary
    if not (payload.level != ReportLevel.EXECUTIVE and es.severity_distribution):
        return
    parts.append(_HR_DIVIDER)
    parts.append("<section class='section'><h2>Severity distribution</h2>")
    parts.append("<table class='risk-table'><colgroup>")
    parts.append("<col style='width:40%'/><col style='width:60%'/></colgroup>")
    parts.append("<tr><th>Severity band</th><th>Count</th></tr>")
    for band, n in sorted(es.severity_distribution.items()):
        cls = _band_css(str(band))
        parts.append(f"<tr><td class='{_esc(cls)}'>{_esc(str(band))}</td><td>{n}</td></tr>")
    parts.append(_TABLE_SECTION_CLOSE)


def _html_top_risks(parts: list[str], payload: PremiumReportPayload) -> None:
    parts.append(_HR_DIVIDER)
    parts.append("<section class='section'><h2>Top prioritized risks</h2>")
    parts.append("<p class='small-muted'>Ranked by composite priority (P1 = immediate attention).</p>")
    parts.append("<table class='risk-table'><colgroup>")
    parts.append(
        "<col class='col-rank'/><col class='col-id'/><col class='col-title'/><col class='col-comp'/>"
        "<col class='col-sev'/><col class='col-score'/><col class='col-tier'/>"
    )
    parts.append("</colgroup><tr>")
    headers = ["#", "ID", "Title", "Component", "Severity", "Score", "Tier"]
    for h in headers:
        parts.append(f"<th>{_esc(h)}</th>")
    parts.append("</tr>")
    for rk in payload.top_risks:
        sev_lbl, sev_cls = _severity_band(rk.severity_score)
        comp = rk.component or "—"
        sc = f"{rk.severity_score:.1f}" if rk.severity_score is not None else f"{rk.composite_score:.2f}"
        tier_cls = _tier_badge_class(rk.priority_tier)
        parts.append("<tr>")
        parts.append(f"<td>{rk.rank}</td>")
        parts.append(f"<td>{_esc(rk.threat_id)}</td>")
        parts.append(f"<td>{_esc(rk.title[:500])}</td>")
        parts.append(f"<td>{_esc(comp[:120])}</td>")
        parts.append(f"<td class='{_esc(sev_cls)}'>{_esc(sev_lbl)}</td>")
        parts.append(f"<td>{_esc(sc)}</td>")
        parts.append(f"<td><span class='badge-tier {_esc(tier_cls)}'>{_esc(rk.priority_tier)}</span></td>")
        parts.append("</tr>")
    parts.append(_TABLE_SECTION_CLOSE)


def _html_root_cause_and_roadmap(parts: list[str], payload: PremiumReportPayload) -> None:
    if payload.root_cause_groups:
        parts.append(_HR_DIVIDER)
        parts.append("<section class='section'><h2>Root cause breakdown</h2>")
        parts.append("<div class='root-grid'>")
        for i, g in enumerate(payload.root_cause_groups[:12]):
            rc = _root_cause_row_class(i)
            icons = ("&#128308;", "&#128992;", "&#128993;", "&#128309;")
            ic = icons[i % 4]
            parts.append(
                f"<div class='root-row {rc}'>{ic} <strong>{_esc(g.display_name)}</strong> "
                f"<span class='tier-p2'>({g.threat_count})</span><br/>"
                f"<span class='small-muted'>{_esc(g.single_fix_recommendation[:320])}</span></div>"
            )
        parts.append("</div></section>")

    if payload.roadmap:
        parts.append(_HR_DIVIDER)
        parts.append("<section class='section'><h2>Remediation roadmap</h2>")
        for ph in payload.roadmap:
            h = _roadmap_heading(ph.phase)
            parts.append(f"<div class='roadmap-block'><h3>{_esc(h)} — {_esc(ph.title)}</h3><ul>")
            for it in ph.items[:20]:
                parts.append(f"<li>{_esc(it[:800])}</li>")
            parts.append("</ul></div>")
        parts.append("</section>")


def _html_quick_and_strategic(parts: list[str], payload: PremiumReportPayload) -> None:
    if payload.level != ReportLevel.EXECUTIVE and payload.quick_wins:
        parts.append(_HR_DIVIDER)
        parts.append("<section class='section'><h2>Quick wins</h2><ul>")
        for qw in payload.quick_wins[:12]:
            parts.append(f"<li><strong>{_esc(qw.title[:200])}</strong> — {_esc(qw.rationale[:400])}</li>")
        parts.append("</ul></section>")

    if payload.level != ReportLevel.EXECUTIVE and payload.strategic_recommendations:
        parts.append(_HR_DIVIDER)
        parts.append("<section class='section'><h2>Strategic recommendations</h2>")
        for s in payload.strategic_recommendations[:10]:
            parts.append(f"<h3>{_esc(s.title)}</h3><p>{_esc(s.detail[:600])}</p>")
        parts.append("</section>")


def _html_detail_tables(parts: list[str], payload: PremiumReportPayload) -> None:
    if payload.level != ReportLevel.EXECUTIVE and payload.explainability:
        parts.append(_HR_DIVIDER)
        parts.append("<section class='section'><h2>Explainability (sample)</h2>")
        parts.append("<table class='risk-table'><tr><th>Category</th><th>Message</th><th>Confidence</th></tr>")
        for snippet in payload.explainability[:10]:
            conf = snippet.confidence or "—"
            parts.append(
                f"<tr><td>{_esc(snippet.category)}</td><td>{_esc(snippet.message[:350])}</td><td>{_esc(conf)}</td></tr>"
            )
        parts.append(_TABLE_SECTION_CLOSE)

    if payload.level != ReportLevel.EXECUTIVE and payload.business_impacts:
        parts.append(_HR_DIVIDER)
        parts.append("<section class='section'><h2>Business impact (sample)</h2>")
        parts.append("<table class='risk-table'><tr><th>Threat</th><th>Labels</th><th>Rationale</th></tr>")
        for impact in payload.business_impacts[:8]:
            labels = ", ".join(impact.labels[:6]) if impact.labels else "—"
            parts.append(
                f"<tr><td>{_esc(impact.threat_id)}</td><td>{_esc(labels)}</td>"
                f"<td>{_esc(impact.rationale[:400])}</td></tr>"
            )
        parts.append(_TABLE_SECTION_CLOSE)


def _html_exploit_and_baseline(parts: list[str], payload: PremiumReportPayload) -> None:
    if payload.level != ReportLevel.EXECUTIVE and payload.exploitability_profiles:
        parts.append(_HR_DIVIDER)
        parts.append("<section class='section'><h2>Exploitability context (sample)</h2>")
        parts.append("<table class='risk-table'><tr><th>Threat</th><th>Locality</th><th>Notes</th></tr>")
        for profile in payload.exploitability_profiles[:8]:
            parts.append(
                f"<tr><td>{_esc(profile.threat_id)}</td><td>{_esc(profile.attack_locality)}</td>"
                f"<td>{_esc(profile.notes[:450])}</td></tr>"
            )
        parts.append(_TABLE_SECTION_CLOSE)

    if payload.baseline_diff and payload.baseline_diff.has_baseline:
        parts.append(_HR_DIVIDER)
        parts.append("<section class='section'><h2>Baseline / delta</h2>")
        parts.append(f"<p>{_esc(payload.baseline_diff.narrative)}</p></section>")


def render_premium_html(payload: PremiumReportPayload) -> str:
    """
    Full HTML for xhtml2pdf. Labels and section chrome are **English** (executive PDF).
    Dynamic threat text follows the payload (may be non-English if model/heuristics are localized).
    """
    parts: list[str] = []
    _html_header(parts, payload)
    _html_executive_summary(parts, payload)
    _html_severity_distribution(parts, payload)
    _html_top_risks(parts, payload)
    _html_root_cause_and_roadmap(parts, payload)
    _html_quick_and_strategic(parts, payload)
    _html_detail_tables(parts, payload)
    _html_exploit_and_baseline(parts, payload)
    parts.append(
        "<footer>App Suite Modeling — Premium security report. "
        "Full technical detail: export Markdown or JSON analysis bundle.</footer></body></html>"
    )
    raw = "".join(parts)
    return re.sub(r">\s+<", "><", raw)
