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
#: Ficam deliberadamente de fora `-`/`*`/`+` (lista), `>` (citação) e `1.` (lista ordenada): não
#: criam secções nem tabelas, aparecem com frequência em descrições legítimas, e neutralizá-los
#: custaria formatação que o autor quis mesmo.
_LEADING_BLOCK = re.compile(r"^(?:#{1,6}(?=\s|$)|\||`{3,}|~{3,}|-{3,}[ \t]*$|={3,}[ \t]*$)")

_LINE_BREAKS = re.compile("[\r\n\x0b\x0c\x85\u2028\u2029]+")


def md_inline(value: object) -> str:
    """Texto do modelo pronto a entrar **dentro** de uma linha de Markdown já formatada.

    Aceita `object` porque as origens são heterogéneas (campos opcionais, números, enums); o que
    interessa é que o resultado nunca contém uma quebra de linha, portanto nunca abre um bloco
    novo. Não escapa `|`: os exportadores deste pacote não emitem tabelas, e onde há tabelas
    (`otm_report_premium._md_cell`) o escape do pipe já existe junto do achatamento.
    """
    return _LINE_BREAKS.sub(" ", str(value))


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
