"""A banda de severidade de uma ameaça declarada tem de vir da mesma leitura que a capa usa.

O `builder` escreve a invariante em código, em `_build_report`:

    "As três leituras da mesma página têm de concordar."

Não concordavam para uma ameaça **declarada**. O estado geral e a urgência liam
`likelihood × impact` (`_overall_max_score`), o quadro de severidade e o mapa STRIDE liam
`risk.score or likelihood × impact`. Quando os dois números discordam, a mesma ameaça sai
classificada de duas maneiras na mesma página:

    L5×I5 com score 9.8   ->  "Requer atenção imediata"  ao lado de  `| medium | 1 |`
    L1×I1 com score 25.0  ->  "Aceitável com acompanhamento"  ao lado de  `| critical | 1 |`

Não é um empate de opinião. `severity.py` — que o seu próprio docstring declara "fonte única de
verdade" — define o domínio da banda como *"o score L×I (1–25)"*, e os limiares 20/12/6 estão
nessa escala. No esquema, `likelihood` e `impact` são obrigatórios e validados em 1–5; `score` é
opcional e a sua descrição admite outra escala — *"Ex.: L×I ou normalizado"*. Um valor CVSS
(0–10) escrito em `score` é legítimo à luz do esquema e destrói a banda.

Por isso a leitura autoritativa de uma ameaça declarada é `likelihood × impact`. Para as
heurísticas nada muda: `build_risk_assessment` grava `score = float(L × I)`.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings", "exporters", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _payload(risk: dict[str, Any] | None) -> Any:
    from otm_core_schema import ThreatModelDocument
    from otm_report_premium import ReportLevel, build_premium_report_payload
    from otm_threat_engine import analyze_document

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0", "system_type": "web_application", "industry_sector": "saas"},
            "metadata": {"title": "Fila"},
            "components": [{"id": "q1", "name": "Fila de eventos", "kind": "queue"}],
            "threats": (
                []
                if risk is None
                else [
                    {
                        "id": "t_dec",
                        "title": "Ameaça declarada pelo modelador",
                        "stride": "spoofing",
                        "target_component_id": "q1",
                        "risk": risk,
                    }
                ]
            ),
        }
    )
    return build_premium_report_payload(document, analyze_document(document), level=ReportLevel.DEEP)


def _bands_of_the_declared_threat(risk: dict[str, Any]) -> tuple[str, dict[str, int], dict[str, int]]:
    """Estado da capa, e o que a ameaça declarada **acrescenta** ao quadro e ao mapa.

    O mesmo componente também gera heurísticas, por isso ler o quadro em bruto mediria as duas
    origens ao mesmo tempo. A diferença contra o mesmo documento sem a ameaça declarada isola a
    contribuição dela — e, se declarar a ameaça apagasse uma linha em vez de a mover, a subtracção
    no outro sentido apanhava isso também.
    """
    base, with_declared = _payload(None), _payload(risk)
    added_severity = Counter(with_declared.executive_summary.severity_distribution) - Counter(
        base.executive_summary.severity_distribution
    )
    removed_severity = Counter(base.executive_summary.severity_distribution) - Counter(
        with_declared.executive_summary.severity_distribution
    )
    assert not removed_severity, f"declarar a ameaça retirou linhas do quadro: {dict(removed_severity)}"

    heat_key = "spoofing"
    added_heat = Counter(with_declared.distributions.heatmap_stride_severity.get(heat_key, {})) - Counter(
        base.distributions.heatmap_stride_severity.get(heat_key, {})
    )
    return with_declared.cover.overall_status, dict(added_severity), dict(added_heat)


def test_o_score_das_heuristicas_e_o_produto_por_construcao() -> None:
    """Premissa: mudar a leitura não mexe em nada que o motor produza."""
    from otm_threat_engine.risk_calc import build_risk_assessment

    for likelihood in range(1, 6):
        for impact in range(1, 6):
            risk = build_risk_assessment(likelihood, impact)
            assert risk.score == float(likelihood * impact)


def test_um_score_fora_de_escala_nao_rebaixa_a_banda() -> None:
    """CVSS 9.8 gravado em `score` sobre L5×I5: a capa diz crítico, o quadro dizia `medium`."""
    status, severity, heat = _bands_of_the_declared_threat({"likelihood": 5, "impact": 5, "score": 9.8})

    assert status == "requires_immediate_attention"
    assert severity == {"critical": 1}, f"quadro de severidade discorda da capa: {severity}"
    assert heat == {"critical": 1}, f"mapa STRIDE discorda da capa: {heat}"


def test_um_score_fora_de_escala_nao_promove_a_banda() -> None:
    """O sentido inverso: score 25 com L1×I1 dava `critical` numa página que diz aceitável."""
    status, severity, heat = _bands_of_the_declared_threat({"likelihood": 1, "impact": 1, "score": 25.0})

    assert status == "acceptable_with_follow_up"
    assert severity == {"low": 1}, f"quadro de severidade discorda da capa: {severity}"
    assert heat == {"low": 1}, f"mapa STRIDE discorda da capa: {heat}"


def test_o_caso_coerente_continua_a_classificar_como_antes() -> None:
    """Âncora: quando `score` é mesmo L×I — o caso dos exemplos publicados — nada muda."""
    status, severity, heat = _bands_of_the_declared_threat({"likelihood": 5, "impact": 5, "score": 25.0})

    assert status == "requires_immediate_attention"
    assert severity == {"critical": 1}
    assert heat == {"critical": 1}


def test_uma_ameaca_declarada_sem_score_continua_a_ser_classificada() -> None:
    """`score` é opcional; a ameaça não pode desaparecer do quadro por o modelador o omitir."""
    status, severity, heat = _bands_of_the_declared_threat({"likelihood": 4, "impact": 4})

    assert status == "action_recommended"
    assert severity == {"high": 1}
    assert heat == {"high": 1}
