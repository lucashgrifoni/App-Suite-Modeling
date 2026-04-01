"""
Importação assistida (leve) a partir de Chart Helm + values.

Escopo intencional:
- Não resolve templates Helm nem executa `helm template`.
- O objetivo é gerar um rascunho canónico e, principalmente, um `import_signals_corpus`
  útil para deteção PLOT4ai em ambientes cloud-native.
"""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import Component, DataFlow, TrustBoundary
from otm_core_schema.enums import ComponentKind, IndustrySector, SystemType

from otm_artifact_import.ai_import_corpus import build_helm_import_signals_corpus
from otm_artifact_import.builders import assemble_draft, slug_id
from otm_artifact_import.types import ArtifactImportResult, InferenceRecord


def import_helm_text(text: str, *, filename: str = "chart.yaml") -> ArtifactImportResult:
    """
    Importa texto de Chart.yaml/values.yaml (ou bundle concatenado).

    Gera um documento minimalista com um componente agregador e um `import_signals_corpus` rico.
    """
    inferences: list[InferenceRecord] = []
    unknowns: list[str] = []

    import_corpus = build_helm_import_signals_corpus(text)
    if not import_corpus:
        unknowns.append("Sem sinais parseáveis em Chart/values; apenas rascunho mínimo foi criado.")

    cid_ext = "ext_helm_clients"
    cid_rel = slug_id(Path(filename).stem, prefix="helm")
    tb_ext = "tb_helm_external"
    tb_app = "tb_helm_release"

    components = [
        Component(
            id=cid_ext,
            name="Clientes (exterior)",
            kind=ComponentKind.EXTERNAL_ENTITY,
            description="Chamadores externos agregados (Helm não descreve topo real sem template).",
            in_trust_boundary=tb_ext,
            metadata={"artifact": filename, "import_kind": "helm"},
        ),
        Component(
            id=cid_rel,
            name=f"Helm release ({Path(filename).stem})",
            kind=ComponentKind.PROCESS,
            description="Release agregada inferida a partir de Chart/values (sem renderização de templates).",
            technology="Helm",
            in_trust_boundary=tb_app,
            metadata={"artifact": filename, "import_kind": "helm"},
        ),
    ]

    flows = [
        DataFlow(
            id="flow_ext_to_release",
            name="Tráfego externo (agregado)",
            from_component=cid_ext,
            to_component=cid_rel,
            protocol=None,
            description="Fluxo heurístico: sem `helm template` não é possível inferir Ingress/Service reais.",
            metadata={"artifact": filename, "import_kind": "helm"},
        )
    ]

    boundaries = [
        TrustBoundary(
            id=tb_ext,
            name="Exterior (heurístico)",
            description="Chamadores externos agregados.",
            member_component_ids=[],
        ),
        TrustBoundary(
            id=tb_app,
            name="Release Helm (agregado)",
            description="Conjunto de workloads/serviços renderizados por Helm (não expandido).",
            member_component_ids=[],
        ),
    ]

    inf_idx = 0

    def inf(msg: str, conf: str, *, related: list[str] | None = None) -> None:
        nonlocal inf_idx
        inf_idx += 1
        inferences.append(
            InferenceRecord(
                id=f"inf_{inf_idx:03d}",
                message=msg,
                confidence=conf,  # type: ignore[arg-type]
                source="helm",
                related_component_ids=list(related or []),
            )
        )

    if import_corpus:
        inf(
            "Sinais de Helm (Chart/values) agregados em `import_signals_corpus` para reforçar deteção PLOT4ai.",
            "medium",
            related=[cid_rel],
        )

    return assemble_draft(
        title=f"Helm ({filename})",
        summary="Rascunho a partir de Helm — release agregada; detalhes exigem renderização de templates.",
        source_kind="helm",
        system_type=SystemType.HYBRID,
        industry=IndustrySector.CLOUD_NATIVE,
        components=components,
        data_flows=flows,
        trust_boundaries=boundaries,
        assets=[],
        inferences=inferences,
        unknowns=unknowns,
        extra_assumptions=[
            "Este import não interpreta templates Helm; use `helm template` + import Kubernetes para diagrama completo.",
        ],
        import_signals_corpus=import_corpus or None,
    )


def import_helm_path(path: Path) -> ArtifactImportResult:
    """
    Importa a partir de um ficheiro (Chart.yaml/values.yaml) ou diretório.

    Em diretórios, concatena `Chart.yaml` + `values*.yaml` se existirem.
    """
    if path.is_dir():
        chunks: list[str] = []
        chart = path / "Chart.yaml"
        if chart.exists():
            chunks.append(chart.read_text(encoding="utf-8"))
        for p in sorted(path.glob("values*.yml")) + sorted(path.glob("values*.yaml")):
            chunks.append(p.read_text(encoding="utf-8"))
        text = "\n---\n".join(chunks)
        label = f"{path.name}/"
        res = import_helm_text(text, filename=label)
        if not chunks:
            res.unknowns.append("Directório sem Chart.yaml nem values*.yaml.")
        return res
    return import_helm_text(path.read_text(encoding="utf-8"), filename=path.name)

