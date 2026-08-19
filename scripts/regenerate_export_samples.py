"""Regenera `examples/export_samples/` a partir de `examples/minimal.otm.yaml`.

Estes ficheiros são o "eis o que a ferramenta produz" que alguém lê **antes de instalar**, e tanto
`examples/export_samples/README.txt` como `docs/features/EXPORTERS.md` declaram que são gerados a
partir daquele modelo. Três dos quatro tinham deixado de o ser: o `minimal.analysis.json` publicado
tinha metade do tamanho da saída real e não mostrava `explanations`, `aggregate_risk`,
`anti_pattern_hits` nem `decision_cockpit` — a explicabilidade que o README vende como
diferenciador. O único que não derivou foi o `minimal.flowchart.mmd`, que era o único com um teste.

Por isso isto existe como comando em vez de instrução: `tests/test_p6_export_samples_are_current.py`
falha quando as amostras divergem, e a resposta a esse falhanço tem de ser uma linha, não uma
sessão de cópia e colagem — foi a cópia e colagem que as deixou cinco meses para trás.

    python scripts/regenerate_export_samples.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_exporters import (
    export_analysis_json,
    export_document_json,
    export_document_markdown,
    export_flowchart_mermaid,
    export_threat_model_bundle_json,
)
from otm_threat_engine import analyze_document

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "examples" / "minimal.otm.yaml"
SAMPLES = ROOT / "examples" / "export_samples"


def build() -> dict[str, str]:
    document = load_document_from_yaml_path(SOURCE)
    analysis = analyze_document(document)
    return {
        "minimal.document.json": export_document_json(document),
        "minimal.document.md": export_document_markdown(document),
        "minimal.analysis.json": export_analysis_json(analysis),
        "minimal.bundle.json": export_threat_model_bundle_json(document, analysis),
        "minimal.flowchart.mmd": export_flowchart_mermaid(document),
    }


def main() -> int:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    for name, content in build().items():
        target = SAMPLES / name
        before = target.read_text(encoding="utf-8") if target.is_file() else None
        # `\n` explícito: estes ficheiros são versionados e não podem mudar por causa do SO de quem
        # os regenerou.
        #
        # O estado compara-se com `written`, e nao com `content`: para alguns exportadores a
        # normalizacao acima muda o valor, e comparar com o de antes dela anunciava
        # "actualizado" em todas as execucoes enquanto `git status` ficava vazio. Um alarme
        # sempre aceso nao responde a pergunta que este script existe para responder.
        written = content.rstrip("\n") + "\n"
        target.write_text(written, encoding="utf-8", newline="\n")
        state = "criado" if before is None else ("inalterado" if before == written else "actualizado")
        print(f"  {name:26} {state}")
    print(f"\nGerados a partir de {SOURCE.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":  # pragma: no cover - ponto de entrada manual
    sys.exit(main())
