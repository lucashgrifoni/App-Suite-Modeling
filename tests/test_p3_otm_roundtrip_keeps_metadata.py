"""O round-trip OTM perdia o `metadata` inteiro — e inventava tags que ninguém escreveu.

`_project_to_otm` guarda `model` e `business_context` em `project.attributes`, e `otm_to_document`
lê-os de volta por `_project_header`. O `metadata` ficou de fora dos dois lados: só `title` e
`summary` sobrevivem, mapeados a `name` e `description`. `owner` e `document_version` desaparecem,
e as tags são **substituídas** por `["imported", "otm"]` — incondicionalmente, mesmo quando a
origem trazia as suas.

As tags alimentam a deteção de contexto de IA. Medido num modelo `plot4ai` com
`tags: [llm, rag, producao]`:

    antes  19 ameaças
    depois 14 ameaças
    perdidas: plot4ai_prompt_injection, plot4ai_model_abuse, plot4ai_rag_data_leakage,
              plot4ai_retrieval_grounding, plot4ai_grounding_attribution_weak

Exportar e reimportar apagava cinco ameaças de segurança de IA, em silêncio, num formato cujo
propósito é transportar o modelo sem perdas. É a mesma classe da descrição dos fluxos, corrigida
antes neste ramo: essa correcção tratou um campo e este ficheiro tinha mais.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "artifact-import", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_TAGS = ["llm", "rag", "producao"]


def _document(*, tags: list[str] | None = None):
    from otm_core_schema import ThreatModelDocument

    metadata = {"title": "Assistente interno", "owner": "appsec@empresa.example", "document_version": "2.1.0"}
    if tags is not None:
        metadata["tags"] = tags
    return ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0", "methodology": "plot4ai"},
            "metadata": metadata,
            "components": [
                {"id": "u", "name": "Utilizador", "kind": "user"},
                {"id": "bot", "name": "Assistente", "kind": "process"},
                {"id": "db", "name": "Base", "kind": "datastore"},
            ],
            "data_flows": [
                {"id": "f1", "name": "pergunta", "from_component": "u", "to_component": "bot"},
                {"id": "f2", "name": "consulta", "from_component": "bot", "to_component": "db"},
            ],
        }
    )


def _roundtrip(doc):
    from otm_artifact_import.otm_native import document_to_otm, otm_to_document

    return otm_to_document(document_to_otm(doc))


def test_o_titulo_ja_sobrevivia() -> None:
    """Premissa: o defeito é dos outros campos, não do round-trip inteiro."""
    assert _roundtrip(_document(tags=_TAGS)).metadata.title == "Assistente interno"


def test_o_dono_e_a_versao_sobrevivem() -> None:
    back = _roundtrip(_document(tags=_TAGS)).metadata

    assert back.owner == "appsec@empresa.example"
    assert back.document_version == "2.1.0"


def test_as_tags_do_autor_sobrevivem() -> None:
    assert _roundtrip(_document(tags=_TAGS)).metadata.tags == _TAGS


def test_sem_tags_na_origem_a_marca_de_importacao_mantem_se() -> None:
    """A marca existe para dizer de onde veio um modelo sem tags; não pode apagar as que existem."""
    assert _roundtrip(_document(tags=None)).metadata.tags == ["imported", "otm"]


def test_a_analise_nao_perde_ameacas_no_round_trip() -> None:
    """O que isto custava: cinco ameaças PLOT4ai desapareciam."""
    from otm_threat_engine import analyze_document

    doc = _document(tags=_TAGS)
    before = {h.id for h in analyze_document(doc).heuristic_threats}
    after = {h.id for h in analyze_document(_roundtrip(doc)).heuristic_threats}

    assert before, "premissa: o documento produz ameaças"
    assert not (before - after), f"perdidas no round-trip: {sorted(before - after)}"
