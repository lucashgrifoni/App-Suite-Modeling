"""PDF a partir de HTML — dependência opcional `xhtml2pdf`."""

from __future__ import annotations

from io import BytesIO


class PdfSupportUnavailable(ImportError):
    """O motor de PDF não pode ser usado neste ambiente.

    Deriva de `ImportError` de propósito: quem chama já encaminha `ImportError` para a resposta
    desenhada para "dependência opcional em falta" — o erro de três linhas na CLI, o 501 na API —
    e uma biblioteca nativa que não carrega é a mesma resposta com outro remédio. Só o remédio
    muda, por isso viaja na exceção em vez de ser reescrito em cada camada.

    Existia apenas o ramo `except ImportError` à volta do `import`, e `pip install
    "open-threat-model[report]"` traz `xhtml2pdf -> svglib -> rlPyCairo -> cairocffi`, que procura
    um `libcairo-2.dll` que o Windows não inclui. O `OSError` do `cairocffi` escapava aos dois
    handlers e o utilizador recebia um traceback completo em vez do erro desenhado, num comando
    documentado (`docs/features/PREMIUM_REPORTS.md`).
    """

    def __init__(self, *, cause: str, next_step: str) -> None:
        super().__init__(f"{cause} {next_step}")
        self.cause = cause
        self.next_step = next_step


def _package_missing() -> PdfSupportUnavailable:
    return PdfSupportUnavailable(
        cause="the optional `xhtml2pdf` package is not installed.",
        next_step='install the extra: `pip install "open-threat-model[report]"`.',
    )


def _native_library_missing(error: OSError) -> PdfSupportUnavailable:
    return PdfSupportUnavailable(
        cause=(
            "the PDF engine is installed but its native Cairo library cannot be loaded "
            f"({type(error).__name__}: {str(error).splitlines()[0] if str(error) else 'no detail'})."
        ),
        next_step=(
            "install Cairo for this platform (Windows: the GTK runtime, which provides "
            "`libcairo-2.dll`; Debian/Ubuntu: `libcairo2`; macOS: `brew install cairo`), "
            "or export the report with `--format markdown`."
        ),
    )


def _embedded_resources_only(uri: str, rel: str) -> str:
    """Resolve recursos `data:` e recusa os externos — **parcialmente**. Leia o alcance real.

    O renderer produz HTML auto-contido: CSS inline, logo como `data:` URI. Nada externo deveria
    ser buscado, por isso não há caso legítimo que esta política possa quebrar.

    **Isto não é a defesa contra o SSRF, e não deve ser tratado como tal.** Medido contra o
    xhtml2pdf instalado, com este callback ativo e um servidor de sonda local:

        <img src="http://…">              BUSCADO À MESMA   (3 tentativas, via `NetworkFileUri`)
        <link rel="stylesheet" href=…>    BUSCADO À MESMA
        @import url(…)                    BUSCADO À MESMA
        css url(…) em background          bloqueado

    Uma em quatro. O callback é ignorado precisamente na construção que o ataque usava. Fica
    porque bloquear uma é melhor que bloquear nenhuma e não custa nada — não porque feche o
    caminho.

    **A defesa é `pdf_text._MARKUP_CHARS`**, que impede o fold de materializar um `<` e portanto
    impede a tag de existir. Se aquilo regredir, isto não segura: reproduzido removendo a guarda
    do fold e observando o processo a ir buscar a sonda (na verdade, a estoirar com segmentation
    fault a meio). Não invente aqui uma segunda linha de defesa que a medição não sustenta.

    O teste `test_the_link_callback_scope_is_what_we_measured` fixa a tabela acima, para que uma
    versão futura do xhtml2pdf que passe a honrar o callback nos avise em vez de nos deixar com
    um comentário desatualizado.

    Devolver `""` faz o xhtml2pdf saltar o recurso e continuar (`err=0`); não aborta o relatório.
    """
    if uri.startswith("data:"):
        return uri
    return ""


def html_to_pdf_bytes(html: str) -> bytes:
    """
    Converte HTML em PDF.

    Raises:
        PdfSupportUnavailable: se `xhtml2pdf` não estiver instalado ou não conseguir carregar as
            suas bibliotecas nativas. É um `ImportError`, por isso os handlers existentes servem.
        RuntimeError: se a geração falhar.
    """
    try:
        from xhtml2pdf import pisa
    except ImportError as e:
        raise _package_missing() from e
    except OSError as e:
        # `cairocffi` levanta `OSError` — não `ImportError` — quando o DLL/so nativo não existe.
        raise _native_library_missing(e) from e

    out = BytesIO()
    enc = html.encode("utf-8")
    status = pisa.CreatePDF(enc, dest=out, encoding="utf-8", link_callback=_embedded_resources_only)
    if status.err:
        raise RuntimeError("PDF generation failed (xhtml2pdf reported an error).")  # noqa: E501  # pragma: no cover - defensive: xhtml2pdf error path
    return out.getvalue()
