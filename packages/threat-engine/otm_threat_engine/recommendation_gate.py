"""
Filtra `control_hints` de packs para evitar recomendações fora do domínio do modelo.

Heurística por palavras-chave, âncoras no texto agregado e tipos de ativo.
"""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument
from otm_core_schema.enums import AssetKind

#: Campo booleano do modelo → a palavra que o mesmo facto teria em prosa.
#:
#: As âncoras abaixo são lexicais, e o corpus lia apenas texto livre: metadados, componentes e
#: ativos. Um modelo que declara a sua natureza em campos estruturados — `privilege_level: admin`,
#: `supports_file_upload: true` — não tinha âncora nenhuma, e o filtro descartava exactamente os
#: controlos que esse modelo precisava. Traduzir o campo para a palavra correspondente mantém o
#: heurístico como está e deixa-o ver o que já estava declarado.
_STRUCTURED_COMPONENT_SIGNALS: tuple[tuple[str, str], ...] = (("supports_admin_operations", "admin"),)
_STRUCTURED_FLOW_SIGNALS: tuple[tuple[str, str], ...] = (("supports_file_upload", "upload"),)


def _corpus(doc: ThreatModelDocument) -> str:
    parts = [doc.metadata.title, doc.metadata.summary or ""]
    for c in doc.components:
        parts.append(f"{c.id} {c.name} {c.description or ''} {c.responsibility or ''} {c.technology or ''}")
        parts.append(c.privilege_level or "")
        parts.extend(word for field, word in _STRUCTURED_COMPONENT_SIGNALS if getattr(c, field) is True)
    for f in doc.data_flows:
        parts.append(f"{f.id} {f.name or ''} {f.description or ''}")
        parts.extend(word for field, word in _STRUCTURED_FLOW_SIGNALS if getattr(f, field) is True)
    for a in doc.assets:
        parts.append(f"{a.name} {a.asset_kind.value} {a.description or ''}")
    return " ".join(parts).lower()


def _has_payment_anchor(doc: ThreatModelDocument) -> bool:
    """Pagamento/checkout só é âncora válida com texto ou ativo/componente explícito."""
    corpus = _corpus(doc)
    if any(
        t in corpus
        for t in (
            "payment",
            "pagamento",
            "checkout",
            "psp",
            "billing",
            "cartão",
            "cartao",
            "card ",
            "transação",
            "transacao",
        )
    ):
        return True
    for a in doc.assets:
        if a.asset_kind == AssetKind.FINANCIAL_RECORD:
            return True
    for c in doc.components:
        cid = f"{c.id} {c.name}".lower()
        if any(t in cid for t in ("payment", "pay", "pagamento", "checkout", "psp")):
            return True
    return False


def _has_upload_anchor(doc: ThreatModelDocument) -> bool:
    corpus = _corpus(doc)
    upload_tokens = ("upload", "ficheiro", "arquivo", "malware", "blob", "s3", "storage", "quarantine")
    if any(t in corpus for t in upload_tokens):
        return True
    return any(a.asset_kind == AssetKind.UPLOADED_CONTENT for a in doc.assets)


def _has_admin_anchor(doc: ThreatModelDocument) -> bool:
    corpus = _corpus(doc)
    admin_tokens = ("admin", "privileg", "backoffice", "portal admin", "auditoria", "audit")
    if any(t in corpus for t in admin_tokens):
        return True
    return any(a.asset_kind == AssetKind.ADMIN_CAPABILITY for a in doc.assets)


def _has_entitlement_commercial_anchor(doc: ThreatModelDocument) -> bool:
    """
    Plano/entitlement/benefício comercial exigem sinal no modelo (texto ou âncora de pagamento).
    Evita hints de catálogo/pricing sem componente de negócio correspondente.
    """
    if _has_payment_anchor(doc):
        return True
    corpus = _corpus(doc)
    return any(
        t in corpus
        for t in (
            "subscription",
            "assinatura",
            "entitlement",
            "premium",
            "benefício",
            "beneficio",
            "plano",
            "pricing",
            "tier",
            "catalog",
            "upsell",
            "sku",
            "licença",
            "licenca",
            "comercial",
            "billing",
        )
    )


def filter_pack_control_hints(doc: ThreatModelDocument, hints: list[str]) -> list[str]:
    """Remove hints cuja âncora semântica não existe no modelo."""
    if not hints:
        return []
    out: list[str] = []

    payment_tokens = ("payment", "pagamento", "checkout", "cartão", "cartao", "billing", "psp", "transação")
    admin_tokens = ("admin", "privileg", "backoffice")
    upload_tokens = ("upload", "ficheiro", "arquivo", "malware")

    pay_ok = _has_payment_anchor(doc)
    admin_ok = _has_admin_anchor(doc)
    upload_ok = _has_upload_anchor(doc)
    entitlement_ok = _has_entitlement_commercial_anchor(doc)

    entitlement_hint_markers = (
        "entitlement",
        "subscription",
        "assinatura",
        "premium",
        "benefício",
        "beneficio",
        "upsell",
        "plano contratado",
        "pricing tier",
        "license tier",
        "catálogo comercial",
        "catalogo comercial",
    )

    for h in hints:
        low = h.lower()
        if any(t in low for t in payment_tokens) and not pay_ok:
            continue
        if any(t in low for t in admin_tokens) and not admin_ok:
            continue
        if any(t in low for t in upload_tokens) and not upload_ok:
            continue
        if any(m in low for m in entitlement_hint_markers) and not entitlement_ok:
            continue
        out.append(h)
    return out
