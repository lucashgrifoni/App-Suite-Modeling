"""O seletor de tipo de sistema tem de oferecer todos os valores que o schema aceita.

`SYSTEM_TYPES` (`apps/web/src/types/document.ts`) é a única origem do `<select>` do wizard, e é
mantido à mão numa linguagem enquanto a verdade — `SystemType` — vive noutra. Faltavam três:
`batch_data_pipeline`, `desktop` e `iot_system`.

O efeito não é uma opção em falta, é uma afirmação errada. Um `<select>` de tamanho 1 cujo `value`
não casa com nenhuma `<option>` selecciona a primeira: o ecrã diz **"Aplicação web"** para os
templates `data-pipeline-etl`, `ai-inference-pipeline`, `batch-scheduled-jobs` (todos
`batch_data_pipeline`) e `industry-transport-logistics` (`iot_system`). E como o `onChange` escreve
o valor do controlo no documento canónico, mexer nele grava `web_application` por cima do que o
template trazia.

`system_type` pontua na recomendação de metodologia. Medido no `data-pipeline-etl` distribuído:
`nist_data_centric` a 83.0 pts com confiança alta; reescrito para `web_application`, `linddun` a
35.0 pts com confiança média. Um clique no controlo que já mostrava a opção errada muda a
metodologia recomendada.

Os rótulos i18n são parte do contrato: sem entrada em `document.systemTypes`, a `<option>` mostra
a chave de tradução em bruto.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_TYPES_TS = _ROOT / "apps" / "web" / "src" / "types" / "document.ts"
_LOCALES = _ROOT / "apps" / "web" / "src" / "i18n" / "locales"

sys.path.insert(0, str(_ROOT / "packages" / "core-schema"))


def _schema_system_types() -> set[str]:
    from otm_core_schema.enums import SystemType

    return {member.value for member in SystemType}


def _ui_system_types() -> list[str]:
    text = _TYPES_TS.read_text(encoding="utf-8")
    start = text.index("export const SYSTEM_TYPES")
    body = text[start : text.index("] as const;", start)]
    return re.findall(r'value:\s*"([^"]+)"', body)


def test_o_seletor_oferece_todos_os_valores_do_schema() -> None:
    missing = sorted(_schema_system_types() - set(_ui_system_types()))

    assert not missing, (
        f"valores de `SystemType` que o wizard não consegue exprimir: {missing}. "
        "Um `<select>` cujo value não casa com nenhuma option mostra a primeira, "
        "e o onChange grava-a por cima do documento."
    )


def test_o_seletor_nao_oferece_valores_que_o_schema_recusa() -> None:
    invented = sorted(set(_ui_system_types()) - _schema_system_types())

    assert not invented, f"valores oferecidos pelo wizard e recusados pelo schema: {invented}"


@pytest.mark.parametrize("locale", ["en", "pt-BR"])
def test_cada_valor_tem_rotulo_em_cada_locale(locale: str) -> None:
    labels = json.loads((_LOCALES / f"{locale}.json").read_text(encoding="utf-8"))["document"]["systemTypes"]
    missing = sorted(set(_ui_system_types()) - set(labels))

    assert not missing, f"{locale}.json não tem rótulo para {missing}; a option mostraria a chave crua"
