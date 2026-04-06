"""Use case: diff two threat model versions."""

from __future__ import annotations

import json
from pathlib import Path

from otm_core_schema import diff_documents
from otm_exporters import export_comparison_markdown
from otm_threat_engine import AnalysisResult, analyze_document
from otm_threat_engine.threat_model_comparison import compare_threat_models

from otm_cli.shared.document_loader import load_otm_document, load_pack_or_raise
from otm_cli.shared.enums import DiffFormat


def run_model_diff(
    baseline: Path,
    revised: Path,
    *,
    with_analysis: bool,
    pack: str | None,
    fmt: DiffFormat,
    summary_only: bool,
) -> tuple[dict, str | None, str | None, str | None]:
    """
    Return (out_payload, json_body_to_print, markdown_body, text_panel_body).

    json_body_to_print: only when fmt==json (preformatted string).
    markdown_body: only when fmt==markdown.
    text_panel_body: multi-line text for Panel in text mode.
    """
    doc_a = load_otm_document(
        baseline,
        failed=f"reading baseline `{baseline}`.",
        validation_next_step="run `otm validate` on the baseline.",
        runtime_next_step="confirm the path and YAML.",
    )
    doc_b = load_otm_document(
        revised,
        failed=f"reading revised `{revised}`.",
        validation_next_step="run `otm validate` on the revised file.",
        runtime_next_step="confirm the path and YAML.",
    )
    pack_def = None
    if pack:
        pack_def = load_pack_or_raise(
            pack_id=pack,
            failed=f"loading pack `{pack}`.",
            next_step="run `otm packs`.",
        )
    ba: AnalysisResult | None = None
    ra: AnalysisResult | None = None
    if with_analysis:
        ba = analyze_document(doc_a, pack=pack_def)
        ra = analyze_document(doc_b, pack=pack_def)
    full = compare_threat_models(doc_a, doc_b, baseline_analysis=ba, revised_analysis=ra)

    if with_analysis:
        out_payload = full.model_dump(mode="json")
    else:
        out_payload = diff_documents(doc_a, doc_b).model_dump(mode="json")

    if fmt == DiffFormat.json:
        return out_payload, json.dumps(out_payload, indent=2, ensure_ascii=False), None, None

    if fmt == DiffFormat.markdown:
        return out_payload, None, export_comparison_markdown(full), None

    if summary_only:
        lines2 = [full.summary.headline, "", "Insights:"]
        for ins in full.key_insights[:25]:
            lines2.append(f"- {ins}")
        return out_payload, None, None, "\n".join(lines2)

    result = full.structural
    lines: list[str] = [full.summary.headline, ""]
    if full.structural_insights:
        lines.append("Structural insights:")
        for ins in full.structural_insights[:12]:
            lines.append(f"- {ins}")
        lines.append("")
    if with_analysis and full.analysis_insights:
        lines.append("Analysis insights:")
        for ins in full.analysis_insights[:12]:
            lines.append(f"- {ins}")
        lines.append("")
    if with_analysis and full.meta:
        meta = full.meta
        disc = meta.interpretation_disclaimer
        if isinstance(disc, str) and disc.strip():
            lines.append("Interpretation disclaimer:")
            lines.append(f"  {disc.strip()}")
            lines.append("")
        sem = meta.semantic_diff_sections
        if sem is not None:
            scs = sem.structural_change_summary or []
            imp, wor, risk = sem.improved or [], sem.worsened or [], sem.risk_impact or []
            if scs or imp or wor or risk:
                lines.append("Semantic diff (heuristic):")
                for x in scs[:5]:
                    lines.append(f"  Δ {x}")
                for x in imp[:6]:
                    lines.append(f"  + {x}")
                for x in wor[:6]:
                    lines.append(f"  ! {x}")
                for x in risk[:5]:
                    lines.append(f"  ~ {x}")
                lines.append("")
        refs = meta.semantic_structural_refs
        if refs:
            lines.append("Structural→interpretation refs (anchored, non-causal):")
            for item in refs[:12]:
                lines.append(f"  {item.ref} · {item.entity_kind} `{item.entity_id}`")
            lines.append("")
        ilinks = meta.semantic_interpretation_links
        if ilinks:
            lines.append("Ref → interpretation mapping (v1.5, with rationale):")
            for item in ilinks[:10]:
                lines.append(
                    f"  {item.structural_ref} → {item.related_section} "
                    f"[{item.link_kind}/{item.inference_strength}]: "
                    f"{str(item.summary)[:100]}"
                )
                if item.anchoring_rationale:
                    lines.append(f"    → {str(item.anchoring_rationale)[:160]}")
            lines.append("")
        si = meta.semantic_insights
        if si:
            lines.append("Semantic insights:")
            for x in si[:10]:
                lines.append(f"- {x}")
            lines.append("")

    for label, sec in [
        ("model_info", result.model_info),
        ("metadata", result.metadata),
        ("business_context", result.business_context),
        ("residual_risk_summary", result.residual_risk_summary),
    ]:
        if sec:
            lines.append(f"[{label}]")
            for ch in sec:
                lines.append(f"  - {ch.field}: changed")
            lines.append("")
    for name, sec in [
        ("assets", result.assets),
        ("components", result.components),
        ("data_flows", result.data_flows),
        ("trust_boundaries", result.trust_boundaries),
        ("threats", result.threats),
        ("mitigations", result.mitigations),
        ("evidence_suggestions", result.evidence_suggestions),
    ]:
        if sec.added or sec.removed or sec.modified:
            lines.append(f"[{name}] +{len(sec.added)} / -{len(sec.removed)} / ~{len(sec.modified)}")
            if sec.added:
                lines.append(f"  added: {', '.join(sec.added)}")
            if sec.removed:
                lines.append(f"  removed: {', '.join(sec.removed)}")
            for m in sec.modified[:12]:
                fields = ", ".join(c.field for c in m.changes)
                lines.append(f"  ~ {m.id}: {fields}")
            if len(sec.modified) > 12:
                lines.append(f"  … +{len(sec.modified) - 12} more modified")
            lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    return out_payload, None, None, text
