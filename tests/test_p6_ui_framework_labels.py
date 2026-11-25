"""P6 — a UI tem de ter rótulo para cada framework que o motor emite.

`apps/web/src/constants/frameworkLabels.ts` mapeia o identificador do framework para o texto que o
utilizador lê em `ThreatsAnalysisCard`. Faltavam dois: o motor emite `capec`, `cwe`, `iso_27001`,
`nist_csf`, `owasp_asvs` e `owasp_tm`, e a UI só rotulava quatro.

Sem entrada, o componente cai no identificador cru (`FRAMEWORK_LABELS[r.framework] ?? r.framework`),
por isso apareciam `cwe:79` e `capec:66` em minúsculas ao lado de `OWASP ASVS:V5.3.4`. Não é dado
errado — degrada com elegância — mas é apresentação inconsistente naquilo que o produto vende como
mapeamento a normas.

O mapa é mantido à mão numa linguagem e a lista de verdade vive noutra, o que é a receita para
divergir em silêncio quando um mapeamento novo for acrescentado. Este teste liga as duas.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_LABELS_TS = _ROOT / "apps" / "web" / "src" / "constants" / "frameworkLabels.ts"

sys.path.insert(0, str(_ROOT / "packages" / "framework-mappings"))


def _ui_labels() -> dict[str, str]:
    text = _LABELS_TS.read_text(encoding="utf-8")
    body = text[text.index("{") : text.index("};") + 1]
    return dict(re.findall(r"(\w+):\s*\"([^\"]+)\"", body))


def _engine_frameworks() -> set[str]:
    from otm_core_schema import StrideCategory
    from otm_framework_mappings import default_stride_registry

    registry = default_stride_registry()
    return {ref.framework for category in StrideCategory for ref in registry.refs_for_stride(category)}


def test_o_motor_emite_frameworks() -> None:
    """Sanidade: sem isto, o teste seguinte passaria por não haver nada para comparar."""
    frameworks = _engine_frameworks()

    assert len(frameworks) >= 4, f"apenas {frameworks}"


def test_cada_framework_emitido_tem_rotulo_na_ui() -> None:
    missing = sorted(_engine_frameworks() - set(_ui_labels()))

    assert not missing, f"frameworks sem rótulo (o utilizador vê o id cru): {missing}"


def test_a_ui_nao_carrega_rotulos_para_frameworks_que_ninguem_emite() -> None:
    """O outro lado da mesma deriva: um rótulo órfão é código morto que ninguém nota."""
    orphans = sorted(set(_ui_labels()) - _engine_frameworks())

    assert not orphans, f"rótulos sem framework correspondente: {orphans}"
