"""Regressions for two engine defects found in the deep code review.

1. PLOT4ai `ai_system_context.heuristic_ids_by_layer` must have a deterministic
   key order (previously seeded from `set(...)`, randomized by PYTHONHASHSEED,
   which broke serialized-output reproducibility).
2. An unencrypted data flow that does NOT cross a trust boundary must not have
   its L×I double-counted (the caller OR-ed `unencrypted` into `crosses_boundary`
   while `risk_calc` already penalized `encrypted is False`, inflating 4×4 to 5×5).
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine import analyze_document
from otm_threat_engine.ai_modeling.summary import PLOT4AI_HEURISTIC_LAYER

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"
_PLOT4AI = sorted(glob.glob(str(_ROOT / "examples" / "plot4ai-calibration" / "*.otm.yaml")))


def test_plot4ai_layer_keys_follow_canonical_order() -> None:
    doc = load_document_from_yaml_path(_PLOT4AI[0])
    result = analyze_document(doc, methodology="plot4ai")
    ctx = result.ai_system_context
    assert ctx is not None
    canonical = list(dict.fromkeys(PLOT4AI_HEURISTIC_LAYER.values()))
    keys = list(ctx.heuristic_ids_by_layer.keys())
    # keys must appear in the canonical first-seen order (a subsequence of it)
    assert keys == [layer for layer in canonical if layer in keys]


def test_plot4ai_summary_key_order_is_seed_independent() -> None:
    """Serialized key order must be identical under different PYTHONHASHSEED values."""
    snippet = (
        "import json, glob;"
        "from otm_core_schema import load_document_from_yaml_path;"
        "from otm_threat_engine import analyze_document;"
        "f=sorted(glob.glob('examples/plot4ai-calibration/*.otm.yaml'))[0];"
        "r=analyze_document(load_document_from_yaml_path(f), methodology='plot4ai');"
        "print(json.dumps(list(r.ai_system_context.heuristic_ids_by_layer.keys())))"
    )

    def run(seed: int) -> list[str]:
        env = {**os.environ, "PYTHONHASHSEED": str(seed)}
        proc = subprocess.run(
            [sys.executable, "-c", snippet],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(_ROOT),
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout.strip().splitlines()[-1])

    first = run(1)
    assert first  # sanity: there is some grouped output
    assert run(42) == first
    assert run(9999) == first


def test_internal_unencrypted_flow_not_double_counted() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc)
    by_id = {h.id: h for h in result.heuristic_threats}
    # `to_db` is an unencrypted flow that stays inside the `vpc` boundary.
    flow_threat = by_id.get("eng_flow_to_db_tampering")
    assert flow_threat is not None
    # 4×4 = 16 after removing the unencrypted double-count (was inflated to 5×5 = 25).
    assert flow_threat.risk.score == 16.0
