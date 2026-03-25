"""
Importação assistida a partir de ficheiros Terraform (.tf).

Parsing intencionalmente conservador: extracção de blocos `resource` por chaves `{}`.
Não executa `terraform graph`; não resolve módulos ou expressões HCL complexas.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from otm_core_schema import Component, DataFlow, TrustBoundary
from otm_core_schema.enums import ComponentKind, IndustrySector, SystemType

from otm_artifact_import.builders import assemble_draft, slug_id
from otm_artifact_import.types import ArtifactImportResult, InferenceRecord

_RESOURCE_HEAD = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{')


def _iter_resource_blocks(text: str) -> Iterator[tuple[str, str, str]]:
    for m in _RESOURCE_HEAD.finditer(text):
        rtype, name = m.group(1), m.group(2)
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            i += 1
        body = text[start : i - 1] if depth == 0 else text[start:]
        yield rtype, name, body


def _helm_chart_hint(text: str) -> bool:
    return bool(re.search(r'resource\s+"helm_release"\s+"', text))


def _public_ingress_hint(body: str) -> bool:
    """Heurística fraca: 0.0.0.0/0 em blocos de rede."""
    return bool(re.search(r'0\.0\.0\.0/0', body))


def _map_resource_kind(rtype: str) -> tuple[ComponentKind, str | None]:
    """Devolve (ComponentKind, technology_hint)."""
    if rtype.startswith("aws_") or rtype.startswith("google_") or rtype.startswith("azurerm_"):
        if "s3_bucket" in rtype or "storage_bucket" in rtype:
            return ComponentKind.DATASTORE, rtype
        if "rds" in rtype or "sql_database" in rtype or "db_instance" in rtype or "database" in rtype:
            return ComponentKind.DATASTORE, rtype
        if "dynamodb" in rtype:
            return ComponentKind.DATASTORE, rtype
        if "sqs_queue" in rtype or "sns_topic" in rtype or "servicebus" in rtype:
            return ComponentKind.QUEUE, rtype
        if "lb" in rtype or "load_balancer" in rtype or "gateway" in rtype:
            return ComponentKind.GATEWAY, rtype
        if "instance" in rtype or "lambda" in rtype or "function" in rtype or "ecs_service" in rtype:
            return ComponentKind.PROCESS, rtype
        return ComponentKind.OTHER, rtype

    if rtype.startswith("kubernetes_") or rtype.startswith("helm_"):
        return ComponentKind.OTHER, rtype
    return ComponentKind.OTHER, rtype


def import_terraform_text(text: str, *, filename: str = "bundle.tf") -> ArtifactImportResult:
    inferences: list[InferenceRecord] = []
    unknowns: list[str] = []
    inf_idx = 0

    def inf(msg: str, conf: str, *, related: list[str] | None = None) -> None:
        nonlocal inf_idx
        inf_idx += 1
        inferences.append(
            InferenceRecord(
                id=f"inf_{inf_idx:03d}",
                message=msg,
                confidence=conf,  # type: ignore[arg-type]
                source="terraform",
                related_component_ids=list(related or []),
            )
        )

    if not text.strip():
        unknowns.append("Ficheiro Terraform vazio.")
        text = "# empty"

    resources = list(_iter_resource_blocks(text))
    if not resources:
        unknowns.append(
            "Nenhum bloco `resource \"tipo\" \"nome\"` encontrado — ficheiro pode usar só módulos ou sintaxe não suportada."
        )

    tb_ext = "tb_internet_facing"
    tb_cloud = "tb_cloud_account"

    ext_clients = "ext_clients_terraform"
    components: list[Component] = [
        Component(
            id=ext_clients,
            name="Clientes / redes externas (genérico)",
            kind=ComponentKind.EXTERNAL_ENTITY,
            description="Entidade externa agregada; detalhe depende do diagrama de rede real.",
            in_trust_boundary=tb_ext,
            metadata={"artifact": filename},
        ),
    ]

    comp_by_key: dict[tuple[str, str], str] = {}
    public_gateways: list[str] = []

    for rtype, name, body in resources:
        kind, tech = _map_resource_kind(rtype)
        cid = slug_id(f"{rtype}_{name}", prefix="tf")
        comp_by_key[(rtype, name)] = cid
        boundary = tb_cloud
        desc = f"Recurso Terraform `{rtype}.{name}` (corpo não interpretado linha-a-linha)."
        wide_net = _public_ingress_hint(body)
        if kind == ComponentKind.GATEWAY and wide_net:
            boundary = tb_ext
            public_gateways.append(cid)
        elif wide_net:
            inf(
                "Regra ou bloco com `0.0.0.0/0` em "
                f"`{rtype}.{name}` — possível superfície alargada; confirmar SG/LB/firewall real.",
                "low",
                related=[cid],
            )
        components.append(
            Component(
                id=cid,
                name=f"{rtype}.{name}",
                kind=kind,
                description=desc,
                technology=tech,
                in_trust_boundary=boundary,
                metadata={"terraform_type": rtype, "terraform_name": name, "artifact": filename},
            )
        )

    if resources:
        inf(
            f"Identificados {len(resources)} recurso(s) Terraform pelo cabeçalho `resource` (sem avaliar expressões HCL).",
            "medium",
            related=[c.id for c in components if c.id != ext_clients][:20],
        )

    if public_gateways:
        inf(
            "Possível exposição pública sugerida por regras com 0.0.0.0/0 próximas de balance/load balancer — rever SG/firewall.",
            "low",
            related=public_gateways,
        )

    if _helm_chart_hint(text):
        inf(
            "Recurso `helm_release` presente — charts completos não foram interpretados (Helm como tal fica para fase seguinte).",
            "medium",
            related=[],
        )

    flows: list[DataFlow] = []
    if public_gateways:
        for gw in public_gateways:
            flows.append(
                DataFlow(
                    id=slug_id(f"flow_ext_{gw}", prefix="fl"),
                    name=f"Tráfego externo → {gw}",
                    from_component=ext_clients,
                    to_component=gw,
                    protocol=None,
                    encrypted=None,
                    description="Fluxo genérico sugerido por gateway com indícios de exposição ampliada.",
                    metadata={"artifact": filename},
                )
            )

    boundaries: list[TrustBoundary] = [
        TrustBoundary(
            id=tb_ext,
            name="Perímetro exposto (heurístico)",
            description="Componentes com indício de alcance alargado na rede.",
            member_component_ids=[],
        ),
        TrustBoundary(
            id=tb_cloud,
            name="Conta cloud / infra própria",
            description="Recursos inferidos como interiores por defeito.",
            member_component_ids=[],
        ),
    ]

    title = f"Infra Terraform ({filename})"
    return assemble_draft(
        title=title,
        summary=f"Rascunho a partir de Terraform — {len(resources)} recurso(s).",
        source_kind="terraform",
        system_type=SystemType.HYBRID,
        industry=IndustrySector.CLOUD_NATIVE,
        components=components,
        data_flows=flows,
        trust_boundaries=boundaries,
        assets=[],
        inferences=inferences,
        unknowns=unknowns,
        extra_assumptions=[
            "Relações entre recursos não seguem dependências `depends_on` nem `terraform graph`.",
            "Módulos e ficheiros `.tf.json` são suportados apenas como texto HCL-equivalente bruto.",
        ],
    )


def import_terraform_path(path: Path) -> ArtifactImportResult:
    if path.is_dir():
        parts: list[str] = []
        for p in sorted(path.glob("*.tf")):
            parts.append(p.read_text(encoding="utf-8"))
        text = "\n\n".join(parts)
        label = f"{path.name}/"
        combined = import_terraform_text(text, filename=label)
        if not parts:
            combined.unknowns.append("Directório sem ficheiros `.tf`.")
        return combined
    return import_terraform_text(path.read_text(encoding="utf-8"), filename=path.name)
