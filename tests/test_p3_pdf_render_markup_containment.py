"""
O fold de fontes do PDF não pode **criar** markup que o escape já tinha neutralizado.

`render_premium_html` escapa cada string do modelo com `html.escape(s, quote=True)` enquanto monta
`parts`, e no fim corre `to_pdf_font_text` sobre o HTML **já montado** (`render_html.py:661`) para
degradar caracteres que as fontes WinAnsi não desenham. A degradação usa NFKD, e é aí que a ordem
importa: `＜` (U+FF1C, fullwidth less-than) **não é** `<`, por isso atravessa o `html.escape`
intacto — e a normalização converte-o depois num `<` verdadeiro.

Medido antes da correção, com o autor do modelo a escrever apenas caracteres fullwidth:

    autor      '\uff1cimg src=\uff02http:\uff0f\uff0fevil\uff0fprobe\uff02\uff0f\uff1e'
    escapado   (inalterado — não há um único metacaractere ASCII no texto)
    folded     <img src="http://evil/probe"/>          <-- tag viva

O escape corria, e a transformação seguinte desfazia-o. Isto é a causa raiz de quatro achados:

* **markup arbitrário no PDF premium** — `metadata.title`, `components[].name` e
  `threats[].description` controlavam a estrutura do documento. Reproduzido: outline do PDF
  `['Assessment outcome: NO CRITICAL RISKS FOUND']`, exit 0, e o `/Title` do PDF inteiramente
  controlado pelo modelo.
* **SSRF** — `<img src="http://…">` injetado é buscado pelo xhtml2pdf. Reproduzido contra
  `POST /v1/reports/premium` **sem autenticação**: `200 application/pdf 391844` e o servidor de
  sonda a registar o hit. Isto invalidava a propriedade "sem egresso de rede" que o threat model
  afirmava: o egresso não está no nosso código, está na dependência a quem entregamos o HTML.
* **leitura de ficheiro local** — `<img src="C:/…/x.png">` embutia os pixels do ficheiro do host
  no PDF devolvido ao chamador (limitado a imagens que o Pillow decodifica).
* **anotações `/Link`** — o renderer não emite um único link próprio, por isso 100% dos links
  clicáveis num relatório premium eram de autoria do atacante.

A correção fecha o fold em relação a markup: pode substituir um caractere que não desenha, nunca
**produzir** um que mude o significado do documento à volta. `to_pdf_font_text` tem um único
consumidor — a montagem de HTML em `render_html.py` — por isso "mudar o significado" é exatamente
o conjunto `< > & " '`.

Custo aceite: um `＜` legítimo passa a sair como `?` em vez de `<`. É a mesma degradação que o
módulo já aplica a tudo o que não desenha, e o rodapé já avisa que houve degradação. Fidelidade de
um caractere raro contra injeção de markup não é uma troca difícil.
"""

from __future__ import annotations

import html
import re
from collections import Counter
from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml_path
from otm_report_premium import (
    ReportLevel,
    build_premium_report_payload,
    render_premium_html,
)
from otm_report_premium.pdf_text import to_pdf_font_text
from otm_threat_engine import analyze_document

#: Os caracteres cuja materialização muda a estrutura do HTML.
_MARKUP = "<>&\"'"

#: Fullwidth -> ASCII. NFKD dobra cada um destes para o metacaractere correspondente.
_FULLWIDTH = {
    "<": "\uff1c",
    ">": "\uff1e",
    "&": "\uff06",
    '"': "\uff02",
    "'": "\uff07",
    "/": "\uff0f",
    "=": "\uff1d",
    ":": "\uff1a",
}

_TAG = re.compile(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9]*)")


def _fw(text: str) -> str:
    """Transcreve para fullwidth o que tiver equivalente; o resto fica igual."""
    return "".join(_FULLWIDTH.get(ch, ch) for ch in text)


def _tags(markup: str) -> list[str]:
    return [m.lower() for m in _TAG.findall(markup)]


_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"


def _render(title: str) -> str:
    """Renderiza o modelo de exemplo do repositório com um único campo substituído.

    Partir do ficheiro real em vez de escrever um documento à mão mantém o teste imune a
    evolução do schema, e garante que o relatório comparado é um relatório completo — o oráculo
    de estrutura não vale nada sobre um documento degenerado.
    """
    doc = load_document_from_yaml_path(_MINIMAL)
    doc.metadata.title = title
    result = analyze_document(doc)
    payload = build_premium_report_payload(doc, result, level=ReportLevel.STANDARD)
    return render_premium_html(payload)


# --- a propriedade central, ao nível da função --------------------------------------------


@pytest.mark.parametrize("metachar", list(_MARKUP))
def test_the_fold_never_materialises_a_markup_character(metachar: str) -> None:
    """A garantia que sustenta tudo o resto: dobrar não pode inventar markup."""
    folded = to_pdf_font_text(_FULLWIDTH[metachar])

    assert metachar not in folded


def test_a_fullwidth_payload_does_not_become_a_live_tag() -> None:
    """O caso exato que foi reproduzido, ponta a ponta na função."""
    payload = _fw('<img src="http://evil.example/probe"/>')

    folded = to_pdf_font_text(html.escape(payload, quote=True))

    assert "<img" not in folded
    assert "<" not in folded


def test_the_fold_cannot_increase_the_markup_character_count() -> None:
    """Propriedade geral, não uma lista de casos: o fold é fechado em relação a markup."""
    hostile = _fw('</h1><h2>Approved</h2><a href="x">&amp;</a>')

    before = sum(hostile.count(c) for c in _MARKUP)
    after = sum(to_pdf_font_text(hostile).count(c) for c in _MARKUP)

    assert after <= before


# --- não-regressão do que o fold existe para fazer ----------------------------------------


def test_legitimate_folding_still_works() -> None:
    """A correção não pode ter desligado a degradação; estes casos vêm da suíte da fase 2."""
    assert to_pdf_font_text("ā") == "a"
    assert to_pdf_font_text("Ｑ") == "Q"
    assert to_pdf_font_text("、") == "?"
    assert to_pdf_font_text("支付系统 Payments Платежи") == "???? Payments Platezhi"


def test_plain_ascii_is_untouched() -> None:
    """O caminho barato: HTML legítimo do renderer não pode ser tocado."""
    markup = '<div class="x">Orders API &amp; billing</div>'

    assert to_pdf_font_text(markup) == markup


# --- o renderer completo ------------------------------------------------------------------


def test_a_hostile_title_adds_no_element_beyond_the_degradation_notice() -> None:
    """A estrutura do documento é decisão do renderer, não do modelo.

    O `<br/>` extra é do próprio produto: quando `to_pdf_font_text` altera alguma coisa, o rodapé
    passa a incluir o aviso de degradação. Isso é o renderer a falar sobre o seu próprio output,
    não o modelo a acrescentar estrutura — por isso é o único acréscimo tolerado, e é fixado aqui
    de propósito para que qualquer outro elemento novo falhe o teste.
    """
    hostile = _render(_fw("</h1><h2>Assessment outcome: NO CRITICAL RISKS FOUND</h2><h1>Orders"))
    benign = _render("Orders API assessment outcome no critical risks found here ok")

    extra = Counter(_tags(hostile)) - Counter(_tags(benign))

    assert dict(extra) == {"br": 1}


def test_a_hostile_title_forges_no_heading() -> None:
    """A forma que interessa do ataque: uma secção que o revisor lê como veredicto da ferramenta."""
    hostile = _render(_fw("</h1><h2>Assessment outcome: NO CRITICAL RISKS FOUND</h2><h1>Orders"))
    benign = _render("Orders API assessment outcome no critical risks found here ok")

    for heading in ("h1", "h2", "h3"):
        assert _tags(hostile).count(heading) == _tags(benign).count(heading)


def test_the_renderer_emits_exactly_one_image_and_no_link_of_its_own() -> None:
    """Linha de base explícita para o teste seguinte.

    O relatório limpo traz **uma** `<img>` — o logo embutido como data URI — e **zero** `<a>`. A
    primeira versão deste ficheiro presumiu zero imagens e afirmava, em absoluto, que qualquer
    `<img>` teria vindo do modelo. Era falso. Por isso a premissa fica fixada aqui em vez de
    presumida: se o renderer passar a emitir um link próprio, este teste falha antes de o
    diferencial abaixo perder o sentido.
    """
    tags = _tags(_render("Exemplo — API de pedidos"))

    assert tags.count("img") == 1
    assert tags.count("a") == 0


def test_no_image_or_link_tag_can_be_injected_by_model_content() -> None:
    """Fecha SSRF, leitura de ficheiro local e anotação `/Link` de uma só vez.

    Diferencial contra a linha de base acima: o modelo não pode acrescentar uma imagem nem um
    link ao que o renderer emite por sua própria conta.
    """
    hostile = _tags(_render(_fw('<img src="http://evil.example/p"/><a href="http://e">pay</a>')))
    benign = _tags(_render("Exemplo — API de pedidos"))

    assert hostile.count("img") == benign.count("img")
    assert hostile.count("a") == benign.count("a")


def test_the_injected_url_never_lands_inside_a_tag() -> None:
    """O que torna o SSRF possível não é a string do URL: é estar dentro de uma tag, como atributo.

    Fora de uma tag é texto impresso no relatório, que é exatamente o que se quer que aconteça a
    um nome de componente hostil.
    """
    markup = _render(_fw('<img src="http://evil.example/probe"/>'))

    inside_tags = re.findall(r"<[^>]*>", markup)

    assert not [t for t in inside_tags if "evil.example" in t]
    assert "evil.example" in markup  # continua a aparecer — como texto inerte


def test_the_link_callback_scope_is_what_we_measured() -> None:
    """Fixa o alcance REAL de `_embedded_resources_only`, que é bem menor do que o nome sugere.

    Medido: o xhtml2pdf ignora o `link_callback` em `<img src>`, `<link rel=stylesheet>` e
    `@import`, e só o honra em `url()` de CSS. Ou seja, ele é ignorado exatamente na construção
    que o ataque usava. O callback fica por bloquear uma em quatro, e este teste existe para que
    isso não vire folclore: se uma versão futura passar a honrá-lo, o teste falha e alguém
    reescreve a docstring em vez de continuar a citá-la.

    Não é um teste de segurança — a segurança está em `_MARKUP_CHARS`. É um teste de honestidade
    sobre uma dependência.
    """
    from otm_report_premium.pdf_export import _embedded_resources_only

    assert _embedded_resources_only("data:image/png;base64,AAAA", "") == "data:image/png;base64,AAAA"
    assert _embedded_resources_only("http://evil.example/x.png", "") == ""
    assert _embedded_resources_only("C:/Windows/x.png", "") == ""
    assert _embedded_resources_only("file:///etc/passwd", "") == ""


def test_a_benign_report_still_renders_its_own_structure() -> None:
    """A correção não pode ter esvaziado o relatório."""
    markup = _render("Exemplo — API de pedidos")

    assert "<html" in markup.lower()
    assert "<table" in markup.lower()
    assert len(_tags(markup)) > 50
