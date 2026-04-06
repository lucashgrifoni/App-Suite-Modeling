"""
Biblioteca de anti-padrões por template / semantic profile.

Heurística conservadora: sinaliza riscos de modelagem quando o contexto declara um perfil
mas o texto agregado não menciona controlos esperados. Não substitui revisão humana.

Extensões v2: mitigadores por keywords, pré-requisitos estruturais mínimos, dica de confiança.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import yaml
from otm_core_schema import ThreatModelDocument
from pydantic import BaseModel, Field

from otm_threat_engine.wizard_signals import signals_for_profile, synthetic_keyword_corpus


def _bump_confidence(hint: str, reason: str) -> str:
    """Ligeiro reforço quando o match é estrutural (auditável no grafo)."""
    order = ("low", "medium", "high")
    if hint not in order:
        return hint
    if reason == "structural_primary" and hint == "low":
        return "medium"
    if reason == "structural_primary" and hint == "medium":
        return "high"
    return hint


def _cross_boundary_flow_ids(doc: ThreatModelDocument) -> set[str]:
    """Cópia local (evita import circular com engine_support)."""
    ids: set[str] = set()
    by_comp = {c.id: c for c in doc.components}
    for flow in doc.data_flows:
        a = by_comp.get(flow.from_component)
        b = by_comp.get(flow.to_component)
        if not a or not b:
            continue
        if (
            a.in_trust_boundary
            and b.in_trust_boundary
            and a.in_trust_boundary != b.in_trust_boundary
        ):
            ids.add(flow.id)
    return ids


class AntiPatternDefinition(BaseModel):
    """Definição carregada do catálogo YAML."""

    id: str
    name: str
    semantic_profiles: list[str] = Field(default_factory=list)
    missing_any_of: list[str] = Field(
        default_factory=list,
        description="Se nenhuma destas substrings existir no corpus, o anti-pattern dispara.",
    )
    severity_hint: str = "medium"
    expected_controls: list[str] = Field(default_factory=list)
    mitigating_keywords: list[str] = Field(
        default_factory=list,
        description="Se qualquer substring existir no corpus, o hit é suprimido (sinal positivo no texto).",
    )
    require_min_data_flows: int = Field(
        default=0,
        description="Só avalia missing_any_of se len(data_flows) >= este valor (0 = sem requisito).",
    )
    require_min_trust_boundaries: int = Field(
        default=0,
        description="Só avalia missing_any_of se len(trust_boundaries) >= este valor.",
    )
    require_any_component_kinds: list[str] = Field(
        default_factory=list,
        description=(
            "Só avalia se existir componente com kind nesta lista "
            "(valores enum em minúsculas)."
        ),
    )
    require_min_cross_boundary_flows: int = Field(
        default=0,
        description="Mínimo de fluxos que cruzam trust boundaries (in_trust_boundary distinto).",
    )
    require_component_id_contains_any: list[str] = Field(
        default_factory=list,
        description="Só avalia se algum `component.id` contém uma destas substrings (case-insensitive).",
    )
    require_asset_name_id_contains_any: list[str] = Field(
        default_factory=list,
        description="Só avalia se algum ativo (id ou nome) contém uma destas substrings.",
    )
    require_flow_flag_any: list[str] = Field(
        default_factory=list,
        description="Só avalia se algum data_flow tem campo booleano True (ex.: supports_file_upload).",
    )
    structural_primary: bool = Field(
        default=False,
        description=(
            "Se True, o disparo pode ocorrer só com gates estruturais (require_*) satisfeitos; "
            "`missing_any_of` torna-se filtro adicional quando não vazio."
        ),
    )
    structural_primary_message: str = Field(
        default="",
        description="Mensagem do hit quando `structural_primary`; se vazio, usa texto padrão.",
    )
    confidence_hint: str = Field(
        default="medium",
        description="Dica de confiança do match (low|medium|high); combina com heurística.",
    )


class AntiPatternHit(BaseModel):
    """Ocorrência detectada para relatório, backlog e benchmark."""

    id: str
    name: str
    severity_hint: str
    message: str
    evidence: list[str] = Field(default_factory=list)
    expected_controls: list[str] = Field(default_factory=list)
    confidence_hint: str = Field(
        default="medium",
        description="Confiança agregada do match (heurística + estrutura).",
    )
    detection_sources: list[str] = Field(
        default_factory=list,
        description="Origens do match (ex.: corpus:missing_any_of, structural:min_flows).",
    )


def _any_component_kind(doc: ThreatModelDocument, kinds: list[str]) -> bool:
    want = {k.strip().lower() for k in kinds if k.strip()}
    if not want:
        return True
    for c in doc.components:
        if c.kind.value.lower() in want:
            return True
    return False


def _component_id_contains(doc: ThreatModelDocument, needles: list[str]) -> bool:
    subs = [n.lower() for n in needles if n.strip()]
    if not subs:
        return True
    for c in doc.components:
        low = c.id.lower()
        if any(s in low for s in subs):
            return True
    return False


def _asset_name_id_contains(doc: ThreatModelDocument, needles: list[str]) -> bool:
    subs = [n.lower() for n in needles if n.strip()]
    if not subs:
        return True
    for a in doc.assets:
        blob = f"{a.id} {a.name}".lower()
        if any(s in blob for s in subs):
            return True
    return False


def _any_flow_bool(doc: ThreatModelDocument, field_names: list[str]) -> bool:
    for flow in doc.data_flows:
        for name in field_names:
            if getattr(flow, name, None) is True:
                return True
    return False


def _corpus(doc: ThreatModelDocument) -> str:
    parts = [
        doc.metadata.title,
        doc.metadata.summary or "",
        doc.business_context.description if doc.business_context and doc.business_context.description else "",
    ]
    for tag in doc.metadata.tags or []:
        if isinstance(tag, str) and tag.lower().startswith("import:signal:"):
            payload = tag.split(":", 2)[2] if tag.count(":") >= 2 else ""
            if payload.strip():
                parts.append(payload)
    for c in doc.components:
        parts.append(f"{c.id} {c.name} {c.description or ''} {c.responsibility or ''}")
    for a in doc.assets:
        parts.append(f"{a.name} {a.description or ''}")
    base = " ".join(parts).lower()
    # Sinais positivos do assistente (`wz:...=yes`) enriquecem o corpus e podem silenciar falsos positivos.
    synth = synthetic_keyword_corpus(signals_for_profile(doc))
    return f"{base} {synth}".strip()


def _load_definitions() -> list[AntiPatternDefinition]:
    try:
        pkg = importlib.resources.files("otm_threat_engine.data.anti_patterns")
        raw = pkg.joinpath("catalog.yaml").read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        path = Path(__file__).resolve().parent / "data" / "anti_patterns" / "catalog.yaml"
        raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    patterns = data.get("patterns") or []
    return [AntiPatternDefinition.model_validate(p) for p in patterns]


def detect_anti_patterns(doc: ThreatModelDocument) -> list[AntiPatternHit]:
    """
    Avalia anti-padrões cujo `semantic_profiles` coincide com `model.template_semantic_profile`.
    """
    profile = (doc.model_info.template_semantic_profile or "").strip().lower()
    if not profile:
        return []

    corpus = _corpus(doc)
    hits: list[AntiPatternHit] = []
    n_flows = len(doc.data_flows)
    n_tb = len(doc.trust_boundaries)

    for dfn in _load_definitions():
        profiles = [p.lower() for p in dfn.semantic_profiles]
        if profile not in profiles:
            continue
        if not dfn.missing_any_of and not dfn.structural_primary:
            continue
        if dfn.require_min_data_flows > 0 and n_flows < dfn.require_min_data_flows:
            continue
        if dfn.require_min_trust_boundaries > 0 and n_tb < dfn.require_min_trust_boundaries:
            continue
        if dfn.require_any_component_kinds and not _any_component_kind(doc, dfn.require_any_component_kinds):
            continue
        if dfn.require_min_cross_boundary_flows > 0:
            nxb = len(_cross_boundary_flow_ids(doc))
            if nxb < dfn.require_min_cross_boundary_flows:
                continue
        if dfn.require_component_id_contains_any and not _component_id_contains(
            doc, dfn.require_component_id_contains_any
        ):
            continue
        if dfn.require_asset_name_id_contains_any and not _asset_name_id_contains(
            doc, dfn.require_asset_name_id_contains_any
        ):
            continue
        if dfn.require_flow_flag_any and not _any_flow_bool(doc, dfn.require_flow_flag_any):
            continue
        if any(mk.lower() in corpus for mk in dfn.mitigating_keywords):
            continue

        if dfn.structural_primary:
            if dfn.missing_any_of:
                missing_sp = [kw for kw in dfn.missing_any_of if kw.lower() not in corpus]
                if len(missing_sp) != len(dfn.missing_any_of):
                    continue
            sources = ["structural:primary"]
            if dfn.require_min_data_flows > 0:
                sources.append(f"structural:min_data_flows>={dfn.require_min_data_flows}")
            if dfn.require_min_trust_boundaries > 0:
                sources.append(f"structural:min_trust_boundaries>={dfn.require_min_trust_boundaries}")
            if dfn.require_any_component_kinds:
                sources.append(f"structural:component_kinds={','.join(dfn.require_any_component_kinds)}")
            if dfn.require_min_cross_boundary_flows > 0:
                sources.append(f"structural:cross_boundary_flows>={dfn.require_min_cross_boundary_flows}")
            if dfn.require_component_id_contains_any:
                sources.append("structural:component_id_contains")
            if dfn.require_asset_name_id_contains_any:
                sources.append("structural:asset_name_id_contains")
            if dfn.require_flow_flag_any:
                sources.append(f"structural:flow_flags={','.join(dfn.require_flow_flag_any)}")
            if dfn.missing_any_of:
                sources.append("corpus:missing_any_of(secondary)")
            msg = (dfn.structural_primary_message or "").strip()
            if not msg:
                msg = (
                    f"Perfil `{profile}`: sinais estruturais do modelo indicam lacuna de controlos "
                    f"({dfn.name})."
                )
            hits.append(
                AntiPatternHit(
                    id=dfn.id,
                    name=dfn.name,
                    severity_hint=dfn.severity_hint,
                    confidence_hint=_bump_confidence(dfn.confidence_hint, "structural_primary"),
                    message=msg,
                    evidence=[
                        f"semantic_profile={profile}",
                        "disparo baseado principalmente em estrutura do grafo/campos",
                    ],
                    expected_controls=list(dfn.expected_controls),
                    detection_sources=sources,
                )
            )
            continue

        missing = [kw for kw in dfn.missing_any_of if kw.lower() not in corpus]
        if len(missing) == len(dfn.missing_any_of):
            sources = ["corpus:missing_any_of"]
            if dfn.require_min_data_flows > 0:
                sources.append(f"structural:min_data_flows>={dfn.require_min_data_flows}")
            if dfn.require_min_trust_boundaries > 0:
                sources.append(f"structural:min_trust_boundaries>={dfn.require_min_trust_boundaries}")
            if dfn.require_any_component_kinds:
                sources.append(f"structural:component_kinds={','.join(dfn.require_any_component_kinds)}")
            if dfn.require_min_cross_boundary_flows > 0:
                sources.append(f"structural:cross_boundary_flows>={dfn.require_min_cross_boundary_flows}")
            if dfn.require_component_id_contains_any:
                sources.append("structural:component_id_contains")
            if dfn.require_asset_name_id_contains_any:
                sources.append("structural:asset_name_id_contains")
            if dfn.require_flow_flag_any:
                sources.append(f"structural:flow_flags={','.join(dfn.require_flow_flag_any)}")
            hits.append(
                AntiPatternHit(
                    id=dfn.id,
                    name=dfn.name,
                    severity_hint=dfn.severity_hint,
                    confidence_hint=dfn.confidence_hint,
                    message=(
                        f"Perfil `{profile}` sem menções explícitas a controlos esperados "
                        f"({', '.join(dfn.missing_any_of[:4])}…)."
                    ),
                    evidence=[
                        f"semantic_profile={profile}",
                        "nenhuma keyword de mitigação encontrada no corpus agregado",
                    ],
                    expected_controls=list(dfn.expected_controls),
                    detection_sources=sources,
                )
            )

    return hits


def catalog_path_for_docs() -> str:
    """Caminho lógico para documentação."""
    return "packages/threat-engine/otm_threat_engine/data/anti_patterns/catalog.yaml"
