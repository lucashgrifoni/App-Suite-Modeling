"""
Uma resposta, uma língua — e um `pack_id` desconhecido é sempre recusado.

**Locale.** A API tem um locale de erro por pedido (`error_locale.resolve_api_error_locale_
from_accept_language`, com default `en`) e usava-o em `DOCUMENT_VALIDATION_ERROR`,
`REQUEST_VALIDATION_ERROR` e `REMEDIATION_GROUP_BY_INVALID`. Três códigos ignoravam-no e
respondiam sempre em português, porque reemitiam o texto da excepção levantada dentro dos
pacotes de domínio: `TEMPLATE_NOT_FOUND` ("Template desconhecido: …"), `PACK_NOT_FOUND`
("Pack desconhecido: …") e `IMPORT_ARTIFACT_INVALID` ("Raiz do artefacto deve ser um objecto
(mapping).", "Não foi possível interpretar como YAML/JSON: …"). Apareciam em respostas
`Accept-Language: en` ao lado de irmãs traduzidas, e dentro do envelope inglês do CLI
("Likely cause: Raiz do artefacto deve ser um objecto (mapping).").

A tradução acontece na fronteira HTTP e não reconhece a frase do pacote: o detalhe do parser
YAML/JSON é recuperado do `__cause__` encadeado, que é um sinal estrutural. Reconhecer texto
deixaria de funcionar em silêncio na primeira vez que essa frase mudasse.

**Pack inerte.** `/v1/models/compare` só resolvia o pack dentro do ramo `run_analysis`, por
isso sem essa flag um id com uma gralha dava 200 — e as respostas para `finance`, `telecom` e
`nope` eram byte-a-byte iguais entre si. Todas as rotas irmãs davam 404 `PACK_NOT_FOUND`, que
`docs/features/API.md` documenta sem carve-out por rota, e o projeto já tinha corrigido
exatamente esta forma de defeito uma vez (`REMEDIATION_GROUP_BY_INVALID` existe porque "antes,
um valor desconhecido devolvia 200 com o agrupamento por defeito").
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from otm_core_schema import load_document_from_yaml_path

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

# Palavras que só existem no português destas mensagens; presentes numa resposta `en`, são a
# prova do vazamento.
_PORTUGUESE_TELLS = ("desconhecido", "artefacto", "não foi possível", "objecto")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _doc() -> dict[str, Any]:
    return load_document_from_yaml_path(_MINIMAL).model_dump(mode="json", by_alias=True)


def _message(r: httpx.Response) -> str:
    return str(r.json()["detail"]["message"])


def _in_english(message: str) -> bool:
    lowered = message.lower()
    return not any(tell in lowered for tell in _PORTUGUESE_TELLS)


def _upload(client: TestClient, route: str, data: bytes, locale: str) -> httpx.Response:
    return client.post(
        f"/v1/imports/{route}",
        files={"file": ("artifact.yaml", data, "application/yaml")},
        headers={"Accept-Language": locale},
    )


# --- TEMPLATE_NOT_FOUND ---------------------------------------------------------------


def test_an_unknown_template_answers_in_english(client: TestClient) -> None:
    r = client.get("/v1/templates/nope-xyz", headers={"Accept-Language": "en"})

    assert _in_english(_message(r))


def test_an_unknown_template_still_names_the_id(client: TestClient) -> None:
    """Sem o id, o utilizador não sabe qual dos seus templates estava errado."""
    r = client.get("/v1/templates/nope-xyz", headers={"Accept-Language": "en"})

    assert "nope-xyz" in _message(r)


def test_an_unknown_template_answers_in_portuguese_when_asked(client: TestClient) -> None:
    r = client.get("/v1/templates/nope-xyz", headers={"Accept-Language": "pt-BR"})

    assert "desconhecido" in _message(r)


def test_instantiating_an_unknown_template_is_localised_too(client: TestClient) -> None:
    """A rota irmã levanta o erro noutro sítio e partilhava o mesmo texto fixo."""
    r = client.post("/v1/templates/nope-xyz/instantiate", headers={"Accept-Language": "en"})

    assert r.status_code == 404
    assert _in_english(_message(r))


# --- PACK_NOT_FOUND -------------------------------------------------------------------


def test_an_unknown_pack_answers_in_english(client: TestClient) -> None:
    r = client.post(
        "/v1/models/analyze",
        json={"document": _doc(), "pack_id": "nope"},
        headers={"Accept-Language": "en"},
    )

    assert _in_english(_message(r))


def test_an_unknown_pack_answers_in_portuguese_when_asked(client: TestClient) -> None:
    r = client.post(
        "/v1/models/analyze",
        json={"document": _doc(), "pack_id": "nope"},
        headers={"Accept-Language": "pt-BR"},
    )

    assert "desconhecido" in _message(r)


def test_an_unknown_pack_still_lists_the_valid_ones(client: TestClient) -> None:
    """É a lista que torna a mensagem acionável; traduzir não pode custá-la."""
    r = client.post("/v1/models/analyze", json={"document": _doc(), "pack_id": "nope"})

    assert "saas" in _message(r)


# --- IMPORT_ARTIFACT_INVALID ----------------------------------------------------------


def test_an_unreadable_artifact_answers_in_english(client: TestClient) -> None:
    r = _upload(client, "openapi", b"just a scalar string", "en")

    assert r.status_code == 400
    assert _in_english(_message(r))


def test_an_unreadable_artifact_answers_in_portuguese_when_asked(client: TestClient) -> None:
    r = _upload(client, "openapi", b"just a scalar string", "pt-BR")

    assert "artefacto" in _message(r).lower()


def test_a_malformed_manifest_keeps_the_parser_location(client: TestClient) -> None:
    """A localização do PyYAML é o valor da mensagem para quem tem de corrigir o ficheiro."""
    r = _upload(client, "kubernetes", b"a: [\n", "en")

    assert "line" in _message(r)


def test_a_malformed_manifest_frames_the_parser_text_in_english(client: TestClient) -> None:
    r = _upload(client, "kubernetes", b"a: [\n", "en")

    assert _in_english(_message(r).split("Parser reported:")[0])


def test_a_shape_error_has_no_parser_tail(client: TestClient) -> None:
    """Texto que se leu bem mas não é um mapping: não há erro de parser para citar."""
    r = _upload(client, "openapi", b"just a scalar string", "en")

    assert "Parser reported" not in _message(r)


def test_the_neighbouring_import_errors_are_still_localised(client: TestClient) -> None:
    """Controlo: as irmãs que já respeitavam o locale não regrediram."""
    r = _upload(client, "openapi", b"", "pt-BR")

    assert r.json()["detail"]["code"] == "IMPORT_EMPTY_ARTIFACT"
    assert "vazio" in _message(r)


# --- pack inerte em /v1/models/compare ------------------------------------------------


def test_an_unknown_pack_is_refused_on_compare_without_run_analysis(client: TestClient) -> None:
    """O sintoma: 200 com uma comparação normal, e o parâmetro sem efeito nenhum."""
    d = _doc()

    r = client.post("/v1/models/compare", json={"baseline": d, "revised": d, "pack_id": "nope"})

    assert r.status_code == 404


def test_the_compare_refusal_uses_the_documented_code(client: TestClient) -> None:
    d = _doc()

    r = client.post("/v1/models/compare", json={"baseline": d, "revised": d, "pack_id": "nope"})

    assert r.json()["detail"]["code"] == "PACK_NOT_FOUND"


def test_compare_refuses_a_blank_pack_id_like_its_siblings(client: TestClient) -> None:
    """`pack_id: ""` é uma escolha falhada do chamador, não "sem pack"."""
    d = _doc()

    r = client.post("/v1/models/compare", json={"baseline": d, "revised": d, "pack_id": ""})

    assert r.status_code == 404


def test_compare_without_a_pack_id_still_works(client: TestClient) -> None:
    """Controlo: ausência e `null` continuam a significar "sem pack"."""
    d = _doc()

    assert client.post("/v1/models/compare", json={"baseline": d, "revised": d}).status_code == 200
    assert client.post("/v1/models/compare", json={"baseline": d, "revised": d, "pack_id": None}).status_code == 200


def test_compare_with_a_real_pack_still_works(client: TestClient) -> None:
    d = _doc()

    r = client.post("/v1/models/compare", json={"baseline": d, "revised": d, "pack_id": "saas"})

    assert r.status_code == 200


def test_compare_with_a_real_pack_and_analysis_still_works(client: TestClient) -> None:
    """O ramo que realmente usa o pack não pode ter sido cortado pela verificação à cabeça."""
    d = _doc()

    r = client.post(
        "/v1/models/compare",
        json={"baseline": d, "revised": d, "run_analysis": True, "pack_id": "saas"},
    )

    assert r.status_code == 200
