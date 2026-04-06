"""Mensagens user-facing por código de erro e locale (``get_api_error_locale``)."""

from __future__ import annotations

from otm_api.error_locale import get_api_error_locale


def _t(en: str, pt_br: str) -> str:
    return pt_br if get_api_error_locale() == "pt-BR" else en


def msg_document_validation_error() -> str:
    return _t(
        "The document does not satisfy the canonical schema.",
        "O documento não satisfaz o schema canónico.",
    )


def msg_analysis_validation_error() -> str:
    return _t(
        "The analysis field is not a valid AnalysisResult.",
        "O campo analysis não é um AnalysisResult válido.",
    )


def msg_template_invalid() -> str:
    return _t(
        "The template does not produce a valid canonical document.",
        "O template não produz um documento canónico válido.",
    )


def msg_request_validation_error() -> str:
    return _t(
        "Invalid request body or parameters.",
        "Corpo do pedido ou parâmetros inválidos.",
    )


def msg_internal_error() -> str:
    return _t(
        "An unexpected error occurred.",
        "Ocorreu um erro inesperado.",
    )


def msg_remediation_input() -> str:
    return _t(
        "Provide `analysis` or set `run_analysis: true`.",
        "Forneça `analysis` ou defina `run_analysis: true`.",
    )
