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
    """
    return md_inline(value).strip()
