# Scope freeze — fecho de engenharia (marco atual)

Documento de **fronteira de escopo** para o estado **release-ready** do App Suite Modeling, sem backlog extenso. Complementa o congelamento mais amplo em [`RELEASE_SCOPE_FREEZE.md`](RELEASE_SCOPE_FREEZE.md).

**Versão coordenada do monorepo:** `7.0.0` (`pyproject.toml`, `apps/web/package.json`) — ver [`CHANGELOG.md`](../CHANGELOG.md).

---

## Dentro do escopo entregue (oficial)

- **Core:** documento canónico `.otm.yaml`, validação, motor multi-metodologia, exportadores.
- **Superfícies:** CLI `otm`, API FastAPI `/v1/`, UI web (fluxo guiado; estado local).
- **Diferenciais já integrados:** import de artefatos suportados, diff de modelo/análise (semântico com versão de contrato documentada), backlog de remediação, explainability onde exposto.
- **Contratos:** OpenAPI como fonte de verdade exportada; verificação **anti-stale** (`verify_openapi_up_to_date` / `contracts:verify`); tipos TS gerados a partir do OpenAPI.
- **Qualidade deste marco:** pytest na raiz; E2E crítico e **híbrido** conforme scripts em `apps/web`; goldens/expectations HTTP onde definidos em `tests/`.

---

## Fora de escopo (consciente, não bloqueia este estado)

- Persistência server-side de modelos/análises; multi-tenant; auth produto na API/UI.
- Novas metodologias ou reescrita grande do motor **além** do já descrito em `RELEASE_SCOPE_FREEZE.md`.
- Canvas/diagrama como fluxo **principal** (MVP permanece texto, relatórios, Mermaid conforme docs).
- Cobertura regulatória exaustiva além de mapeamentos/heurísticas atuais.

---

## Limitações conhecidas e aceites (esta versão)

Resumo: ver [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md). Inclui MVP sem persistência/auth integrada, heurísticas com revisão humana, requisitos de ambiente para E2E, notas Windows/Unicode e política de dependências.

---

## Próximos passos opcionais (futuro — não bloqueiam o freeze)

- Evolução incremental de heurísticas e catálogos (templates, importadores).
- Mais cenários E2E ou hardening de CI conforme necessidade de implantação.
- Publicação PyPI/registry e materiais de marketing **fora** do critério “código pronto” deste documento.

Qualquer item acima **só** reabre escopo quando houver decisão explícita de produto/engineering — não faz parte deste fecho.

---

## Relação com outros documentos

| Documento | Função |
|-----------|--------|
| [`RELEASE_SCOPE_FREEZE.md`](RELEASE_SCOPE_FREEZE.md) | Matriz de maturidade por área e exclusões amplas |
| [`RELEASE_ENGINEERING_CHECKLIST.md`](RELEASE_ENGINEERING_CHECKLIST.md) | Comandos e critérios técnicos antes da tag |
| [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md) | Regras de merge e manutenção contínua |
