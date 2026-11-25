"""Carregamento de um ficheiro de regras personalizadas.

O ficheiro vem de fora do projecto — do repositório de quem adopta a ferramenta — por isso é
tratado como entrada não confiável: `safe_load` (nunca `load`), limite de tamanho antes de
parsear, e validação completa pelo modelo antes de qualquer regra tocar no motor.

Erros são `ValueError` com texto accionável. Quem traduz para código de saída é o CLI, tal
como já acontece no bridge OTM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from otm_core_schema.io import safe_load_bounded

from otm_threat_engine.custom_rules.models import CustomRuleSet

#: Um ficheiro de regras legítimo tem alguns KB. O limite existe para que um ficheiro
#: gigante seja rejeitado antes de o parser de YAML gastar memória com ele.
MAX_RULES_FILE_BYTES = 512 * 1024


def load_custom_rules(path: str | Path) -> CustomRuleSet:
    """Lê, valida e devolve o conjunto de regras de `path`."""
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"rules file not found: {p}")

    size = p.stat().st_size
    if size > MAX_RULES_FILE_BYTES:
        raise ValueError(f"rules file is {size} bytes; the limit is {MAX_RULES_FILE_BYTES}.")

    try:
        # `safe_load_bounded`, não `yaml.safe_load`: o segundo impede tipos Python arbitrários mas
        # não limita expansão de aliases nem profundidade de aninhamento. Um ficheiro de regras de
        # 4 KB esgotava a pilha e saía como `RecursionError` cru — que não é `ValueError`, logo
        # escapava ao contrato que esta função declara e que o CLI traduz para `CliUserError`.
        # É o mesmo defeito que o documento canónico teve, e usa o mesmo tecto: o ficheiro de
        # regras é entrada não confiável exatamente como o modelo.
        raw: Any = safe_load_bounded(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"rules file is not valid YAML: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(f"rules file is not valid UTF-8: {exc}") from exc
    except RecursionError as exc:
        # Defesa em profundidade, pelo mesmo motivo que em `_yamljson.load_object_from_text`.
        raise ValueError("rules file is too deeply nested to parse.") from exc

    if raw is None:
        raise ValueError("rules file is empty.")
    if not isinstance(raw, dict):
        # Rejeitar em vez de coagir. Coagir importaria um ficheiro malformado como um
        # conjunto vazio de regras, que é silenciosamente pior do que falhar.
        raise ValueError(f"rules file must be a mapping at the top level, got {type(raw).__name__}.")

    return CustomRuleSet.model_validate(raw)
