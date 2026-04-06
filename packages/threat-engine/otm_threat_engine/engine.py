"""Orquestração da análise: um ponto de entrada claro."""

from __future__ import annotations

import os

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_core_schema.model_quality_precheck import assess_model_precheck
from otm_industry_packs.models import PackDefinition

from otm_threat_engine.anti_pattern_library import detect_anti_patterns
from otm_threat_engine.business_abuse_heuristics import append_business_abuse_heuristics
from otm_threat_engine.composite_heuristics import append_composite_heuristics
from otm_threat_engine.engine_finalize import finalize_analysis_with_methodology
from otm_threat_engine.engine_methodology_runtime import resolve_methodology_selection
from otm_threat_engine.engine_stride_builder import (
    append_component_heuristics,
    append_flow_heuristics,
)
from otm_threat_engine.engine_support import (
    build_analysis_summary,
    cross_boundary_flow_ids,
    existing_threat_keys,
    extend_with_pack_heuristics,
)
from otm_threat_engine.methodology_completeness import assess_methodology_completeness
from otm_threat_engine.recommendation_gate import filter_pack_control_hints
from otm_threat_engine.result import AnalysisResult, HeuristicThreat
from otm_threat_engine.structural import collect_structural_findings
from otm_threat_engine.trust_insights import analyze_trust_boundary_crossings
from otm_threat_engine.version import ENGINE_VERSION
from otm_threat_engine.wizard_signals import (
    apply_wizard_context_to_heuristics,
    build_corpus_mitigation_trace,
    signals_for_profile,
)


def _biz_family_flags_from_heuristics(heuristics: list[HeuristicThreat]) -> dict[str, bool]:
    ids = " ".join(h.id.lower() for h in heuristics if h.id.startswith("biz_"))
    return {
        "webhook": "biz_webhook_" in ids,
        "coupon": "biz_coupon_" in ids,
        "payment_entitlement": "biz_payment_entitlement_" in ids,
        "authorization": "biz_authorization_" in ids,
        "balance": "biz_balance_" in ids,
        "cancel": "biz_cancel_" in ids,
    }


def _token_hit(h: HeuristicThreat, *, tokens: tuple[str, ...]) -> bool:
    t = f"{h.id} {h.title} {h.target_component_id or ''} {h.target_data_flow_id or ''}".lower()
    return any(tok in t for tok in tokens)


def _should_suppress_stride_noise(*, h: HeuristicThreat, flags: dict[str, bool]) -> bool:
    # Somente reduzir ruído STRIDE base (não mexer em `biz_*` ou pack).
    if not h.id.startswith("eng_"):
        return False
    if h.skipped_as_duplicate:
        return False
    if h.stride.value not in {"tampering", "elevation_of_privilege"}:
        return False

    # Webhook / gateway / replay / idempotência
    if flags.get("webhook") and _token_hit(
        h,
        tokens=(
            "webhook",
            "gateway_webhook",
            "payment_gateway",
            "payment_webhook_provider",
        ),
    ):
        return True

    # Cupom / desconto
    if flags.get("coupon") and _token_hit(
        h,
        tokens=("coupon", "cupom", "desconto", "discount", "checkout_coupon", "coupon_store"),
    ):
        return True

    # Entitlement / billing mismatch / ativação indevida
    if flags.get("payment_entitlement") and _token_hit(
        h,
        tokens=(
            "entitlement",
            "premium",
            "billing",
            "subscription",
            "subscription_service",
            "entitlement_service",
        ),
    ):
        return True

    # Authorization contextual
    if flags.get("authorization") and _token_hit(
        h, tokens=("authorization", "autoriz", "ownership", "vinculo", "vínculo")
    ):
        return True

    # Saldo / ledger / consistência
    if flags.get("balance") and _token_hit(
        h, tokens=("balance", "saldo", "ledger", "transactions", "transacoes", "ledger_service")
    ):
        return True

    # Cancelamento / revogação
    if flags.get("cancel") and _token_hit(h, tokens=("cancel", "revog", "subscription")):
        return True

    return False


def suppress_stride_genericity_noise(heuristics: list[HeuristicThreat]) -> int:
    """
    Etapa 3 (motor): reduzir ruído STRIDE quando já houver `biz_*` cobrindo a mesma causa raiz.

    Importante:
    - Não remove achados: marca como `skipped_as_duplicate=True` (rastreável no JSON).
    - Conservador: somente `eng_*` + `tampering/elevation_of_privilege` + clusters com famílias
      `biz_*`.
    """
    toggle = (os.environ.get("OTM_ENGINE_STRIDE_NOISE_SUPPRESSION") or "1").strip().lower()
    if toggle in {"0", "false", "off", "no"}:
        return 0
    flags = _biz_family_flags_from_heuristics(heuristics)
    if not any(flags.values()):
        return 0
    suppressed = 0
    for h in heuristics:
        if _should_suppress_stride_noise(h=h, flags=flags):
            h.skipped_as_duplicate = True
            suppressed += 1
    return suppressed


def _build_covered_threat_keys(
    *,
    doc: ThreatModelDocument,
    heuristics: list[HeuristicThreat],
) -> set[tuple[str | None, str | None, str]]:
    covered = set(existing_threat_keys(doc))
    for h in heuristics:
        if h.skipped_as_duplicate:
            continue
        covered.add((h.target_component_id, h.target_data_flow_id, h.stride.value))
    return covered


class ThreatAnalysisEngine:
    """
    Motor inicial: validação estrutural (avisos), insights de fronteira,
    ameaças heurísticas STRIDE e pontuação L×I.
    Opcionalmente aplica um industry pack (pesos e ameaças de contexto).
    """

    def _analyze_stride_core(
        self,
        doc: ThreatModelDocument,
        pack: PackDefinition | None = None,
    ) -> AnalysisResult:
        structural = collect_structural_findings(doc)
        trust_findings = analyze_trust_boundary_crossings(doc)
        existing = existing_threat_keys(doc)
        assets_by_id = {a.id: a for a in doc.assets}
        cross_flows = cross_boundary_flow_ids(doc)

        heuristics: list[HeuristicThreat] = []
        skipped = append_component_heuristics(
            doc=doc,
            heuristics=heuristics,
            existing=existing,
            assets_by_id=assets_by_id,
            pack=pack,
        )
        skipped += append_flow_heuristics(
            doc=doc,
            heuristics=heuristics,
            existing=existing,
            cross_flows=cross_flows,
            pack=pack,
        )
        append_business_abuse_heuristics(doc=doc, heuristics=heuristics)

        append_composite_heuristics(
            doc,
            heuristics,
            existing_ids={h.id for h in heuristics},
        )
        covered = _build_covered_threat_keys(doc=doc, heuristics=heuristics)

        pack_gen, pack_skip, pack_hints = extend_with_pack_heuristics(
            doc=doc,
            heuristics=heuristics,
            covered=covered,
            pack=pack,
        )
        pack_hints = filter_pack_control_hints(doc, pack_hints)
        skipped += suppress_stride_genericity_noise(heuristics)
        _, wizard_notes, boost_trace = apply_wizard_context_to_heuristics(doc, heuristics)
        corpus_trace = build_corpus_mitigation_trace(signals_for_profile(doc))
        wizard_signal_trace = [*boost_trace, *corpus_trace]
        summary = build_analysis_summary(
            structural_count=len(structural),
            trust_count=len(trust_findings),
            heuristics=heuristics,
            base_skipped=skipped,
            pack_gen=pack_gen,
            pack_skip=pack_skip,
        )

        raw = AnalysisResult(
            engine_version=ENGINE_VERSION,
            methodology=ThreatModelMethodology.STRIDE,
            document_title=doc.metadata.title,
            structural_findings=structural,
            trust_boundary_findings=trust_findings,
            heuristic_threats=heuristics,
            summary=summary,
            industry_pack_id=pack.id if pack else None,
            pack_control_hints=pack_hints,
            wizard_context_notes=wizard_notes,
            wizard_signal_trace=wizard_signal_trace,
        )
        return raw

    def analyze(
        self,
        doc: ThreatModelDocument,
        pack: PackDefinition | None = None,
        *,
        methodology: ThreatModelMethodology | str | None = None,
        auto_recommend: bool = False,
    ) -> AnalysisResult:
        chosen, rec_reason, meth_exps = resolve_methodology_selection(
            doc,
            methodology=methodology,
            auto_recommend=auto_recommend,
        )

        base = self._analyze_stride_core(doc, pack=pack)
        final = finalize_analysis_with_methodology(
            doc=doc,
            base=base,
            methodology=chosen,
            recommendation_reason=rec_reason,
            methodology_explanations=meth_exps,
        )
        return final.model_copy(
            update={
                "model_quality_precheck": assess_model_precheck(doc),
                "methodology_completeness": assess_methodology_completeness(doc, chosen),
                "anti_pattern_hits": detect_anti_patterns(doc),
            }
        )


def analyze_document(
    doc: ThreatModelDocument,
    pack: PackDefinition | None = None,
    *,
    methodology: ThreatModelMethodology | str | None = None,
    auto_recommend: bool = False,
) -> AnalysisResult:
    """Atalho funcional equivalente a `ThreatAnalysisEngine().analyze(...)`."""
    return ThreatAnalysisEngine().analyze(
        doc,
        pack=pack,
        methodology=methodology,
        auto_recommend=auto_recommend,
    )
