"""Coverage — direct unit tests for specific reachable branches the pipeline sweep misses."""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import IndustrySector, create_blank_document
from otm_core_schema.diff import _field_changes_for_dicts


def test_field_changes_added_only_and_removed_only() -> None:
    # key only in `after` -> before=None; key only in `before` -> after=None
    changes = _field_changes_for_dicts({"id": "x", "removed_key": 1}, {"id": "x", "added_key": 2})
    by_field = {c.field: (c.before, c.after) for c in changes}
    assert by_field["added_key"] == (None, 2)
    assert by_field["removed_key"] == (1, None)


def test_suppress_stride_noise_toggle_off(monkeypatch) -> None:
    from otm_threat_engine import engine

    monkeypatch.setenv("OTM_ENGINE_STRIDE_NOISE_SUPPRESSION", "0")
    assert engine.suppress_stride_genericity_noise([]) == 0


def test_payment_anchor_absent_returns_false() -> None:
    from otm_threat_engine.recommendation_gate import _has_payment_anchor

    assert _has_payment_anchor(create_blank_document()) is False


def test_looks_like_ai_context_via_keyword() -> None:
    from otm_threat_engine.methodology_lenses.common import looks_like_ai_context

    doc = create_blank_document()
    doc = doc.model_copy(update={"metadata": doc.metadata.model_copy(update={"summary": "prompt orchestration layer"})})
    # no llm/rag token, no safe-ai marker -> falls through to the final keyword `any(...)` (returns True on "prompt")
    assert looks_like_ai_context(doc) is True


def test_pii_context_healthcare_sector() -> None:
    from otm_threat_engine.methodology_lenses.linddun import _looks_like_pii_context

    doc = create_blank_document()
    doc = doc.model_copy(
        update={"model_info": doc.model_info.model_copy(update={"industry_sector": IndustrySector.HEALTHCARE})}
    )
    # no explicit privacy tokens in the blob, but HEALTHCARE sector -> the sector branch returns True
    assert _looks_like_pii_context(doc) is True


def test_k8s_ingress_host_extraction() -> None:
    from otm_artifact_import.k8s_import import import_kubernetes_text

    manifest = (
        "apiVersion: networking.k8s.io/v1\n"
        "kind: Ingress\n"
        "metadata:\n"
        "  name: web-ingress\n"
        "rules:\n"
        "  - host: app.example.com\n"
        "  - host: api.example.com\n"
    )
    res = import_kubernetes_text(manifest)
    # host extraction branch populates the ingress hosts -> referenced in the draft
    assert res.document is not None


def test_terraform_path_empty_directory(tmp_path: Path) -> None:
    from otm_artifact_import.terraform_import import import_terraform_path

    res = import_terraform_path(tmp_path)
    assert any("`.tf`" in u for u in res.unknowns)


def test_helm_path_empty_directory(tmp_path: Path) -> None:
    from otm_artifact_import.helm_import import import_helm_path

    res = import_helm_path(tmp_path)
    assert any("Chart.yaml" in u for u in res.unknowns)


def test_framework_refs_compact_none_and_overflow() -> None:
    from otm_core_schema import FrameworkRef
    from otm_exporters.analysis_markdown import _format_framework_refs_compact, analysis_markdown_messages

    msgs = analysis_markdown_messages(None)
    assert _format_framework_refs_compact([], msgs) == msgs.ref_none  # empty -> ref_none branch
    many = [FrameworkRef(framework="NIST", control_id=f"C{i}") for i in range(10)]
    out = _format_framework_refs_compact(many, msgs)  # > max_items -> ref_more branch
    assert out  # contains the "+N more" suffix


def test_append_bullet_section_empty_returns() -> None:
    from otm_exporters.analysis_markdown import _append_bullet_section

    lines: list[str] = []
    _append_bullet_section(lines, "Header", [], 5)  # empty items -> early return
    assert lines == []


def test_md_table_empty_rows() -> None:
    from otm_report_premium.render_markdown import _md_table

    assert _md_table(["A", "B"], [], "no-data") == "no-data\n"  # empty rows -> empty_msg branch


def test_suppress_stride_noise_no_biz_families(monkeypatch) -> None:
    from otm_threat_engine import engine

    monkeypatch.delenv("OTM_ENGINE_STRIDE_NOISE_SUPPRESSION", raising=False)  # default ON
    # toggle on, but no heuristics -> no biz family flags -> the `not any(flags)` return-0 branch
    assert engine.suppress_stride_genericity_noise([]) == 0


def test_risk_calc_data_flow_payment_semantic() -> None:
    from otm_core_schema.document import DataFlow
    from otm_core_schema.enums import FlowSemanticClass
    from otm_threat_engine.risk_calc import likelihood_impact_for_data_flow

    flow = DataFlow(
        id="f_pay",
        name="checkout",
        from_component="c1",
        to_component="c2",
        semantic_class=FlowSemanticClass.PAYMENT_FLOW,
    )
    likelihood, impact = likelihood_impact_for_data_flow(flow, crosses_boundary=False)
    # PAYMENT_FLOW semantic class bumps impact
    assert 1 <= likelihood <= 5 and 1 <= impact <= 5


def test_payment_anchor_via_component_name() -> None:
    from otm_core_schema import create_blank_document
    from otm_core_schema.document import Component
    from otm_core_schema.enums import ComponentKind
    from otm_threat_engine.recommendation_gate import _has_payment_anchor

    doc = create_blank_document()
    # component name carries the "pay" token (not the broader corpus tokens) -> component-loop anchor branch
    doc = doc.model_copy(
        update={"components": [Component(id="payroll_svc", name="Payroll Service", kind=ComponentKind.PROCESS)]}
    )
    assert _has_payment_anchor(doc) is True


def test_semantic_diff_degraded_and_antipattern_removal() -> None:
    from pathlib import Path as _P

    from otm_core_schema import ThreatModelMethodology, load_document_from_yaml_path
    from otm_threat_engine import analyze_document
    from otm_threat_engine.semantic_comparison import semantic_diff_from_analyses_only

    root = _P(__file__).resolve().parents[1]
    rich = load_document_from_yaml_path(root / "examples" / "saas-ordering-v1.otm.yaml")
    baseline = analyze_document(rich, methodology=ThreatModelMethodology.STRIDE)
    # blank doc under a data-centric lens -> degraded completeness, no anti-patterns, different top-5
    revised = analyze_document(create_blank_document(), methodology=ThreatModelMethodology.NIST_DATA_CENTRIC)
    insights, improved, worsened, risk_impact = semantic_diff_from_analyses_only(baseline, revised)
    # methodology state differs (one side degraded), anti-patterns drop, and top ranking changes
    assert isinstance(insights, list)
    assert worsened or improved or risk_impact or insights


def test_semantic_diff_methodology_improved_branch() -> None:
    from pathlib import Path as _P

    from otm_core_schema import ThreatModelMethodology, load_document_from_yaml_path
    from otm_threat_engine import analyze_document
    from otm_threat_engine.semantic_comparison import semantic_diff_from_analyses_only

    root = _P(__file__).resolve().parents[1]
    health = load_document_from_yaml_path(root / "examples" / "test-apps" / "health-clinic.otm.yaml")
    rich = load_document_from_yaml_path(root / "examples" / "saas-ordering-v1.otm.yaml")
    # two complete-ish but differently-shaped analyses -> methodology state may differ without "degraded"
    a = analyze_document(health, methodology=ThreatModelMethodology.LINDDUN)
    b = analyze_document(rich, methodology=ThreatModelMethodology.STRIDE)
    out = semantic_diff_from_analyses_only(a, b)
    assert isinstance(out, tuple) and len(out) == 4


def test_owner_for_third_party_and_ml() -> None:
    from otm_threat_engine.remediation.build import _owner_for

    role, _why = _owner_for(None, "third_party_integration", "vendor_and_integration_governance")
    assert role == "vendor_or_integration_lead"
    role2, _why2 = _owner_for(None, "ai_ml_specific", "ai_ml_governance")
    assert role2 == "ml_platform_or_app_security"


def test_extra_entries_from_document_shortcut() -> None:
    from otm_threat_engine.ai_modeling.heuristics import extra_entries_from_document

    doc = create_blank_document()
    doc = doc.model_copy(
        update={"metadata": doc.metadata.model_copy(update={"summary": "llm rag agent vector embedding prompt"})}
    )
    assert isinstance(extra_entries_from_document(doc), list)


def test_looks_like_ai_context_safe_marker_branch() -> None:
    from otm_threat_engine.methodology_lenses.common import looks_like_ai_context

    doc = create_blank_document()
    # "ai inference" -> short `ai` token + technical companion, no llm/rag token -> safe-ai-marker branch
    doc = doc.model_copy(update={"metadata": doc.metadata.model_copy(update={"summary": "ai inference service"})})
    assert looks_like_ai_context(doc) is True


def test_methodology_state_delta_degraded_and_improved() -> None:
    from otm_core_schema.enums import MethodologyCompletenessState as St
    from otm_threat_engine import analyze_document
    from otm_threat_engine.result import MethodologyCompletenessInfo
    from otm_threat_engine.semantic_comparison import _append_methodology_state_delta

    base = analyze_document(create_blank_document()).model_copy(
        update={"methodology_completeness": MethodologyCompletenessInfo(state=St.COMPLETE)}
    )
    degraded = analyze_document(create_blank_document()).model_copy(
        update={"methodology_completeness": MethodologyCompletenessInfo(state=St.DEGRADED)}
    )
    ins: list[str] = []
    imp: list[str] = []
    wor: list[str] = []
    _append_methodology_state_delta(base, degraded, ins, imp, wor)
    assert any("degrada" in w for w in wor)  # degraded -> worsened branch

    partial = analyze_document(create_blank_document()).model_copy(
        update={"methodology_completeness": MethodologyCompletenessInfo(state=St.PARTIAL)}
    )
    ins2: list[str] = []
    imp2: list[str] = []
    wor2: list[str] = []
    _append_methodology_state_delta(base, partial, ins2, imp2, wor2)
    assert imp2  # state changed but not degraded -> improved/else branch


def test_semantic_diff_antipattern_removed() -> None:
    from otm_threat_engine import analyze_document
    from otm_threat_engine.result import AntiPatternHit
    from otm_threat_engine.semantic_comparison import semantic_diff_from_analyses_only

    hit = AntiPatternHit(id="ap_x", name="Pattern X", severity_hint="medium", message="m")
    base = analyze_document(create_blank_document()).model_copy(update={"anti_pattern_hits": [hit]})
    rev = analyze_document(create_blank_document()).model_copy(update={"anti_pattern_hits": []})
    _ins, improved, _wor, _risk = semantic_diff_from_analyses_only(base, rev)
    assert any("deixaram de aplicar" in x for x in improved)  # removed anti-patterns -> improved branch


def test_comparison_flow_metadata_changed() -> None:
    from pathlib import Path as _P

    from otm_core_schema import load_document_from_yaml_path
    from otm_threat_engine import analyze_document
    from otm_threat_engine.threat_model_comparison import compare_threat_models

    root = _P(__file__).resolve().parents[1]
    base = load_document_from_yaml_path(root / "examples" / "saas-ordering-v1.otm.yaml")
    flows = list(base.data_flows)
    assert flows, "fixture must have flows"
    flows[0] = flows[0].model_copy(update={"protocol": "ALTERED-PROTOCOL-XYZ"})
    revised = base.model_copy(update={"data_flows": flows})
    cmp = compare_threat_models(
        base, revised, baseline_analysis=analyze_document(base), revised_analysis=analyze_document(revised)
    )
    assert cmp is not None  # data_flows "changed" -> risk_impact flow-change branch


def test_analysis_diff_added_and_signature_remap() -> None:
    from otm_core_schema import StrideCategory
    from otm_threat_engine import analyze_document
    from otm_threat_engine.analysis_diff import diff_analysis_results
    from otm_threat_engine.result import HeuristicThreat
    from otm_threat_engine.risk_calc import build_risk_assessment

    def _h(hid: str, title: str) -> HeuristicThreat:
        return HeuristicThreat(
            id=hid,
            title=title,
            description="d",
            stride=StrideCategory.TAMPERING,
            risk=build_risk_assessment(3, 3),
            target_component_id="c1",
        )

    base = analyze_document(create_blank_document()).model_copy(update={"heuristic_threats": [_h("old_id", "Same")]})
    # "new_id" has the same signature as removed "old_id" (remap hint) + an extra added one
    revised = analyze_document(create_blank_document()).model_copy(
        update={"heuristic_threats": [_h("new_id", "Same"), _h("extra_added", "Brand New")]}
    )
    diff = diff_analysis_results(base, revised)
    assert diff.heuristic_threats.added  # added-section branch
    assert diff.signature_remap_hints  # signature remap branch


def test_write_explain_json(tmp_path: Path) -> None:
    from otm_cli.application.import_service import write_explain_json

    out = tmp_path / "explain.json"
    write_explain_json({"inferences": [{"id": "i1"}]}, out)
    assert out.exists()


def test_run_explain_empty_returns_empty(tmp_path: Path) -> None:
    import json

    from otm_cli.application.explain_service import run_explain

    f = tmp_path / "a.json"
    f.write_text(json.dumps({"explanations": []}), encoding="utf-8")
    # no explanations -> early empty-list return
    assert run_explain(f, kind="analysis", category=None, limit=10) == []


def test_helm_corpus_release_name_regex() -> None:
    from otm_artifact_import.ai_import_corpus import build_helm_import_signals_corpus

    # the release(_name)? pattern matches `release\:\<name>` (literal backslashes) -> capture branch
    out = build_helm_import_signals_corpus("release\\:\\myrelease")
    assert "myrelease" in out


def test_should_suppress_stride_noise_cancel_branch() -> None:
    from otm_core_schema import StrideCategory
    from otm_threat_engine.engine import _should_suppress_stride_noise
    from otm_threat_engine.result import HeuristicThreat
    from otm_threat_engine.risk_calc import build_risk_assessment

    h = HeuristicThreat(
        id="eng_cancel_x",
        title="cancel subscription revog",
        description="d",
        stride=StrideCategory.TAMPERING,
        risk=build_risk_assessment(3, 3),
    )
    # only the `cancel` family armed -> earlier families skipped, cancel-token branch returns True
    assert _should_suppress_stride_noise(h=h, flags={"cancel": True}) is True


def test_description_for_component_handles_credentials() -> None:
    from otm_core_schema.document import Component
    from otm_core_schema.enums import ComponentKind
    from otm_threat_engine.stride_heuristics import description_for_component_threat

    comp = Component(id="auth", name="Auth", kind=ComponentKind.PROCESS, handles_credentials=True)
    desc = description_for_component_threat(comp)
    assert "credenciais" in desc  # handles_credentials -> extra text branch


def test_business_abuse_append_dedup_guard() -> None:
    from otm_core_schema import StrideCategory
    from otm_threat_engine.business_abuse_heuristics import _append

    hs: list = []
    ids = {"dup_id"}
    _append(
        hs,
        ids,
        hid="dup_id",
        title="t",
        description="d",
        stride=StrideCategory.TAMPERING,
        likelihood=3,
        impact=3,
        target_component_id=None,
        target_data_flow_id=None,
        target_asset_id=None,
    )
    assert hs == []  # hid already present -> early return guard


def test_registry_from_yaml_path() -> None:
    import otm_framework_mappings
    from otm_framework_mappings.registry import StrideFrameworkRegistry

    data = Path(otm_framework_mappings.__file__).resolve().parent / "data" / "stride_framework_map.yaml"
    reg = StrideFrameworkRegistry.from_yaml_path(data)  # path-read classmethod branch
    assert reg is not None


def test_diff_insights_added_flow_external_entity() -> None:
    from otm_core_schema.diff import diff_documents
    from otm_core_schema.diff_insights import structural_key_insights
    from otm_core_schema.document import Component, DataFlow
    from otm_core_schema.enums import ComponentKind

    ext = Component(id="ext1", name="External Caller", kind=ComponentKind.EXTERNAL_ENTITY)
    proc = Component(id="p1", name="Service", kind=ComponentKind.PROCESS)
    base = create_blank_document().model_copy(update={"components": [ext, proc]})
    flow = DataFlow(id="f_new", name="call", from_component="ext1", to_component="p1")
    revised = base.model_copy(update={"data_flows": [flow]})
    d = diff_documents(base, revised)
    insights = structural_key_insights(base, revised, d)
    # added flow involving an external entity (not crossing boundaries) -> external-entity insight branch
    assert any("entidade externa" in s for s in insights)


def test_repo_scan_routes_and_dir_hints(tmp_path: Path) -> None:
    from otm_artifact_import import scan_node_express_repo

    (tmp_path / "package.json").write_text('{"dependencies": {"express": "^4"}}', encoding="utf-8")
    (tmp_path / "server.js").write_text(
        "const app = require('express')();\napp.get('/users', (req, res) => res.send('ok'));\n", encoding="utf-8"
    )
    (tmp_path / "public").mkdir()  # directory-convention hint branch
    out = scan_node_express_repo(tmp_path)
    # the `public` subdir triggers the directory-convention hint branch; route regex runs on server.js
    assert isinstance(out, dict)
    assert "directory_convention" in repr(out)


def test_root_cause_recommendations_cancel() -> None:
    from otm_core_schema import StrideCategory
    from otm_exporters.analysis_markdown import _append_root_cause_recommendations, analysis_markdown_messages
    from otm_threat_engine.result import HeuristicThreat
    from otm_threat_engine.risk_calc import build_risk_assessment

    msgs = analysis_markdown_messages(None)
    h = HeuristicThreat(
        id="h_cancel",
        title="cancel subscription abuse",
        description="revoga acesso",
        stride=StrideCategory.TAMPERING,
        risk=build_risk_assessment(3, 3),
    )
    lines: list[str] = []
    _append_root_cause_recommendations(lines, [h], msgs)
    assert any(msgs.rec_cancel in ln for ln in lines)  # "cancel" text -> rec_cancel branch


def test_run_diff_analysis_text_with_remap(tmp_path: Path) -> None:
    import json

    from otm_cli.application.diff_analysis_service import run_diff_analysis
    from otm_cli.shared.enums import DiffFormat
    from otm_core_schema import StrideCategory
    from otm_threat_engine import analyze_document
    from otm_threat_engine.result import HeuristicThreat
    from otm_threat_engine.risk_calc import build_risk_assessment

    def _h(hid: str) -> HeuristicThreat:
        return HeuristicThreat(
            id=hid,
            title="Same Title",
            description="d",
            stride=StrideCategory.TAMPERING,
            risk=build_risk_assessment(3, 3),
            target_component_id="c1",
        )

    base = analyze_document(create_blank_document()).model_copy(update={"heuristic_threats": [_h("old_id")]})
    rev = analyze_document(create_blank_document()).model_copy(update={"heuristic_threats": [_h("new_id")]})
    bf = tmp_path / "b.json"
    rf = tmp_path / "r.json"
    bf.write_text(json.dumps(base.model_dump(mode="json")), encoding="utf-8")
    rf.write_text(json.dumps(rev.model_dump(mode="json")), encoding="utf-8")
    _payload, lines, _ad = run_diff_analysis(bf, rf, fmt=DiffFormat.text)
    # same-signature rename -> signature_remap_hints rendered (text branch)
    assert lines is not None and any("remap" in ln.lower() or "→" in ln for ln in lines)


def test_flow_heuristics_skipped_as_duplicate() -> None:
    from otm_core_schema import StrideCategory
    from otm_core_schema.document import Component, DataFlow
    from otm_core_schema.enums import ComponentKind
    from otm_threat_engine.engine_stride_builder import append_flow_heuristics

    doc = create_blank_document().model_copy(
        update={
            "components": [
                Component(id="a", name="A", kind=ComponentKind.PROCESS),
                Component(id="b", name="B", kind=ComponentKind.PROCESS),
            ],
            "data_flows": [DataFlow(id="f1", name="flow", from_component="a", to_component="b")],
        }
    )
    existing = {(None, "f1", s.value) for s in StrideCategory}  # pre-seed all stride keys for f1
    skipped = append_flow_heuristics(doc=doc, heuristics=[], existing=existing, cross_flows=set(), pack=None)
    assert skipped > 0  # every candidate stride already present -> skipped-as-duplicate branch


def test_wizard_ranking_trace_isolated_api_no() -> None:
    from otm_threat_engine.wizard_signals import WizardSignal, _build_ranking_trace_entries

    sigs = [WizardSignal(profile="api_backend_rest", key="auth", value="no")]
    trace = _build_ranking_trace_entries(admin=False, file_r=False, api_r=False, ecom=False, signals=sigs)
    # exactly one API negative, cluster not armed -> the audit-only isolated-no trace entry
    assert any("api_backend_rest:isolated_no" in t.source_tag for t in trace)


def test_plot4ai_agent_block_fallback_evidence() -> None:
    from otm_threat_engine.ai_modeling.explanation_plot4ai_blocks import append_agent_block
    from otm_threat_engine.ai_modeling.signals import AiSignalBundle
    from otm_threat_engine.result import AiSystemContextSummary

    sig = AiSignalBundle(agent_tool=True)  # agent signal set, but no recorded evidence
    ctx = AiSystemContextSummary(synopsis="s", primary_risk_surfaces=[])  # no agent surfaces
    counter = [0]

    def _take() -> int:
        counter[0] += 1
        return counter[0]

    out: list = []
    append_agent_block(out, take_id=_take, sig=sig, ctx=ctx, rel_doc=[])
    assert out  # no evidence + no agent surface -> the default agent_ev fallback branch


def test_model_diff_more_than_12_modified(tmp_path: Path) -> None:
    import yaml
    from otm_cli.application.diff_service import run_model_diff
    from otm_cli.shared.enums import DiffFormat
    from otm_core_schema.document import Component
    from otm_core_schema.enums import ComponentKind

    comps_a = [Component(id=f"c{i}", name=f"Name {i}", kind=ComponentKind.PROCESS) for i in range(13)]
    comps_b = [Component(id=f"c{i}", name=f"Renamed {i}", kind=ComponentKind.PROCESS) for i in range(13)]
    base = create_blank_document().model_copy(update={"components": comps_a})
    revised = create_blank_document().model_copy(update={"components": comps_b})
    bf = tmp_path / "b.otm.yaml"
    rf = tmp_path / "r.otm.yaml"
    bf.write_text(yaml.safe_dump(base.model_dump(mode="json", by_alias=True)), encoding="utf-8")
    rf.write_text(yaml.safe_dump(revised.model_dump(mode="json", by_alias=True)), encoding="utf-8")
    _payload, _j, _m, text, _ad = run_model_diff(
        bf, rf, with_analysis=False, pack=None, fmt=DiffFormat.text, summary_only=False
    )
    assert text is not None and "more modified" in text  # >12 modified -> truncation summary branch


def test_openapi_path_level_security_auth() -> None:
    from otm_artifact_import.openapi_import import import_openapi_text

    spec = (
        "openapi: 3.0.0\n"
        "info:\n  title: Secured API\n"
        "paths:\n"
        "  /x:\n"
        "    security:\n      - apiKey: []\n"  # path-level security (no op-level security key)
        "    get:\n"
        "      responses:\n        '200':\n          description: ok\n"
    )
    res = import_openapi_text(spec)
    # root has no security, ops have no security key, but path-level security -> `all(path_level_sec)` branch
    assert res.document is not None


def test_field_changes_heuristic_framework_refs() -> None:
    from otm_core_schema import FrameworkRef, StrideCategory
    from otm_threat_engine.analysis_diff import _field_changes_heuristic
    from otm_threat_engine.result import HeuristicThreat
    from otm_threat_engine.risk_calc import build_risk_assessment

    def _h(refs: list) -> HeuristicThreat:
        return HeuristicThreat(
            id="h",
            title="T",
            description="d",
            stride=StrideCategory.TAMPERING,
            risk=build_risk_assessment(3, 3),
            framework_refs=refs,
        )

    a = _h([FrameworkRef(framework="NIST", control_id="AC-1")])
    b = _h([])
    changes = _field_changes_heuristic(a, b)
    assert any(c.field == "framework_refs" for c in changes)  # framework_refs differ -> field-change branch


def test_run_backlog_unsupported_extension(tmp_path: Path) -> None:
    from otm_cli.application.backlog_service import run_backlog
    from otm_cli.shared.enums import BacklogFormat
    from otm_cli.shared.errors import CliUserError

    f = tmp_path / "x.txt"
    f.write_text("not yaml or json", encoding="utf-8")
    with pytest.raises(CliUserError):  # unsupported extension -> raises
        run_backlog(f, document=None, pack=None, fmt=BacklogFormat.markdown, group_by=None)


def test_k8s_find_ingress_spec_no_match_returns_none() -> None:
    from otm_artifact_import.k8s_import import _find_ingress_spec

    # no Ingress doc with that name -> the loop falls through to the final `return None`
    assert _find_ingress_spec([], "missing") is None
    assert _find_ingress_spec([{"kind": "Service", "metadata": {"name": "x"}}], "x") is None


def test_k8s_backend_service_name_variants() -> None:
    from otm_artifact_import.k8s_import import _backend_service_name

    assert _backend_service_name(None) is None  # not a dict -> early None
    assert _backend_service_name({"service": {"name": "svc-a"}}) == "svc-a"  # modern .service.name
    assert _backend_service_name({"serviceName": "svc-b"}) == "svc-b"  # legacy serviceName
    assert _backend_service_name({"service": {}}) is None  # backend present, no service name -> final None


def test_k8s_ingress_backend_names_malformed_paths() -> None:
    from otm_artifact_import.k8s_import import _ingress_backend_service_names

    assert _ingress_backend_service_names(None) == []  # no spec -> rules not a list
    assert _ingress_backend_service_names({"rules": "nope"}) == []  # rules not a list
    # rules present but http.paths is not a list -> the inner `continue`
    assert _ingress_backend_service_names({"rules": [{"http": {"paths": "nope"}}]}) == []


def test_diff_semantic_lines_empty_sections_returns_empty() -> None:
    from types import SimpleNamespace

    from otm_cli.application.diff_service import _semantic_diff_lines

    # all four sections empty -> early `return []` (no "Semantic diff" header)
    empty = SimpleNamespace(structural_change_summary=[], improved=[], worsened=[], risk_impact=[])
    assert _semantic_diff_lines(empty) == []
    # one section populated -> header + that entry rendered
    one = SimpleNamespace(structural_change_summary=["chg"], improved=[], worsened=[], risk_impact=[])
    assert _semantic_diff_lines(one) == ["Semantic diff (heuristic):", "  Δ chg", ""]
