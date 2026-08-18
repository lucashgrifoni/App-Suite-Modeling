"""Round-4 API reproduction: a stale analysis passed the ANALYSIS_DOCUMENT_MISMATCH guard.

`_unknown_target_component_ids` only asked whether the analysis named components the document
lacks. An analysis of revision 1 references a strict *subset* of revision 2's components, so that
set was empty and the guard passed. `/v1/reports/premium`, `/v1/remediation/backlog` and
`/v1/exports` then returned 200 for a document whose newest component — an unauthenticated,
unencrypted, publicly exposed file-upload target — was listed in the inventory ("Componentes: 6",
"Servidor FTP legado") and carried no threat, no risk-table row and no mitigation anywhere.

The reverse direction, "components the document defines that the analysis never saw", is the
signal, and it is exact rather than proportional: the engine emits at least one heuristic threat
per component (see `test_p2r4_identity_shared.py`, which pins that and its one lens exception).

The same module also has to stop refusing correct pairs, so the second half of this file is the
false-refuse side: every methodology, a pack, and a renamed baseline must still get their 200.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_TEMPLATE_A = "admin-portal"
_TEMPLATE_B = "api-backend"

_PAIRED_ROUTES = [
    ("/v1/remediation/backlog", {}),
    ("/v1/reports/premium", {"level": "deep"}),
    ("/v1/exports", {"formats": ["analysis_markdown"]}),
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _document(client: TestClient, template_id: str) -> dict[str, Any]:
    return client.post(f"/v1/templates/{template_id}/instantiate").json()["document"]


def _analysis(client: TestClient, document: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return client.post("/v1/models/analyze", json={"document": document, **extra}).json()


def _with_legacy_ftp(document: dict[str, Any]) -> dict[str, Any]:
    """The edit the reporter made: one component and one flow appended to the model."""
    edited = copy.deepcopy(document)
    edited["components"].append(
        {
            "id": "legacy_ftp",
            "name": "Servidor FTP legado",
            "kind": "external_entity",
            "handles_sensitive_data": True,
        }
    )
    edited.setdefault("data_flows", []).append(
        {
            "id": "f_legacy",
            "name": "Upload para FTP",
            "from_component": edited["components"][0]["id"],
            "to_component": "legacy_ftp",
            "protocol": "FTP",
            "authenticated": False,
            "encrypted": False,
            "public_exposure": True,
            "supports_file_upload": True,
        }
    )
    return edited


@pytest.fixture
def stale_pair(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    """The edited document, paired with the analysis produced before the edit."""
    document = _document(client, _TEMPLATE_A)
    return _with_legacy_ftp(document), _analysis(client, document)


# --- the edited document really is valid on its own --------------------------------------------


def test_the_edited_document_is_accepted_by_validate(
    client: TestClient, stale_pair: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    """The user's edit is legitimate; only the pairing is wrong."""
    edited, _ = stale_pair

    r = client.post("/v1/models/validate", json={"document": edited})

    assert r.status_code == 200, r.text


def test_the_edit_really_adds_threats_the_stale_analysis_lacks(
    client: TestClient, stale_pair: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    """Without this the refusal would be pedantry: the omission is four real threats."""
    edited, stale = stale_pair
    fresh = _analysis(client, edited)

    assert len(fresh["heuristic_threats"]) > len(stale["heuristic_threats"])


# --- the reproduction ---------------------------------------------------------------------------


@pytest.mark.parametrize(("path", "extra"), _PAIRED_ROUTES)
def test_a_stale_analysis_is_refused(
    client: TestClient, stale_pair: tuple[dict[str, Any], dict[str, Any]], path: str, extra: dict[str, Any]
) -> None:
    edited, stale = stale_pair

    r = client.post(path, json={"document": edited, "analysis": stale, **extra})

    assert r.status_code == 422, r.text


@pytest.mark.parametrize(("path", "extra"), _PAIRED_ROUTES)
def test_a_stale_analysis_carries_the_documented_error_code(
    client: TestClient, stale_pair: tuple[dict[str, Any], dict[str, Any]], path: str, extra: dict[str, Any]
) -> None:
    edited, stale = stale_pair

    r = client.post(path, json={"document": edited, "analysis": stale, **extra})

    assert r.json()["detail"]["code"] == "ANALYSIS_DOCUMENT_MISMATCH"


def test_the_stale_error_is_reported_under_its_own_type(
    client: TestClient, stale_pair: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    """A client has to be able to tell "wrong model" from "old analysis": the fixes differ."""
    edited, stale = stale_pair

    r = client.post("/v1/remediation/backlog", json={"document": edited, "analysis": stale})

    types = [e["type"] for e in r.json()["detail"]["errors"]]
    assert types == ["analysis_document_mismatch.stale_components"]


def test_the_stale_error_names_the_component_that_was_added(
    client: TestClient, stale_pair: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    edited, stale = stale_pair

    r = client.post("/v1/remediation/backlog", json={"document": edited, "analysis": stale})

    assert "legacy_ftp" in r.json()["detail"]["errors"][0]["msg"]


def test_run_analysis_true_recovers_from_the_stale_analysis(
    client: TestClient, stale_pair: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    """The guard's own advice has to work: a stale `analysis` still loses to a fresh run."""
    edited, _ = stale_pair

    r = client.post("/v1/remediation/backlog", json={"document": edited, "run_analysis": True})

    assert r.status_code == 200, r.text


def test_a_refreshed_analysis_of_the_edited_document_is_accepted(
    client: TestClient, stale_pair: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    edited, _ = stale_pair

    r = client.post(
        "/v1/reports/premium", json={"document": edited, "analysis": _analysis(client, edited), "level": "deep"}
    )

    assert r.status_code == 200, r.text


def test_the_refreshed_report_actually_names_the_new_component(
    client: TestClient, stale_pair: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    """The stale report listed `Servidor FTP legado` and gave it no finding; the fresh one must."""
    edited, _ = stale_pair

    r = client.post(
        "/v1/reports/premium", json={"document": edited, "analysis": _analysis(client, edited), "level": "deep"}
    )

    assert "legacy_ftp" in r.text


# --- two models, one template title --------------------------------------------------------------


@pytest.fixture
def crossed_same_title(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    """Document A wearing B's title, paired with B's analysis: the title check cannot see it."""
    doc_a = _document(client, _TEMPLATE_A)
    doc_b = _document(client, _TEMPLATE_B)
    doc_a = {**doc_a, "metadata": {**doc_a["metadata"], "title": doc_b["metadata"]["title"]}}
    return doc_a, _analysis(client, doc_b)


def test_a_same_title_cross_pair_is_refused(
    client: TestClient, crossed_same_title: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    doc_a, analysis_b = crossed_same_title

    r = client.post("/v1/remediation/backlog", json={"document": doc_a, "analysis": analysis_b})

    assert r.status_code == 422, r.text


def test_a_same_title_cross_pair_reports_no_title_error(
    client: TestClient, crossed_same_title: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    """Proof it is the structural signal doing the work, not the one that used to."""
    doc_a, analysis_b = crossed_same_title

    r = client.post("/v1/remediation/backlog", json={"document": doc_a, "analysis": analysis_b})

    types = [e["type"] for e in r.json()["detail"]["errors"]]
    assert "analysis_document_mismatch.title" not in types


# --- the guard must not refuse a correct pair ------------------------------------------------------


@pytest.mark.parametrize(
    "methodology",
    ["stride", "linddun", "nist_data_centric", "octave_allegro", "cia_die", "pasta", "plot4ai"],
)
def test_every_methodology_still_pairs_with_its_own_document(client: TestClient, methodology: str) -> None:
    """Every lens, `cia_die` included, must still pair with the document it was produced from."""
    document = _document(client, _TEMPLATE_A)
    analysis = _analysis(client, document, methodology=methodology)

    r = client.post("/v1/remediation/backlog", json={"document": document, "analysis": analysis})

    assert r.status_code == 200, r.text


def test_a_packed_analysis_still_pairs_with_its_own_document(client: TestClient) -> None:
    document = _document(client, _TEMPLATE_A)
    analysis = _analysis(client, document, pack_id="saas")

    r = client.post("/v1/remediation/backlog", json={"document": document, "analysis": analysis})

    assert r.status_code == 200, r.text


@pytest.mark.parametrize(("path", "extra"), _PAIRED_ROUTES)
def test_the_matching_pair_still_works(client: TestClient, path: str, extra: dict[str, Any]) -> None:
    document = _document(client, _TEMPLATE_A)

    r = client.post(path, json={"document": document, "analysis": _analysis(client, document), **extra})

    assert r.status_code == 200, r.text
