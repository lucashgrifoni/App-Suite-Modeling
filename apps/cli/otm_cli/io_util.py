"""Document loading and user-friendly validation messages."""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path

import yaml
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from pydantic import ValidationError


def refuse_character_device(path: Path) -> None:
    """Refuse a path that names a character device instead of a file.

    `otm validate CON` never returned. On Windows the reserved names (`CON`, `NUL`, `COM1`, …)
    resolve to a device, and opening `CON` for reading blocks on console input forever — the
    process had to be killed, and in CI that holds a runner until the job-level timeout, which is
    a worse failure mode than any error. Every read command that takes a path was affected
    (`analyze`, `precheck`, `export`, `diagram`, `diff`, `explain`).

    Only character devices are refused, deliberately. Regular files and FIFOs stay accepted, so
    `cat model.yaml | otm validate /dev/stdin` still works; what goes is the class of paths that
    can never hold a document and can block instead of answering.

    Raises `OSError` rather than a CLI error so that every caller keeps turning it into its own
    already-shaped message, with no new error vocabulary anywhere.
    """
    try:
        mode = os.stat(path).st_mode
    except OSError:
        return  # unreadable or absent: the caller's own open() reports that, with its own wording
    if stat.S_ISCHR(mode):
        raise OSError(errno.EINVAL, "not a document: this path is a character device, not a file", str(path))


def load_doc(path: Path) -> ThreatModelDocument:
    """Load and validate against the canonical schema."""
    try:
        refuse_character_device(path)
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
