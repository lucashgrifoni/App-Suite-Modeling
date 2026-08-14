"""
Cinco defeitos de baixa severidade da auditoria da fase 3, agrupados por causa.

Nenhum é explorável para acesso indevido. Três são de **integridade de saída** — o artefacto que
sai não é o que o consumidor a jusante espera — e dois são de **limite de entrada** ausente num
sítio onde os irmãos já o têm. Ficam juntos porque separá-los em cinco commits daria mais ruído
do que sinal.

## Integridade de saída

**JSON com `NaN`/`Infinity`.** `json.dumps` aceita não-finitos por omissão e escreve `NaN` cru,
que **não é JSON** — nenhum parser fora de Python o lê. Um consumidor em Go ou Java rejeita o
documento inteiro; o `jq` reescreve silenciosamente o valor para `null`, o que num campo de score
é pior do que rejeitar. Hoje todos os scores calculados são finitos, por isso isto é uma rede de
segurança e não a correção de um bug ativo: `allow_nan=False` transforma um artefacto inválido
emitido em silêncio num erro alto e claro no momento em que for gerado.

**ANSI e NUL em Markdown.** `md_inline`/`md_block` achatavam terminadores de linha e deixavam
passar tudo o resto. `CSI 2K` + `CSI G` num nome de componente repintam a linha num terminal — o
`otm report` escreve para stdout com um `print()` — e um NUL literal fica dentro do `.md`
entregue. Não muda o *contorno* do documento, por isso o oráculo de estrutura não o via; muda o
que o leitor vê, que é o mesmo ativo.

**Separadores de linha Unicode em Mermaid.** `_LABEL_CONTROL_RE` cobria `\\r\\n\\t\\f\\v` e não
cobria NEL (U+0085), LINE SEPARATOR (U+2028) e PARAGRAPH SEPARATOR (U+2029). O invariante que o
exportador declara é "um nome não pode acrescentar uma linha"; estes três acrescentam. Não foi
demonstrada injeção de statement — as aspas seguram —, por isso é `INFO`, mas o invariante é do
exportador e estava falso.

## Limite de entrada

**Profundidade do ficheiro de regras.** `load_custom_rules` tem tecto de bytes e usa
`yaml.safe_load` — o mesmo `safe_load` sem tecto de profundidade que já foi corrigido para o
documento canónico em `f96817a`. Um ficheiro de 4 KB rebentava a pilha e saía como
`RecursionError` cru, fora do contrato `ValueError`/`CliUserError` que o próprio loader declara.
A correção é ligar o consumidor ao limite que já existe, não inventar outro.

**Comprimento de cada `refs`.** `max_length=20` limita a **lista**, não cada string: um único
item de 400 000 caracteres passava, enquanto `title`, `description` e os restantes campos irmãos
têm tecto próprio. O ref entra no relatório e no SARIF por cada ameaça que a regra dispara, por
isso o custo multiplica pela população que casa.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml_path
from otm_exporters import export_analysis_json, export_document_json
from otm_exporters.markdown_text import md_block, md_inline
from otm_exporters.mermaid_flowchart import _mermaid_label
from otm_threat_engine import analyze_document
from otm_threat_engine.custom_rules import CustomRuleSet
from otm_threat_engine.custom_rules.loader import load_custom_rules

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"


# --- integridade de saída: JSON -----------------------------------------------------------


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_the_exporter_refuses_a_non_finite_score_instead_of_writing_invalid_json(value: float) -> None:
    """`NaN` cru não é JSON. Falhar alto vale mais do que emitir um ficheiro que ninguém lê.

    Exercita o **exportador**, não o `json.dumps`. A primeira versão deste teste asseriva
    `json.dumps({...}, allow_nan=False)` e passaria com a correção revertida, porque testava a
    biblioteca-padrão em vez da mudança — o mesmo defeito de oráculo que esta fase encontrou nos
    testes de estrutura Markdown.

    O caminho é real: `risk.score` é um `float` do Pydantic e aceita atribuição de não-finito, por
    isso um score corrompido a montante chegava ao ficheiro em vez de ser recusado.
    """
    result = analyze_document(load_document_from_yaml_path(_MINIMAL))
    threat = next(t for t in result.heuristic_threats if t.risk)
    threat.risk.score = value

    with pytest.raises(ValueError, match="JSON compliant"):
        export_analysis_json(result)


def test_the_shipped_model_still_exports_parseable_json() -> None:
    """Controlo: a rede de segurança não pode ter apanhado o caso normal."""
    text = export_document_json(load_document_from_yaml_path(_MINIMAL))

    assert json.loads(text)["metadata"]["title"]


# --- integridade de saída: Markdown --------------------------------------------------------


@pytest.mark.parametrize("helper", [md_inline, md_block])
def test_ansi_escapes_do_not_survive_into_markdown(helper) -> None:
    """`CSI 2K` + `CSI G` repintam a linha de um terminal que mostre o relatório."""
    out = helper("Edge\x1b[2K\x1b[G REPAINTED")

    assert "\x1b" not in out


@pytest.mark.parametrize("helper", [md_inline, md_block])
def test_a_nul_byte_does_not_survive_into_markdown(helper) -> None:
    """Um NUL literal num `.md` entregue é lixo que nenhum autor escreveu de propósito."""
    out = helper("Edge\x00gateway")

    assert "\x00" not in out


@pytest.mark.parametrize("helper", [md_inline, md_block])
def test_the_visible_text_is_preserved(helper) -> None:
    """Neutralizar, não censurar — a mesma regra do resto do módulo."""
    out = helper("Edge\x1b[2K gateway")

    assert "Edge" in out
    assert "gateway" in out


@pytest.mark.parametrize("helper", [md_inline, md_block])
def test_ordinary_text_is_untouched(helper) -> None:
    assert helper("Edge gateway (HTTPS) — 99.9%") == "Edge gateway (HTTPS) — 99.9%"


# --- integridade de saída: Mermaid ---------------------------------------------------------


@pytest.mark.parametrize(
    ("separator", "name"),
    [("", "NEL"), (" ", "LINE SEPARATOR"), (" ", "PARAGRAPH SEPARATOR")],
)
def test_unicode_line_separators_cannot_add_a_line_to_a_mermaid_label(separator: str, name: str) -> None:
    """O invariante que o exportador declara: um nome não acrescenta uma linha."""
    label = _mermaid_label(f"a{separator}b")

    assert separator not in label


def test_the_separators_already_covered_still_are() -> None:
    """Não-regressão do que `_LABEL_CONTROL_RE` já cobria."""
    for separator in ("\r", "\n", "\t", "\f", "\v"):
        assert separator not in _mermaid_label(f"a{separator}b")


def test_a_normal_label_is_unchanged() -> None:
    assert "Edge gateway" in _mermaid_label("Edge gateway")


# --- limite de entrada: profundidade do ficheiro de regras ---------------------------------


def test_a_deeply_nested_rules_file_is_refused_as_a_value_error(tmp_path: Path) -> None:
    """O contrato do loader é `ValueError`; `RecursionError` escapava-lhe."""
    rules = tmp_path / "deep.yaml"
    rules.write_text("a: " + "[" * 3000 + "]" * 3000, encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        load_custom_rules(rules)

    assert not isinstance(exc.value, RecursionError)


def test_the_rules_file_bound_is_the_same_one_the_document_uses(tmp_path: Path) -> None:
    """Ligar o consumidor ao limite existente, em vez de inventar um segundo."""
    from otm_core_schema.io import ENV_MAX_DOCUMENT_DEPTH

    rules = tmp_path / "deep.yaml"
    rules.write_text("a: " + "[" * 3000 + "]" * 3000, encoding="utf-8")

    with pytest.raises(ValueError, match=ENV_MAX_DOCUMENT_DEPTH):
        load_custom_rules(rules)


def test_an_ordinary_rules_file_still_loads(tmp_path: Path) -> None:
    rules = tmp_path / "ok.yaml"
    rules.write_text(
        "id: rs\n"
        "rules:\n"
        "  - id: a\n"
        "    title: 'Rule A'\n"
        "    stride: tampering\n"
        "    match:\n"
        "      component:\n"
        "        kind: [process]\n",
        encoding="utf-8",
    )

    assert load_custom_rules(rules).id == "rs"


# --- limite de entrada: comprimento de cada `refs` -----------------------------------------


def _ruleset(refs: list[str]) -> dict:
    return {
        "id": "rs",
        "rules": [
            {
                "id": "a",
                "title": "T",
                "stride": "tampering",
                "match": {"component": {"kind": ["process"]}},
                "refs": refs,
            }
        ],
    }


def test_an_enormous_single_ref_is_refused() -> None:
    """`max_length=20` limita a lista; cada item precisa do seu próprio tecto."""
    with pytest.raises(ValueError):
        CustomRuleSet.model_validate(_ruleset(["R" * 400_000]))


def test_an_ordinary_ref_is_accepted() -> None:
    ruleset = CustomRuleSet.model_validate(_ruleset(["ISO/IEC 27001:2022 A.8.24", "internal-std-014"]))

    assert ruleset.rules[0].refs == ["ISO/IEC 27001:2022 A.8.24", "internal-std-014"]


def test_the_list_length_cap_still_applies() -> None:
    """A correção acrescenta um tecto; não pode ter removido o que já existia."""
    with pytest.raises(ValueError):
        CustomRuleSet.model_validate(_ruleset([f"ref-{i}" for i in range(50)]))


# --- higiene de escrita: `otm import repo` -------------------------------------------------
#
# Não é um limite, é a mesma família: um guarda que os irmãos têm e este não tinha.
# `_emit_repo_scan` era o único caminho de escrita do CLI que não passava `sources=` ao emissor,
# por isso destruía um ficheiro do repositório analisado segundos depois de o ler, com **exit 0**
# — enquanto `export`, `analyze`, `diff` e `backlog` recusam o caso equivalente com exit 1.


def _node_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "package.json").write_text('{"name":"x"}\n', encoding="utf-8")
    (root / "src" / "app.js").write_text("PRECIOUS SOURCE\n", encoding="utf-8")
    return root


def test_import_repo_refuses_to_write_over_a_file_it_just_scanned(tmp_path: Path) -> None:
    from otm_cli.cli import app
    from typer.testing import CliRunner

    root = _node_repo(tmp_path)
    victim = root / "src" / "app.js"

    result = CliRunner().invoke(app, ["import", "repo", str(root), "--json-out", str(victim)])

    assert result.exit_code == 1
    assert victim.read_text(encoding="utf-8") == "PRECIOUS SOURCE\n"


def test_import_repo_still_writes_to_a_new_path_inside_the_same_tree(tmp_path: Path) -> None:
    """O guarda é sobre ficheiros lidos, não sobre a árvore: `--json-out ./scan.json` é legítimo."""
    from otm_cli.cli import app
    from typer.testing import CliRunner

    root = _node_repo(tmp_path)
    out = root / "scan.json"

    result = CliRunner().invoke(app, ["import", "repo", str(root), "--json-out", str(out)])

    assert result.exit_code == 0, result.output
    assert json.loads(out.read_text(encoding="utf-8"))["files_scanned"] >= 1


# --- higiene de escrita: o default do PDF premium ------------------------------------------
#
# `otm report -f pdf` sem `-o` escreve `report-premium.pdf` no directório actual — a única
# escrita do CLI para um caminho que o utilizador não nomeou. Substituir continua a ser o
# comportamento (recusar quebraria quem corre isto em sequência); o que muda é o silêncio.


def _pdf_invocation(tmp_path: Path, *extra: str):
    from otm_cli.cli import app
    from typer.testing import CliRunner

    model = tmp_path / "m.otm.yaml"
    model.write_text(_MINIMAL.read_text(encoding="utf-8"), encoding="utf-8")
    return CliRunner().invoke(app, ["report", str(model), "--level", "executive", "-f", "pdf", *extra])


def test_replacing_the_unnamed_default_is_announced(tmp_path: Path, monkeypatch) -> None:
    """Correr duas vezes na mesma pasta deitava fora o primeiro entregável sem dizer nada."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "report-premium.pdf").write_text("PRIOR DELIVERABLE", encoding="utf-8")

    result = _pdf_invocation(tmp_path)

    assert result.exit_code == 0, result.output
    assert "replaced" in result.output


def test_a_first_run_says_nothing_about_replacing(tmp_path: Path, monkeypatch) -> None:
    """O aviso é sobre substituir, não sobre escrever."""
    monkeypatch.chdir(tmp_path)

    result = _pdf_invocation(tmp_path)

    assert result.exit_code == 0, result.output
    assert "replaced" not in result.output


def test_an_explicit_output_is_never_second_guessed(tmp_path: Path, monkeypatch) -> None:
    """Com `-o` o caminho é escolha de quem chamou, como em qualquer CLI."""
    monkeypatch.chdir(tmp_path)
    named = tmp_path / "mine.pdf"
    named.write_text("PRIOR", encoding="utf-8")

    result = _pdf_invocation(tmp_path, "-o", str(named))

    assert result.exit_code == 0, result.output
    assert "replaced" not in result.output


# --- identidade: SARIF diz a que a sua URI é relativa --------------------------------------


def test_sarif_declares_what_its_uri_is_relative_to() -> None:
    """Sem `uriBaseId` o consumidor adivinha, e o GitHub adivinha "raiz do repositório".

    Com `working-directory: apps/api` na Action, `sub/m.otm.yaml` era resolvido a partir da raiz
    do repositório — um caminho que pode existir e ser **outro ficheiro**.
    """
    from otm_exporters.analysis_sarif import export_analysis_sarif_obj

    result = analyze_document(load_document_from_yaml_path(_MINIMAL))
    sarif = export_analysis_sarif_obj(result, model_uri="sub/m.otm.yaml")
    run = sarif["runs"][0]

    assert run["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uriBaseId"]
    assert run["originalUriBaseIds"]


def test_every_result_carries_the_same_declared_base() -> None:
    """Um resultado sem base num run que a declara é pior do que nenhum: silenciosamente relativo."""
    from otm_exporters.analysis_sarif import export_analysis_sarif_obj

    result = analyze_document(load_document_from_yaml_path(_MINIMAL))
    run = export_analysis_sarif_obj(result, model_uri="sub/m.otm.yaml")["runs"][0]
    declared = set(run["originalUriBaseIds"])

    for res in run["results"]:
        base = res["locations"][0]["physicalLocation"]["artifactLocation"]["uriBaseId"]
        assert base in declared


# --- identidade: o round-trip OTM preserva ids que já eram válidos --------------------------


def test_slug_id_leaves_an_already_valid_id_alone() -> None:
    """`User.Portal` casa `ENTITY_ID_PATTERN` sem alteração; reescrevê-lo só quebra identidade."""
    from otm_artifact_import.builders import slug_id

    for valid in ("User.Portal", "API-Gateway", "Flow.One", "db_2", "a"):
        assert slug_id(valid) == valid


def test_slug_id_still_slugifies_free_text() -> None:
    """A correção não pode ter desligado a slugificação do que não é um id."""
    from otm_artifact_import.builders import slug_id

    assert slug_id("Orders API") == "orders_api"
    assert slug_id("My Service (v2)") == "my_service_v2"
    assert slug_id("has spaces") == "has_spaces"


def test_an_over_long_valid_id_is_still_capped() -> None:
    """O tecto de 56 continua a valer — um id válido mas enorme não passa por ser válido."""
    from otm_artifact_import.builders import slug_id

    assert len(slug_id("a" * 200)) == 56
