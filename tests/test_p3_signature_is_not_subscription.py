""""Assinatura" é assinatura criptográfica **e** subscrição comercial, e o gate lia só a segunda.

`entitlement_hint_markers` existe para exigir uma âncora comercial antes de sugerir controlos de
*entitlement* — não faz sentido recomendar gestão de plano pago a um modelo que não vende nada. A
lista incluía a palavra solta `"assinatura"`, que em português significa as duas coisas.

Medido no template `industry-transport-logistics` com o pack `transport` — o par que o próprio
`.meta.json` do template recomenda:

    REMOVIDO  Assinatura de mensagens de telemetria e relógio de confiança
    MANTIDO   Plano de continuidade para operações em tempo real

O controlo apagado é integridade de mensagens numa frota telemétrica, e desaparece exactamente do
modelo para que foi escrito. Em todo o conteúdo distribuído a palavra aparece uma única vez, e é no
sentido criptográfico: a marca solta não apanhava nenhum caso comercial verdadeiro e apanhava este
errado.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _kept_hints(template_id: str, pack_id: str) -> list[str]:
    import yaml
    from otm_core_schema import ThreatModelDocument
    from otm_industry_packs.loader import load_pack, load_template_yaml
    from otm_threat_engine.recommendation_gate import filter_pack_control_hints

    document = ThreatModelDocument.model_validate(yaml.safe_load(load_template_yaml(template_id)))
    return filter_pack_control_hints(document, list(load_pack(pack_id).control_hints))


def test_o_controlo_de_assinatura_de_mensagens_sobrevive() -> None:
    kept = _kept_hints("industry-transport-logistics", "transport")

    assert any("Assinatura de mensagens" in hint for hint in kept), (
        f"o controlo de integridade de mensagens foi removido do seu próprio template: {kept}"
    )


def test_um_controlo_de_subscricao_sem_ancora_comercial_continua_a_ser_removido() -> None:
    """A correcção não podia ser desligar o portão: é para isso que ele existe."""
    import yaml
    from otm_core_schema import ThreatModelDocument
    from otm_industry_packs.loader import load_template_yaml
    from otm_threat_engine.recommendation_gate import filter_pack_control_hints

    document = ThreatModelDocument.model_validate(
        yaml.safe_load(load_template_yaml("industry-transport-logistics"))
    )
    commercial = [
        "Gerir a assinatura do plano premium e os seus benefícios",
        "Controlar entitlement por plano contratado",
    ]

    assert filter_pack_control_hints(document, commercial) == []


def test_nenhum_hint_distribuido_e_removido_por_ambiguidade_da_palavra() -> None:
    """A varredura que justificou o desenho: a palavra aparece uma vez, no sentido criptográfico."""
    from otm_industry_packs.loader import list_pack_ids, load_pack

    signature_hints = [
        (pack_id, hint)
        for pack_id in list_pack_ids()
        for hint in load_pack(pack_id).control_hints
        if "assinatura" in hint.lower()
    ]

    assert signature_hints, "premissa: existe pelo menos um hint com a palavra"
    for pack_id, hint in signature_hints:
        assert "mensagens" in hint.lower() or "digital" in hint.lower(), (
            f"{pack_id} usa `assinatura` num sentido que este teste não previu: {hint}"
        )
