""" "Assinatura" é assinatura criptográfica **e** subscrição comercial — outra vez, noutro sítio.

`recommendation_gate` já tinha tirado a palavra solta da sua lista de marcas comerciais, pela mesma
razão e com o mesmo raciocínio (ver `tests/test_p3_signature_is_not_subscription.py`).
`business_abuse_context` ficou com ela:

    entitlement_asset = first_asset_id_with(doc, "entitlement", "premium", "subscription", "assinatura")

Num modelo de plataforma de contratos com dois ativos — `Assinatura digital dos contratos`
(credencial) e `Plano pago do cliente (subscription)` — o primeiro ganha, porque `first_...` devolve
o primeiro que casar. A ameaça CRÍTICA de fraude económica `biz_payment_entitlement_mismatch`
(L4×I5 = 20) sai então apontada ao certificado de assinatura, e o plano pago — o ativo que a ameaça
descreve — fica sem ninguém a apontar-lhe.

Contrafactual medido, com o id do ativo constante e só o nome a mudar:

    "Assinatura digital dos contratos"   -> entitlement_asset = doc_sig
    "Certificado digital dos contratos"  -> entitlement_asset = plano_pago

As formas que ficam na lista nomeiam a subscrição sem ambiguidade, exactamente como no gate.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_SIGNATURE_ASSET = "doc_sig"
_PAID_PLAN_ASSET = "plano_pago"


def _document(first_asset_name: str) -> Any:
    from otm_core_schema import ThreatModelDocument

    return ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0", "system_type": "web_application", "industry_sector": "saas"},
            "metadata": {"title": "Plataforma de contratos"},
            "components": [
                {"id": "checkout", "name": "Checkout", "kind": "process"},
                {"id": "entitlement_svc", "name": "Entitlement service", "kind": "process"},
            ],
            "assets": [
                {"id": _SIGNATURE_ASSET, "name": first_asset_name, "asset_kind": "credential"},
                {
                    "id": _PAID_PLAN_ASSET,
                    "name": "Plano pago do cliente (subscription)",
                    "asset_kind": "financial_record",
                },
            ],
        }
    )


def _entitlement_asset(first_asset_name: str) -> str | None:
    from otm_threat_engine.business_abuse_context import build_business_abuse_context

    return build_business_abuse_context(_document(first_asset_name)).entitlement_asset


def test_o_contrafactual_isola_o_nome_do_ativo() -> None:
    """Premissa: com um nome sem ambiguidade, o ativo certo é escolhido."""
    assert _entitlement_asset("Certificado digital dos contratos") == _PAID_PLAN_ASSET


def test_a_assinatura_criptografica_nao_e_o_plano_pago() -> None:
    assert _entitlement_asset("Assinatura digital dos contratos") == _PAID_PLAN_ASSET


def test_a_subscricao_nomeada_sem_ambiguidade_continua_a_contar() -> None:
    """Apertar não pode calar o caso comercial verdadeiro."""
    for name in ("Assinatura do plano mensal", "Plano de assinatura premium", "Assinatura paga"):
        assert _entitlement_asset(name) == _SIGNATURE_ASSET, f"deixou de reconhecer: {name}"


def test_a_ameaca_de_fraude_economica_aponta_ao_ativo_certo() -> None:
    """O que o utilizador vê: a ameaça crítica na saída do `otm analyze`."""
    from otm_threat_engine import analyze_document

    threats = {
        h.id: h
        for h in analyze_document(_document("Assinatura digital dos contratos")).heuristic_threats
        if not h.skipped_as_duplicate
    }
    mismatch = threats.get("biz_payment_entitlement_mismatch")

    assert mismatch is not None, f"a ameaça deixou de ser emitida: {sorted(threats)}"
    assert mismatch.target_asset_id == _PAID_PLAN_ASSET, (
        f"a fraude económica aponta a {mismatch.target_asset_id}, não ao plano pago"
    )
