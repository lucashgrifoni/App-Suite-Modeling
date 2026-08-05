"""P3 — regras de ameaça declaradas pela organização (`otm analyze --rules`).

Duas propriedades mandam aqui, e as duas são sobre falha silenciosa:

* **Uma regra que nunca dispara por engano é pior do que nenhuma regra.** A organização
  acredita que está coberta e não está. Por isso um campo desconhecido é erro, não um
  critério ignorado; e `null` não é `false`.
* **Uma regra que dispara mas desaparece do relatório também é falha silenciosa.** Por isso
  as regras da organização não são suprimidas pela cobertura das heurísticas base, e as
  referências que a regra declara sobrevivem ao enriquecimento de frameworks.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from otm_cli.cli import app
from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine import analyze_document
from otm_threat_engine.custom_rules import (
    COMPONENT_MATCH_FIELDS,
    FLOW_MATCH_FIELDS,
    CustomRuleSet,
    collect_control_hints,
    iter_custom_rule_threats,
    load_custom_rules,
)
from typer.testing import CliRunner

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
_MODEL = _EXAMPLES / "saas-ordering-v1.otm.yaml"
_EXAMPLE_RULES = _EXAMPLES / "custom-rules.example.yaml"


def _ruleset(*rules: dict[str, object]) -> CustomRuleSet:
    return CustomRuleSet.model_validate({"id": "acme", "rules": list(rules)})


def _rule(rid: str, match: dict[str, object], **kw: object) -> dict[str, object]:
    return {"id": rid, "title": f"regra {rid}", "stride": "tampering", "match": match, **kw}


@pytest.fixture(scope="module")
def doc():  # noqa: ANN201 - pytest fixture
    return load_document_from_yaml_path(_MODEL)


# --------------------------------------------------------------------------- validação


def test_unknown_field_is_an_error_not_a_rule_that_never_matches() -> None:
    """O modo de falha caro: um typo cria uma regra que nunca dispara e ninguém repara."""
    with pytest.raises(ValueError, match="unknown component field"):
        _ruleset(_rule("a", {"component": {"suports_admin_operations": True}}))

    with pytest.raises(ValueError, match="unknown flow field"):
        _ruleset(_rule("a", {"flow": {"encripted": False}}))


def test_error_message_lists_the_valid_fields() -> None:
    """Sem a lista, o autor da regra fica a adivinhar."""
    with pytest.raises(ValueError) as exc:
        _ruleset(_rule("a", {"component": {"nope": 1}}))
    assert "kind" in str(exc.value) and "handles_credentials" in str(exc.value)


@pytest.mark.parametrize(
    ("match", "expected"),
    [
        ({}, "not.*neither|neither"),
        ({"component": {"kind": "process"}, "flow": {"encrypted": True}}, "both"),
        ({"component": {}}, "empty"),
    ],
)
def test_a_rule_has_exactly_one_non_empty_subject(match: dict[str, object], expected: str) -> None:
    with pytest.raises(ValueError, match=expected):
        _ruleset(_rule("a", match))


def test_rule_ids_are_constrained_to_a_slug() -> None:
    """Ids entram em ids de ameaça e em tabelas Markdown; um slug evita escapar em cada saída."""
    with pytest.raises(ValueError):
        _ruleset(_rule("Regra Com Espaços", {"component": {"kind": "process"}}))


def test_duplicate_rule_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate rule id"):
        _ruleset(
            _rule("same", {"component": {"kind": "process"}}),
            _rule("same", {"component": {"kind": "datastore"}}),
        )


def test_matchable_fields_exclude_identifiers_and_free_text() -> None:
    for noise in ("id", "name", "description", "metadata"):
        assert noise not in COMPONENT_MATCH_FIELDS
        assert noise not in FLOW_MATCH_FIELDS
    assert "crosses_boundary" in FLOW_MATCH_FIELDS, "derived matcher must be offered"


# --------------------------------------------------------------------------- matching


def test_component_rule_fires_once_per_matching_component(doc) -> None:  # noqa: ANN001
    threats, fired = iter_custom_rule_threats(doc, _ruleset(_rule("ds", {"component": {"kind": "datastore"}})))
    assert sorted(t.target_component_id or "" for t in threats) == ["cache", "db"]
    assert fired == {"ds"}
    assert all(t.target_data_flow_id is None for t in threats)


def test_a_list_means_any_of(doc) -> None:  # noqa: ANN001
    threats, _ = iter_custom_rule_threats(doc, _ruleset(_rule("k", {"component": {"kind": ["datastore", "gateway"]}})))
    assert sorted(t.target_component_id or "" for t in threats) == ["cache", "db", "waf"]


def test_several_criteria_must_all_hold(doc) -> None:  # noqa: ANN001
    """AND, não OR: `waf` é gateway mas não é datastore."""
    threats, _ = iter_custom_rule_threats(
        doc, _ruleset(_rule("k", {"component": {"kind": "datastore", "handles_credentials": True}}))
    )
    assert threats == []


def test_null_is_not_false(doc) -> None:  # noqa: ANN001
    """A distinção que mais engana quem escreve regras.

    `api_to_worker` não declara `encrypted`. `encrypted: false` NÃO o apanha; para apanhar
    "não confirmado como cifrado" é preciso dizê-lo com `[false, null]`.
    """
    strict, _ = iter_custom_rule_threats(doc, _ruleset(_rule("s", {"flow": {"encrypted": False}})))
    assert strict == []

    permissive, _ = iter_custom_rule_threats(doc, _ruleset(_rule("p", {"flow": {"encrypted": [False, None]}})))
    assert [t.target_data_flow_id for t in permissive] == ["api_to_worker"]


def test_crosses_boundary_is_derived_not_read_from_the_document(doc) -> None:  # noqa: ANN001
    """O campo não existe no schema; vem do motor."""
    crossing, _ = iter_custom_rule_threats(doc, _ruleset(_rule("x", {"flow": {"crosses_boundary": True}})))
    assert sorted(t.target_data_flow_id or "" for t in crossing) == [
        "api_to_cache",
        "user_to_waf",
        "waf_to_api",
        "worker_to_db",
    ]
    internal, _ = iter_custom_rule_threats(doc, _ruleset(_rule("i", {"flow": {"crosses_boundary": False}})))
    assert [t.target_data_flow_id for t in internal] == ["api_to_worker"]


def test_the_same_rule_never_fires_twice_on_one_target(doc) -> None:  # noqa: ANN001
    threats, _ = iter_custom_rule_threats(doc, _ruleset(_rule("ds", {"component": {"kind": "datastore"}})))
    assert len({t.id for t in threats}) == len(threats)


def test_output_is_deterministic(doc) -> None:  # noqa: ANN001
    rs = _ruleset(_rule("a", {"component": {"kind": "datastore"}}), _rule("b", {"flow": {"crosses_boundary": True}}))
    first, _ = iter_custom_rule_threats(doc, rs)
    second, _ = iter_custom_rule_threats(doc, rs)
    assert [t.id for t in first] == [t.id for t in second]


# --------------------------------------------------------------------------- integração


def test_org_rules_are_not_suppressed_by_the_base_heuristics(doc) -> None:  # noqa: ANN001
    """Escolha deliberada, e o oposto do que os industry packs fazem.

    O motor já emite `information_disclosure` para cada datastore. Uma regra da organização
    sobre o mesmo alvo e categoria diz algo mais específico — o controlo, o dono, a
    referência interna. Marcá-la como duplicada apagava exactamente essa informação.
    """
    rs = _ruleset(_rule("ds", {"component": {"kind": "datastore"}}, stride="information_disclosure"))
    result = analyze_document(doc, custom_rules=rs)
    custom = [h for h in result.heuristic_threats if h.id.startswith("custom_")]
    assert len(custom) == 2
    assert all(h.skipped_as_duplicate is False for h in custom)


def test_declared_refs_survive_framework_enrichment(doc) -> None:  # noqa: ANN001
    """Regressão: o enriquecimento SUBSTITUÍA `framework_refs` em vez de acrescentar.

    A referência interna que o autor escreveu desaparecia em silêncio do resultado.
    """
    rs = _ruleset(_rule("ds", {"component": {"kind": "datastore"}}, refs=["ORG-SEC-012"]))
    result = analyze_document(doc, custom_rules=rs)
    custom = [h for h in result.heuristic_threats if h.id.startswith("custom_")]
    assert custom, "rule produced no threat"
    for h in custom:
        declared = [r.control_id for r in h.framework_refs if r.framework == "custom"]
        assert declared == ["ORG-SEC-012"], "the rule's own reference was dropped"
        assert any(r.framework == "cwe" for r in h.framework_refs), "STRIDE enrichment must still apply"


def test_base_heuristics_keep_their_refs_unchanged(doc) -> None:  # noqa: ANN001
    """A mudança no enriquecimento não pode alterar quem não trazia refs."""
    without = analyze_document(doc)
    base = [h for h in without.heuristic_threats if not h.id.startswith("custom_")]
    assert base and all(h.framework_refs for h in base)


def test_control_hints_come_only_from_rules_that_fired(doc) -> None:  # noqa: ANN001
    """Sugerir um controlo para uma ameaça que não foi levantada inventa um problema."""
    rs = _ruleset(
        _rule("fires", {"component": {"kind": "datastore"}}, control_hint="cifra em repouso"),
        _rule("never", {"component": {"kind": "orchestrator"}}, control_hint="nunca deve aparecer"),
    )
    threats, fired = iter_custom_rule_threats(doc, rs)
    assert fired == {"fires"}
    assert collect_control_hints(rs, fired) == ["cifra em repouso"]
    assert threats


def test_threat_ids_are_namespaced(doc) -> None:  # noqa: ANN001
    """Um leitor tem de distinguir uma regra da organização de uma heurística do motor."""
    threats, _ = iter_custom_rule_threats(doc, _ruleset(_rule("ds", {"component": {"kind": "datastore"}})))
    assert all(t.id.startswith("custom_acme_ds_") for t in threats)
    assert all(t.title.startswith("[rules:acme]") for t in threats)


def test_analysis_without_rules_is_unchanged(doc) -> None:  # noqa: ANN001
    """A funcionalidade é opt-in: sem `--rules` nada muda."""
    a = analyze_document(doc)
    b = analyze_document(doc, custom_rules=None)
    assert [h.id for h in a.heuristic_threats] == [h.id for h in b.heuristic_threats]


# --------------------------------------------------------------------------- loader


def test_shipped_example_rules_file_is_valid() -> None:
    """O exemplo documenta o formato; se não carregar, a documentação mente."""
    rs = load_custom_rules(_EXAMPLE_RULES)
    assert rs.id == "example-org"
    assert len(rs.rules) >= 5


def test_loader_rejects_malformed_input(tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"
    with pytest.raises(ValueError, match="not found"):
        load_custom_rules(missing)

    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_custom_rules(empty)

    listy = tmp_path / "list.yaml"
    listy.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping at the top level"):
        load_custom_rules(listy)

    broken = tmp_path / "broken.yaml"
    broken.write_text("id: x\n  bad indent:\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid YAML"):
        load_custom_rules(broken)


def test_loader_refuses_an_oversized_file(tmp_path: Path) -> None:
    big = tmp_path / "big.yaml"
    big.write_text("# " + ("x" * (600 * 1024)), encoding="utf-8")
    with pytest.raises(ValueError, match="the limit is"):
        load_custom_rules(big)


def test_loader_does_not_construct_arbitrary_python_objects(tmp_path: Path) -> None:
    """`safe_load`, não `load`: o ficheiro vem do repositório de terceiros."""
    evil = tmp_path / "evil.yaml"
    evil.write_text("id: x\nrules: !!python/object/apply:os.system ['echo pwned']\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid YAML"):
        load_custom_rules(evil)


# --------------------------------------------------------------------------- CLI


def test_cli_analyze_accepts_rules(tmp_path: Path) -> None:
    out = tmp_path / "a.json"
    r = CliRunner().invoke(app, ["analyze", str(_MODEL), "--rules", str(_EXAMPLE_RULES), "--json-out", str(out), "-q"])
    assert r.exit_code == 0
    payload = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert any(h["id"].startswith("custom_") for h in payload["heuristic_threats"])


def test_cli_reports_a_bad_rules_file_as_a_usage_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("id: x\n", encoding="utf-8")  # no `rules:`
    r = CliRunner().invoke(app, ["analyze", str(_MODEL), "--rules", str(bad)])
    assert r.exit_code == 1
    assert "CUSTOM_RULES" in (r.stdout + (r.stderr or "")), "the error must point at the format docs"
