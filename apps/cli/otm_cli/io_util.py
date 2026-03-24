"""Carregamento de documentos e mensagens de erro amigáveis."""

from __future__ import annotations

from pathlib import Path

import yaml
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from pydantic import ValidationError


def load_doc(path: Path) -> ThreatModelDocument:
    """Carrega e valida o schema canônico."""
    try:
        return load_document_from_yaml_path(path)
    except ValidationError:
        raise
    except yaml.YAMLError as e:
        raise RuntimeError(f"YAML inválido em {path}:\n{e}") from e
    except ValueError as e:
        raise RuntimeError(str(e)) from e
    except OSError as e:
        raise RuntimeError(f"Não foi possível ler o arquivo: {path}\n{e}") from e


def format_validation_error(err: ValidationError) -> str:
    """Uma linha por erro, com localização."""
    lines = ["O documento não é válido para o schema canônico:", ""]
    for e in err.errors():
        loc = " → ".join(str(x) for x in e.get("loc", ()))
        msg = e.get("msg", "")
        lines.append(f"  • [{loc}] {msg}")
    return "\n".join(lines)
