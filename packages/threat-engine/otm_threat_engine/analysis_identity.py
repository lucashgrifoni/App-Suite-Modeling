"""Do these two artifacts belong together? One vocabulary for every pairing guard.

Two *different* questions get asked about a stored `AnalysisResult`, and answering both with the
same signal — `document_title` — is what produced the pairing defects:

* **Same revision.** "Was this analysis produced from *this* document?" Asked by
  `otm report --analysis-json`, `otm backlog --document`, and every API route that takes a
  `document` and an `analysis` side by side. The two artifacts must describe the same revision;
  any divergence is an error.
* **Same system.** "Is this baseline an earlier version of *this* system?" Asked by
  `otm report --baseline` and `otm diff-analysis`. The two artifacts describe different
  revisions on purpose — divergence is the deliverable — but they must still be one system.

`document_title` answers neither. It is user-facing prose, so it is *not stable* across
revisions (renaming a model made `--baseline` refuse the exact pair it exists for) and it is
*not distinguishing* between models (`otm init -t <template>` copies the template's title
verbatim, so every model made from one template collides on it by construction, and an analysis
of one was accepted for another).

What the artifacts actually carry:

* `heuristic_threats[].target_*` — the modelled entities the analysis hangs threats off;
* `trust_boundary_findings[].{from,to}_boundary_id` — the boundary-to-boundary edges it saw.

Two facts about the engine make that enough, and both are pinned by tests:

1. Every component of the analysed document yields at least one heuristic threat
   (`append_component_heuristics` iterates `doc.components` unconditionally and
   `strides_for_component` never returns an empty tuple; noise suppression *flags*
   `skipped_as_duplicate` rather than dropping the record). So a component the analysis never
   names is a component that did not exist when the analysis ran — a staleness signal that a
   title comparison cannot see. Every lens holds this: a lens adds heuristics, notes and
   insight blocks, and none removes. `cia_die` used to be the exception — it returned the ten
   highest-scoring actives and dropped the rest — and this module carried a
   `_SUMMARISING_METHODOLOGIES` exemption for it. That truncation was a defect, not a
   methodology: it also emptied the CI drift gate, the SARIF upload and the premium report.
   It now keeps every heuristic and expresses the top ten as a `methodology_insights` block,
   so the exemption is gone and `cia_die` is held to fact 1 like every other lens.
2. No heuristic ever targets an entity absent from the document it was produced from, so an
   analysis that names one was produced from a different document.

Flows and assets carry only fact 2: a flow with no risky property and an asset nobody threatens
legitimately go unmentioned, so their absence proves nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

from otm_core_schema import ThreatModelDocument

from otm_threat_engine.result import AnalysisResult, HeuristicThreat, TrustBoundaryFinding

#: Share of the smaller structural shape that must reappear in the other analysis for the two to
#: count as one system. Two thirds sits inside the measured gap between different systems (<= 0.57
#: shared, they collide on catalog ids like `api`, `db`, `user`) and the same system across
#: renames, prose edits and growth (>= 0.79). See `system_overlap`.
MIN_SHARED_SHAPE = 2 / 3


def _threat_shape(threat: HeuristicThreat) -> set[str]:
    """The modelled entities one suggested threat hangs off, tagged by kind."""
    targets = (
        ("component", threat.target_component_id),
        ("flow", threat.target_data_flow_id),
        ("asset", threat.target_asset_id),
    )
    return {f"{kind}:{entity_id}" for kind, entity_id in targets if entity_id}


def _crossing_shape(finding: TrustBoundaryFinding) -> set[str]:
    """The boundary-to-boundary edge a flow crosses.

    Ids on their own are a weak signal: the template catalog hands out `user`, `api`, `db`, so
    unrelated models overlap on a handful of them. The *wiring* — which boundary reaches which —
    is what separates them, and adding it is what widens the measured gap between the same system
    and a different one from 0.06 to 0.21.

    A finding that names no boundaries contributes nothing. An artifact written by an older
    version or edited by hand can carry one, and two unrelated models must not be read as the
    same system because they record the same *absence*.
    """
    if not (finding.from_boundary_id and finding.to_boundary_id):
        return set()
    return {f"edge:{finding.from_boundary_id}>{finding.to_boundary_id}"}


def structural_shape(result: AnalysisResult) -> set[str]:
    """What the analysis says the modelled system *is*, independent of what it is called."""
    shape: set[str] = set()
    for threat in result.heuristic_threats:
        if not threat.skipped_as_duplicate:
            shape |= _threat_shape(threat)
    for finding in result.trust_boundary_findings:
        shape |= _crossing_shape(finding)
    return shape


@dataclass(frozen=True)
class SystemOverlap:
    """How much of the smaller structural shape the two analyses share."""

    shared: int
    smaller: int

    @property
    def is_same_system(self) -> bool:
        """A proportion of the *smaller* shape, not equality.

        Adding components is the normal case a baseline exists to judge and must not read as a
        change of system, so a measure that punishes growth is unusable here. An analysis with no
        shape at all (a model with no components) contradicts nothing: refusing on no evidence
        would put a mismatch error where a real result belongs, which is the failure mode these
        guards exist to prevent.
        """
        if not self.smaller:
            return True
        return self.shared / self.smaller >= MIN_SHARED_SHAPE


def system_overlap(one: AnalysisResult, other: AnalysisResult) -> SystemOverlap:
    """Measure whether two analyses describe one system across revisions."""
    one_shape = structural_shape(one)
    other_shape = structural_shape(other)
    return SystemOverlap(
        shared=len(one_shape & other_shape),
        smaller=min(len(one_shape), len(other_shape)),
    )


def _document_entities(document: ThreatModelDocument) -> set[str]:
    return (
        {f"component:{c.id}" for c in document.components}
        | {f"flow:{f.id}" for f in document.data_flows}
        | {f"asset:{a.id}" for a in document.assets}
    )


def foreign_entity_ids(document: ThreatModelDocument, analysis: AnalysisResult) -> list[str]:
    """Entities the analysis hangs threats off that this document does not define.

    Duplicates count: a threat flagged `skipped_as_duplicate` still proves the engine saw the
    entity, so suppression must not turn a foreign entity invisible.
    """
    referenced: set[str] = set()
    for threat in analysis.heuristic_threats:
        referenced |= _threat_shape(threat)
    return sorted(referenced - _document_entities(document))


def unanalysed_component_ids(document: ThreatModelDocument, analysis: AnalysisResult) -> list[str]:
    """Components this document defines that the analysis never saw — it predates them.

    This is the staleness signal a title comparison cannot produce: an analysis of revision 1
    references a strict subset of revision 2's components, so every other pairing check passes
    while the report inventories the new component and reports no threat against it.

    No methodology is exempt. The exemption that used to sit here existed only because the
    `cia_die` lens truncated its own output; the lens now keeps every heuristic, so every lens
    names every component and a gap here means the analysis really is older than the document.
    """
    seen = {threat.target_component_id for threat in analysis.heuristic_threats if threat.target_component_id}
    return sorted({component.id for component in document.components} - seen)
