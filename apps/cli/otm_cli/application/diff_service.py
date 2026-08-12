"""Use case: diff two threat model versions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from otm_core_schema import diff_documents
from otm_exporters import export_comparison_markdown
from otm_threat_engine import AnalysisResult, analyze_document
from otm_threat_engine.comparison_models import AnalysisDiff
from otm_threat_engine.threat_model_comparison import compare_threat_models

from otm_cli.application.custom_rules_io import load_custom_rules_or_raise
from otm_cli.shared.document_loader import load_otm_document, load_pack_or_raise
from otm_cli.shared.enums import DiffFormat, MethodologyOption


def _diff_header_lines(full: Any, with_analysis: bool) -> list[str]:
    """Cabeçalho do painel de texto: headline + insights estruturais/de análise."""
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
    return lines


def _semantic_diff_lines(sem: Any) -> list[str]:
    scs = sem.structural_change_summary or []
    imp, wor, risk = sem.improved or [], sem.worsened or [], sem.risk_impact or []
    if not (scs or imp or wor or risk):
        return []
    lines = ["Semantic diff (heuristic):"]
    lines.extend(f"  Δ {x}" for x in scs[:5])
    lines.extend(f"  + {x}" for x in imp[:6])
    lines.extend(f"  ! {x}" for x in wor[:6])
    lines.extend(f"  ~ {x}" for x in risk[:5])
    lines.append("")
    return lines


def _interpretation_link_lines(ilinks: Any) -> list[str]:
    lines = ["Ref → interpretation mapping (v1.5, with rationale):"]
    for link_item in ilinks[:10]:
        lines.append(
            f"  {link_item.structural_ref} → {link_item.related_section} "
            f"[{link_item.link_kind}/{link_item.inference_strength}]: "
            f"{str(link_item.summary)[:100]}"
        )
        if link_item.anchoring_rationale:
            lines.append(f"    → {str(link_item.anchoring_rationale)[:160]}")
    lines.append("")
    return lines


def _diff_meta_lines(meta: Any) -> list[str]:
    """Secção de metadados semânticos (apenas em modo análise com `meta`)."""
    lines: list[str] = []
    disc = meta.interpretation_disclaimer
    if isinstance(disc, str) and disc.strip():
        lines.append("Interpretation disclaimer:")
        lines.append(f"  {disc.strip()}")
        lines.append("")
    sem = meta.semantic_diff_sections
    if sem is not None:
        lines.extend(_semantic_diff_lines(sem))
    refs = meta.semantic_structural_refs
    if refs:
        lines.append("Structural→interpretation refs (anchored, non-causal):")
        for ref_item in refs[:12]:
            lines.append(f"  {ref_item.ref} · {ref_item.entity_kind} `{ref_item.entity_id}`")
        lines.append("")
    ilinks = meta.semantic_interpretation_links
    if ilinks:
        lines.extend(_interpretation_link_lines(ilinks))
    si = meta.semantic_insights
    if si:
        lines.append("Semantic insights:")
        for x in si[:10]:
            lines.append(f"- {x}")
        lines.append("")
    return lines


def _field_section_lines(result: Any) -> list[str]:
    lines: list[str] = []
    for label, field_section in [
        ("model_info", result.model_info),
        ("metadata", result.metadata),
        ("business_context", result.business_context),
        ("residual_risk_summary", result.residual_risk_summary),
    ]:
        if field_section:
            lines.append(f"[{label}]")
            for ch in field_section:
                lines.append(f"  - {ch.field}: changed")
            lines.append("")
    return lines


def _id_section_block(name: str, id_section: Any) -> list[str]:
    if not (id_section.added or id_section.removed or id_section.modified):
        return []
    lines = [f"[{name}] +{len(id_section.added)} / -{len(id_section.removed)} / ~{len(id_section.modified)}"]
    if id_section.added:
        lines.append(f"  added: {', '.join(id_section.added)}")
    if id_section.removed:
        lines.append(f"  removed: {', '.join(id_section.removed)}")
    for m in id_section.modified[:12]:
        fields = ", ".join(c.field for c in m.changes)
        lines.append(f"  ~ {m.id}: {fields}")
    if len(id_section.modified) > 12:
        lines.append(f"  … +{len(id_section.modified) - 12} more modified")
    lines.append("")
    return lines


def _id_section_lines(result: Any) -> list[str]:
    lines: list[str] = []
    for name, id_section in [
        ("assets", result.assets),
        ("components", result.components),
        ("data_flows", result.data_flows),
        ("trust_boundaries", result.trust_boundaries),
        ("threats", result.threats),
        ("mitigations", result.mitigations),
        ("evidence_suggestions", result.evidence_suggestions),
    ]:
        lines.extend(_id_section_block(name, id_section))
    return lines


def run_model_diff(
    baseline: Path,
    revised: Path,
    *,
    with_analysis: bool,
    pack: str | None,
    fmt: DiffFormat,
    summary_only: bool,
    methodology: MethodologyOption | None = None,
    auto_methodology: bool = False,
    rules: Path | None = None,
) -> tuple[dict, str | None, str | None, str | None, AnalysisDiff | None]:
    """
    Return (out_payload, json_body_to_print, markdown_body, text_panel_body, analysis_diff).

    json_body_to_print: only when fmt==json (preformatted string).
    markdown_body: only when fmt==markdown.
    text_panel_body: multi-line text for Panel in text mode.
    analysis_diff: heuristic/risk delta, present only when `with_analysis` — what the CI gate evaluates.
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
    ruleset = load_custom_rules_or_raise(rules)
    ba: AnalysisResult | None = None
    ra: AnalysisResult | None = None
    if with_analysis:
        # Both sides must run under the SAME lens, and it must be the lens the caller asked
        # for: the gate compares these two analyses, so judging them under a different
        # methodology than the one configured is a silent pass or a spurious failure. The same
        # applies to the organisation rules: one ruleset, both sides, so a custom-rule threat
        # that appears only on the revised side is a real regression and not a config artefact.
        lens = methodology.value if methodology else None
        ba = analyze_document(
            doc_a, pack=pack_def, methodology=lens, auto_recommend=auto_methodology, custom_rules=ruleset
        )
        ra = analyze_document(
            doc_b, pack=pack_def, methodology=lens, auto_recommend=auto_methodology, custom_rules=ruleset
        )
    full = compare_threat_models(doc_a, doc_b, baseline_analysis=ba, revised_analysis=ra)

    if with_analysis:
        out_payload = full.model_dump(mode="json")
    else:
        out_payload = diff_documents(doc_a, doc_b).model_dump(mode="json")

    analysis_diff = full.analysis

    if fmt == DiffFormat.json:
        return out_payload, json.dumps(out_payload, indent=2, ensure_ascii=False), None, None, analysis_diff

    if fmt == DiffFormat.markdown:
        return out_payload, None, export_comparison_markdown(full), None, analysis_diff

    if summary_only:
        lines2 = [full.summary.headline, "", "Insights:"]
        for ins in full.key_insights[:25]:
            lines2.append(f"- {ins}")
        return out_payload, None, None, "\n".join(lines2), analysis_diff

    result = full.structural
    lines = _diff_header_lines(full, with_analysis)
    if with_analysis and full.meta:
        lines.extend(_diff_meta_lines(full.meta))
    lines.extend(_field_section_lines(result))
    lines.extend(_id_section_lines(result))
    text = "\n".join(lines).rstrip() + "\n"
    return out_payload, None, None, text, analysis_diff
