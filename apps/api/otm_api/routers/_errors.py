from __future__ import annotations

from typing import Any, cast

from fastapi import HTTPException, status
from otm_core_schema import ThreatModelDocument
from otm_industry_packs.loader import list_pack_ids
from otm_threat_engine import AnalysisResult
from pydantic import ValidationError as PydanticValidationError

from otm_api.api_error_messages import (
    msg_analysis_document_mismatch,
    msg_analysis_validation_error,
    msg_baseline_system_mismatch,
    msg_document_too_large,
    msg_document_validation_error,
    msg_pack_not_found,
    msg_template_invalid,
    msg_template_not_found,
)
from otm_api.document_limits import count_document_entities, resolve_max_document_entities
from otm_api.errors import _truncated_errors
from otm_api.services.analysis_pairing import analysis_document_mismatches, baseline_system_mismatches
from otm_api.services.documents import document_from_payload


def _pydantic_error_items(exc: PydanticValidationError) -> list[dict[str, Any]]:
    """
    Erros no formato esperado pela API, seguros para JSON.

    Com ``include_context=True`` (default), o Pydantic pode incluir em ``ctx``
    objetos ``Exception`` (ex.: ``ValueError`` em validação de referências de
    fluxos). Isso quebra ``JSONResponse`` do FastAPI com TypeError e aparece
    como 500 genérico no cliente.

    O campo ``input`` (e ``ctx``) é truncado com o mesmo limite das respostas
    422 de ``RequestValidationError`` (256 carateres): mantém a resposta
    delimitada perante payloads enormes e evita que estes erros de domínio
    ecoem conteúdo arbitrário não-delimitado de volta ao cliente.
    """
    items = cast(list[dict[str, Any]], exc.errors(include_context=False))
    return _truncated_errors(items)


def error_detail(
    *,
    code: str,
    message: str,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {"code": code, "message": message}
    if errors is not None:
        detail["errors"] = errors
    return detail


def raise_document_validation_error(exc: PydanticValidationError) -> HTTPException:
    """422 when the canonical document payload is invalid."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="DOCUMENT_VALIDATION_ERROR",
            message=msg_document_validation_error(),
            errors=_pydantic_error_items(exc),
        ),
    )


def raise_analysis_validation_error(exc: PydanticValidationError) -> HTTPException:
    """422 when `analysis` is not a valid AnalysisResult."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="ANALYSIS_VALIDATION_ERROR",
            message=msg_analysis_validation_error(),
            errors=_pydantic_error_items(exc),
        ),
    )


def ensure_analysis_matches_document(
    document: ThreatModelDocument,
    analysis: AnalysisResult,
    *,
    analysis_field: str = "analysis",
    document_field: str = "document",
) -> None:
    """
    422 quando o `analysis` recebido não foi produzido para o `document` recebido.

    Guarda, não conversor: as rotas que emparelham os dois artefactos chamam-na depois de
    validar cada um. Ver `services/analysis_pairing.py` para o critério e o âmbito.

    Os nomes dos campos são parâmetros porque `/v1/models/compare` recebe **dois** pares e
    tem de dizer qual deles está trocado.
    """
    mismatches = analysis_document_mismatches(
        document,
        analysis,
        analysis_field=analysis_field,
        document_field=document_field,
    )
    if not mismatches:
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="ANALYSIS_DOCUMENT_MISMATCH",
            message=msg_analysis_document_mismatch(analysis_field=analysis_field, document_field=document_field),
            errors=mismatches,
        ),
    )


def ensure_baseline_describes_same_system(
    current: AnalysisResult,
    baseline: AnalysisResult,
    *,
    baseline_field: str = "baseline_analysis",
) -> None:
    """
    422 quando o baseline recebido não é uma revisão anterior *deste* sistema.

    A guarda irmã de `ensure_analysis_matches_document`, e deliberadamente mais fraca: um
    baseline é de outra revisão por construção, por isso divergir é o produto do endpoint —
    o que não pode acontecer é o par descrever dois sistemas diferentes, porque então o
    `## Baseline / diff` do relatório é inventado. A CLI já recusava esse par
    (`analysis_match.require_baseline_describes_same_system`); a API devolvia 200.

    Ver `services/analysis_pairing.baseline_system_mismatches` para o critério.
    """
    mismatches = baseline_system_mismatches(current, baseline, baseline_field=baseline_field)
    if not mismatches:
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="BASELINE_SYSTEM_MISMATCH",
            message=msg_baseline_system_mismatch(baseline_field=baseline_field),
            errors=mismatches,
        ),
    )


def raise_pack_not_found(pack_id: str | None) -> HTTPException:
    """
    404 when the requested industry pack does not exist.

    Recebe o `pack_id` e não a `FileNotFoundError`: o texto do loader é uma frase em
    português fixo, e reemiti-la punha metade de uma resposta em inglês na outra língua
    (ver `api_error_messages.msg_pack_not_found`).
    """
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail(
            code="PACK_NOT_FOUND",
            message=msg_pack_not_found(pack_id=pack_id, accepted=", ".join(list_pack_ids())),
        ),
    )


def ensure_pack_exists(pack_id: str | None) -> None:
    """
    404 `PACK_NOT_FOUND` para um `pack_id` desconhecido, antes de qualquer trabalho.

    `/v1/models/compare` só resolvia o pack dentro do ramo `run_analysis`, por isso sem essa
    flag um id com uma gralha era aceite com 200 — inerte e silencioso — enquanto todas as
    rotas irmãs davam 404 para o mesmo valor. O `is not None` acompanha `services.analysis`:
    `pack_id: ""` é uma escolha falhada do chamador, não "sem pack".
    """
    if pack_id is None:
        return
    if pack_id not in list_pack_ids():
        raise raise_pack_not_found(pack_id)


def raise_template_not_found(template_id: str) -> HTTPException:
    """404 when the template does not exist in the embedded catalog."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail(
            code="TEMPLATE_NOT_FOUND",
            message=msg_template_not_found(template_id=template_id),
        ),
    )


def raise_template_invalid(exc: PydanticValidationError) -> HTTPException:
    """422 when template YAML does not yield a valid canonical document."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="TEMPLATE_INVALID",
            message=msg_template_invalid(),
            errors=_pydantic_error_items(exc),
        ),
    )


def raise_document_too_large(*, entities: int, ceiling: int) -> HTTPException:
    """413 quando o documento excede o tecto de entidades que o operador configurou."""
    return HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail=error_detail(
            code="DOCUMENT_TOO_LARGE",
            message=msg_document_too_large(entities=entities, ceiling=ceiling),
        ),
    )


def document_from_payload_or_422(data: dict[str, Any]) -> ThreatModelDocument:
    """
    O funil por onde passam todas as rotas que recebem um documento — e por isso o sítio onde
    o tecto opcional de entidades é aplicado, antes de o motor correr e antes de a resposta
    ser construída. Ver `otm_api.document_limits`.
    """
    try:
        document = document_from_payload(data)
    except PydanticValidationError as e:
        raise raise_document_validation_error(e) from e
    ceiling = resolve_max_document_entities()
    entities = count_document_entities(document)
    if ceiling is not None and entities > ceiling:
        raise raise_document_too_large(entities=entities, ceiling=ceiling)
    return document


def analysis_from_payload_or_422(data: dict[str, Any] | None) -> AnalysisResult | None:
    """`AnalysisResult` validado, ou `None` quando o campo foi omitido."""
    if data is None:
        return None
    try:
        return AnalysisResult.model_validate(data)
    except PydanticValidationError as e:
        raise raise_analysis_validation_error(e) from e
