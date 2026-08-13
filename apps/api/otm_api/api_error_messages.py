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


def msg_import_empty_artifact() -> str:
    return _t(
        "The uploaded artifact is empty. Send the file contents, not a zero-byte file.",
        "O artefacto enviado está vazio. Envie o conteúdo do ficheiro, não um ficheiro de zero bytes.",
    )


def msg_remediation_group_by_invalid(*, value: str, accepted: str) -> str:
    return _t(
        f"`group_by={value!r}` is not a known grouping. Accepted values: {accepted}.",
        f"`group_by={value!r}` não é um agrupamento conhecido. Valores aceites: {accepted}.",
    )


def msg_import_too_large(*, limit_mib: int) -> str:
    """O limite vem do chamador para não haver duas fontes de verdade para o mesmo número."""
    return _t(
        f"The artifact is larger than the {limit_mib} MiB upload limit. Split it, or import the "
        "directory with the CLI (`otm import`).",
        f"O artefacto é maior do que o limite de {limit_mib} MiB por upload. Divida-o, ou importe "
        "a pasta com o CLI (`otm import`).",
    )


def msg_import_not_utf8() -> str:
    return _t(
        "The artifact is not valid UTF-8 text. Re-save it as UTF-8; this endpoint takes text, not binaries.",
        "O artefacto não é texto UTF-8 válido. Grave-o como UTF-8; este endpoint recebe texto, não binários.",
    )


def msg_api_key_required() -> str:
    return _t(
        "Invalid or missing API key. Send X-OTM-API-Key or Authorization: Bearer.",
        "Chave de API ausente ou inválida. Envie X-OTM-API-Key ou Authorization: Bearer.",
    )


def msg_api_key_misconfigured() -> str:
    return _t(
        "OTM_API_KEY is set but blank, so no credential can be accepted. "
        "Set a non-empty value on the server, or unset it to serve /v1 without a key.",
        "OTM_API_KEY está definida mas em branco, por isso nenhuma credencial pode ser aceite. "
        "Defina um valor não vazio no servidor, ou remova a variável para servir /v1 sem chave.",
    )


def msg_analysis_document_mismatch(*, analysis_field: str = "analysis", document_field: str = "document") -> str:
    """
    Os nomes dos campos são parâmetros porque o mesmo erro aparece em rotas onde o par não se
    chama `document`/`analysis`: em `/v1/models/compare` são `baseline`/`baseline_analysis` e
    `revised`/`revised_analysis`. Dizer "analysis" numa resposta a um pedido que não tem esse
    campo manda o cliente procurar o problema no sítio errado.
    """
    return _t(
        f"The supplied `{analysis_field}` was not produced for the supplied `{document_field}`. "
        f"Re-run the analysis for this document, or omit `{analysis_field}` and set `run_analysis: true`.",
        f"O `{analysis_field}` enviado não foi produzido para o `{document_field}` enviado. "
        f"Volte a correr a análise para este documento, ou omita `{analysis_field}` e defina "
        "`run_analysis: true`.",
    )


def msg_pack_not_found(*, pack_id: str | None, accepted: str) -> str:
    """
    A lista de packs válidos faz parte da mensagem: é o que a torna acionável.

    Antes, a resposta era o texto da `FileNotFoundError` do loader — uma frase em português
    fixo, dentro de uma resposta que o resto do envelope já tinha traduzido para inglês.

    `pack_id` acompanha o tipo do campo do pedido (`str | None`). Só o loader levanta o erro
    que traz aqui, e ele só corre quando o campo veio preenchido, mas repetir a garantia com
    um `assert` seria uma linha que nenhum teste pode alcançar.
    """
    return _t(
        f"Unknown pack: {pack_id!r}. Accepted values: {accepted}.",
        f"Pack desconhecido: {pack_id!r}. Valores aceites: {accepted}.",
    )


def msg_template_not_found(*, template_id: str) -> str:
    return _t(
        f"Unknown template: {template_id!r}. List the built-in catalog with GET /v1/templates.",
        f"Template desconhecido: {template_id!r}. Consulte o catálogo embutido em GET /v1/templates.",
    )


def msg_import_artifact_invalid(*, parser_detail: str | None) -> str:
    """
    Enquadramento traduzido para um artefacto ilegível, com o detalhe do parser preservado.

    O texto vinha do importador (`otm_artifact_import`), que escreve em português fixo, e
    saía tal e qual numa resposta em inglês. O que a API sabe sem depender da redação desse
    pacote é estrutural: houve, ou não, um erro de parser encadeado (`__cause__`). A
    localização que o PyYAML dá — "line 3, column 5" — é o valor da mensagem para quem tem
    de corrigir o ficheiro, por isso segue como cauda técnica em vez de ser descartada.
    """
    head = _t(
        "The artifact is not a YAML or JSON object (a mapping) this importer can read.",
        "O artefacto não é um objecto YAML ou JSON (mapping) que este importador consiga ler.",
    )
    if not parser_detail:
        return head
    tail = _t("Parser reported: ", "O parser indicou: ")
    return f"{head} {tail}{parser_detail}"


def msg_remediation_input() -> str:
    return _t(
        "Provide `analysis` or set `run_analysis: true`.",
        "Forneça `analysis` ou defina `run_analysis: true`.",
    )
