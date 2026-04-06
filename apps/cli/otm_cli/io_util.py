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


def format_validation_error(err: ValidationError) -> str:
    """One line per error with field location."""
    lines = ["The document is not valid for the canonical schema:", ""]
    for e in err.errors():
        loc = " → ".join(str(x) for x in e.get("loc", ()))
        msg = e.get("msg", "")
        lines.append(f"  • [{loc}] {msg}")
    return "\n".join(lines)
