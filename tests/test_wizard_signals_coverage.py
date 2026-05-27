"""Coverage — wizard signal parsing, synthetic corpus, and context boosts."""

from __future__ import annotations

from otm_threat_engine import wizard_signals as ws

_ALL_YES = [
    "wz:internal_admin_portal:approval=yes",
    "wz:internal_admin_portal:segregation=yes",
    "wz:internal_admin_portal:jit=yes",
    "wz:file_handling_application:quarantine=yes",
    "wz:file_handling_application:scan=yes",
    "wz:file_handling_application:public_objects=yes",
    "wz:api_backend_rest:auth=yes",
    "wz:api_backend_rest:rate_limit=yes",
    "wz:api_backend_rest:edge_controls=yes",
    "wz:industry_ecommerce:checkout=yes",
    "wz:industry_ecommerce:psp_boundary=yes",
    "wz:industry_ecommerce:sensitive_data=yes",
]


def test_parse_wizard_tags_valid_and_invalid() -> None:
    sigs = ws.parse_wizard_tags([*_ALL_YES, "not-a-tag", "", "wz:bad", None])  # type: ignore[list-item]
    assert len(sigs) == len(_ALL_YES)
    assert {s.value for s in sigs} == {"yes"}


def test_synthetic_keyword_corpus_all_profiles() -> None:
    sigs = ws.parse_wizard_tags(_ALL_YES)
    corpus = ws.synthetic_keyword_corpus(sigs)
    for token in ("approval", "quarantine", "oauth", "checkout", "waf", "pci"):
        assert token in corpus


def test_synthetic_keyword_corpus_ignores_non_yes() -> None:
    sigs = ws.parse_wizard_tags(["wz:api_backend_rest:auth=no", "wz:api_backend_rest:auth=unk"])
    assert ws.synthetic_keyword_corpus(sigs) == ""


def test_admin_negative_count() -> None:
    sigs = ws.parse_wizard_tags(
        [
            "wz:internal_admin_portal:approval=no",
            "wz:internal_admin_portal:segregation=no",
            "wz:internal_admin_portal:jit=no",  # not in the {approval, segregation} cluster
            "wz:api_backend_rest:auth=no",  # different profile
        ]
    )
    assert ws._admin_negative_count(sigs) == 2
