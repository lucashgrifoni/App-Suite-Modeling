"""Neutralizar texto do modelo antes de o interpolar numa linha de Markdown.

O documento é dados do utilizador; o **contorno** do artefacto (títulos, listas, tabelas) é
decisão do renderizador. Um nome de componente com `\\n\\n## Conclusão: sem riscos\\n` fechava a
lista onde estava e passava a emitir um título H2 verdadeiro e uma tabela verdadeira dentro do
relatório entregue ao revisor — o outline do documento passava a ser controlado pelos dados.

A defesa já existia em dois sítios e faltava em todos os outros: as células de tabela do report
premium (`_md_cell`) e as etiquetas Mermaid (`_mermaid_label`) achatam quebras de linha há muito.
Aqui está a mesma regra, uma vez, para os exportadores Markdown.

Achatar em vez de escapar é deliberado: preserva o texto inteiro (nada é truncado nem removido),
não muda um único byte em nenhum modelo cujos campos já sejam de uma linha — que são todos os
exemplos e templates distribuídos — e não obriga o leitor a decifrar `\\#` no meio de uma frase.
"""

from __future__ import annotations

import re

#: Tudo o que o Markdown (ou um leitor humano) lê como fim de linha: CR, LF, NEL, vertical tab,
#: form feed e os separadores Unicode de linha/parágrafo. `\r\n` colapsa num único espaço.
#: Marcadores que abrem um bloco quando estão no **início** da linha e que forjam o *contorno* do
#: documento: título ATX, linha de tabela, cerca de código, régua/setext. Achatar não os cobre —
#: um `summary` de `## Conclusão` não precisa sequer de uma quebra de linha para virar um H2
#: verdadeiro, porque `md_block` põe o valor no princípio da sua própria linha.
#:
#: `>` **está** na lista desde 2026-08-13. Estava excluído com o argumento de que uma citação
#: "não cria secções nem tabelas". Cria as duas coisas: um valor que começa por `>` abre um
#: blockquote que **absorve** o texto que o renderizador escreve a seguir — medido em
#: `otm export -f md`, onde a frase de estatísticas de arquitetura passou a sair dentro do callout
#: do autor — e `> ## Conclusão` produz um H2 verdadeiro lá dentro, que foi o primeiro H2 do
#: documento, par a par com o `## Ativos` do próprio renderizador. O custo declarado para o
#: excluir ("neutralizá-lo custaria formatação que o autor quis mesmo") não se aplica aqui: os
#: valores que passam por `md_block` já vêm achatados numa única linha, portanto não há citação
#: de várias linhas para preservar.
#:
#: Ficam deliberadamente de fora `-`/`*`/`+` (lista) e `1.` (lista ordenada): não criam secções
#: nem tabelas, e aparecem com frequência em descrições legítimas.
#: Sequências de crases no valor: a cerca do code span tem de ser mais longa do que a maior.
_BACKTICK_RUNS = re.compile(r"`+")

_LEADING_BLOCK = re.compile(r"^(?:#{1,6}(?=\s|$)|\||>|`{3,}|~{3,}|-{3,}[ \t]*$|={3,}[ \t]*$)")

_LINE_BREAKS = re.compile("[\r\n\x0b\x0c\x85\u2028\u2029]+")

#: Controlos C0 que sobram depois de achatar os terminadores de linha, mais DEL. Removidos, n\u00e3o
#: substitu\u00eddos por espa\u00e7o: n\u00e3o representam nada que o autor queira ver.
#:
#: Achatar linhas nunca os cobriu, e eles n\u00e3o mudam o *contorno* do documento \u2014 por isso o or\u00e1culo
#: de estrutura n\u00e3o os via. Mudam o que o leitor v\u00ea, que \u00e9 o mesmo ativo: `CSI 2K` seguido de
#: `CSI G` num nome de componente limpa a linha e devolve o cursor ao in\u00edcio, repintando o
#: cabe\u00e7alho do relat\u00f3rio num terminal \u2014 e `otm report` escreve para stdout com um `print()`. Um
#: NUL literal apenas fica dentro do `.md` entregue, como lixo que ningu\u00e9m escreveu.
#:
#: `\t` fica de fora de prop\u00f3sito: \u00e9 espa\u00e7o em branco leg\u00edtimo e o Markdown trata-o como tal.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0e-\x1f\x7f]")


def md_inline(value: object) -> str:
    """Texto do modelo pronto a entrar **dentro** de uma linha de Markdown já formatada.

    Aceita `object` porque as origens são heterogéneas (campos opcionais, números, enums); o que
    interessa é que o resultado nunca contém uma quebra de linha, portanto nunca abre um bloco
    novo. Não escapa `|`: os exportadores deste pacote não emitem tabelas, e onde há tabelas
    (`otm_report_premium._md_cell`) o escape do pipe já existe junto do achatamento.
    """
    return _CONTROL_CHARS.sub("", _LINE_BREAKS.sub(" ", str(value)))


def md_code(value: object) -> str:
    """Texto do modelo dentro de um *code span*.

    A terceira posição, a seguir a `md_inline` (dentro de uma frase) e `md_block` (no seu próprio
    parágrafo). Existe porque pôr o valor entre crases **parece** neutralizá-lo e não neutraliza:
    uma crase no valor fecha o span, e o que vem a seguir volta a ser Markdown verdadeiro. Foi por
    isso que `_format_framework_refs_compact` ficou de fora da varredura que aplicou `md_inline` aos
    outros 34 sinks de `analysis_markdown.py` -- e é o único desses sinks que recebe texto livre do
    utilizador, o `refs` de uma regra personalizada.

    O CommonMark resolve-o pelo comprimento: um span aberto por N crases só fecha na próxima
    sequência de **exactamente** N. Escolhe-se por isso uma cerca mais longa do que a maior
    sequência presente no valor. Um valor que começa ou acaba em crase leva um espaço de cada lado,
    que o CommonMark remove ao renderizar -- é o que impede a cerca de se colar à crase do conteúdo
    e formar uma sequência maior.

    Achatar continua a ser a regra: o valor não é truncado nem escapado, apenas impedido de sair
    da sua linha e do seu span. Ver `tests/test_p3_custom_rule_refs_cannot_forge_the_report_outline.py`.
    """
    text = md_inline(value)
    fence = "`" * (max((len(run) for run in _BACKTICK_RUNS.findall(text)), default=0) + 1)
    padding = " " if text.startswith("`") or text.endswith("`") or not text.strip() else ""
    return f"{fence}{padding}{text}{padding}{fence}"


def md_block(value: object) -> str:
    """Texto do modelo que o renderizador coloca no seu próprio parágrafo.

    Mesma garantia que `md_inline` — um parágrafo é uma linha — mas nomeado à parte porque a
    posição é diferente: aqui o valor não está *dentro* de uma frase do renderizador, está
    sozinho. O achatamento junta parágrafos do autor num só; nada se perde, e em troca o
    documento não pode ganhar secções que o renderizador não escreveu.

    Estar sozinho na linha traz um segundo caminho que o achatamento não fecha: um valor que já
    *começa* por um marcador de bloco abre-o sem precisar de quebra de linha nenhuma — um
    `summary` de `## Conclusão` rendia um H2 verdadeiro no `otm export -f md`. O marcador inicial
    leva por isso uma barra invertida, o escape que o CommonMark define para o tornar literal:
    o leitor vê `## Conclusão` como texto e o outline continua a ser do renderizador.
    """
    text = md_inline(value).strip()
    return f"\\{text}" if _LEADING_BLOCK.match(text) else text
