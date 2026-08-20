from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import sysconfig
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

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


def _pytest_collected(xml_path: Path) -> int | None:
    """Quantos testes o junitxml diz que correram, ou `None` se nao houver ficheiro legivel."""
    try:
        root = ET.parse(xml_path).getroot()
    except (OSError, ET.ParseError):
        return None
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    return sum(int(s.get("tests", 0)) for s in suites) or None


def _cmd(exe: str) -> str:
    # Windows resolves npm as npm.cmd when not using a shell
    if os.name == "nt" and not exe.lower().endswith(".cmd"):
        return f"{exe}.cmd"
    return exe


def _run(cmd: list[str], *, cwd: Path, out_file: Path, env: dict[str, str] | None = None) -> int:
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True)
    out_file.write_text(
        f"$ {' '.join(cmd)}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}\n",
        encoding="utf-8",
    )
    return proc.returncode


def main() -> int:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifacts = ARTIFACTS_ROOT / ts
    artifacts.mkdir(parents=True, exist_ok=True)

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

    # 2.1) A suite Python inteira, que e o que o CI corre (`python -m pytest`, job `python`).
    # Este gate corria dois ficheiros. Nao era decisao registada em lado nenhum: era heranca, e
    # escondia que 38 testes nem coleccionavam (f4df962) alem de deixar ~3480 por executar.
    junit = artifacts / "pytest-full.xml"
    pystep("pytest_full_suite", ["-m", "pytest", "-q", f"--junitxml={junit}"])

    # E a prova de que o passo acima correu a suite, e nao um pedaco dela. Sem isto, um erro de
    # coleccao, um `testpaths` mal apontado ou um filtro esquecido dariam verde tendo medido
    # quase nada -- que e a classe de defeito que este gate existe para apanhar.
    collected = _pytest_collected(junit)
    if collected is None:
        blocked("pytest_full_suite_size", f"sem junitxml legivel em {junit}")
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
    npm = _cmd("npm")
    step("web_npm_ci", [npm, "ci"], web)
    step("web_build_portable", [npm, "run", "ci:build:portable"], web)
    # As 503 assercoes de vitest. O CI corre-as (`npm test`, job `web`), este gate nao corria —
    # a mesma assimetria que ja tinha sido corrigida neste ficheiro para o `e2e:critical`, e
    # que deixava o veredito local a afirmar mais do que tinha medido. Custa 8 s.
    step("web_unit_tests", [npm, "test"], web)
    # Avoid npx resolution variance: call local Playwright CLI
    step(
        "web_playwright_install_chromium",
        ["node", r".\node_modules\@playwright\test\cli.js", "install", "chromium"],
        web,
    )
    step("web_e2e_smoke_portable", [npm, "run", "e2e:smoke:portable"], web)
    # O conjunto critico tambem, que e o que o CI corre no job `web-e2e-critical`. Com so o
    # smoke aqui, uma asserção de `cockpit.spec.ts` ficou a exigir o plural que 45b2994 tinha
    # acabado de corrigir e o gate local continuou verde. `e2e:hybrid` NAO entra: precisa de
    # ligar um servidor em 127.0.0.1:8000, que nem toda a maquina permite, e um passo que pode
    # falhar por causa do ambiente nao pertence a um gate cujo veredito tem de significar algo.
    step("web_e2e_critical", [npm, "run", "e2e:critical"], web)
    # E o resto dos specs. Ate aqui o CI e este gate corriam so `smoke` + `critical`, o que
    # deixava `diagram`, `pdf`, `history`, `i18n` e `release` sem nenhum gate a executa-los —
    # incluindo o teste que fixa o defeito HIGH de perda de dados do inspector do diagrama
    # (02834b2). O conjunto inteiro corre em 35 s, por isso nao havia troca a fazer.
    step("web_e2e_rest", [npm, "run", "e2e:rest"], web)

    (artifacts / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    any_fail = any(s["exit_code"] != 0 for s in steps)
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
