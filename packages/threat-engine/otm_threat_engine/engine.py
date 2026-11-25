"""Orquestração da análise: um ponto de entrada claro."""

from __future__ import annotations

import os
from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from types import MappingProxyType

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_core_schema.model_quality_precheck import assess_model_precheck
from otm_industry_packs.models import PackDefinition

from otm_threat_engine.anti_pattern_library import detect_anti_patterns
from otm_threat_engine.business_abuse_heuristics import append_business_abuse_heuristics
from otm_threat_engine.composite_heuristics import append_composite_heuristics
from otm_threat_engine.custom_rules.models import CustomRuleSet
from otm_threat_engine.custom_rules.runtime import collect_control_hints, iter_custom_rule_threats
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
from otm_threat_engine.result import (
    AnalysisResult,
    HeuristicThreat,
    assert_threat_ids_are_injective,
)
from otm_threat_engine.risk_aggregate import build_aggregate_and_cockpit
from otm_threat_engine.structural import collect_structural_findings
from otm_threat_engine.trust_insights import analyze_trust_boundary_crossings
from otm_threat_engine.version import ENGINE_VERSION
from otm_threat_engine.wizard_signals import (
    apply_wizard_context_to_heuristics,
    build_corpus_mitigation_trace,
    signals_for_profile,
)

#: Família de abuso de negócio → vocabulário genérico que a delata numa heurística `eng_*`.
#: A chave é também o infixo do id `biz_` que arma a família (`biz_<família>_...`).
_BIZ_FAMILY_TOKENS: dict[str, tuple[str, ...]] = {
    # Webhook / gateway / replay / idempotência
    "webhook": ("webhook", "gateway_webhook", "payment_gateway", "payment_webhook_provider"),
    # Cupão / desconto
    "coupon": ("coupon", "cupom", "desconto", "discount", "checkout_coupon", "coupon_store"),
    # Entitlement / billing mismatch / activação indevida
    "payment_entitlement": (
        "entitlement",
        "premium",
        "billing",
        "subscription",
        "subscription_service",
        "entitlement_service",
    ),
    # Autorização contextual
    "authorization": ("authorization", "autoriz", "ownership", "vinculo", "vínculo"),
    # Saldo / ledger / consistência
    "balance": ("balance", "saldo", "ledger", "transactions", "transacoes", "ledger_service"),
    # Cancelamento / revogação
    "cancel": ("cancel", "revog", "subscription"),
}


def _token_hit(h: HeuristicThreat, *, tokens: tuple[str, ...]) -> bool:
    t = f"{h.id} {h.title} {h.target_component_id or ''} {h.target_data_flow_id or ''}".lower()
    return any(tok in t for tok in tokens)


def _biz_family_targets(heuristics: list[HeuristicThreat]) -> dict[str, set[str]]:
    """Por família `biz_*`, os alvos que essa família **realmente** cobre neste modelo.

    O vocabulário de cada família é comércio corrente — "billing", "subscription", "ledger",
    "cancel", "webhook", "coupon". Armar uma família pela mera *presença* de um achado `biz_*`
    em qualquer ponto do modelo e depois casar por substring apagava achados em alvos que a
    ameaça de negócio nunca tocou: um `biz_payment_entitlement_mismatch` sobre
    `entitlement_service` silenciava um fluxo `billing_admin_sync` do outro lado do sistema,
    e bastava renomear o fluxo para `partner_admin_sync` — mesmas propriedades de segurança —
    para o mesmo achado CRITICAL voltar a existir e o gate de CI voltar a disparar.

    Exigir alvo partilhado era o que já se fazia para a família `authorization`; as outras
    cinco continuavam globais. Um achado de negócio só pode falar pelo que aponta.
    """
    targets: dict[str, set[str]] = {}
    for h in heuristics:
        for family in _BIZ_FAMILY_TOKENS:
            if not h.id.startswith(f"biz_{family}_"):
                continue
            bucket = targets.setdefault(family, set())
            bucket.update(t for t in (h.target_component_id, h.target_data_flow_id) if t)
    return targets


def _shares_target(h: HeuristicThreat, targets: AbstractSet[str]) -> bool:
    return h.target_component_id in targets or h.target_data_flow_id in targets


def _should_suppress_stride_noise(
    *,
    h: HeuristicThreat,
    # Defaults to "no family covers anything", so a caller that omits it keeps findings
    # rather than silently dropping them.
    family_targets: Mapping[str, AbstractSet[str]] = MappingProxyType({}),
) -> bool:
    # Somente reduzir ruído STRIDE base (não mexer em `biz_*` ou pack).
    if not h.id.startswith("eng_"):
        return False
    if h.skipped_as_duplicate:
        return False
    if h.stride.value not in {"tampering", "elevation_of_privilege"}:
        return False
    return any(
        _shares_target(h, targets) and _token_hit(h, tokens=_BIZ_FAMILY_TOKENS[family])
        for family, targets in family_targets.items()
    )


def suppress_stride_genericity_noise(heuristics: list[HeuristicThreat]) -> int:
    """
    Etapa 3 (motor): reduzir ruído STRIDE quando já houver `biz_*` cobrindo a mesma causa raiz.

    Importante:
    - Não remove achados: marca como `skipped_as_duplicate=True` (rastreável no JSON).
    - Conservador: somente `eng_*` + `tampering/elevation_of_privilege` + o **mesmo alvo** que
      o achado `biz_*` da família aponta (ver `_biz_family_targets`).
    """
    toggle = (os.environ.get("OTM_ENGINE_STRIDE_NOISE_SUPPRESSION") or "1").strip().lower()
    if toggle in {"0", "false", "off", "no"}:
        return 0
    family_targets = _biz_family_targets(heuristics)
    if not family_targets:
        return 0
    suppressed = 0
    for h in heuristics:
        if _should_suppress_stride_noise(h=h, family_targets=family_targets):
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
        *,
        custom_rules: CustomRuleSet | None = None,
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
        # O filtro de âncora existe para os hints de pack, que são emitidos incondicionalmente:
        # descarta o que não tem correspondência no domínio do modelo. Corre aqui, **antes** dos
        # controlos das regras da organização, e nunca sobre eles.
        pack_hints = filter_pack_control_hints(doc, pack_hints)

        # Regras da organização correm por último e são aditivas: não suprimem nem são
        # suprimidas pelas heurísticas base (ver `iter_custom_rule_threats`).
        #
        # Os seus `control_hint` também não passam pelo filtro de âncora, e por uma razão de
        # fundo: `collect_control_hints` só devolve controlos de regras que **dispararam** neste
        # modelo, portanto a pergunta que o filtro faz — "existe âncora para isto?" — já foi
        # respondida pela própria correspondência da regra. Passá-los pelo filtro apagava o
        # controlo de regras que tinham acabado de levantar a ameaça: uma regra sobre
        # `privilege_level: admin` ou `supports_file_upload: true` casa em campos estruturados
        # que o corpus do filtro nem lê, por isso o motor levantava o achado e deitava fora a
        # correcção, sem nota, aviso ou registo.
        if custom_rules is not None:
            custom_threats, fired_rules = iter_custom_rule_threats(doc, custom_rules)
            heuristics.extend(custom_threats)
            pack_hints = [*pack_hints, *collect_control_hints(custom_rules, fired_rules)]

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

        # Depois de todas as fontes (base, composite, pack, regras da organização) e antes de o
        # resultado sair daqui: nenhum consumidor a jusante distingue duas ameaças com o mesmo id.
        assert_threat_ids_are_injective(heuristics)

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
        custom_rules: CustomRuleSet | None = None,
    ) -> AnalysisResult:
        chosen, rec_reason, meth_exps = resolve_methodology_selection(
            doc,
            methodology=methodology,
            auto_recommend=auto_recommend,
        )

        base = self._analyze_stride_core(doc, pack=pack, custom_rules=custom_rules)
        final = finalize_analysis_with_methodology(
            doc=doc,
            base=base,
            methodology=chosen,
            recommendation_reason=rec_reason,
            methodology_explanations=meth_exps,
        )
        risk_views = build_aggregate_and_cockpit(final)
        return final.model_copy(
            update={
                "model_quality_precheck": assess_model_precheck(doc),
                "methodology_completeness": assess_methodology_completeness(doc, chosen),
                "anti_pattern_hits": detect_anti_patterns(doc),
                "aggregate_risk": risk_views["aggregate_risk"].model_dump(mode="json"),
                "decision_cockpit": risk_views["decision_cockpit"].model_dump(mode="json"),
            }
        )


def analyze_document(
    doc: ThreatModelDocument,
    pack: PackDefinition | None = None,
    *,
    methodology: ThreatModelMethodology | str | None = None,
    auto_recommend: bool = False,
    custom_rules: CustomRuleSet | None = None,
) -> AnalysisResult:
    """Atalho funcional equivalente a `ThreatAnalysisEngine().analyze(...)`."""
    return ThreatAnalysisEngine().analyze(
        doc,
        pack=pack,
        methodology=methodology,
        auto_recommend=auto_recommend,
        custom_rules=custom_rules,
    )
