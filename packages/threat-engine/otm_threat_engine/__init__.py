"""
Motor de análise OTM — consome `ThreatModelDocument` e produz `AnalysisResult`.

**Separação de responsabilidades**
- *Parsing / schema*: `otm_core_schema` (YAML/JSON e validação estrutural estrita).
- *Análise*: este pacote (`ThreatAnalysisEngine`, heurísticas STRIDE, risco).
- *Exportação*: `otm_exporters` (Markdown, Mermaid, …) — não importado aqui.

**Uso típico**

```python
from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine import ThreatAnalysisEngine, merge_heuristic_threats

doc = load_document_from_yaml_path("modelo.otm.yaml")
result = ThreatAnalysisEngine().analyze(doc)
# result = ThreatAnalysisEngine().analyze(doc, pack=load_pack("finance"))

updated = merge_heuristic_threats(doc, result.heuristic_threats)
```
"""

from otm_threat_engine.analysis_diff import diff_analysis_results
from otm_threat_engine.comparison_models import AnalysisDiff, ThreatModelComparisonResult
from otm_threat_engine.engine import ThreatAnalysisEngine, analyze_document
from otm_threat_engine.framework_refs import enrich_analysis_framework_refs, enrich_heuristic_threat
from otm_threat_engine.merge import merge_heuristic_threats
from otm_threat_engine.methodologies import recommend_methodology
from otm_threat_engine.methodology_lenses.contracts import MethodologyRecommendation
from otm_threat_engine.remediation import (
    BACKLOG_CONTRACT_VERSION,
    BacklogItem,
    FindingRef,
    RemediationBacklog,
    build_remediation_backlog,
)
from otm_threat_engine.result import (
    AnalysisResult,
    AnalysisSummary,
    HeuristicThreat,
    StructuralFinding,
    TrustBoundaryFinding,
)
from otm_threat_engine.severity import (
    SEVERITY_ORDER,
    Severity,
    severity_at_least,
    severity_for_score,
    severity_rank,
)
from otm_threat_engine.threat_model_comparison import compare_threat_models
from otm_threat_engine.version import ENGINE_VERSION

__all__ = [
    "BACKLOG_CONTRACT_VERSION",
    "BacklogItem",
    "ENGINE_VERSION",
    "FindingRef",
    "RemediationBacklog",
    "build_remediation_backlog",
    "AnalysisDiff",
    "ThreatModelComparisonResult",
    "AnalysisResult",
    "AnalysisSummary",
    "HeuristicThreat",
    "StructuralFinding",
    "ThreatAnalysisEngine",
    "TrustBoundaryFinding",
    "analyze_document",
    "compare_threat_models",
    "diff_analysis_results",
    "enrich_analysis_framework_refs",
    "enrich_heuristic_threat",
    "MethodologyRecommendation",
    "merge_heuristic_threats",
    "recommend_methodology",
    "SEVERITY_ORDER",
    "Severity",
    "severity_at_least",
    "severity_for_score",
    "severity_rank",
]
