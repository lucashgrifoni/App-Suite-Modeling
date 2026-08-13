"""Document loading and user-friendly validation messages."""

from __future__ import annotations

from pathlib import Path

import yaml
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from pydantic import ValidationError


def load_doc(path: Path) -> ThreatModelDocument:
    """Load and validate against the canonical schema."""
    try:
        return load_document_from_yaml_path(path)
    except ValidationError:
        raise
    except yaml.YAMLError as e:
        raise RuntimeError(f"Invalid YAML in {path}:\n{e}") from e
    except ValueError as e:
        raise RuntimeError(str(e)) from e
    except OSError as e:
        raise RuntimeError(f"Could not read file: {path}\n{e}") from e


#: Cabeçalho por omissão — o caso original, um documento canónico.
_SCHEMA_HEADER = "The document is not valid for the canonical schema:"


def format_validation_error(err: ValidationError, *, header: str = _SCHEMA_HEADER) -> str:
    """One line per error with field location.

    `header` existe porque o mesmo formatador serve agora ficheiros que não são o documento
    canónico (um ficheiro de regras, por exemplo); só muda a frase de abertura, o corpo `• [campo]
    mensagem` é o mesmo em todo o CLI. Sem parâmetro, o texto é byte a byte o de antes.
    """
    lines = [header, ""]
    for e in err.errors():
        loc = " → ".join(str(x) for x in e.get("loc", ()))
        msg = e.get("msg", "")
        lines.append(f"  • [{loc}] {msg}")
    return "\n".join(lines)
