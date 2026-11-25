"""Uma palavra-chave a meio de outra palavra silenciava o anti-padrão.

`missing_any_of` dispara quando **nenhuma** das suas palavras aparece no corpus. A comparação era
por subcadeia, e o corpus junta títulos, nomes, ids e descrições de tudo. `rate` está dentro de
**Corporate**; `card` está dentro de **discard** e de **wildcard**.

Renomear um componente de "Partner webhook endpoint" para "Corporate webhook endpoint" — sem tocar
em mais nada — fazia `rate` deixar de estar em falta e silenciava o anti-padrão de ingestão sem
limite de taxa. A direcção é a pior das duas: um achado que devia aparecer desaparece por uma
palavra sem relação nenhuma com o assunto.

A fronteira é só à **esquerda**, não em ambos os lados: o catálogo usa radicais de propósito —
`mascar` para mascarar/mascaramento, `redac` para redacted/redação, `reauth` — e exigir fronteira à
direita partia-os. Medido sobre os 38 templates distribuídos: **zero** respostas mudam.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _hit(keyword: str, corpus: str) -> bool:
    from otm_threat_engine.anti_pattern_library import corpus_mentions

    return corpus_mentions(keyword, corpus)


@pytest.mark.parametrize(
    ("corpus", "keyword"),
    [
        ("corporate webhook endpoint", "rate"),
        ("accurate metrics", "rate"),
        ("discard invalid input", "card"),
        ("wildcard certificate", "card"),
    ],
)
def test_uma_palavra_a_meio_de_outra_nao_conta(corpus: str, keyword: str) -> None:
    assert not _hit(keyword, corpus), f"`{keyword}` contou dentro de `{corpus}`"


@pytest.mark.parametrize(
    ("corpus", "keyword"),
    [("rate limit por cliente", "rate"), ("card number vault", "card"), ("origin header", "origin")],
)
def test_a_palavra_no_seu_lugar_continua_a_contar(corpus: str, keyword: str) -> None:
    assert _hit(keyword, corpus)


@pytest.mark.parametrize(
    ("corpus", "keyword"),
    [("mascaramento de dados", "mascar"), ("dados mascarados", "mascar"), ("redacted logs", "redac")],
)
def test_os_radicais_do_catalogo_continuam_a_contar(corpus: str, keyword: str) -> None:
    """O catálogo usa radicais de propósito; exigir fronteira à direita partia-os."""
    assert _hit(keyword, corpus)


def test_os_templates_distribuidos_nao_mudam_de_resposta() -> None:
    """A medição que justificou a fronteira só à esquerda, presa para não se perder."""
    import yaml
    from otm_core_schema import ThreatModelDocument
    from otm_industry_packs.loader import list_template_ids, load_template_yaml

    catalog = yaml.safe_load(
        (
            _ROOT / "packages" / "threat-engine" / "otm_threat_engine" / "data" / "anti_patterns" / "catalog.yaml"
        ).read_text(encoding="utf-8")
    )
    keywords = {k for item in catalog["patterns"] for k in (item.get("missing_any_of") or [])}

    changed: list[tuple[str, str]] = []
    for template_id in list_template_ids():
        document = ThreatModelDocument.model_validate(yaml.safe_load(load_template_yaml(template_id)))
        corpus = " ".join(
            [
                document.metadata.title or "",
                *(c.name or "" for c in document.components),
                *(c.id for c in document.components),
            ]
        ).lower()
        changed += [(template_id, k) for k in keywords if (k.lower() in corpus) != _hit(k, corpus)]

    assert not changed, f"a fronteira mudou respostas em templates distribuídos: {changed[:6]}"
