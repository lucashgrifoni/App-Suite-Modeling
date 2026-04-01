from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts" / "test-app-validation"
PY_MODULE = "otm_cli.main"
APP_ENTRY = "app.py"


APPS = [
    {
        "id": "finance",
        "smoke_script": ROOT / "fixtures" / "apps" / "finance" / APP_ENTRY,
        "model": ROOT / "examples" / "test-apps" / "finance-wallet.otm.yaml",
        "methodology": "stride",
    },
    {
        "id": "health",
        "smoke_script": ROOT / "fixtures" / "apps" / "health" / APP_ENTRY,
        "model": ROOT / "examples" / "test-apps" / "health-clinic.otm.yaml",
        "methodology": "linddun",
    },
    {
        "id": "ecommerce-subscription",
        "smoke_script": ROOT / "fixtures" / "apps" / "ecommerce_subscription" / APP_ENTRY,
        "model": ROOT / "examples" / "test-apps" / "ecommerce-subscription.otm.yaml",
        "methodology": "pasta",
    },
]


def _env_for_cli() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath_parts = [
        ROOT / "packages" / "core-schema",
        ROOT / "packages" / "threat-engine",
        ROOT / "packages" / "framework-mappings",
        ROOT / "packages" / "exporters",
        ROOT / "packages" / "diagram-engine",
        ROOT / "packages" / "industry-packs",
        ROOT / "apps" / "cli",
        ROOT / "apps" / "api",
    ]
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([str(p) for p in pythonpath_parts] + ([prev] if prev else []))
    return env


def run_and_log(cmd: list[str], out_file: Path, env: dict[str, str]) -> int:
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    out_file.write_text(
        f"$ {' '.join(cmd)}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}\n",
        encoding="utf-8",
    )
    return proc.returncode


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    env = _env_for_cli()
    summary: dict[str, dict[str, object]] = {}

    for app in APPS:
        app_id = app["id"]
        app_dir = ARTIFACTS / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        status = {
            "smoke_ok": False,
            "validate_ok": False,
            "analyze_ok": False,
            "report_ok": False,
            "methodology": app["methodology"],
        }

        smoke_rc = run_and_log([sys.executable, str(app["smoke_script"])], app_dir / "smoke.stdout.log", env)
        status["smoke_ok"] = smoke_rc == 0

        validate_cmd = [sys.executable, "-m", PY_MODULE, "validate", str(app["model"])]
        validate_rc = run_and_log(validate_cmd, app_dir / "validate.stdout.log", env)
        status["validate_ok"] = validate_rc == 0

        analyze_json = app_dir / "analyze.json"
        analyze_cmd = [
            sys.executable,
            "-m",
            PY_MODULE,
            "analyze",
            str(app["model"]),
            "--methodology",
            str(app["methodology"]),
            "--json-out",
            str(analyze_json),
        ]
        analyze_rc = run_and_log(analyze_cmd, app_dir / "analyze.stdout.log", env)
        status["analyze_ok"] = analyze_rc == 0 and analyze_json.exists()

        report_cmd = [
            sys.executable,
            "-m",
            PY_MODULE,
            "report",
            str(app["model"]),
            "--output",
            str(app_dir / "report.md"),
        ]
        report_rc = run_and_log(report_cmd, app_dir / "report.stdout.log", env)
        status["report_ok"] = report_rc == 0

        summary[app_id] = status

    (ARTIFACTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    any_fail = any(not all(bool(v) for k, v in s.items() if k.endswith("_ok")) for s in summary.values())
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
