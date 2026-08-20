"""A lista de riscos prioritários tem de conter a ameaça que o modelador declarou.

`sorted_threats` é construído só a partir de `active` — as heurísticas — e alimenta o "Top 10
riscos prioritários", o "Top 5" do resumo executivo, os perfis de exploitability e as linhas de
impacto de negócio. `doc.threats` nunca lá chega.

O resultado é um relatório que se contradiz na mesma página. Num modelo cuja única ameaça de
severidade 25 é declarada pelo modelador — um RCE não autenticado saído de um pentest — e cuja
maior heurística vale 12:

    - **Estado geral:** Requer atenção imediata
    - **Urgência:** high
    | critical | 1 |
    - **Total de ameaças (canónicas + heurísticas activas):** 10

e a tabela accionável logo abaixo lista dez heurísticas de 12 para baixo, sem uma linha sobre o
RCE. Foi medido a zero ocorrências nos níveis executivo e standard.

O builder já escreve a regra: *"As três leituras da mesma página têm de concordar"*. A capa, a
urgência, o quadro de severidade, o mapa e o contador de fronteiras já contam as declaradas. A
lista pela qual alguém decide o que fazer a seguir era a última que não contava.

Uma ameaça declarada **sem** `risk` não pode ser ordenada contra scores sem lhe inventar um
número, por isso fica de fora — mas fica de fora à vista, num aviso contado no bloco de limites
de inferência, e não em silêncio.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings", "exporters", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_DECLARED_ID = "t_pentest_rce"
_DECLARED_TITLE = "RCE não autenticado encontrado no último pentest"


def _document(*, declared_risk: dict[str, Any] | None, declare: bool = True) -> Any:
    from otm_core_schema import ThreatModelDocument

    threat: dict[str, Any] = {
        "id": _DECLARED_ID,
        "title": _DECLARED_TITLE,
        "stride": "elevation_of_privilege",
        "target_component_id": "c0",
    }
    if declared_risk is not None:
        threat["risk"] = declared_risk

    return ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0", "system_type": "web_application", "industry_sector": "saas"},
            "metadata": {"title": "Portal"},
            "components": [
                {"id": "c0", "name": "Portal web", "kind": "process"},
                {"id": "db", "name": "Base de dados", "kind": "datastore"},
            ],
            "data_flows": [{"id": "f0", "name": "Consulta", "from_component": "c0", "to_component": "db"}],
            "threats": [threat] if declare else [],
        }
    )


def _payload(*, declared_risk: dict[str, Any] | None = None, declare: bool = True, level: str = "standard") -> Any:
    from otm_report_premium import ReportLevel, build_premium_report_payload
    from otm_threat_engine import analyze_document

    document = _document(declared_risk=declared_risk, declare=declare)
    return build_premium_report_payload(document, analyze_document(document), level=ReportLevel(level))


def test_a_maior_heuristica_fica_abaixo_da_ameaca_declarada() -> None:
    """Premissa: sem isto, a ameaça declarada podia estar ausente do topo por ser mesmo menor."""
    top = _payload(declare=False).top_risks

    assert top, "o modelo base tem de produzir heurísticas, senão o teste não mede nada"
    assert max(t.severity_score or 0.0 for t in top) < 25.0


def test_a_ameaca_declarada_encabeca_os_riscos_prioritarios() -> None:
    top = _payload(declared_risk={"likelihood": 5, "impact": 5}).top_risks
    ids = [t.threat_id for t in top]

    assert _DECLARED_ID in ids, f"a ameaça declarada não está na lista accionável: {ids}"
    assert ids[0] == _DECLARED_ID, f"a maior do documento não ficou em primeiro: {ids}"


def test_a_ameaca_declarada_entra_no_top5_do_resumo_executivo() -> None:
    titles = _payload(declared_risk={"likelihood": 5, "impact": 5}).executive_summary.top5_risk_titles

    assert _DECLARED_TITLE in titles, f"o Top 5 executivo ignora-a: {titles}"


def test_o_relatorio_impresso_menciona_a_ameaca_declarada() -> None:
    """O nível standard é o que um decisor lê; era onde as ocorrências davam zero."""
    from otm_report_premium import render_premium_markdown

    for level in ("executive", "standard", "deep"):
        markdown = render_premium_markdown(_payload(declared_risk={"likelihood": 5, "impact": 5}, level=level))
        assert _DECLARED_TITLE in markdown, f"nível {level}: o relatório não menciona a ameaça declarada"


def test_uma_declarada_menor_nao_salta_a_frente_das_heuristicas() -> None:
    """A ordenação continua a ser por score: declarar não é uma via para o topo."""
    top = _payload(declared_risk={"likelihood": 1, "impact": 1}).top_risks
    ids = [t.threat_id for t in top]

    assert ids[0] != _DECLARED_ID, f"uma ameaça L1xI1 encabeçou a lista: {ids}"


def test_uma_declarada_sem_risco_e_excluida_a_vista() -> None:
    """Não se ordena o que não tem score — mas a exclusão tem de aparecer no relatório."""
    from otm_report_premium import render_premium_markdown

    payload = _payload(declared_risk=None)
    baseline = _payload(declared_risk={"likelihood": 5, "impact": 5})

    assert _DECLARED_ID not in [t.threat_id for t in payload.top_risks]
    extra = [b for b in payload.disclaimer.bullets if b not in baseline.disclaimer.bullets]
    assert len(extra) == 1, f"o bloco de limites não ganhou o aviso: {payload.disclaimer.bullets}"
    assert "1" in extra[0], f"o aviso não diz quantas ficaram de fora: {extra[0]}"
    assert extra[0] in render_premium_markdown(payload), "o aviso não chega ao relatório impresso"


def test_sem_declaradas_sem_risco_nao_ha_aviso() -> None:
    """O aviso é sobre um facto do documento; não pode aparecer quando o facto não existe."""
    com_risco = _payload(declared_risk={"likelihood": 5, "impact": 5})
    sem_declaradas = _payload(declare=False)

    assert len(com_risco.disclaimer.bullets) == len(sem_declaradas.disclaimer.bullets)
