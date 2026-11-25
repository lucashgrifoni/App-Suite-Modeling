"""O `refs` de uma regra personalizada não pode escrever o contorno do relatório.

`markdown_text.py` existe para isto e está aplicado em 34 sítios de `analysis_markdown.py`.
`_format_framework_refs_compact` ficou de fora, e é o único sink deste ficheiro que recebe texto
livre do utilizador: `runtime.py` constrói `FrameworkRef(framework=CUSTOM_REF_FRAMEWORK,
control_id=ref)` com o `refs` da regra tal como veio do ficheiro.

Passou despercebido porque o valor entra **dentro de crases**, o que parece bastar. Não basta:
uma crase no valor fecha o code span, e o que vem depois é Markdown verdadeiro. Medido antes da
correção, com um ficheiro de regras e o CLI distribuído, o relatório ganhava um `##` de nível 2 e
um marcador que se lê como achado do motor -- e os refs da ameaça **seguinte**, legítima, ficavam
órfãos num parágrafo solto.

O ficheiro de regras é a entrada não confiável por desenho: vem do repositório da organização que
adota a ferramenta e corre em CI. Quem consegue mudá-lo consegue fazer o relatório -- que é a
evidência de release -- exibir achados fabricados indistinguíveis dos do motor.

Verificado por medição que **não** é alcançável por um `.otm.yaml` sozinho: um documento pode
declarar `framework_refs` (o schema não restringe `framework` nem `control_id`), mas os refs de
ameaças declaradas não passam por este sink.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "exporters", "industry-packs"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_FORGED_HEADING = "## Secao escrita pelo ficheiro de regras"
_PAYLOAD = f"CWE-306`\n\n{_FORGED_HEADING}\n\n- **achado HIGH falso** (`h_fake`) score 25\n\n`x"


def _report_with_rule_ref(tmp_path: Path, ref: str) -> str:
    from otm_core_schema import ThreatModelDocument
    from otm_exporters import export_analysis_markdown
    from otm_threat_engine import analyze_document
    from otm_threat_engine.custom_rules.loader import load_custom_rules

    rules = tmp_path / "rules.yaml"
    rules.write_text(
        "id: acme\nrules:\n  - id: evil\n    title: benign\n    stride: spoofing\n"
        "    match:\n      component:\n        kind: process\n    refs:\n      - " + json.dumps(ref) + "\n",
        encoding="utf-8",
    )
    doc = ThreatModelDocument.model_validate(
        yaml.safe_load((_ROOT / "examples" / "minimal.otm.yaml").read_text(encoding="utf-8"))
    )
    return export_analysis_markdown(analyze_document(doc, custom_rules=load_custom_rules(rules)))


def test_o_payload_cabe_no_tecto_declarado_do_campo() -> None:
    """Sanidade: se o `max_length` já o barrasse, o resto não provaria nada."""
    from otm_threat_engine.custom_rules.models import CustomRule

    cap = CustomRule.model_fields["refs"].annotation
    assert len(_PAYLOAD) < 200, f"o payload tem {len(_PAYLOAD)} caracteres e o tecto do campo é 200"
    assert cap is not None


def test_o_ref_nao_cria_um_titulo_no_relatorio(tmp_path: Path) -> None:
    report = _report_with_rule_ref(tmp_path, _PAYLOAD)

    forged = [line for line in report.splitlines() if line.strip().startswith("#") and "Secao escrita" in line]
    assert not forged, f"o ficheiro de regras escreveu um título no relatório: {forged}"


def test_o_ref_nao_abre_blocos_novos(tmp_path: Path) -> None:
    """Nem título, nem marcador de lista próprio: o valor tem de caber numa linha."""
    report = _report_with_rule_ref(tmp_path, _PAYLOAD)

    assert "achado HIGH falso" in report, "o texto do ref desapareceu; achatar não é truncar"
    offending = [
        line for line in report.splitlines() if "achado HIGH falso" in line and line.lstrip().startswith("- **achado")
    ]
    assert not offending, f"o ref virou um marcador de lista próprio: {offending}"


@pytest.mark.parametrize(
    "ref",
    [
        "CWE-306",
        "uma`crase",
        "```tres```",
        "`comeca com crase",
        "acaba com crase`",
        "`",
        "ASVS 4.0.3 V2.2.1",
    ],
)
def test_o_valor_sobrevive_inteiro_dentro_do_code_span(ref: str) -> None:
    """Nada é truncado nem removido — a promessa que `markdown_text` faz no seu próprio docstring."""
    from otm_exporters.markdown_text import md_code

    rendered = md_code(ref)

    assert "\n" not in rendered
    assert ref.strip() in rendered, f"`md_code({ref!r})` perdeu texto: {rendered!r}"
    fence = rendered[: len(rendered) - len(rendered.lstrip("`"))]
    assert fence, "não há cerca de abertura"
    assert fence not in ref, f"a cerca {fence!r} aparece dentro do próprio valor e fecha o span"
