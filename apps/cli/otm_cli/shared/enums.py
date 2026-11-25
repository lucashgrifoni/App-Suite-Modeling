"""Enums shared by commands and application services."""

from __future__ import annotations

from enum import StrEnum


class BacklogFormat(StrEnum):
    markdown = "markdown"
    json = "json"


class BacklogGroupBy(StrEnum):
    """`otm backlog --group-by`.

    Declared as a plain `str` before, so `--group-by categry` exited 0 and silently produced the
    default root-cause grouping — while `--format`, `--methodology` and `--level` all rejected an
    unknown value with exit 2. The renderer keys off these exact strings.
    """

    root_cause = "root-cause"
    control = "control"
    category = "category"


class DiffFormat(StrEnum):
    text = "text"
    json = "json"
    markdown = "markdown"


class ExportFormat(StrEnum):
    yaml = "yaml"
    json = "json"
    md = "md"
    otm = "otm"


class TemplateComplexity(StrEnum):
    """`otm templates list --complexity`.

    Declared as a plain `str` before, so `--complexity bogus` exited 0 after printing a bare
    catalog header — a user could not tell an unknown filter value from a catalog with no match.
    Same defect and same fix as `BacklogGroupBy`. The three members are the whole vocabulary the
    shipped template manifests use, and the help text already documented exactly these.
    """

    low = "low"
    medium = "medium"
    high = "high"


class MethodologyOption(StrEnum):
    stride = "stride"
    linddun = "linddun"
    nist_data_centric = "nist_data_centric"
    octave_allegro = "octave_allegro"
    cia_die = "cia_die"
    pasta = "pasta"
    plot4ai = "plot4ai"
