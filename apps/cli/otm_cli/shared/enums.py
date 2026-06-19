"""Enums shared by commands and application services."""

from __future__ import annotations

from enum import StrEnum


class BacklogFormat(StrEnum):
    markdown = "markdown"
    json = "json"


class DiffFormat(StrEnum):
    text = "text"
    json = "json"
    markdown = "markdown"


class ExportFormat(StrEnum):
    yaml = "yaml"
    json = "json"
    md = "md"
    otm = "otm"


class MethodologyOption(StrEnum):
    stride = "stride"
    linddun = "linddun"
    nist_data_centric = "nist_data_centric"
    octave_allegro = "octave_allegro"
    cia_die = "cia_die"
    pasta = "pasta"
    plot4ai = "plot4ai"
