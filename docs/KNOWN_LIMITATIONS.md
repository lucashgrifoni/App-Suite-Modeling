# Limitações conhecidas (série 7.x)

Documento objetivo para utilizadores e mantenedores. Complementa o [congelamento de escopo](internal/decisions/RELEASE_SCOPE_FREEZE.md) e o [fecho de engenharia](internal/decisions/ENGINEERING_CLOSEOUT_SCOPE.md).

## Produto e plataforma

- **Sem persistência server-side:** a UI usa rascunho local (`sessionStorage`). Não há contas, equipas nem histórico centralizado.
- **Autenticação na API (opcional):** pode activar-se **`OTM_API_KEY`** para proteger `/v1/*`; sem esta variável, a API permanece aberta na rede onde correr. A UI não gere contas; implantação pública requer reverso/gateway conforme `architecture/DEPLOYMENT_INVARIANTS.md`.
- **MVP de diagramação:** canvas avançado não é o fluxo principal; exportação textual e Mermaid cobrem o núcleo.

## Heurísticas e metodologias

- **Falsos positivos/negativos:** análise é assistida por heurísticas e lentes; revisão humana permanece obrigatória para decisões de risco.
- **PLOT4ai:** matching “token-safe” reduz ruído; textos ambíguos ou muito curtos ainda podem gerar sinais imperfeitos (ver `features/PLOT4AI_AI_SYSTEM.md`).
- **Maturidade variável:** STRIDE é o mais maduro; outras metodologias são **Evolving** ou **Specialized** (ver matriz em `internal/decisions/RELEASE_SCOPE_FREEZE.md`).

## Gate de deriva na CI (`otm diff --fail-on`)

- **Renomear componentes ou fluxos gera ruído:** o id da heurística deriva do alvo, logo renomear um componente muda a assinatura da ameaça e ela aparece como **nova**. O relatório do gate mostra as remoções emparelhadas, tornando o rename evidente, mas o build reprova. Renomeie em PRs separados das mudanças de arquitectura.
- **Só é significativo dentro de uma versão do motor:** heurísticas evoluem entre versões. `otm diff --with-analysis` analisa ambos os lados no mesmo processo (seguro); `otm diff-analysis` recusa gatear dois `analyze.json` com `engine_version` diferente (exit `1`).
- **O gate herda os limites das heurísticas:** um gate verde significa "nenhuma ameaça *heurística* nova acima do limiar", não "o modelo é seguro". Ver `CI_AND_SECURITY_EVIDENCE.md` §8.

## Import de artefatos

- **Rascunho, não verdade:** imports produzem `.otm.yaml` para revisão; nomes, trust boundaries e classificação de dados podem exigir ajuste manual.
- **Cobertura:** formatos suportados e comportamento estão em `features/ARTIFACT_IMPORT.md`; artefatos exóticos ou malformados podem falhar validação de forma explícita.

## Windows e terminal

- **`npm run build`:** em paths com caracteres problemáticos (ex.: `&`), o wrapper `.cmd` pode falhar; usar **`npm run ci:build:portable`** (chama `node` diretamente).
- **Unicode na consola:** saída da CLI com setas/carateres Unicode (ex. `→`) pode gerar `UnicodeEncodeError` ao imprimir para stdout em consolas `cp1252`; preferir **redirecionar para ficheiro** (`-o`) ou usar terminal UTF-8.

## Build e CI

- **E2E Playwright:** requer browsers instalados (`npx playwright install chromium`); em CI isso deve estar no pipeline.
- **Wheel:** gerado com `python -m build`; artefactos em `dist/` estão no `.gitignore`.

## Dependências e segurança open source

- **Segredos:** não commitar tokens, passwords ou chaves privadas; usar variáveis de ambiente e `.env` ignorado.
- **SCA:** executar auditoria periódica (`pip audit`, `npm audit`) antes de releases; o projeto não fixa versões patch-a-patch de todas as transitivas — avaliar risco no contexto da sua implantação.

## Compatibilidade

- **Python:** `>=3.11` conforme `pyproject.toml`.
- **API `/v1/`:** clientes devem tolerar campos opcionais adicionados sem quebra em **minor releases** da mesma linha de versão publicada (ver `CHANGELOG.md` para mudanças de contrato).
