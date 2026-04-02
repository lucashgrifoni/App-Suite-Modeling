"""HTML semântico + CSS embutido para PDF premium (intermediário reproduzível)."""

from __future__ import annotations

import html
import re

from .models import PremiumReportPayload

_PREMIUM_CSS = """
@page { size: A4; margin: 14mm; }
body {
  font-family: "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 10pt;
  color: #1a1d26;
  line-height: 1.35;
}
header.cover {
  border-bottom: 3px solid #2563eb;
  padding-bottom: 12px;
  margin-bottom: 18px;
}
h1 { font-size: 20pt; color: #0f172a; margin: 0 0 6px 0; }
h2 { font-size: 13pt; color: #1e3a8a; margin-top: 18px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }
h3 { font-size: 11pt; color: #334155; margin-top: 12px; }
.meta { font-size: 9pt; color: #475569; }
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 8.5pt;
  font-weight: 600;
  background: #eff6ff;
  color: #1d4ed8;
  margin-right: 6px;
}
.disclaimer {
  background: #fffbeb;
  border-left: 4px solid #f59e0b;
  padding: 8px 12px;
  margin: 12px 0;
  font-size: 9pt;
}
table { border-collapse: collapse; width: 100%; margin: 8px 0 14px 0; font-size: 9pt; }
th, td { border: 1px solid #cbd5e1; padding: 5px 7px; text-align: left; vertical-align: top; }
th { background: #f1f5f9; color: #0f172a; }
tr:nth-child(even) td { background: #f8fafc; }
.section { page-break-inside: avoid; }
footer { font-size: 8pt; color: #64748b; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 8px; }
"""


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def render_premium_html(payload: PremiumReportPayload) -> str:
    """HTML completo (uma página fluida) para conversão PDF."""
    c = payload.cover
    parts: list[str] = [
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'/>",
        f"<title>{_esc(c.title)}</title><style>{_PREMIUM_CSS}</style></head><body>",
        "<header class='cover'>",
        "<span class='badge'>App Suite Modeling</span>",
        f"<h1>{_esc(c.title)}</h1>",
        "<p class='meta'>",
        f"Schema {_esc(c.schema_version)} · Metodologia {_esc(c.primary_methodology)} · ",
        f"Data {_esc(c.analysis_date_iso)} · Versão produto {_esc(c.app_suite_version)}",
        "</p>",
        f"<p><strong>Estado:</strong> {_esc(c.overall_status_display)} · ",
        f"<strong>Risco (heurístico):</strong> {_esc(c.overall_risk_label)}</p>",
        "</header>",
        "<div class='disclaimer'>",
        f"<strong>Inferência.</strong> {_esc(payload.disclaimer.summary)}",
        "</div>",
        "<section class='section'><h2>Executive summary</h2>",
        f"<p>{_esc(payload.executive_summary.executive_conclusion)}</p>",
        "<p><strong>Ameaças totais:</strong> "
        f"{payload.executive_summary.threat_count} · <strong>Urgência:</strong> "
        f"{_esc(payload.executive_summary.urgency_level)}</p>",
        "</section>",
    ]

    parts.append("<section class='section'><h2>Top riscos</h2><table><tr>")
    parts.append("<th>#</th><th>ID</th><th>Título</th><th>Tier</th><th>P</th></tr>")
    for r in payload.top_risks:
        parts.append(
            "<tr>"
            f"<td>{r.rank}</td>"
            f"<td>{_esc(r.threat_id)}</td>"
            f"<td>{_esc(r.title[:200])}</td>"
            f"<td>{_esc(r.priority_tier)}</td>"
            f"<td>{r.composite_score:.2f}</td>"
            "</tr>"
        )
    parts.append("</table></section>")

    if payload.root_cause_groups:
        parts.append("<section class='section'><h2>Causas raiz</h2><ul>")
        for g in payload.root_cause_groups[:12]:
            parts.append(
                f"<li><strong>{_esc(g.display_name)}</strong> ({g.threat_count}) — "
                f"{_esc(g.single_fix_recommendation[:280])}</li>"
            )
        parts.append("</ul></section>")

    if payload.roadmap:
        parts.append("<section class='section'><h2>Roadmap</h2>")
        for ph in payload.roadmap:
            parts.append(f"<h3>{_esc(ph.title)}</h3><ul>")
            for it in ph.items[:15]:
                parts.append(f"<li>{_esc(it[:500])}</li>")
            parts.append("</ul>")
        parts.append("</section>")

    if payload.baseline_diff and payload.baseline_diff.has_baseline:
        parts.append(
            "<section class='section'><h2>Baseline / diff</h2>"
            f"<p>{_esc(payload.baseline_diff.narrative)}</p></section>"
        )

    parts.append(
        "<footer>Relatório premium — App Suite Modeling. "
        "Conteúdo técnico completo disponível em Markdown exportado.</footer>"
        "</body></html>"
    )
    # Remove newlines that break very old parsers
    raw = "".join(parts)
    return re.sub(r">\s+<", "><", raw)
