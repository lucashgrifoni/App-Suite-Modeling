"""PDF a partir de HTML — dependência opcional `xhtml2pdf`."""

from __future__ import annotations

from io import BytesIO


def html_to_pdf_bytes(html: str) -> bytes:
    """
    Converte HTML em PDF.

    Raises:
        ImportError: se `xhtml2pdf` não estiver instalado.
        RuntimeError: se a geração falhar.
    """
    try:
        from xhtml2pdf import pisa
    except ImportError as e:
        raise ImportError(
            "PDF requer o pacote opcional: pip install 'open-threat-model[report]' "
            "ou pip install xhtml2pdf"
        ) from e

    out = BytesIO()
    enc = html.encode("utf-8")
    status = pisa.CreatePDF(enc, dest=out, encoding="utf-8")
    if status.err:
        raise RuntimeError("Falha ao gerar PDF (xhtml2pdf reportou erro).")
    return out.getvalue()
