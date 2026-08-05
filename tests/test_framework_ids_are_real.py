"""Os IDs de controlo que o projeto distribui têm de existir nas versões que ele declara.

Regressão: o cabeçalho do mapa declara "OWASP ASVS 4.0.3; NIST CSF 2.0; ISO/IEC 27001:2022
Annex A", mas seis entradas citavam IDs de outras versões — `PR.DS-06`, `PR.AC-01` e
`PR.AC-04` são NIST CSF **1.1** (a família `PR.AC-*` passou a `PR.AA-*` no 2.0), e três
controlos ISO apontavam para o número errado (`A.8.17` é sincronização de relógios, não
registo de eventos; `A.8.11` é mascaramento de dados, não criptografia; `A.8.13` é cópia de
segurança, não redundância).

Isto é pior do que um erro de documentação. O produto vende rastreabilidade para normas; um
ID inventado transforma essa rastreabilidade em ruído que alguém vai citar num relatório de
auditoria. O cabeçalho passa a ser verificado em vez de afirmado.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_DATA = Path(__file__).resolve().parents[1] / "packages" / "framework-mappings" / "otm_framework_mappings" / "data"

#: NIST CSF 2.0 — categorias válidas da função Protect/Detect usadas por este mapa.
#: `PR.AC-*` NÃO consta: foi substituída por `PR.AA-*` na 2.0.
_CSF_20 = {
    "PR.AA-01",
    "PR.AA-02",
    "PR.AA-03",
    "PR.AA-04",
    "PR.AA-05",
    "PR.AA-06",
    "PR.AT-01",
    "PR.AT-02",
    "PR.DS-01",
    "PR.DS-02",
    "PR.DS-10",
    "PR.DS-11",
    "PR.PS-01",
    "PR.PS-02",
    "PR.PS-03",
    "PR.PS-04",
    "PR.PS-05",
    "PR.PS-06",
    "PR.IR-01",
    "PR.IR-02",
    "PR.IR-03",
    "PR.IR-04",
    "DE.CM-01",
    "DE.CM-02",
    "DE.CM-03",
    "DE.CM-06",
    "DE.CM-09",
    "DE.AE-02",
    "DE.AE-03",
    "DE.AE-04",
    "DE.AE-06",
    "DE.AE-07",
    "DE.AE-08",
}

#: ISO/IEC 27001:2022 Annex A — os 93 controlos vivem em A.5.1–A.5.37, A.6.1–A.6.8,
#: A.7.1–A.7.14 e A.8.1–A.8.34. Validamos a gama, que é o que apanha um número inventado.
_ISO_RANGES = {"5": 37, "6": 8, "7": 14, "8": 34}


def _control_ids() -> list[tuple[str, str, Path]]:
    out: list[tuple[str, str, Path]] = []
    for path in sorted(_DATA.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))

        def walk(node: object) -> None:
            if isinstance(node, dict):
                fw, cid = node.get("framework"), node.get("control_id")
                if isinstance(fw, str) and isinstance(cid, str):
                    out.append((fw, cid, path))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(data)
    return out


_IDS = _control_ids()


def test_the_map_actually_contains_mappings() -> None:
    """Sem isto, todos os testes abaixo passariam num ficheiro vazio."""
    assert len(_IDS) > 20


@pytest.mark.parametrize(("framework", "control_id"), [(f, c) for f, c, _ in _IDS if f == "nist_csf"])
def test_nist_csf_ids_exist_in_csf_20(framework: str, control_id: str) -> None:
    assert not control_id.startswith("PR.AC-"), (
        f"`{control_id}` is NIST CSF 1.1; the family became PR.AA-* in CSF 2.0, which this map declares."
    )
    assert control_id in _CSF_20, f"`{control_id}` is not a NIST CSF 2.0 subcategory."


@pytest.mark.parametrize(("framework", "control_id"), [(f, c) for f, c, _ in _IDS if f == "iso_27001"])
def test_iso_27001_ids_are_within_the_2022_annex_a_ranges(framework: str, control_id: str) -> None:
    match = re.fullmatch(r"A\.(\d)\.(\d{1,2})", control_id)
    assert match, f"`{control_id}` is not an ISO/IEC 27001:2022 Annex A identifier."
    clause, number = match.group(1), int(match.group(2))
    assert clause in _ISO_RANGES, f"`{control_id}`: Annex A has clauses 5-8 only."
    assert 1 <= number <= _ISO_RANGES[clause], (
        f"`{control_id}` is out of range; A.{clause}.x stops at {_ISO_RANGES[clause]}."
    )


@pytest.mark.parametrize(("framework", "control_id"), [(f, c) for f, c, _ in _IDS if f in ("cwe", "capec")])
def test_cwe_and_capec_ids_are_well_formed(framework: str, control_id: str) -> None:
    assert re.fullmatch(r"(CWE|CAPEC)-\d+", control_id), f"`{control_id}` is not a MITRE identifier."
    assert control_id.startswith(framework.upper() + "-"), f"`{control_id}` filed under the wrong catalogue."


@pytest.mark.parametrize(("framework", "control_id"), [(f, c) for f, c, _ in _IDS if f == "owasp_asvs"])
def test_asvs_ids_are_well_formed(framework: str, control_id: str) -> None:
    assert re.fullmatch(r"V\d{1,2}\.\d{1,2}\.\d{1,2}", control_id), (
        f"`{control_id}` is not an ASVS 4.0.3 requirement id."
    )


def test_no_iso_control_is_described_with_another_controls_title() -> None:
    """As três trocas ISO que passaram despercebidas eram exactamente isto.

    O número estava certo na sintaxe e errado no significado — o `notes` descrevia um
    controlo diferente daquele que o `control_id` aponta.
    """
    wrong_pairs = {
        "A.8.17": "registo",  # A.8.17 é sincronização de relógios
        "A.8.11": "criptografia",  # A.8.11 é mascaramento de dados
        "A.8.13": "redundância",  # A.8.13 é cópia de segurança
    }
    for path in sorted(_DATA.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        for control_id, wrong_topic in wrong_pairs.items():
            if control_id in text:
                block = text[text.index(control_id) : text.index(control_id) + 200].lower()
                assert wrong_topic not in block, (
                    f"{path.name}: `{control_id}` is described as '{wrong_topic}', which is a different control."
                )
