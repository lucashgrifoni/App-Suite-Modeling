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

from otm_artifact_import.ai_import_corpus import build_terraform_import_signals_corpus
from otm_artifact_import.builders import assemble_draft, slug_id
from otm_artifact_import.types import ArtifactImportResult, InferenceRecord

_RESOURCE_HEAD = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{')


def _iter_resource_blocks(text: str) -> Iterator[tuple[str, str, str]]:
    """Os blocos `resource`, cada um limitado ao texto que lhe pertence.

    Um bloco cujas chavetas nunca fecham termina onde o cabeçalho seguinte começa. É o que uma
    chaveta em falta significa para quem escreveu o ficheiro, e sem esse limite a varredura de
    **cada** cabeçalho corria até ao fim do texto: com M cabeçalhos em L bytes, O(L*M) a percorrer
    e outro tanto a reter, porque `import_terraform_text` materializa todos os corpos de uma vez.
    Medido, 54 KB de HCL desequilibrado custavam 2,65 s de CPU e 44 MB retidos, contra 1,2 ms para
    54 KB equilibrados; `POST /v1/imports/terraform` aceita 2 MiB, dispensa credencial na postura
    por omissão e corre isto sincronamente dentro de um handler `async`, pelo que o custo parava o
    servidor inteiro e não só o pedido.

    O corpo tem um único consumidor — `_public_ingress_hint` — e era aí que a ausência de limite
    fazia o estrago silencioso: corpos que se estendiam até ao fim do ficheiro sobrepunham-se, e um
    `0.0.0.0/0` declarado num recurso tardio caía dentro do corpo de todos os anteriores. Uma
    chaveta em falta bastava para mover um balanceador `internal = true` para `tb_internet_facing`.

    Os intervalos entre cabeçalhos consecutivos são disjuntos, por isso limitar cada varredura ao
    cabeçalho seguinte deixa o custo total linear no ficheiro, sem perder nenhum recurso declarado.
    Um cabeçalho encontrado dentro de outro bloco encerra-o: já hoje `finditer` o devolvia como
    recurso próprio, e passa a sê-lo sem ficar também dentro do corpo alheio.
    """
    heads = list(_RESOURCE_HEAD.finditer(text))
    for position, head in enumerate(heads):
        start = head.end()
        limit = heads[position + 1].start() if position + 1 < len(heads) else len(text)
        depth = 1
        i = start
        while i < limit and depth > 0:
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            i += 1
        body = text[start : i - 1] if depth == 0 else text[start:limit]
        yield head.group(1), head.group(2), body


def _helm_chart_hint(text: str) -> bool:
    return bool(re.search(r'resource\s+"helm_release"\s+"', text))


def _public_ingress_hint(body: str) -> bool:
    """Heurística fraca: 0.0.0.0/0 em blocos de rede."""
    return bool(re.search(r"0\.0\.0\.0/0", body))


_CLOUD_PREFIXES = ("aws_", "google_", "azurerm_")

# Avaliadas por ordem; primeira keyword presente em `rtype` define o ComponentKind.
_CLOUD_RESOURCE_RULES: list[tuple[tuple[str, ...], ComponentKind]] = [
    (("s3_bucket", "storage_bucket"), ComponentKind.DATASTORE),
    (("rds", "sql_database", "db_instance", "database"), ComponentKind.DATASTORE),
    (("dynamodb",), ComponentKind.DATASTORE),
    (("sqs_queue", "sns_topic", "servicebus"), ComponentKind.QUEUE),
    (("lb", "load_balancer", "gateway"), ComponentKind.GATEWAY),
    (("instance", "lambda", "function", "ecs_service"), ComponentKind.PROCESS),
]


def _map_resource_kind(rtype: str) -> tuple[ComponentKind, str | None]:
    """Devolve (ComponentKind, technology_hint)."""
    if rtype.startswith(_CLOUD_PREFIXES):
        for keywords, kind in _CLOUD_RESOURCE_RULES:
            if any(k in rtype for k in keywords):
                return kind, rtype
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
                confidence=conf,
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
            'Nenhum bloco `resource "tipo" "nome"` encontrado — ficheiro pode usar só módulos ou sintaxe não suportada.'
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
    import_corpus = build_terraform_import_signals_corpus(text)
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
        import_signals_corpus=import_corpus or None,
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
