"""P6 — as amostras publicadas têm de ser o que a ferramenta produz hoje.

`examples/export_samples/README.txt` e `docs/features/EXPORTERS.md` declaram ambos que estes
ficheiros são "gerados a partir de `examples/minimal.otm.yaml`". Três dos quatro tinham deixado de
o ser. Medido antes desta correcção:

| ficheiro | publicado | regenerado | tinha teste? |
|---|---:|---:|---|
| `minimal.document.json` | 1 925 B | 3 283 B | não |
| `minimal.analysis.json` | 34 075 B | 68 046 B | não |
| `minimal.bundle.json` | 38 300 B | 75 851 B | não |
| `minimal.flowchart.mmd` | 166 B | 166 B | **sim** |

O único com teste é o único que não derivou. Não é coincidência, e é o argumento inteiro deste
ficheiro.

À cópia publicada de `minimal.analysis.json` faltavam `explanations`, `aggregate_risk`,
`anti_pattern_hits`, `decision_cockpit` e `ai_system_context` — precisamente a explicabilidade e o
pré-check de qualidade que o README vende como diferenciadores. Estas amostras são o "eis o que a
ferramenta produz" que alguém lê **antes de instalar**: mostravam um motor de várias versões atrás,
sem as capacidades anunciadas duas páginas antes.

O teste compara com a saída fresca em vez de fixar bytes literais, por isso não obriga a mexer aqui
quando a saída mudar legitimamente — obriga a **regenerar**, que é o que a declaração promete.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml_path
from otm_exporters import (
    export_analysis_json,
    export_document_json,
    export_document_markdown,
    export_flowchart_mermaid,
    export_threat_model_bundle_json,
)
from otm_threat_engine import analyze_document

_ROOT = Path(__file__).resolve().parents[1]
_SAMPLES = _ROOT / "examples" / "export_samples"
_SOURCE = _ROOT / "examples" / "minimal.otm.yaml"


def _fresh() -> dict[str, str]:
    doc = load_document_from_yaml_path(_SOURCE)
    result = analyze_document(doc)
    return {
        "minimal.document.json": export_document_json(doc),
        "minimal.document.md": export_document_markdown(doc),
        "minimal.analysis.json": export_analysis_json(result),
        "minimal.bundle.json": export_threat_model_bundle_json(doc, result),
        "minimal.flowchart.mmd": export_flowchart_mermaid(doc),
    }


@pytest.mark.parametrize("name", sorted(_fresh()))
def test_a_amostra_publicada_e_a_saida_actual(name: str) -> None:
    """Regenerar é a correcção; editar à mão é o que fez isto derivar."""
    published = _SAMPLES / name

    assert published.is_file(), f"{name} é declarado em EXPORTERS.md mas não existe"
    assert published.read_text(encoding="utf-8").strip() == _fresh()[name].strip(), (
        f"{name} deixou de corresponder a `otm` sobre {_SOURCE.name}; regenere-o"
    )


def test_a_analise_publicada_mostra_a_explicabilidade_que_o_readme_promete() -> None:
    """O sintoma concreto da deriva: faltavam as secções que distinguem o produto.

    Um teste só de igualdade passaria a verde com uma amostra vazia se a ferramenta regredisse.
    Este nomeia o que tem de lá estar.
    """
    import json

    published = json.loads((_SAMPLES / "minimal.analysis.json").read_text(encoding="utf-8"))

    for key in ("explanations", "aggregate_risk", "anti_pattern_hits", "decision_cockpit"):
        assert key in published, f"a amostra publicada não mostra `{key}`"


def test_a_declaracao_de_origem_continua_a_ser_verdade() -> None:
    """Se alguém mudar a fonte, esta é a linha que tem de mudar com ela."""
    readme = (_SAMPLES / "README.txt").read_text(encoding="utf-8")

    assert "minimal.otm.yaml" in readme
