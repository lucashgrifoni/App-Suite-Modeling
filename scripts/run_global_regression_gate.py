from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_ROOT = ROOT / "artifacts" / "global-regression-gate"


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

    def step(name: str, cmd: list[str], cwd: Path) -> None:
        log = artifacts / f"{name}.log"
        rc = _run(cmd, cwd=cwd, out_file=log, env=os.environ.copy())
        summary["steps"].append(
            {
                "name": name,
                "cwd": str(cwd),
                "cmd": cmd,
                "exit_code": rc,
                "log": str(log),
            }
        )

    # 0) Fronteira core/adaptador (rápido; alinhado a CI e CONTRACT_AND_SNAPSHOTS.md)
    step(
        "check_core_adapter_boundary",
        [sys.executable, "scripts/check_core_adapter_boundary.py"],
        ROOT,
    )

    # 0.1) Lint e formatacao, no MESMO escopo que o CI usa (`packages apps tests`), porque este
    # gate e o proxy local do CI e nao os corria. Onze ficheiros desta campanha falhavam
    # `ruff format --check` -- um passo bloqueante em `github-ci-cd.yml` -- e so foram apanhados
    # por uma verificacao manual: o gate dava verde num branch que o CI teria recusado.
    step(
        "ruff_lint",
        [sys.executable, "-m", "ruff", "check", "packages", "apps", "tests"],
        ROOT,
    )
    step(
        "ruff_format_check",
        [sys.executable, "-m", "ruff", "format", "--check", "packages", "apps", "tests"],
        ROOT,
    )

    # 0.2) Tipos e SAST, os outros dois passos bloqueantes do mesmo job de CI. Faltavam aqui pela
    # mesma razao que o ruff faltava, e o mypy estava vermelho por causa de um `type: ignore` que
    # este proprio branch acrescentou. `pip-audit` NAO esta aqui: o CI instala-o num venv proprio e
    # ele precisa de rede, portanto correr-lo daqui daria um resultado que depende do ambiente.
    # Fica de fora explicitamente, para nao passar por PASS o que nao foi executado.
    step(
        "mypy_monorepo",
        [
            sys.executable,
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
        ROOT,
    )
    step(
        "bandit_sast",
        [sys.executable, "-m", "bandit", "-r", "packages", "apps", "-ll", "-q"],
        ROOT,
    )

    # 1) Motor / core smoke (release-candidate)
    step(
        "pytest_smoke_release_candidate",
        [sys.executable, "-m", "pytest", "tests/test_smoke_release_candidate.py", "-q"],
        ROOT,
    )
    step(
        "pytest_threat_engine",
        [sys.executable, "-m", "pytest", "tests/test_threat_engine.py", "-q"],
        ROOT,
    )

    # 2) Fixtures validation flow (end-to-end)
    step(
        "test_apps_validation",
        [sys.executable, "scripts/run_test_app_validation.py"],
        ROOT,
    )

    # 3) Web build + e2e smoke (Windows portable path)
    web = ROOT / "apps" / "web"
    npm = _cmd("npm")
    step("web_npm_ci", [npm, "ci"], web)
    step("web_build_portable", [npm, "run", "ci:build:portable"], web)
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

    (artifacts / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    any_fail = any(s["exit_code"] != 0 for s in summary["steps"])  # type: ignore[index]
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

