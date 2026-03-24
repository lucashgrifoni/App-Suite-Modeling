# Schema canônico OTM v1

## 1. Modelagem conceitual

Um **ThreatModelDocument** é o artefato raiz. Ele descreve:

| Bloco | Função |
|--------|--------|
| **`model`** | Metadados técnicos: versão do **contrato** (`schema_version`), **tipo de sistema** (`system_type`) e **setor** (`industry_sector`). |
| **`metadata`** | Título, dono, tags e **versão do documento** (`document_version`) — evolução do modelo de ameaças, não do schema. |
| **`business_context`** | Narrativa, objetivos, stakeholders, regulatório e premissas. |
| **`assets`** | O que proteger (dados, credenciais, serviços críticos) com ligação opcional a componentes. |
| **`trust_boundaries`** | Fronteiras de confiança e membros (componentes). |
| **`components`** | Processos, dados, utilizadores, gateways, etc., com `asset_ids` opcional. |
| **`data_flows`** | Fluxos entre componentes (protocolo, auth, cifra). |
| **`threats`** | Ameaças STRIDE com risco, **estado de tratamento**, dono, prazo, notas, **mapeamentos** e **evidências sugeridas**. |
| **`mitigations`** | Controlo com **estado**, dono e ligação a ameaças + frameworks. |
| **`evidence_suggestions`** | Catálogo de evidências sugeridas (tipo + ligação a ameaças). |
| **`residual_risk_summary`** | Agregado opcional ao nível do documento (relatório). |

**Extensibilidade:** cada entidade relevante expõe `metadata: dict` (exceto onde `extra=forbid` na raiz impede chaves soltas — use `metadata` aninhado).

## 2. Versionamento do schema

- **`schema_version`** (em `model`): string **semver** do **contrato** canônico consumido pelo core (ex.: `1.0.0`).
- Constante no código: `CANONICAL_SCHEMA_VERSION` em `otm_core_schema.version`.
- **Regras práticas:**
  - **PATCH** (1.0.x): clarificações, campos opcionais novos, sem quebrar YAML existente.
  - **MINOR** (1.x.0): novos blocos ou enums opcionais; manter compatibilidade com documentos antigos quando possível.
  - **MAJOR** (2.0.0): renomeações ou obrigatoriedade nova; exige migração documentada.

## 3. Enums essenciais

- **STRIDE:** `StrideCategory`
- **Componentes:** `ComponentKind`
- **Sistema / negócio:** `SystemType`, `IndustrySector` (inclui `cloud_native` para packs cloud/Kubernetes)
- **Ativos:** `AssetKind`
- **Tratamento:** `TreatmentStatus` (ameaça), `MitigationStatus` (mitigação)
- **Evidência:** `EvidenceKind`

Valores estáveis em **snake_case** para YAML manual e geração por wizard.

## 4. Validações importantes (integridade)

- IDs únicos dentro de cada lista (`components`, `data_flows`, `trust_boundaries`, `assets`, `threats`, `mitigations`, `evidence_suggestions`).
- `data_flows` referenciam apenas `components` existentes.
- `trust_boundaries` e `components` referenciam fronteiras e ativos válidos.
- `threats` referenciam opcionalmente componente, fluxo, ativo e evidências existentes.
- `mitigations.threat_ids` ⊆ `threats`.
- `evidence_suggestions.related_threat_ids` ⊆ `threats`.

## 5. Arquivos de exemplo

| Arquivo | Descrição |
|----------|-----------|
| `examples/minimal.otm.yaml` | Mínimo válido |
| `examples/saas-ordering-v1.otm.yaml` | Cenário B2B com ativos, ameaças, mitigações, evidências e risco |

## 6. Modelos Pydantic

Implementação única em `packages/core-schema/otm_core_schema/document.py`; enums em `enums.py`; `ThreatModelDocument.model_json_schema()` gera JSON Schema para API/UI.
