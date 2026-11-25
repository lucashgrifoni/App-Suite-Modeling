"""Renomear um componente não pode reprovar o gate de CI.

Os matchers de contexto do wizard comparam literais curtos por subcadeia sobre um blob que inclui o
**nome do componente**. `"file"` mora dentro de *pro**file***, e `"rate"` dentro de *corpo**rate***.

Medido no template `file-upload-processing` com as tags de wizard que armam o cluster de upload,
mudando **uma única linha** — o nome de um componente, de "User Account Service" para "User Profile
Service":

    THREAT MODEL GATE: FAILED   policy: --fail-on=high
    WORSENED threats crossing into high+ (3)
    exit 3

Cinco ameaças ganham +1 de impacto e um ref de auditoria `wizard:context_boost` que afirma um
match de cluster de upload de ficheiros que não existe. O `action.yml` decide o veredito por este
mesmo comando, portanto uma pull request que só renomeia um componente reprova o CI de quem
consome a Action, com três escalonamentos de severidade fabricados.

A regra é fronteira à **esquerda**, a mesma escolhida para o catálogo de anti-padrões e pela mesma
razão: preserva os radicais deliberados (`admin` em *administrator*, `privileg` em *privilegiado*,
`api` em *apigateway*, `ficheiro` em *ficheiros*) e mata as colisões a meio da palavra.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _model(component_name: str, tmp_path: Path, filename: str) -> Path:
    from otm_industry_packs.loader import load_template_yaml

    document = yaml.safe_load(load_template_yaml("file-upload-processing"))
    document.setdefault("metadata", {}).setdefault("tags", [])
    document["metadata"]["tags"] += [
        "wz:file_handling_application:quarantine=no",
        "wz:file_handling_application:scan=no",
    ]
    boundary = document["trust_boundaries"][0]["id"] if document.get("trust_boundaries") else None
    component = {"id": "prof", "name": component_name, "kind": "process"}
    if boundary:
        component["in_trust_boundary"] = boundary
    document["components"].append(component)

    path = tmp_path / filename
    path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _threat_impacts(component_name: str, tmp_path: Path) -> dict[str, int]:
    from otm_core_schema import ThreatModelDocument
    from otm_threat_engine import analyze_document

    path = _model(component_name, tmp_path, "m.otm.yaml")
    document = ThreatModelDocument.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    result = analyze_document(document)
    return {h.id: h.risk.impact for h in result.heuristic_threats if h.target_component_id == "prof"}


def test_o_par_de_modelos_difere_so_no_nome(tmp_path: Path) -> None:
    """Sanidade: sem isto o teste seguinte podia estar a medir outra mudança."""
    before = _model("User Account Service", tmp_path, "a.otm.yaml").read_text(encoding="utf-8")
    after = _model("User Profile Service", tmp_path, "b.otm.yaml").read_text(encoding="utf-8")

    differing = [(x, y) for x, y in zip(before.splitlines(), after.splitlines(), strict=True) if x != y]
    assert len(differing) == 1, differing


def test_renomear_para_profile_nao_altera_o_impacto(tmp_path: Path) -> None:
    account = _threat_impacts("User Account Service", tmp_path)
    profile = _threat_impacts("User Profile Service", tmp_path)

    assert account, "premissa: o componente produz ameaças"
    assert profile == account, (
        "`file` casou dentro de `Profile` e armou o cluster de upload: "
        f"{ {k: (account[k], profile[k]) for k in account if account[k] != profile.get(k)} }"
    )


def test_renomear_para_corporate_nao_altera_o_impacto(tmp_path: Path) -> None:
    """A segunda instância no mesmo ficheiro: `rate` dentro de `Corporate`."""
    partner = _threat_impacts("Partner Directory Sync", tmp_path)
    corporate = _threat_impacts("Corporate Directory Sync", tmp_path)

    assert corporate == partner, (
        f"{ {k: (partner[k], corporate[k]) for k in partner if partner[k] != corporate.get(k)} }"
    )


def test_um_nome_que_e_mesmo_de_upload_continua_a_armar(tmp_path: Path) -> None:
    """A correcção não podia ser desligar o boost: o caso legítimo tem de continuar."""
    plain = _threat_impacts("User Account Service", tmp_path)
    upload = _threat_impacts("File Upload Handler", tmp_path)

    assert any(upload[k] > plain[k] for k in plain), f"plain={plain} upload={upload}"


def test_o_gate_nao_reprova_por_um_rename(tmp_path: Path) -> None:
    """Ponta a ponta, pelo comando que o `action.yml` corre."""
    before = _model("User Account Service", tmp_path, "before.otm.yaml")
    after = _model("User Profile Service", tmp_path, "after.otm.yaml")

    result = subprocess.run(  # noqa: S603 - argv fixo, sem shell
        [
            sys.executable,
            "-m",
            "otm_cli.main",
            "diff",
            str(before),
            str(after),
            "--with-analysis",
            "--fail-on",
            "high",
        ],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )

    assert result.returncode == 0, f"o gate reprovou um rename (exit {result.returncode}):\n{result.stdout[-700:]}"


@pytest.mark.parametrize(
    ("keyword", "text", "expected"),
    [
        ("file", "user profile service", False),
        ("file", "file upload handler", True),
        ("rate", "corporate directory", False),
        ("rate", "rate limit", True),
        ("api", "apigateway ingress", True),
        ("admin", "administrator console", True),
        ("privileg", "acesso privilegiado", True),
        ("ficheiro", "ficheiros temporarios", True),
    ],
)
def test_a_regra_preserva_os_radicais_deliberados(keyword: str, text: str, expected: bool) -> None:
    from otm_core_schema.ai_context import has_stem

    assert has_stem(text, keyword) is expected
