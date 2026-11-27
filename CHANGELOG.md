# Changelog

All notable changes to this project are documented here.

This project follows **Keep a Changelog** and **Semantic Versioning**.

---

## [Unreleased]

## [7.10.1] — 2026-11-27

### Fixed

- Preserve distinct Kubernetes resource and flow IDs when resources share a name across namespaces.
- Preserve distinct Terraform resource and flow IDs when local modules contain resources with the same name.
- Keep IDs stable when inputs are reordered or when an unrelated resource is added.

### Changed

- Updated Tailwind CSS for the modeling workspace and the project site.
- Added property-based tests for model ID normalization and document identity.

### Security

- Verify Python dependency hashes in CI, the API image, and the package build. Verify the Snyk CLI binary before running scans.
- Align the Snyk GitHub integration with Python 3.12 for the repository lockfiles.
- Narrow workflow permissions and keep API credential values and lengths out of the startup warning.

## [7.10.0] — 2026-11-25

### Changed

- Updated the web workspace for modeling, analysis, risk decisions, and export.
- Made the unified risk report the default in the CLI, API, and web workspace. The cover shows total recorded threats. Markdown and PDF include treatment decisions, rationale, and review details for accepted risks.
- Linked SARIF results to the target entity's source line when the analysis starts from a YAML file.
- Updated dependencies and hardened PDF rendering, input handling, and CI gates.

### Security
- **O fold de fontes do PDF recriava markup que o escape já tinha neutralizado.** O renderer
  premium escapa cada string do modelo com `html.escape(quote=True)` e, no fim, corre
  `to_pdf_font_text` sobre o HTML **já escapado** para degradar caracteres que as fontes WinAnsi
  não desenham. Essa degradação é NFKD, e a ordem era o defeito: `＜` (U+FF1C) não é `<`, atravessa
  o escape intacto, e o fold convertia-o num `<` verdadeiro. Consequências, todas reproduzidas:
  markup arbitrário no PDF (outline forjado a dizer "NO CRITICAL RISKS FOUND", `/Title` sob
  controlo do modelo); **SSRF** — um `<img src="http://…">` injetado era buscado pelo xhtml2pdf,
  reproduzido contra `POST /v1/reports/premium` **sem autenticação**; **leitura de ficheiro local**
  embutida no PDF devolvido; e anotações `/Link`, das quais 100% eram de autoria do atacante,
  porque o renderer não emite nenhum link próprio. O fold passa a ser fechado em relação a markup:
  pode substituir um caractere que não desenha, nunca produzir um que mude o significado do
  documento à volta. Provado ponta a ponta contra um servidor de sonda: zero pedidos.
  <br>Um `link_callback` foi acrescentado ao `pisa.CreatePDF`, mas **não** como segunda linha de
  defesa: medido, este xhtml2pdf ignora-o em `<img src>`, `<link rel=stylesheet>` e `@import`, e
  só o honra em `url()` de CSS — uma construção em quatro, e é ignorado precisamente na que o
  ataque usava. Fica porque bloquear uma é melhor que nenhuma; a docstring carrega a tabela
  medida e um teste fixa-a.
- **Cinco limites em falta, de baixa severidade, agrupados por causa.** Nenhum é explorável para
  acesso indevido; três são de integridade de saída e dois de limite de entrada ausente onde os
  campos irmãos já o têm.
  - **JSON com `NaN`/`Infinity`.** `json.dumps` aceita não-finitos por omissão e escreve `NaN`
    cru, que não é JSON: um consumidor em Go ou Java rejeita o documento inteiro, e o `jq`
    reescreve o valor para `null` — num campo de score, pior do que rejeitar. `risk.score` é um
    `float` do Pydantic e aceita atribuição de não-finito, por isso o caminho é real. Os seis
    exportadores passam a `allow_nan=False`: erro alto no momento da geração em vez de um
    ficheiro inválido em silêncio.
  - **ANSI e NUL em Markdown.** `md_inline`/`md_block` achatavam terminadores de linha e deixavam
    passar o resto. `CSI 2K` + `CSI G` num nome de componente repintam a linha num terminal — e
    `otm report` escreve para stdout com um `print()` — enquanto um NUL literal fica dentro do
    `.md` entregue. Não muda o contorno do documento, por isso o oráculo de estrutura não o via.
  - **Separadores Unicode em Mermaid.** `_LABEL_CONTROL_RE` cobria `\r\n\t\f\v` e não NEL (U+0085),
    LS (U+2028) nem PS (U+2029). O invariante que o exportador declara é "um nome não pode
    acrescentar uma linha"; estes três acrescentavam.
  - **Profundidade do ficheiro de regras.** `load_custom_rules` tinha tecto de bytes e usava
    `yaml.safe_load` — o mesmo sem tecto de profundidade já corrigido para o documento canónico.
    4 KB rebentavam a pilha e saíam como `RecursionError` cru, fora do contrato `ValueError` que o
    loader declara. Ligado ao tecto existente, não a um segundo.
  - **Comprimento de cada `refs`.** `max_length=20` limita a lista, não cada item: 400 000
    caracteres num único ref passavam, enquanto `title`, `description` e `control_hint` têm tecto
    próprio. O ref é reemitido por cada ameaça que a regra dispara, portanto o custo multiplica.
- **85 testes verdes enquanto a injeção de cabeçalhos estava viva — o oráculo é que era cego.**
  `_outline`/`_structure`, os oráculos que garantem que "o contorno do documento é decisão do
  renderizador", eram uma regex ancorada no início da **linha física**
  (`^\s{0,3}(#{1,6}\s|\||>|…)`). O renderizador escreve os seus bullets como `- {valor}`, e `- `
  são dois caracteres que não são whitespace: um nome começado por `## ` produzia
  `- ## Conclusion…`, que o CommonMark lê como item de lista **contendo um H2 verdadeiro**, e a
  regex nunca casava. Medido: `_outline(hostil) == _outline(benigno)` enquanto um parse real dava
  80 blocos contra 93. Um oráculo que não vê a construção que existe para apanhar transforma "não
  verificado" em "verificado seguro", que é pior do que não ter teste nenhum. Ambos os oráculos
  (`test_p2r5_report_markdown_structure.py` e `test_p2r4_cli_markdown_structure.py`) passam a
  parsear CommonMark a sério, com `markdown-it-py` declarado no extra `dev` em vez de deixado como
  transitivo do `rich` — sustenta uma propriedade de segurança, portanto é uma dependência a
  sério. Trocar só o oráculo, sem tocar no produto, tornou 18 casos vermelhos de imediato.
- **Cinco listas do relatório premium interpolavam o valor do modelo em cru.**
  `top_trust_boundaries`, `top_attack_surfaces`, `top5_risk_titles`, `main_components` e
  `main_flows` saíam como `f"- {x}"`, a duas linhas de um `md_block(ar.narrative)` que fazia a
  coisa certa. Um nome começado por `## ` forjava uma secção real no contorno do relatório —
  "Conclusion: no risks were found. Approved for release." como secção genuína do documento que a
  ferramenta assina. Medido em `examples/minimal.otm.yaml`: 6 cabeçalhos forjados no executive, 13
  no standard e no deep, nos dois locales, e também por HTTP em `POST /v1/reports/premium`.
  Alcançável **sem escrever um modelo**: um `info.title` hostil num spec OpenAPI sobrevive ao
  `otm import openapi` intacto até ao campo `name`. Agora 0 em todos os níveis, com o texto do
  autor preservado — neutralizado, não censurado.
- **`>` deixou de estar fora de `_LEADING_BLOCK`.** Estava excluído com o argumento de que uma
  citação "não cria secções nem tabelas". Cria as duas: um valor começado por `>` abre um
  blockquote que **absorve** a frase que o renderizador escreve a seguir, e `> ## Conclusão` produz
  lá dentro um H2 verdadeiro — que era o primeiro H2 do documento, par a par com o `## Ativos` do
  próprio renderizador. O custo declarado para o excluir não se aplica: os valores que passam por
  `md_block` já vêm achatados numa linha, portanto não há citação multi-linha a preservar. O teste
  que fixava o comportamento antigo foi atualizado com a razão, não contornado.
- **Duas ameaças distintas podiam partilhar um id, e o gate de CI julgava-as como uma.** Os ids
  são concatenações com `_`, e `_` é legal dentro de um id de entidade: `eng_{comp.id}_{stride}` e
  `eng_flow_{flow.id}_{stride}` partilham um espaço de nomes plano, por isso um componente
  `flow_svc` e um fluxo `svc` produzem a mesma string — com o documento a passar em `otm validate`
  como **Valid**, 0 avisos estruturais. As regras personalizadas têm a mesma forma: regra `a` sobre
  `b_c` colide com regra `a_b` sobre `c`. Três consumidores colapsavam o par **em silêncio**: o
  dict de `analysis_diff` (o último vencia), `merge_heuristic_threats` (saltava sem diagnóstico) e
  o `partialFingerprints.otmThreatId` do SARIF, que é a identidade do alerta no GitHub code
  scanning. O efeito prático era o gate de drift ver uma ameaça **substituída** onde tinha sido
  **acrescentada**. A análise passa a ser recusada, nomeando os dois sujeitos.
  <br>**Porque recusar e não renomear:** tornar a junção injetiva mudaria *todos* os ids,
  invalidando os fingerprints SARIF e todas as baselines guardadas — a primeira execução após a
  atualização reportaria cada ameaça como nova e faria disparar os gates de toda a gente. O
  formato documentado em `docs/features/CUSTOM_RULES.md` fica intacto, e quem não tem colisão não
  paga nada.
- **Um upload de 10 KB escrevia 628 KB de log e devolvia 500.** O documento não confiável tinha
  tecto de bytes e tecto de expansão de aliases, mas nenhum de **profundidade**. `"a: " +
  "["*5000 + "]"*5000` são 10 003 bytes sem um único alias, por isso não gastavam nada do
  contador de nós e desciam até `compose_node` esgotar a pilha. O `RecursionError` daí não é
  `ValueError`, e `_draft_from_upload` só traduz `UnicodeDecodeError`, `ValueError`,
  `AttributeError` e `TypeError` — subia ao handler genérico como `500 INTERNAL_ERROR` com o
  traceback inteiro no log. Medido: **627 695 bytes de log por 10 003 bytes de entrada, 62,8x de
  amplificação**, em `POST /v1/imports/kubernetes` e `/v1/imports/openapi`. O 500 era o sintoma
  visível; o custo real era disco e ingestão de logs a partir de um upload trivial. Agora:
  **400 no envelope documentado, 13 bytes de log, 0,00x**.
- **O mesmo buraco existia no ramo JSON, e foi encontrado a procurar variantes.**
  `load_object_from_text` escolhe `json.loads` quando o texto começa por `{`, e `json.loads`
  também desce recursivamente sem limite: `'{"a":' * 20000` devolvia 500 pela mesma razão, com o
  `RecursionError` a escapar a um `except (yaml.YAMLError, json.JSONDecodeError)`. Fechado com o
  **mesmo tecto** — são duas serializações da mesma forma de documento, e um limite por formato
  deixaria a segunda porta aberta. A profundidade do JSON mede-se por varrimento linear antes do
  parser, com saída à primeira violação: 600 KB hostis são recusados em 0,003 s, sem pagar a
  recursão. `RecursionError` passa também a ser traduzido como defesa em profundidade.
- **`MAX_DOCUMENT_DEPTH = 100`** (`OTM_MAX_DOCUMENT_DEPTH`), a par de `MAX_DOCUMENT_BYTES` e
  `MAX_YAML_EXPANDED_NODES`. O documento mais profundo deste repositório tem profundidade **6**,
  medida em 23 ficheiros YAML — exemplos, fixtures, workflows, `docker-compose`. A folga é ~16x,
  na mesma linha dos 38x que o tecto de nós deixa. 25 testes de regressão, provados a
  discriminar: com a guarda neutralizada e as constantes intactas, **11 falham**.

### Added
- Preview OpenAPI revisions against the active model and apply compatible changes after reviewing conflicts.
- Use organization rules for analysis and drift checks in the GitHub Action. Pull request checks load the policy from the base revision.
- Added an OpenWiki quickstart and reference pages linked to the source.
- **Custom rules can match assets.** `match: { asset: { data_classification: [confidential, restricted], owner: null } }` — a rule now targets a component, a flow **or an asset**, and emits a threat carrying `target_asset_id`. This was shipped as a documented gap and it was the wrong one to leave open: a great deal of organisation policy is about the data rather than the component that happens to hold it. "Anything classified confidential has a named accountable owner" is a statement about the asset. Matchable: `asset_kind`, `sensitivity`, `data_classification`, `data_nature`, `business_criticality`, `regulatory_relevance`, `owner`, `location`, and the component/flow link fields. Same semantics as the other subjects — scalar is equality, list is any-of, unknown field names are an error.
- **Route table coverage in the web app.** The suite had 68 tests and none touched the router; the `react-router` v8 migration rewrote imports in 15 files and stayed green throughout, proving nothing. The contents of `BrowserRouter` moved into an exported `AppRoutes` (behaviour identical) so tests can mount the app at a chosen URL, and 15 tests now assert that every declared path resolves to itself and that four kinds of unknown URL redirect home rather than leaving a blank screen. Web suite: 68 → 83.

### Security
- **Three CI gates were green without covering anything.** `.semgrepignore` excluded `.github/`, so `--config p/github-actions` — a ruleset whose entire purpose is analysing workflows — ran over 65 files containing not one workflow. `publish-pypi` checked the built version against the tag only on the `release` event, leaving `workflow_dispatch` able to build any branch and publish it unverified; harmless while no publisher existed, but the fastest way to permanently burn a version number now that one does. And the Snyk jobs finished green having scanned nothing on pull requests from forks, since secrets are not exposed there — irrelevant on a private repository, but this one is public and takes external contributions. All three closed; the workflow scan reports 0 findings with `.github/` finally in scope.

### Fixed
- **`docs/internal/` read as current documentation while describing a product from several releases ago** — an unauthenticated API, a pipeline with no SAST, scanners "not configured", all long since false. Rewriting the records would destroy what makes them worth keeping, so all 34 carry a dated banner pointing at a new `docs/internal/README.md` that names the stale claims and says which sources win. Nine of them linked to `.github/workflows/ci.yml`, gone since the CI reorg.
- **`NOTICE` was missing** while the project references MITRE, OWASP, NIST, ISO and PLOT4ai material. It now attributes each source and draws the line that matters: this project ships identifiers and short official names, never the normative text of any standard, and every descriptive string in the framework maps was written here. Includes the trademark notice and states that the `open-threat-model` name follows IriusRisk's OTM format without affiliation.
- **The documented CLI exit-code contract was incomplete.** It said "1 = usage error"; Click raises **2** for an invalid enum value, an unknown flag or a missing argument, and this CLI does not override that. A CI script branching on `1` alone missed half the cases. Documented and pinned by a test.

---

## [7.9.0] — 2026-08-05

### Security
- **The Semgrep gate was not gating.** `--severity` is a *filter*, and it is repeatable — a single `--severity WARNING` therefore loaded **only** warning-severity rules and silently dropped every ERROR-severity (high) rule in `p/security-audit`, `p/github-actions` and the project's own pack. The gate ran on every push and never saw the findings it existed to catch. Reproduced with a two-rule fixture: the old flags reported *"1 Code rule"*, the fixed ones *"2 Code rules"*. Both severities now run, and the step asserts the exit code explicitly instead of trusting `--error` to fail the job — a security gate that depends on a flag's side effect is one flag change away from passing everything.

### Fixed
- **Shipped framework mappings cited control IDs that do not exist in the versions the file declares.** The header claims OWASP ASVS 4.0.3, NIST CSF 2.0 and ISO/IEC 27001:2022 Annex A; six entries did not match. `PR.DS-06`, `PR.AC-01` and `PR.AC-04` are **CSF 1.1** — the `PR.AC-*` family became `PR.AA-*` in 2.0 — and three ISO controls pointed at the wrong number: `A.8.17` is clock synchronisation (logging is `A.8.15`), `A.8.11` is data masking (use of cryptography is `A.8.24`), `A.8.13` is information backup (redundancy is `A.8.14`). This matters more than a typo: the product sells standards traceability, and an invented identifier becomes noise somebody quotes in an audit report. Corrected, and a new test pins **every** `control_id` against the declared framework version, so the header is now verified rather than asserted.
- **The landing page advertised "LLM-assisted" analysis. There is no LLM in the product** — no SDK in any manifest, no HTTP client anywhere under `packages/`, no network egress possible. What exists is the inverse: `ai_modeling/` *detects* LLM, RAG and agent components in the architecture **being modelled**. Both entries now describe what ships.
- **Every call to action on the published landing page pointed at `https://github.com`.** The repository URL defaulted to a bare placeholder and the Pages workflow never set `VITE_REPO_URL`, so "View on GitHub", "Docs" and "Issues" all dropped the visitor on GitHub's homepage. The default is now this project's repository.
- **`SECURITY.md` and `CODE_OF_CONDUCT.md` had no reachable reporting channel** — both pointed at "the private channel defined in the repository", which did not exist. Both now link to GitHub private vulnerability reporting directly, and the code of conduct states plainly that this project has a single maintainer and names GitHub Support as the escalation path when the complaint concerns them.
- **`SONAR_DECISION_REPORT.md` stated as "verified final state" that `sonar-project.properties` had been removed.** The file is tracked at the repository root and was reinstated for the local Sonar campaign. The document now describes the real state, including the residual caveat that its presence can suggest a CI quality gate that does not exist.
- **The README's Versioning section had said `7.6.4` for three releases.** It no longer restates the version at all — a number copied into prose goes stale the moment it is bumped.

### Added
- **Custom rules — organisation heuristics without forking the engine (`otm analyze --rules <file>`).** Every organisation has threat-modelling rules the generic engine cannot know: an internal standard, a control the platform team mandates, a lesson from an incident. Those now go in a YAML file in your own repository and run alongside the engine, feeding the same result, JSON, SARIF and CI gate. Documented in [docs/features/CUSTOM_RULES.md](docs/features/CUSTOM_RULES.md), with a working [`examples/custom-rules.example.yaml`](examples/custom-rules.example.yaml).
  - **Rules are data, not code.** No expression language, no regex, no callbacks, nothing executed. The file is `safe_load`-ed, size-capped and fully validated before a rule reaches the engine. That is the entire sandbox and it is a deliberate ceiling: the worst a hostile rules file can do is describe threats nobody cares about.
  - **Matching** is over the attributes the schema already models — 15 on components (`kind`, `privilege_level`, `exposure_type`, `handles_credentials`, `executes_code_or_commands`, `supports_admin_operations`, …) and 18 on flows (`encrypted`, `authenticated`, `public_exposure`, `input_from_untrusted_source`, `supports_file_upload`, …) plus the engine-derived **`crosses_boundary`**. A scalar is equality, a list is any-of, and every key in a block must hold. A rule matches exactly one subject, so it is never ambiguous how many threats it raises.
  - **An unknown field name is an error, not an ignored criterion.** A misspelled field would produce a rule that never fires, and a rule that never fires is worse than no rule: the organisation believes it is covered when it is not. The error names the valid fields. For the same reason the docs are explicit that **`null` is not `false`** — `encrypted: false` matches only flows explicitly marked unencrypted; `encrypted: [false, null]` also catches the ones nobody has answered for, which is usually the real intent.
  - **Organisation rules are never suppressed by the base heuristics**, unlike industry-pack threats. This is deliberate: the engine's generic `information_disclosure` on a datastore and your rule about that datastore are not the same finding — yours carries the control, the owner and the internal reference. Marking it a duplicate would delete exactly what someone wrote the rule to carry. Within a rule set, the same rule never fires twice on one target.
  - Generated threats are namespaced (`custom_<set>_<rule>_<target>`, titled `[rules:<set>]`), declared `refs` are kept under their own `custom` catalogue rather than mixed into the verified CAPEC/CWE mappings, and a rule's `control_hint` appears **only if that rule actually fired** — suggesting a control for a threat that was never raised tells the reader there is a problem where the engine found none.

### Fixed
- **Framework enrichment overwrote a threat's existing references instead of adding to them.** `enrich_heuristic_threat` replaced `framework_refs` wholesale with the STRIDE- and AI-derived ones, so any reference already on the threat vanished silently. Harmless until now (nothing set them beforehand), but it silently deleted the internal references custom rules declare. Enrichment now merges, author references first.

### Added
- **Composite GitHub Action ([`action.yml`](action.yml)).** Drop the whole flow into any repository's CI: validate the model, run the engine, write SARIF 2.1.0, optionally upload it to code scanning, and optionally fail the build on threat-model drift. By default it installs the engine **from its own checkout**, so the CLI is exactly the version pinned in `uses:` — the action and the tool cannot drift apart, and no PyPI round-trip is involved. Outputs `sarif-file`, `analysis-file`, and `gate-outcome` (`passed` / `tripped` / `not-evaluated` / `skipped`).
  - The gate step distinguishes the CLI's exit codes rather than treating any non-zero as failure: `3` is a policy trip (fails the job with a clear annotation), while `1` is a usage or input error and is reported as such — a mistyped path must never masquerade as "your threat model got worse". `not-evaluated` is surfaced as its own outcome so a methodology switch is not silently read as a pass.
  - A `composite-action` job in `github-ci-cd.yml` runs the action against this repository on every push. An action nobody executes is an action nobody knows is broken.
- **pre-commit hook ([`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml)).** `otm-validate` checks every changed `.otm.yaml` against the canonical schema at commit time.
- **PyPI release workflow ([`.github/workflows/publish-pypi.yml`](.github/workflows/publish-pypi.yml)).** Publishes `open-threat-model` on GitHub Release via **OIDC trusted publishing** — no API token stored, nothing to rotate or leak. The build job holds no publish permission; only the `publish` job, bound to a `pypi` environment, can mint an OIDC token. Before upload it verifies that the built version matches the release tag (PyPI never lets a version number be reused, so publishing the wrong one burns it permanently) and smoke-tests the wheel in a clean virtualenv, proving the console script runs and the embedded data files shipped. Artifacts carry a build provenance attestation. **Not yet active:** the one-time pending publisher must be created on pypi.org by the repository owner.

### Changed
- **`otm validate` accepts several files.** `otm validate a.otm.yaml b.otm.yaml` validates each and exits `1` if any failed, reporting *every* bad file instead of dying on the first — a contributor fixing a batch wants the whole list. Required by pre-commit, which hands a hook every matching path at once. A single-file invocation is unchanged: same panel, same rich diagnostic, same exit code.

### Fixed
- **`pip install open-threat-model` produced an `otm` command that could not run.** The console script is declared unconditionally in `[project.scripts]`, but Typer, Rich and Click lived in the `[cli]` extra — so the advertised install produced an entry point that died on `ModuleNotFoundError: No module named 'typer'`. The CLI runtime is now a base dependency; `[cli]` remains as a no-op alias so `pip install -e ".[dev,cli,api]"` and any existing instructions keep working. Caught by installing the built wheel into a clean virtualenv, which the release workflow now does on every publish.

---

## [7.8.0] — 2026-08-05

### Added
- **Threat-model drift gate for CI — `otm diff --fail-on <none|low|medium|high|critical>`.** The threat-modeling analogue of a security gate: a pull request that introduces new risk fails the build. Trips when a **new** threat lands at or above the band, or when an existing threat **worsens across** a band (`medium → high`). Exits `3` — distinct from `1` (usage error), so CI can tell "the policy failed" from "the command failed". A second, opt-in `--fail-on-risk-increase` trips when the maximum risk score rises at all (catching within-band worsening). Available on `otm diff` (runs the engine on both `.otm.yaml` files) and `otm diff-analysis` (compares two stored `analyze.json`). No baseline or suppression file is needed: the committed model *is* the baseline, so pre-existing risk appears on both sides of the diff and never counts as new. Fifth step of the evolution plan; documented in [docs/CI_AND_SECURITY_EVIDENCE.md](docs/CI_AND_SECURITY_EVIDENCE.md) §8.
  - **Never fails a build for something the developer cannot act on:** removals, improvements, score drops, inert renames, methodology changes, and within-band bumps all exit `0`. The default (`--fail-on none`) is inert, so every existing invocation is byte-for-byte unchanged.
  - **Never passes silently what should trip:** a threat whose id churns appears as an `(added, removed)` pair — never in `modified` — and the remap signature ignores the score. The gate therefore compares a remapped threat against its removed twin: an inert rename passes, but a rename that *also* crossed a band fails. A remap with no baseline score fails closed. New threats with no score are reported as `unranked`, never silently dropped.
  - The gate is evaluated **after** all output and `--json-out` artifacts are written (CI wants the diff most on the runs that fail), and its report goes to **stderr**, so `--format json` keeps stdout valid JSON.
- **`AnalysisDiff` now records remap pairings structurally.** `HeuristicThreatDelta.match_kind` / `paired_id` (which existed but were never populated) are now set on both sides of a signature remap, and the added side carries `score_before` / `score_delta` from its twin. Pairing is 1:1 and deterministic; previously a single removed threat could be claimed by several added ones. `signature_remap_hints` is unchanged and now derives from the same pairing.
- **`severity_for_score` / `severity_at_least` / `SEVERITY_ORDER`** exported from `otm_threat_engine`, so any surface (reports, exporters, CI gates) can label severity without redefining the thresholds.

### Fixed
- **One canonical severity band.** The engine banded threats `critical ≥ 20 / high ≥ 12 / medium ≥ 6`, while the premium report banded them `critical ≥ 20 / high ≥ 15 / medium ≥ 9`. The same threat scoring `12` was therefore reported as **high** by `otm analyze` (and in `summary.severity_distribution`, the JSON/API contract, and the SARIF levels) but as **medium** by the premium report and its HTML. A new `otm_threat_engine.severity.severity_for_score` is now the single source of truth, and the engine aggregate, the premium payload (`by_severity_band`), and the premium HTML all delegate to it. The engine band wins because it feeds the machine-readable contract; the practical effect is that premium reports now label scores `6–8` as *medium* (was *low*) and `12–14` as *high* (was *medium*) — a more conservative, and now consistent, labelling. No test previously discriminated the two bands, which is why the divergence survived; boundary tests were added.

- **Pre-release deep review — four defects, two of them in the CI gate itself.** As before every release, an adversarial review ran over everything added since the last tag (five independent lenses, each candidate re-checked by two skeptics). It produced 17 candidates, of which 6 survived — 4 distinct defects, none of which the green pipeline, `ruff`, `mypy`, or any scanner had caught:
  - **A methodology switch failed the build (high).** Changing the lens swaps the ruler: the heuristics of one methodology do not exist in the other, so every threat of the new lens landed in `added`. `otm diff --fail-on high` across `stride → nist_data_centric` exited `3` with *"16 condition(s) hit"* on a one-line YAML change nobody could act on — directly contradicting the gate module's own first principle, *"troca de metodologia nunca dispara"*. The gate now declines to issue a verdict and the CLI prints **`NOT EVALUATED`**, never `PASSED`: a pass banner on a diff nobody judged would be the gate claiming a clean bill of health it never took. Exits `0`. This mirrors the guard `otm diff-analysis` already had for an engine-version mismatch.
  - **The gate failed open on within-band worsening (high).** `--fail-on` only trips on a band *crossing*, and `--fail-on-risk-increase` read `max_risk_delta` — the summary-wide maximum. A threat rising `12 → 15` (both `high`) that was not the global maximum was therefore caught by **nothing**, including the strictest policy the CLI offers, while the same run's own text output printed *"subiu (Δ score +3.0)"*. `--fail-on-risk-increase` now evaluates every threat, not just the summary maximum, and does not report a threat twice when it also crossed a band. Reachable through both `modified` and the id-churn remap path.
  - **The severity unification above was half done (medium).** It repointed `_band_for_score` and the HTML band at the canonical `20/12/6` but left the *narrative* helpers in the same module on the old `20/15/9`. One document therefore called the same score **"medium"** on its cover and **"High"** in its own severity table, for every score in `[6,9)` and `[12,15)`. The cover adjective, the urgency level, and the readiness question keep their own vocabulary but now take their cut points from `severity_for_score`. (`remediation._priority_label` is deliberately untouched: it is a priority axis, not severity.)
  - **`--fail-on --help` had lost its allowed values (low).** Rich parses `[...]` as a style tag, so `[none|low|medium|high|critical]` was silently dropped from the help on both subcommands — the accepted values were discoverable only by guessing wrong. Now escaped.
  - 25 regression tests were added. They were checked for *discrimination*, not just for passing: reverting the source while keeping the tests fails 14 of them. That check is precisely what was missing when the severity divergence shipped.

### Security
- **Six open Dependabot alerts cleared; the web dependency tree is back to `npm audit` clean.** Five needed nothing but a lockfile re-resolve inside the existing semver ranges: **postcss** `8.5.15 → 8.5.25` in both `apps/web` and `gitpage` ([GHSA-r28c-9q8g-f849](https://github.com/advisories/GHSA-r28c-9q8g-f849), path traversal via attacker-controlled `sourceMappingURL`), **js-yaml** `4.2.0 → 4.3.1` ([GHSA-52cp-r559-cp3m](https://github.com/advisories/GHSA-52cp-r559-cp3m), quadratic CPU on merge-key chains — the `js-yaml` override floor had to move to `^4.3.0` because `@redocly/openapi-core` pins `4.1.1`), **brace-expansion** `2.1.1 → 2.1.4` ([GHSA-mh99-v99m-4gvg](https://github.com/advisories/GHSA-mh99-v99m-4gvg), via `minimatch`), and **dompurify** `3.4.11 → 3.4.13` ([GHSA-c2j3-45gr-mqc4](https://github.com/advisories/GHSA-c2j3-45gr-mqc4), via `jspdf`). Evidence is differential — `npm audit --package-lock-only` reported 7 vulnerabilities in `apps/web` and 1 in `gitpage` on the parent commit, and 0 in both afterwards. No scanner threshold, skip-dir, or ignore file was touched: nothing here was suppressed.
- **The sixth, `react-router` ([GHSA-qwww-vcr4-c8h2](https://github.com/advisories/GHSA-qwww-vcr4-c8h2), high), was not exploitable here — and was fixed anyway.** The advisory is explicit that it "only affects your application if you are using the unstable RSC APIs"; this app is a client-side SPA on `BrowserRouter` with no server components, server actions, or data router, so the vulnerable path was never reachable. It was still worth closing rather than documenting as an exception, because the only patched version is `react-router@8.3.0` and reaching it also retires an end-of-life runtime — see below.

### Changed
- **`react-router-dom` replaced by `react-router` v8; CI baseline raised from Node 20 to Node 22.** These are one change, not two. `react-router-dom` has no v8 — it was removed in that release, and on v7 it is a shim pinning `react-router` to the exact same 7.x version, so the fix was never reachable by a version bump. Migrating means importing from `react-router` directly (15 files, import specifier only — every API this app uses, `BrowserRouter` / `Routes` / `Route` / `Link` / `NavLink` / `Navigate` / `Outlet` / `useNavigate` / `useLocation`, exists unchanged on the v8 root export), and `react-router@8` declares `engines: node >=22.22.0`.
  - **Node 20 reached end-of-life on 2026-04-30**, so all three workflows were building, testing, and publishing on a runtime that no longer receives security patches. That is a defect on its own terms; the router migration only surfaced it. `NODE_VERSION` is now `"22"` in `github-ci-cd.yml`, `security-ci-cd.yml`, and `deploy-github-pages.yml`, and the README badge follows. Contributors on Node 20 will need to upgrade.
  - **No behavioural change was expected and none was observed:** `tsc --noEmit` clean, 68/68 Vitest, both builds clean, and — because no unit test touches the router at all, so the green unit suite proved nothing about this change — the full Playwright suite was run as the actual evidence: 15/15 across smoke, cockpit, journeys, import, diagram, pdf, history, release, and i18n.

---

## [7.7.0] — 2026-07-09

### Added
- **Threat traceability (CAPEC/CWE):** every generated STRIDE threat now carries a MITRE **CAPEC** attack-pattern and **CWE** weakness reference (e.g. Spoofing → `CAPEC-151` / `CWE-287`, Information Disclosure → `CAPEC-118` / `CWE-200`), alongside the existing OWASP ASVS / NIST CSF / ISO 27001 control references. Surfaced in `framework_ref_counts_by_catalog` and in the Markdown/JSON exports. Implemented data-driven via the STRIDE map — **no schema or OpenAPI contract change**. First step of the documented evolution plan ([docs/internal/reports/IMPROVEMENT_RESEARCH_2026-06.md](docs/internal/reports/IMPROVEMENT_RESEARCH_2026-06.md)).
- **SARIF export (`otm analyze --sarif-out <file>`):** suggested threats can now be written as **SARIF 2.1.0** — one result per active threat, grouped by a methodology+STRIDE rule, severity (`error`/`warning`/`note`) derived from the L×I score, and a rule `helpUri` linking to the threat's CWE/CAPEC reference — ready to upload to GitHub code scanning or any SARIF-aware pipeline. New `export_analysis_sarif` exporter; deterministic output. Contract-stable (CLI + exporter only). Second step of the evolution plan.
- **Open Threat Model (OTM) interoperability:** import IriusRisk **OTM 0.2.0** documents (`otm import otm <file>`) and export the canonical model to OTM (`otm export … --format otm`). Faithful structural round-trip (project / trust zones / components / dataflows / assets) with id sanitisation, referential-integrity guards, and component-`type`↔`kind` mapping — bridging App Suite Modeling with the OTM ecosystem (IriusRisk, StartLeft), the project's namesake format. New `otm_native` converter; CLI + converter only, no API/OpenAPI contract change. Third step of the evolution plan.
- **AI-lens traceability (OWASP LLM Top 10 2025 + MITRE ATLAS):** each PLOT4ai heuristic now carries standard AI-threat references — mapped per heuristic to the **OWASP Top 10 for LLM Applications 2025** (e.g. prompt-injection heuristics → `LLM01:2025`, RAG/embedding heuristics → `LLM08:2025`, agent tool-use → `LLM06:2025`, inference abuse → `LLM10:2025`) and, where a technique id is verified, to **MITRE ATLAS** (`AML.T0051` LLM Prompt Injection, `AML.T0024` Exfiltration via AI Inference API, `AML.T0034` Cost Harvesting). These are **additive** — a PLOT4ai threat keeps its STRIDE-category CAPEC/CWE references and gains the AI-specific ones — and surface in `framework_ref_counts_by_catalog` and the Markdown/JSON exports. Implemented data-driven via a new per-heuristic map (`ai_heuristic_framework_map.yaml`), reusing the same `framework_refs` mechanism as the CAPEC/CWE step — **no schema or OpenAPI contract change**. Fourth step of the evolution plan.
- **Report polish:** framework-reference aggregates now render friendly catalog labels — `capec` → *MITRE CAPEC*, `cwe` → *MITRE CWE*, `owasp_llm` → *OWASP LLM Top 10 (2025)*, `mitre_atlas` → *MITRE ATLAS* (previously the raw ids for the first two).

### Fixed
- **OTM import — malformed collection no longer crashes or silently empties the model.** `otm import otm` iterated the top-level OTM arrays with `for x in otm.get(key) or []`, which only substitutes *falsy* values. A present-but-non-array value therefore slipped through: a truthy scalar (`components: 5`, `dataflows: 3`) raised an uncaught `TypeError` that escaped every handler and printed a raw stack trace, while a string or mapping silently iterated its characters/keys and imported **zero** entries. Each of `trustZones` / `components` / `dataflows` / `assets` is now required to be an array when present, raising a `ValueError` the CLI renders as a friendly, actionable error (exit 1). Absent/`null`/empty still mean "no entries". Found by a pre-release deep review; regression tests added.
- **MITRE ATLAS reference name corrected.** The note for `AML.T0024` shipped the stale pre-rename name *"Exfiltration via ML Inference API"*. Per the canonical [`mitre-atlas/atlas-data`](https://github.com/mitre-atlas/atlas-data) (`dist/ATLAS.yaml`), MITRE renamed several techniques from *ML* to *AI*; the technique is **"Exfiltration via AI Inference API"**. The identifier itself was always correct. A test now pins the canonical names of all three referenced ATLAS techniques.
- **Security CI — a transient Snyk failure can no longer silently drop the Snyk gate.** The token probe added in `390c6fd` treated *any* non-zero `snyk auth` exit as "token unusable" and skipped the scan with a green job — so a Snyk outage, a `429` rate-limit, or a DNS/TLS blip would have quietly removed SAST+SCA coverage from a passing pipeline. The probe now distinguishes a genuine auth rejection (`SNYK-0005` / HTTP 401 → skip, with a Step Summary note) from every other failure (→ **fail closed and loud**, with an `::error::` annotation). Found by the same deep review.

### Maintenance
- **Dependencies:** refreshed `apps/web` and `gitpage` to the latest in-range versions (React 19.2.7, i18next 26.3.1, react-i18next 17.0.8, @playwright/test 1.61, Vitest, @vitejs/plugin-react 6.0.2, autoprefixer 10.5.0, lucide-react 0.577.0, and other in-range updates). `npm audit` remains **0** in both projects. Clears the open Dependabot npm PRs.
- **CI:** bumped pinned GitHub Actions to current SHAs — `step-security/harden-runner`, `actions/checkout`, and `github/codeql-action` (v4.36.2).
- **Repo hygiene:** `gitpage/.gitignore` now excludes the local `design-sync` tooling directories (scratch, ~43M of installed scripts/`node_modules`, and build bundles).

---

## [7.6.4] — 2026-06-18

### Security
- **API / industry-pack loader — path traversal (High, fixed):** `load_pack`, `load_template_yaml`, and `load_template_info` now reject any id that is not present in the embedded catalog *before* touching the filesystem. Previously an attacker-controlled `pack_id` (e.g. via unauthenticated `POST /v1/models/compare` with `run_analysis: true`) could contain `../` or an absolute path and make the loader read an arbitrary local `.yaml` file; combined with the validation-error echo below, the file's parsed contents were disclosed in the `422` body. Added an end-to-end regression test.
- **API — bounded validation-error echo:** domain `422` responses (`validate` / `precheck` / `analyze` / `diff` / `compare`) now truncate the echoed `input`/`ctx` to the same 256-character cap already applied to request-validation errors, so these errors can no longer reflect unbounded parsed content back to the client (closes the disclosure amplifier above and a ~1.6× response-amplification vector).
- **Exporters — generated-artifact injection hardening:** component and data-flow names are attacker-controllable model text. The Mermaid flowchart exporter now collapses line breaks and neutralizes the label-terminating `"`/`|`, so a crafted name can no longer inject extra Mermaid nodes/edges into the diagram source; the premium Markdown report escapes `|` and flattens line breaks in table cells, so a crafted name/threat title can no longer add columns or split a table row.
- **Web (`apps/web`):** bump `dompurify` `3.4.7 → 3.4.11` (transitive via `jspdf`), fixing three **Medium** DOMPurify advisories ([SNYK-JS-DOMPURIFY-17342528](https://security.snyk.io/vuln/SNYK-JS-DOMPURIFY-17342528), `-17344549`, `-17375136`); bump `vite → 8.0.16` (dev server / build tooling — **not** shipped in `dist/`) clearing [GHSA-fx2h-pf6j-xcff](https://github.com/advisories/GHSA-fx2h-pf6j-xcff) and [GHSA-v6wh-96g9-6wx3](https://github.com/advisories/GHSA-v6wh-96g9-6wx3); pin `js-yaml ≥ 4.2.0` via `overrides` to clear a **Medium** advisory reached through `openapi-typescript → @redocly/openapi-core`. `npm audit` now reports **0 vulnerabilities**.
- **GitHub Pages (`gitpage`):** bump `vite → 8.0.16`, clearing the same dev-tooling advisory; `npm audit` clean.

### CI
- **Security CI/CD** now degrades gracefully across contexts. A `preflight` job detects code-scanning availability (public repo or Advanced Security) and the Dependabot run context; SARIF upload, CodeQL, and Dependency Review are **skipped (not failed)** when unavailable, and Snyk/Gitleaks skip cleanly on Dependabot's read-only token. The scanners themselves remain hard gates on real findings. This clears the perpetual red on scheduled runs and Dependabot PRs without weakening detection, and re-activates full SARIF reporting automatically when the repository is public.

### Tests
- **Web UI:** added a Vitest component/hook/context/storage layer (jsdom + Testing Library) — 40 new unit tests covering `apiFetch` error mapping, analysis filters, browser-storage helpers, `ThemeContext`, `ToastContext`, `RiskScoreBar`, `StatusPill`, `EmptyState`, and `ErrorBoundary` (68 web unit tests total). Wired `vitest` into the GitHub CI/CD web job so unit tests now gate on every push and PR (previously only the build + Playwright E2E ran).
- **Python:** added the API error-truncation defensive branches (`errors.py` now 100%), a path-traversal security regression suite, and engine-defect regressions (PLOT4ai key-order seed independence; data-flow scoring). Suite is now **966 tests**.

### Fixed
- **Engine determinism (PLOT4ai):** `ai_system_context.heuristic_ids_by_layer` is now emitted in a stable canonical layer order. It was seeded from a `set(...)`, so the serialized key order varied with `PYTHONHASHSEED` across runs and broke byte-for-byte reproducibility of PLOT4ai analysis JSON (snapshots, signing, diffs). Values were already sorted — only the key order was affected.
- **Engine risk scoring (data flows):** an unencrypted data flow that does **not** cross a trust boundary is no longer double-counted. The STRIDE builder OR-ed "unencrypted" into the boundary-crossing signal while `risk_calc` already applied a dedicated encryption penalty, inflating such flows to L×I `5×5` (25, *critical*) instead of `4×4` (16, *high*). **Behavioral note:** this lowers scores and shifts the severity distribution for unencrypted internal flows (boundary-crossing and encrypted flows are unchanged); pinned analysis snapshots were regenerated accordingly.
- **Artifact import robustness:** importers no longer crash on valid-but-colliding or hostile input. `assemble_draft` now de-duplicates entities whose artifact-derived id collides — e.g. two Kubernetes resources of the same kind sharing a name across namespaces, a Terraform address duplicated across concatenated files, or names that collide after the slug length cap or against a reserved internal id — keeping the first and recording a reconciliation note in the draft's `unknowns`, instead of failing the entire draft with a schema "duplicate id" error (which previously surfaced as HTTP 400 / a CLI stack trace). OpenAPI/Swagger import additionally guards against non-string HTTP-method keys (YAML 1.1 `on`/`off`/numeric keys), which previously raised an `AttributeError` (HTTP 500).

---

## [7.6.3] — 2026-06-03

### Fixed
- **Web UI accessibility:** `Button` now renders an explicit keyboard-scoped `focus-visible` ring, matching the focus treatment of `Input` / `Select` / `Checkbox` (it previously relied only on the global outline, which the gradient variant could visually clip).
- **Web UI contrast:** lifted the dark-theme `--otm-text-subtle` token from `#5f7a6d` (~4.1:1) to `#789684` to clear WCAG AA (4.5:1) on the darkest surfaces, while keeping it clearly dimmer than `--otm-text-muted` (hierarchy preserved).

### CI
- Bumped `aquasecurity/trivy-action` to `v0.36.0` and `gitleaks/gitleaks-action` to `v3.0.0`, clearing the GitHub Actions Node 20 deprecation warnings (both now run on Node 24).

---

## [7.6.2] — 2026-06-03

### Security
- **Web (`apps/web`):** bump `react-router-dom` floor to `^7.14.2`; the lockfile now resolves `react-router` / `react-router-dom` `7.14.0 → 7.16.0`, fixing a **Critical** *Deserialization of Untrusted Data* advisory in `react-router` ([SNYK-JS-REACTROUTER-17137394](https://security.snyk.io/vuln/SNYK-JS-REACTROUTER-17137394)). Surfaced by the Snyk Open Source gate once code scanning re-enabled on the public repository; not yet present in the GitHub Advisory database at release time.

### Notes
- Supersedes `7.6.1`, whose security pipeline failed on the advisory above. `7.6.1` carries no contract change of its own; adopters should use `7.6.2`.

---

## [7.6.1] — 2026-06-03

### Summary
Maintenance and publication-readiness release. Clears the remaining CI quality gates from the 7.6.0 line, fixes cross-platform file-id handling in repository import, embeds real product screenshots in the README, and aligns the package version with the four post-7.6.0 commits. **No public CLI / API / UI contract change.**

### Fixed
- `otm import repo`: `_short_file_id` normalizes Windows backslash separators so generated component IDs are stable across operating systems.

### CI / Quality
- Cleared the Ruff format gate (`ruff format` across 34 files) and the Mypy (monorepo) gate by enabling the `pydantic.mypy` plugin for aliased-field call-args.
- Cleared lint, KICS (Checkmarx IaC), Snyk Code, and Docker hardening gates.

### Docs
- README embeds real product screenshots (landing page + analysis output) under `docs/screenshots/` in place of the previous placeholders.
- Refreshed the maintainer release assessment for the 7.6.x line (`docs/internal/reports/`).

### Repository hygiene
- Package version aligned to `7.6.1` across `pyproject.toml`, `apps/web/package.json`, and the web lockfile.

---

## [7.6.0] — 2026-05-28

### Summary
End-user validation hardening release: CLI now fails gracefully on missing output directories and refuses contradictory analyze flags, the Windows console renders accents/em-dashes/emojis correctly, the API caps echoed input in `422` responses, the diagram component stabilizes React Flow renders, and `otm import repo` can emit a chainable `.otm.yaml` seed. No public contract change beyond the new optional `--draft-out` flag and the additional 422 truncation; existing pipelines keep working.

### Highlights
- **CLI** `otm import repo` ganhou `--draft-out <path.otm.yaml>` que materializa um *seed* canónico mínimo (componentes, fronteira, fluxos e ativos) directamente encadeável em `otm validate` / `otm analyze`.
- **CLI** força `UTF-8` em `stdout` / `stderr` no entrypoint e desactiva `legacy_windows` no Rich console: em PowerShell 7, Windows Terminal e VS Code, acentos `pt-BR`, em-dashes `—`, bullets `·`, setas `→` e emojis aparecem íntegros sem `chcp 65001`.
- **API** `RequestValidationError` agora trunca strings/listas/dicts grandes no campo `errors[].input` (cap em 256 chars) — uma `422` para um `title` de 200 KB cabe em <1 KB.
- **UI** `ThreatModelDiagram` move `nodeTypes`/`edgeTypes` para escopo de módulo com `Object.freeze` e centraliza o `markerEnd` de edges, silenciando o aviso "new nodeTypes object" do React Flow em StrictMode.

### Fixed
- `otm init` deixou de vazar `FileNotFoundError` quando o diretório pai não existe: a CLI agora devolve `Failure: cannot write to ...` + `Next step: create the directory first` (`apps/cli/otm_cli/application/init_service.py`).
- `otm analyze --json-out`, `otm precheck --json-out`, `otm diff-analysis --json-out`, `otm report -o`, `otm diagram -o`, `otm export -o`, `otm backlog -o`, `otm import openapi/terraform/k8s/repo --output/--json-out/--explain-out/--draft-out`, e `otm diff --json-out` deixaram de vazar tracebacks quando o diretório de saída não existe; todos passam pelo helper único `shared/emit.write_text_file` + `write_json_file` que valida o `parent` e levanta `CliUserError` legível.
- `otm analyze -m <metodologia> --auto-methodology` deixou de aceitar silenciosamente o conflito; agora dispara `BadParameter` ("mutually exclusive; pass only one") em vez de executar `stride` ignorando o pedido de recomendação automática.

### Changed
- `apps/cli/otm_cli/main.py` configura `PYTHONIOENCODING=utf-8` e chama `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` antes de importar `otm_cli.cli`.
- `apps/cli/otm_cli/commands/bootstrap.py` instancia o Rich `Console(..., legacy_windows=False)` para preservar caixas/painéis íntegros no Windows moderno.
- `apps/web/src/components/diagram/ThreatModelDiagram.tsx`: `EDGE_MARKER_END` ao módulo, `nodeTypes` e `edgeTypes` `Object.freeze` no escopo do ficheiro, e a `<ReactFlow>` recebe ambos.

### Security
- 422 da API deixa de ecoar input completo: o handler em `apps/api/otm_api/errors.py` trunca strings com mais de 256 caracteres com sufixo `…[N chars suppressed]`, listas longas com `…[N items suppressed]` e limita aninhamento, reduzindo amplificação por *input echo* em cenários hostis.
- `SECURITY.md` ganhou uma secção *Postura de implantação* explicando que a API e a UI são desenhadas para uso local; quando expostas, é necessário activar `slowapi`, `OptionalApiKeyMiddleware` e restringir `CORS`.

### Docs
- `docs/README.md` actualiza a referência de versão para `7.6.0` (resolvia drift contra `pyproject.toml`).
- `docs/features/CLI.md` documenta a nova mensagem de erro para `-o`/`--json-out` em directório inexistente, a exclusividade `--methodology` vs `--auto-methodology`, e a postura UTF-8 no Windows.
- `docs/features/ARTIFACT_IMPORT.md` clarifica o âmbito de `otm import repo` ("scan pragmático") e documenta `--draft-out` como caminho oficial para encadear em `validate`/`analyze`.

### Repository hygiene
- `.gitignore` passa a ignorar `_tortura_sandbox/`, `.playwright-mcp/` e `ui-*.png` (artefactos locais da validação extrema).

### Tests
- Nova suite `tests/test_cli_write_paths_and_flag_conflicts.py` cobre os caminhos que antes vazavam traceback e a exclusividade `-m` ↔ `--auto-methodology`.
- Nova suite `tests/test_api_errors_truncate.py` valida o cap de 256 chars em strings/dicts/listas e a preservação dos demais campos do `errors[]`.
- Nova suite `tests/test_cli_import_draft.py` cobre `scan_payload_to_draft_yaml` (estrutura, ativo de sessão, marcação de `/admin`, ausência de inferências) e o encadeamento `import repo --draft-out` → `validate`.
- Suite total: **951 passed, 1 skipped** + **17 testes regressivos novos**.

---

## [7.5.0] — 2026-04-09

### Summary
Release metadata alignment, clearer public changelog narrative, and **Typer/Click** constraints so the CLI and test suite load cleanly on Python 3.12+ (generic `click.Choice` compatibility).

### Highlights
- **Dependencies:** `typer>=0.12.3` and `click>=8.2` for `[cli]` and `[dev]` — avoids `TypeError: type 'Choice' is not subscriptable` when importing the CLI in tests
- More consistent, user-facing **CHANGELOG** wording for the capability set shipped in the 7.4 line
- **SemVer** alignment across `pyproject.toml` and the web app (`7.5.0`) for packaging and GitHub Releases
- Tag **`v.7.5`** follows the repository’s existing `v.7.x` tagging style

### Improvements
- Easier mapping between Git tags and package version for adopters and CI
- Clearer communication of methodology guidance, model validation, and analysis reporting themes

---

## [7.4.0] — 2026-04-07

### Summary
Improved methodology recommendation, stronger model quality validation, and better analysis reporting.

### Highlights
- Refined methodology recommendation and ranking behavior
- Improved model quality precheck for stronger validation
- Added aggregate risk summary to analysis exports
- Better alignment of industry-pack template metadata
- Expanded regression coverage for ranking and catalog consistency

### Improvements
- Better consistency between methodology guidance and engine analysis
- Improved export clarity for decision-making
- Enhanced reliability in catalog and recommendation behavior

---

## [7.3.0] — 2026-04-07

### Summary
Documentation restructuring, improved premium reporting, stronger core validation, and platform governance enhancements.

### Highlights
- Reorganized documentation for better structure and maintainability
- Improved premium reporting (PDF/HTML) with more structured outputs
- Stronger core validation with standardized entity identifiers
- Enhanced Web UI normalization for better comparison and display
- Improved open-source governance (community templates and standards)

### Improvements
- Better consistency across documentation and platform structure
- Improved report quality and readability
- Enhanced CI stability and dependency management

---

## [7.2.0] — 2026-04-02

### Summary
Security and DevSecOps improvements, frontend upgrades, and stronger API controls.

### Highlights
- Optional API security controls (rate limiting and API key support)
- Upgraded frontend stack for better performance and stability
- Strengthened CI/CD with additional security and quality checks
- Improved dependency management for deterministic builds

### Improvements
- Better API behavior and validation handling
- Enhanced test coverage and CI reliability
- Improved frontend stability and build consistency

---

## [7.1.0] — 2026-04-08

### Summary
Internationalization, improved reporting, and stronger platform modularity.

### Highlights
- Full internationalization support (pt-BR / en)
- Localized exports and reporting capabilities
- Improved CLI structure and modularity
- Enhanced API observability and configuration
- Strengthened CI, testing, and security checks

### Improvements
- Better consistency across Web, API, and CLI
- Improved semantic comparison capabilities
- Enhanced documentation structure and clarity

---

## [7.0.0] — 2026-04-07

### Summary
Contract-driven architecture, semantic comparison improvements, and hybrid E2E testing.

### Highlights
- OpenAPI as the single source of truth for contracts
- Improved semantic comparison engine
- Hybrid end-to-end testing across API and UI
- Stronger CI validation for contract consistency

### Improvements
- Better alignment between backend and frontend
- Improved reliability of generated outputs
- Enhanced testing and validation workflows

---

## [6.0.0] — 2026-04-06

### Summary
Stronger type contracts, improved comparison capabilities, and expanded analysis coverage.

### Highlights
- Improved type safety across platform components
- Enhanced semantic comparison with structured insights
- Expanded detection capabilities and analysis coverage
- Improved reporting and export consistency

### Improvements
- Better platform stability and validation
- Increased reliability across workflows
- Enhanced multi-channel output consistency

---

## [5.0.0] — 2026-04-03

### Summary
Improved analysis experience and introduction of advanced modeling capabilities.

### Highlights
- Enhanced analysis UI with decision support features
- Introduction of anti-pattern detection and benchmark metrics
- Improved semantic comparison capabilities
- Repository scanning for artifact import

### Improvements
- Better usability across modeling workflows
- Increased accuracy of analysis results
- Stronger foundation for advanced features

---

## [4.0.0] — 2026-04-02

### Summary
Improved modeling quality and introduction of premium reporting.

### Highlights
- Advanced reporting capabilities
- Improved modeling validation and guidance
- Expanded methodology coverage

### Improvements
- Better consistency across platform components
- Improved output quality and usability

---

## [0.1.0] — 2026-04-01

### Summary
Initial public release introducing the core platform.

### Highlights
- Core threat modeling engine and workflows
- Web UI, API, and CLI integration
- Export capabilities (JSON, Markdown, diagrams)
- Initial methodology support and analysis features
- Basic CI, testing, and validation setup

### Improvements
- Established foundation for future platform growth

---

**License:** MIT
