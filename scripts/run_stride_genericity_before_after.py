from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts" / "stride-genericity-reduction"
PY_MODULE = "otm_cli.main"

APPS = [
    {
        "id": "finance",
        "model": ROOT / "examples" / "test-apps" / "finance-wallet.otm.yaml",
        "methodology": "stride",
    },
    {
        "id": "ecommerce-subscription",
        "model": ROOT / "examples" / "test-apps" / "ecommerce-subscription.otm.yaml",
        "methodology": "pasta",
    },
]


ENGINE_MATRIX = {
    "engine_suppression_off": "0",
    "engine_suppression_on": "1",
}
VIEW_MODES = ("legacy", "harmonized")


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


def _count_stride_generic_lines(report_text: str) -> int:
    # Heurística simples e estável para comparabilidade: linhas de item que citam `eng_` e não são `biz_`.
    n = 0
    for line in report_text.splitlines():
        l = line.lower()
        if l.strip().startswith("- **") and "`eng_" in l and "`biz_" not in l:
            n += 1
    return n


def _run_analyze(*, app: dict[str, object], env: dict[str, str], out_dir: Path) -> tuple[bool, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    analyze_json = out_dir / "analyze.json"
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
    analyze_rc = run_and_log(analyze_cmd, out_dir / "analyze.stdout.log", env)
    return analyze_rc == 0 and analyze_json.exists(), analyze_json


def _run_report_variant(
    *,
    app: dict[str, object],
    base_env: dict[str, str],
    analyze_json: Path,
    app_summary: dict[str, object],
    engine_mode: str,
    toggle: str,
    view_mode: str,
) -> None:
    mode_dir = ARTIFACTS / engine_mode / view_mode / str(app["id"])
    mode_dir.mkdir(parents=True, exist_ok=True)

    env_mode = base_env.copy()
    env_mode["OTM_ENGINE_STRIDE_NOISE_SUPPRESSION"] = toggle
    env_mode["OTM_MARKDOWN_VIEW_MODE"] = view_mode

    report_path = mode_dir / "report.md"
    report_cmd = [
        sys.executable,
        "-m",
        PY_MODULE,
        "report",
        str(app["model"]),
        "--output",
        str(report_path),
    ]
    report_rc = run_and_log(report_cmd, mode_dir / "report.stdout.log", env_mode)
    ok = report_rc == 0 and report_path.exists()
    app_summary[f"report_{engine_mode}_{view_mode}_ok"] = ok

    if ok:
        txt = report_path.read_text(encoding="utf-8", errors="replace")
        app_summary[f"stride_generic_item_lines_{engine_mode}_{view_mode}"] = _count_stride_generic_lines(txt)

    if analyze_json.exists():
        (mode_dir / "analyze.json").write_text(analyze_json.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    env = _env_for_cli()

    summary: dict[str, object] = {
        "apps": {},
        "notes": {
            "objective": "Comparação before/after do Markdown sem alterar analyze.json.",
            "view_modes": ["legacy", "harmonized"],
            "engine_modes": ["engine_suppression_off", "engine_suppression_on"],
            "env_var_markdown": "OTM_MARKDOWN_VIEW_MODE",
            "env_var_engine": "OTM_ENGINE_STRIDE_NOISE_SUPPRESSION",
        },
    }

    for app in APPS:
        app_id = app["id"]
        app_summary: dict[str, object] = {}

        analyze_ok, analyze_json = _run_analyze(app=app, env=env, out_dir=ARTIFACTS / "analyze" / str(app_id))
        app_summary["analyze_ok"] = analyze_ok

        for engine_mode, toggle in ENGINE_MATRIX.items():
            for view_mode in VIEW_MODES:
                _run_report_variant(
                    app=app,
                    base_env=env,
                    analyze_json=analyze_json,
                    app_summary=app_summary,
                    engine_mode=engine_mode,
                    toggle=toggle,
                    view_mode=view_mode,
                )

        summary["apps"][app_id] = app_summary

    (ARTIFACTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    any_fail = False
    for _app_id, s in summary["apps"].items():  # type: ignore[assignment]
        if not all(bool(v) for k, v in s.items() if k.endswith("_ok")):
            any_fail = True
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

