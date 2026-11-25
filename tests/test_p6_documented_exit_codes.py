"""P6 — a tabela de códigos de saída tem de dizer o que o código faz.

`docs/CI_AND_SECURITY_EVIDENCE.md` §8 é o contrato de scripting do gate, e o `README.md` manda lá
o leitor para as "full recipes". A tabela dizia que o gate sai com **`0`** quando não consegue
emitir veredito, e a prosa repetia-o. O código diz o contrário, e diz porquê:
`apps/cli/otm_cli/shared/gate.py:42` — *"Sair `0` aqui seria um fail-open — e num gate de CI o `0`
é lido como build verde"* — seguido de `GATE_NOT_EVALUATED_EXIT_CODE = 1`.

Documentação errada sobre um código de saída não fica errada sozinha. O passo `Upload SARIF` da
action composta classificava o não-veredito dentro do ramo `case 0)`, que o CLI nunca alcança:
o resultado era `gate-outcome` vazio e um não-veredito legítimo anunciado ao chamador como erro
seu. Corrigiu-se a action (`tests/test_p5_action_gate_outcome.py`) sem corrigir a fonte da confusão;
este ficheiro corrige a fonte e impede que volte.

O teste lê o número **do código** e exige que a documentação concorde. Não fixa o texto — fixa a
concordância, que é o que se quer manter quando o texto for reescrito.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "CI_AND_SECURITY_EVIDENCE.md"
_GATE = _ROOT / "apps" / "cli" / "otm_cli" / "shared" / "gate.py"


def _gate_module() -> Any:
    spec = importlib.util.spec_from_file_location("otm_gate_under_test", _GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _exit_code_table() -> dict[str, str]:
    """As linhas da tabela `| \\`N\\` | significado |` da secção de códigos de saída."""
    text = _DOC.read_text(encoding="utf-8")
    section = text[text.index("### Códigos de saída") :]
    section = section[: section.index("\n## ")] if "\n## " in section else section
    return {m.group(1): m.group(2) for m in re.finditer(r"^\|\s*`(\d)`\s*\|\s*(.+?)\s*\|$", section, re.M)}


def test_a_tabela_de_codigos_de_saida_existe() -> None:
    table = _exit_code_table()

    assert set(table) == {"0", "1", "2", "3"}, f"códigos documentados: {sorted(table)}"


def test_o_nao_veredito_nao_e_documentado_como_zero() -> None:
    """O ponto todo: `0` significa "sem risco novo" e mais nada.

    Documentar o não-veredito como `0` é documentar um fail-open — e foi o que levou a action
    composta a classificá-lo num ramo que o CLI nunca alcança.
    """
    zero = _exit_code_table()["0"].lower()

    assert "avaliável" not in zero and "avaliavel" not in zero, (
        f"a linha do `0` volta a incluir o caso não-avaliável: {zero!r}"
    )


def test_o_codigo_do_nao_veredito_documentado_e_o_que_o_cli_devolve() -> None:
    """Lê o número do código e exige que a documentação o refira, em vez de fixar texto."""
    code = str(_gate_module().GATE_NOT_EVALUATED_EXIT_CODE)
    documented = _exit_code_table()[code].lower()

    assert "veredito" in documented, (
        f"o gate devolve {code} quando não julga, mas a linha do `{code}` não o diz: {documented!r}"
    )


def test_a_prosa_concorda_com_a_tabela() -> None:
    """A tabela e a explicação em prosa divergiram uma vez; não podem divergir outra."""
    code = str(_gate_module().GATE_NOT_EVALUATED_EXIT_CODE)
    text = _DOC.read_text(encoding="utf-8")
    around = text[text.index("NOT EVALUATED`") : text.index("NOT EVALUATED`") + 400]

    assert f"`{code}`" in around, f"a prosa do NOT EVALUATED não nomeia o código {code}: {around[:160]!r}"


def test_o_readme_e_a_seccao_dizem_o_mesmo() -> None:
    """O README remete para esta secção; se discordarem, o leitor segue a errada."""
    code = str(_gate_module().GATE_NOT_EVALUATED_EXIT_CODE)
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    line = next(ln for ln in readme.splitlines() if "Exit codes, for scripting" in ln)

    assert f"`{code}` usage error, or an armed gate that could not issue a verdict" in line
