"""Use case: initialize an OTM file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otm_core_schema import BLANK_DOCUMENT_YAML
from otm_industry_packs.loader import load_template_info, load_template_yaml

from otm_cli.shared.emit import write_text_file
from otm_cli.shared.errors import CliUserError

INIT_TEMPLATE = BLANK_DOCUMENT_YAML


@dataclass
class InitResult:
    path: Path
    used_template: bool
    template_id: str | None
    suggested_pack: str | None
    message_key: str  # "template" | "blank"


def run_init(
    path: Path,
    *,
    force: bool,
    template: str | None,
) -> InitResult:
    if path.exists() and not force:
        raise CliUserError(
            exit_code=1,
            failed=f"file already exists: {path}",
            cause="without --force the file is not overwritten.",
            next_step="use --force or choose another path.",
        )
    if template:
        try:
            body = load_template_yaml(template)
        except FileNotFoundError as e:
            raise CliUserError(
                exit_code=1,
                failed=f"unknown template `{template}`.",
                cause="the template ID is not in the embedded catalog.",
                next_step="run `otm templates list`.",
            ) from e
        write_text_file(content=body, output=path)
        info = load_template_info(template)
        return InitResult(
            path=path,
            used_template=True,
            template_id=template,
            suggested_pack=info.suggested_pack if info else None,
            message_key="template",
        )
    write_text_file(content=INIT_TEMPLATE, output=path)
    return InitResult(
        path=path,
        used_template=False,
        template_id=None,
        suggested_pack=None,
        message_key="blank",
    )
