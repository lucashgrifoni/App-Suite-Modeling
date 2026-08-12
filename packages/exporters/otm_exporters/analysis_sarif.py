"""SARIF 2.1.0 export of analysis threats.

Lets `otm analyze` output flow into GitHub code scanning (or any SARIF-aware
pipeline): each suggested threat becomes a SARIF `result`, grouped by a rule per
methodology+STRIDE category, with `helpUri` pointing at the threat's CWE/CAPEC
reference (from the framework map). Deterministic output (stable ordering and
fingerprints) so it diffs cleanly in CI.

SARIF spec: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
"""

from __future__ import annotations

import importlib.metadata
import json
from typing import Any

from otm_threat_engine.result import AnalysisResult, HeuristicThreat

_SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_TOOL_NAME = "App Suite Modeling"
_TOOL_URI = "https://github.com/lucashgrifoni/App-Suite-Modeling"
_DISTRIBUTION = "open-threat-model"

#: Artefacto a que os resultados são ancorados quando quem chama não diz qual é o ficheiro.
#: Uma ameaça STRIDE não tem ficheiro-fonte nem linha: o sujeito do achado é o próprio modelo de
#: ameaças, por isso é o `.otm.yaml` que vai em `artifactLocation.uri`. A API (documento vindo
#: num POST) e qualquer chamador em memória não têm caminho nenhum, e o GitHub exige
#: `physicalLocation` com `uri` e `region.startLine` para ingerir o resultado — daí o nome
#: canónico por omissão em vez de campo nenhum.
_DEFAULT_MODEL_URI = "threat-model.otm.yaml"


def product_version() -> str:
    """Versão do produto instalado, para `tool.driver.version`.

    `result.engine_version` identifica o motor de heurísticas (`0.1.0`, nunca incrementado) e é
    isso que estava a ser publicado como versão da ferramenta chamada "App Suite Modeling" —
    dois scans de releases diferentes ficavam indistinguíveis. O motor continua no property bag.
    """
    try:
        return importlib.metadata.version(_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        return "dev"


def _level_for_score(score: float | None) -> str:
    """Map L×I score (1-25) to a SARIF level. critical/high -> error; medium -> warning; low -> note."""
    s = score or 0
    if s >= 12:
        return "error"
    if s >= 6:
        return "warning"
    return "note"


def _help_uri(threat: HeuristicThreat) -> str | None:
    """Prefer a CWE reference, then CAPEC, for the rule's helpUri (set by the framework map)."""
    cwe = next((r for r in threat.framework_refs if r.framework == "cwe"), None)
    if cwe and cwe.control_id.startswith("CWE-"):
        return f"https://cwe.mitre.org/data/definitions/{cwe.control_id.removeprefix('CWE-')}.html"
    capec = next((r for r in threat.framework_refs if r.framework == "capec"), None)
    if capec and capec.control_id.startswith("CAPEC-"):
        return f"https://capec.mitre.org/data/definitions/{capec.control_id.removeprefix('CAPEC-')}.html"
    return None


def _rule_id(result: AnalysisResult, threat: HeuristicThreat) -> str:
    return f"{result.methodology.value}.{threat.stride.value}"


def _logical_location(threat: HeuristicThreat) -> dict[str, Any] | None:
    """First target the threat declares, in precedence order, with its SARIF kind.

    Pairing each id with its kind in one table keeps the two from drifting apart: picking the
    target and naming it were previously two independent expressions over the same fields.
    """
    for target, kind in (
        (threat.target_component_id, "component"),
        (threat.target_data_flow_id, "dataflow"),
        (threat.target_asset_id, "asset"),
    ):
        if target:
            return {"fullyQualifiedName": target, "kind": kind}
    return None


def _physical_location(model_uri: str) -> dict[str, Any]:
    """`physicalLocation` do modelo, obrigatório para o GitHub code scanning.

    O GitHub documenta `result.locations[]`, `location.physicalLocation`,
    `artifactLocation.uri` e `region.startLine` como necessários para ingerir um resultado; sem
    eles o upload que o `--sarif-out` e o `upload-sarif` da Action anunciam não produz alertas
    localizados. A ameaça não tem linha própria — é o documento inteiro que a origina — por isso
    todas ancoram na linha 1 do modelo, que é a convenção para achados ao nível do ficheiro.
    """
    return {"artifactLocation": {"uri": model_uri}, "region": {"startLine": 1}}


def _location(threat: HeuristicThreat, model_uri: str) -> dict[str, Any]:
    """The single `location` of a result: always the model file, plus the target when there is one.

    A threat that declares no component, data flow or asset — PASTA emits five of them, one per
    model-level concern — still belongs to the model file, so it gets the same `physicalLocation`
    as every other result. Anchoring it is what makes it ingestible; the `logicalLocations` entry
    is what makes it readable, and only that part depends on a target existing.
    """
    location: dict[str, Any] = {"physicalLocation": _physical_location(model_uri)}
    logical = _logical_location(threat)
    if logical:
        location["logicalLocations"] = [logical]
    return location


def export_analysis_sarif_obj(result: AnalysisResult, *, model_uri: str = _DEFAULT_MODEL_URI) -> dict[str, Any]:
    """SARIF 2.1.0 object for the analysis result (one run, one result per active threat).

    `model_uri` is the artifact every result points at — the threat-model file the analysis came
    from, relative to the repository root so GitHub can resolve it.
    """
    threats = [t for t in result.heuristic_threats if not t.skipped_as_duplicate]

    rules: list[dict[str, Any]] = []
    rule_index: dict[str, int] = {}
    sarif_results: list[dict[str, Any]] = []

    for t in threats:
        rid = _rule_id(result, t)
        if rid not in rule_index:
            rule_index[rid] = len(rules)
            rule: dict[str, Any] = {
                "id": rid,
                "name": f"{result.methodology.value.upper()} {t.stride.value}",
                "shortDescription": {"text": f"{t.stride.value} threats ({result.methodology.value})"},
                "defaultConfiguration": {"level": _level_for_score(t.risk.score)},
            }
            help_uri = _help_uri(t)
            if help_uri:
                rule["helpUri"] = help_uri
            rules.append(rule)

        refs = [f"{r.framework}:{r.control_id}" for r in t.framework_refs]
        res: dict[str, Any] = {
            "ruleId": rid,
            "ruleIndex": rule_index[rid],
            "level": _level_for_score(t.risk.score),
            "message": {"text": f"{t.title}. {t.description}".strip()},
            "partialFingerprints": {"otmThreatId": t.id},
            "properties": {
                "likelihood": t.risk.likelihood,
                "impact": t.risk.impact,
                "score": t.risk.score,
                "stride": t.stride.value,
                "references": refs,
            },
        }
        res["locations"] = [_location(t, model_uri)]
        sarif_results.append(res)

    return {
        "version": "2.1.0",
        "$schema": _SARIF_SCHEMA,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": _TOOL_NAME,
                        "informationUri": _TOOL_URI,
                        "version": product_version(),
                        "properties": {"engineVersion": result.engine_version},
                        "rules": rules,
                    }
                },
                "results": sarif_results,
            }
        ],
    }


def export_analysis_sarif(result: AnalysisResult, *, model_uri: str = _DEFAULT_MODEL_URI) -> str:
    """SARIF 2.1.0 JSON text for the analysis result."""
    return json.dumps(export_analysis_sarif_obj(result, model_uri=model_uri), indent=2, ensure_ascii=False)
