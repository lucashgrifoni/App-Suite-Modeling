from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import sysconfig
from datetime import UTC, datetime
from pathlib import Path

from dev_env import npm_command

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_ROOT = ROOT / "artifacts" / "global-regression-gate"

# ----------------------------------------------------------------------------------------------
# Interpretador isolado para os passos Python.
#
# Este gate corria no interpretador com que fosse invocado. MEDIDO em 2026-08-20, mesma arvore e
# mesmo minuto: no Python global desta maquina a suite completa da 27 falhas; num venv limpo
# construido do proprio `pyproject.toml` da 3483 passed, 0 failed. Nenhuma das falhas vem do
# produto. O global tem `svglib 1.6.0`, fixado la por outro projecto, onde `rlpycairo` e uma
# dependencia incondicional que arrasta `cairocffi` e exige a Cairo nativa; a resolucao limpa da
# `svglib 2.2.0`, onde `rlpycairo` esta atras de `extra == "bitmaps"` e nunca entra no grafo.
#
# A mesma sopa afectava as outras ferramentas: global `ruff 0.15.13` e `mypy 1.20.1` contra
# `0.16.3` e `2.3.1` numa resolucao limpa -- o gate lintava e tipava com versoes que o CI nao usa,
# e uma major de mypy de distancia. Ambas medidas verdes no venv antes desta mudanca.
#
# Sem isto o passo de `pytest` completo era impossivel de ligar: ficaria permanentemente vermelho
# por razoes de ambiente, que e precisamente o que descredibiliza um gate.
# ----------------------------------------------------------------------------------------------

#: Exactamente a linha do CI (`github-ci-cd.yml`, job `python`). Entra na chave do stamp.
GATE_EXTRAS = "dev,cli,api"
GATE_VENV = ROOT / ".gate-venv"
GATE_STAMP = GATE_VENV / ".gate-stamp.json"

#: Subir isto invalida os venvs existentes quando a receita de provisionamento muda.
GATE_PROVISION_SCHEMA = 1

#: Chao do que `python -m pytest` tem de recolher. MEDIDO: 3483 testes. Um passo que recolha muito
#: menos correu um subconjunto e passaria verde sem medir o que diz medir -- a classe de defeito
#: que este gate existe para apanhar. A folga absorve remocoes legitimas sem deixar passar um
#: colapso de coleccao (os `2 errors during collection` de f4df962 matavam a suite inteira).
PYTEST_MIN_TESTS = 3300


#: A prova de que a instalacao ficou utilizavel, e nao apenas que o `pip` saiu a zero. O `pip`
#: aceita um extra inexistente com um aviso e codigo 0: MEDIDO, um `GATE_EXTRAS` mal escrito dava
#: um venv sem ruff, mypy, bandit nem pytest, e o gate reportava sete falhas por ferramenta em vez
#: de dizer que o ambiente nao tinha sido construido. `otm_cli.main` esta aqui porque varios testes
#: o lancam em subprocesso, onde o `pythonpath` do pytest nao chega: so o editable o torna
#: importavel.
_IMPORT_PROBE = "import pytest, ruff, mypy, bandit, otm_cli.main, otm_api.main"


#: O workflow de CI e a fonte de verdade das versoes de runtime. Lidas de la, e nao copiadas para
#: aqui, para nao passarem a mentir no dia em que o CI subir uma delas.
CI_WORKFLOW = ROOT / ".github" / "workflows" / "github-ci-cd.yml"


def _ci_pinned_runtimes() -> dict[str, str] | None:
    """`{"python": "3.12", "node": "22"}` lido do workflow, ou `None` se as chaves mudaram.

    Devolver `None` em vez de `{}` e deliberado: um bloco `env:` renomeado tornaria a comparacao
    vazia, e uma comparacao vazia passa sempre. O chamador trata isso como falha, nao como acordo.
    """
    try:
        text = CI_WORKFLOW.read_text(encoding="utf-8")
    except OSError:
        return None
    found = {}
    for key, name in (("PYTHON_VERSION", "python"), ("NODE_VERSION", "node")):
        m = re.search(rf"^\s*{key}:\s*[\"']?([0-9.]+)[\"']?\s*$", text, re.MULTILINE)
        if not m:
            return None
        found[name] = m.group(1)
    return found


def _local_node_major() -> str | None:
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip().lstrip("v").split(".")[0] if out.returncode == 0 else None


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _gate_env() -> dict[str, str]:
    """Ambiente dos subprocessos, sem os canais que furam o isolamento do venv.

    `PYTHONPATH` e herdado pelo interpretador do venv: um modulo la colocado fica importavel la
    dentro, e o isolamento deixava de existir sem aviso. O cache do mypy e separado porque as duas
    versoes (global 1.20.1, venv 2.3.1) partilhavam `.mypy_cache` e uma invalidava o trabalho da
    outra a cada execucao.
    """
    env = os.environ.copy()
    for leak in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "VIRTUAL_ENV", "PIP_TARGET"):
        env.pop(leak, None)
    env["MYPY_CACHE_DIR"] = str(ROOT / ".mypy_cache-gate")
    return env


def _provision_key() -> str:
    """Identidade do venv. Muda quando muda a receita, o manifesto, o Python ou a plataforma."""
    digest = hashlib.sha256()
    for chunk in (
        str(GATE_PROVISION_SCHEMA).encode(),
        (ROOT / "pyproject.toml").read_bytes(),
        GATE_EXTRAS.encode(),
        f"{sys.version_info[0]}.{sys.version_info[1]}".encode(),
        sysconfig.get_platform().encode(),
    ):
        digest.update(chunk)
        digest.update(bytes([0]))
    return digest.hexdigest()


def _pytest_collected(count_path: Path) -> int | None:
    """Lê o total recolhido pelo pytest, se o gate recebeu um valor positivo."""
    try:
        collected = int(count_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return collected if collected > 0 else None


def _run(cmd: list[str], *, cwd: Path, out_file: Path, env: dict[str, str] | None = None) -> int:
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True)
    out_file.write_text(
        f"$ {' '.join(cmd)}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}\n",
        encoding="utf-8",
    )
    return proc.returncode


def main() -> int:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    artifacts = ARTIFACTS_ROOT / ts
    artifacts.mkdir(parents=True)

    summary: dict[str, object] = {"timestamp_utc": ts, "steps": []}
    steps: list[dict[str, object]] = summary["steps"]  # type: ignore[assignment]

    def step(name: str, cmd: list[str], cwd: Path) -> int:
        log = artifacts / f"{name}.log"
        rc = _run(cmd, cwd=cwd, out_file=log, env=_gate_env())
        steps.append(
            {
                "name": name,
                "cwd": str(cwd),
                "cmd": cmd,
                "exit_code": rc,
                "log": str(log),
            }
        )
        return rc

    def blocked(name: str, reason: str) -> None:
        """Passo que nao correu. Nunca conta como PASS: entra com exit 1 e diz porque."""
        steps.append({"name": name, "status": "BLOCKED", "reason": reason, "exit_code": 1})

    def ensure_gate_venv() -> Path | None:
        """Devolve o interpretador do venv do gate, ou `None` se nao foi possivel provisiona-lo.

        Nunca ha recurso ao interpretador global: era exactamente isso que tornava o veredito
        deste gate dependente do que houvesse instalado na maquina.
        """
        key = _provision_key()
        py = _venv_python(GATE_VENV)
        if py.exists() and GATE_STAMP.exists():
            try:
                if json.loads(GATE_STAMP.read_text(encoding="utf-8")).get("key") == key:
                    steps.append({"name": "gate_venv_reused", "exit_code": 0, "key": key[:12]})
                    return py
            except (OSError, ValueError):
                pass  # stamp ilegivel: reconstroi

        if step("gate_venv_create", [sys.executable, "-m", "venv", "--clear", str(GATE_VENV)], ROOT):
            return None
        if step("gate_venv_install", [str(py), "-m", "pip", "install", "-q", "-e", f".[{GATE_EXTRAS}]"], ROOT):
            return None
        if step("gate_venv_probe", [str(py), "-c", _IMPORT_PROBE], ROOT):
            return None
        # So depois de a instalacao responder e que o stamp e escrito: um venv meio-instalado que
        # ficasse marcado como bom seria reutilizado para sempre.
        GATE_STAMP.write_text(json.dumps({"key": key, "extras": GATE_EXTRAS}), encoding="utf-8")
        return py

    # -1) As versoes de runtime que este gate usa contra as que o CI fixa.
    #
    # O gate diz de si proprio que e o proxy local do CI. Essa afirmacao e falsificavel, e ate aqui
    # ninguem a verificava: o venv e construido do Python com que o gate for invocado, e os passos
    # web correm com o Node que estiver no PATH. MEDIDO hoje: Python coincide (3.12 dos dois
    # lados), Node NAO -- CI fixa 22, esta maquina tem 24, dois majors de distancia.
    #
    # Isto NAO e uma alegacao de que o codigo esta partido. Medi o que a evidencia dava para medir:
    # dos 176 pacotes que declaram `engines.node` no lockfile, nenhum tem tecto que exclua o 24, e
    # o `npm ci` nao emitiu um unico aviso de engine. O que fica por medir e o comportamento em
    # execucao, que so se sabe correndo nas duas versoes.
    #
    # Por isso o passo reprova: nao porque o produto esteja mal, mas porque o veredito dos passos
    # web nao pode ser apresentado como equivalente ao do CI enquanto os runtimes divergirem. Ha
    # duas maneiras de o resolver, e a escolha e do dono: instalar o Node 22 (que e o LTS, e o que
    # o CI fixa), ou subir `NODE_VERSION` no workflow se a intencao for mesmo o 24.
    pins = _ci_pinned_runtimes()
    local = {"python": f"{sys.version_info[0]}.{sys.version_info[1]}", "node": _local_node_major()}
    if pins is None:
        blocked("runtime_version_parity", f"nao encontrei PYTHON_VERSION/NODE_VERSION em {CI_WORKFLOW}")
    else:
        diff = {k: {"ci": v, "local": local[k]} for k, v in pins.items() if local[k] != v}
        steps.append(
            {
                "name": "runtime_version_parity",
                "ci": pins,
                "local": local,
                "divergentes": diff or None,
                "exit_code": 1 if diff else 0,
            }
        )

    py = ensure_gate_venv()

    def pystep(name: str, args: list[str], cwd: Path = ROOT) -> int:
        """Passo que precisa do interpretador do gate. Sem venv fica BLOCKED, nunca PASS."""
        if py is None:
            blocked(name, "venv do gate indisponivel; recusado correr no interpretador global")
            return 1
        return step(name, [str(py), *args], cwd)

    # 0) Fronteira core/adaptador (rápido; alinhado a CI e CONTRACT_AND_SNAPSHOTS.md)
    pystep("check_core_adapter_boundary", ["scripts/check_core_adapter_boundary.py"])

    # 0.1) Lint e formatacao, no MESMO escopo que o CI usa (`packages apps tests`), porque este
    # gate e o proxy local do CI e nao os corria. Onze ficheiros desta campanha falhavam
    # `ruff format --check` -- um passo bloqueante em `github-ci-cd.yml` -- e so foram apanhados
    # por uma verificacao manual: o gate dava verde num branch que o CI teria recusado.
    pystep("ruff_lint", ["-m", "ruff", "check", "packages", "apps", "tests"])
    pystep("ruff_format_check", ["-m", "ruff", "format", "--check", "packages", "apps", "tests"])

    # 0.2) Tipos e SAST, os outros dois passos bloqueantes do mesmo job de CI. Faltavam aqui pela
    # mesma razao que o ruff faltava, e o mypy estava vermelho por causa de um `type: ignore` que
    # este proprio branch acrescentou. `pip-audit` NAO esta aqui: o CI instala-o num venv proprio e
    # ele precisa de rede, portanto correr-lo daqui daria um resultado que depende do ambiente.
    # Fica de fora explicitamente, para nao passar por PASS o que nao foi executado.
    pystep(
        "mypy_monorepo",
        [
            "-m",
            "mypy",
            "packages/core-schema/otm_core_schema",
            "apps/api/otm_api",
            "packages/explainability/otm_explainability",
            "packages/framework-mappings/otm_framework_mappings",
            "packages/diagram-engine/otm_diagram_engine",
            "apps/cli/otm_cli",
            "packages/exporters/otm_exporters",
            "packages/artifact-import/otm_artifact_import",
            "packages/report-premium/otm_report_premium",
            "packages/threat-engine/otm_threat_engine",
            "packages/industry-packs/otm_industry_packs",
        ],
    )
    pystep("bandit_sast", ["-m", "bandit", "-r", "packages", "apps", "-ll", "-q"])

    # 1) Motor / core smoke (release-candidate)
    pystep("pytest_smoke_release_candidate", ["-m", "pytest", "tests/test_smoke_release_candidate.py", "-q"])
    pystep("pytest_threat_engine", ["-m", "pytest", "tests/test_threat_engine.py", "-q"])

    # 2) Fixtures validation flow (end-to-end)
    pystep("test_apps_validation", ["scripts/run_test_app_validation.py"])

    # 2.0.1) Frescura do contrato, lado Python: `contracts/openapi.json` contra o que a app
    # FastAPI produz hoje. E um passo bloqueante do mesmo job de CI e faltava aqui, portanto uma
    # deriva do contrato passava o gate local sem ninguem reparar. Determinista, offline,
    # read-only -- verificado por leitura antes de ser ligado.
    pystep("openapi_contract_fresh", ["scripts/verify_openapi_up_to_date.py"])

    # 2.1) A suite Python inteira, que e o que o CI corre (`python -m pytest`, job `python`).
    # Este gate corria dois ficheiros. Nao era decisao registada em lado nenhum: era heranca, e
    # escondia que 38 testes nem coleccionavam (f4df962) alem de deixar ~3480 por executar.
    junit = artifacts / "pytest-full.xml"
    count_file = artifacts / "pytest-full-count.txt"
    pystep(
        "pytest_full_suite",
        [
            "-m",
            "pytest",
            "-q",
            "-p",
            "scripts.pytest_gate_count",
            f"--junitxml={junit}",
            f"--gate-count-file={count_file}",
        ],
    )

    # E a prova de que o passo acima correu a suite, e nao um pedaco dela. Sem isto, um erro de
    # coleccao, um `testpaths` mal apontado ou um filtro esquecido dariam verde tendo medido
    # quase nada -- que e a classe de defeito que este gate existe para apanhar.
    collected = _pytest_collected(count_file)
    if collected is None:
        blocked("pytest_full_suite_size", f"sem contagem legível em {count_file}")
    else:
        steps.append(
            {
                "name": "pytest_full_suite_size",
                "collected": collected,
                "floor": PYTEST_MIN_TESTS,
                "exit_code": 0 if collected >= PYTEST_MIN_TESTS else 1,
            }
        )

    # 3) Web build + e2e smoke (Windows portable path)
    web = ROOT / "apps" / "web"
    try:
        npm = npm_command()
    except FileNotFoundError as error:
        blocked("web_npm", str(error))
        npm = []

    def webstep(name: str, args: list[str]) -> None:
        if not npm:
            blocked(name, "npm indisponível")
            return
        step(name, [*npm, *args], web)

    webstep("web_npm_ci", ["ci"])
    webstep("web_build_portable", ["run", "ci:build:portable"])
    # As 503 assercoes de vitest. O CI corre-as (`npm test`, job `web`), este gate nao corria —
    # a mesma assimetria que ja tinha sido corrigida neste ficheiro para o `e2e:critical`, e
    # que deixava o veredito local a afirmar mais do que tinha medido. Custa 8 s.
    # A outra ponta da mesma cadeia: `contracts/openapi.json` contra os tipos TS gerados e
    # versionados. Sem os dois lados, uma deriva no meio da cadeia fica invisivel — o contrato
    # pode estar alinhado com a app e os tipos do web nao, ou o inverso.
    webstep("web_contracts_check", ["run", "contracts:check"])
    webstep("web_unit_tests", ["test"])
    # Avoid npx resolution variance: call local Playwright CLI
    step(
        "web_playwright_install_chromium",
        ["node", r".\node_modules\@playwright\test\cli.js", "install", "chromium"],
        web,
    )
    webstep("web_e2e_smoke_portable", ["run", "e2e:smoke:portable"])
    # O conjunto critico tambem, que e o que o CI corre no job `web-e2e-critical`. Com so o
    # smoke aqui, uma asserção de `cockpit.spec.ts` ficou a exigir o plural que 45b2994 tinha
    # acabado de corrigir e o gate local continuou verde. `e2e:hybrid` NAO entra: precisa de
    # ligar um servidor em 127.0.0.1:8000, que nem toda a maquina permite, e um passo que pode
    # falhar por causa do ambiente nao pertence a um gate cujo veredito tem de significar algo.
    webstep("web_e2e_critical", ["run", "e2e:critical"])
    # E o resto dos specs. Ate aqui o CI e este gate corriam so `smoke` + `critical`, o que
    # deixava `diagram`, `pdf`, `history`, `i18n` e `release` sem nenhum gate a executa-los —
    # incluindo o teste que fixa o defeito HIGH de perda de dados do inspector do diagrama
    # (02834b2). O conjunto inteiro corre em 35 s, por isso nao havia troca a fazer.
    webstep("web_e2e_rest", ["run", "e2e:rest"])

    (artifacts / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    any_fail = any(s["exit_code"] != 0 for s in steps)
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
