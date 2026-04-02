"""
Biblioteca de anti-padrões por template / semantic profile.

Heurística conservadora: sinaliza riscos de modelagem quando o contexto declara um perfil
mas o texto agregado não menciona controlos esperados. Não substitui revisão humana.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from otm_core_schema import ThreatModelDocument

from otm_threat_engine.wizard_signals import signals_for_profile, synthetic_keyword_corpus


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


class AntiPatternHit(BaseModel):
    """Ocorrência detectada para relatório, backlog e benchmark."""

    id: str
    name: str
    severity_hint: str
    message: str
    evidence: list[str] = Field(default_factory=list)
    expected_controls: list[str] = Field(default_factory=list)


def _corpus(doc: ThreatModelDocument) -> str:
    parts = [
        doc.metadata.title,
        doc.metadata.summary or "",
        doc.business_context.description if doc.business_context and doc.business_context.description else "",
    ]
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

    for dfn in _load_definitions():
        profiles = [p.lower() for p in dfn.semantic_profiles]
        if profile not in profiles:
            continue
        missing = [kw for kw in dfn.missing_any_of if kw.lower() not in corpus]
        if not dfn.missing_any_of:
            continue
        if len(missing) == len(dfn.missing_any_of):
            hits.append(
                AntiPatternHit(
                    id=dfn.id,
                    name=dfn.name,
                    severity_hint=dfn.severity_hint,
                    message=(
                        f"Perfil `{profile}` sem menções explícitas a controlos esperados "
                        f"({', '.join(dfn.missing_any_of[:4])}…)."
                    ),
                    evidence=[
                        f"semantic_profile={profile}",
                        "nenhuma keyword de mitigação encontrada no corpus agregado",
                    ],
                    expected_controls=list(dfn.expected_controls),
                )
            )

    return hits


def catalog_path_for_docs() -> str:
    """Caminho lógico para documentação."""
    return "packages/threat-engine/otm_threat_engine/data/anti_patterns/catalog.yaml"
