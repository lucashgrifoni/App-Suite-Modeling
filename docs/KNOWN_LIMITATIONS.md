# Limitações conhecidas (série 7.x)

Documento objetivo para utilizadores e mantenedores. Complementa o [congelamento de escopo](RELEASE_SCOPE_FREEZE.md) e o [fecho de engenharia](ENGINEERING_CLOSEOUT_SCOPE.md).

## Produto e plataforma

- **Sem persistência server-side:** a UI usa rascunho local (`sessionStorage`). Não há contas, equipas nem histórico centralizado.
- **Sem autenticação/autorização na API/UI:** implantação exposta à internet requer reverso com controlo de acesso à sua cargo.
- **MVP de diagramação:** canvas avançado não é o fluxo principal; exportação textual e Mermaid cobrem o núcleo.

## Heurísticas e metodologias

- **Falsos positivos/negativos:** análise é assistida por heurísticas e lentes; revisão humana permanece obrigatória para decisões de risco.
- **PLOT4ai:** matching “token-safe” reduz ruído; textos ambíguos ou muito curtos ainda podem gerar sinais imperfeitos (ver `PLOT4AI_AI_SYSTEM.md`).
- **Maturidade variável:** STRIDE é o mais maduro; outras metodologias são **Evolving** ou **Specialized** (ver matriz em `RELEASE_SCOPE_FREEZE.md`).

## Import de artefatos

- **Rascunho, não verdade:** imports produzem `.otm.yaml` para revisão; nomes, trust boundaries e classificação de dados podem exigir ajuste manual.
- **Cobertura:** formatos suportados e comportamento estão em `ARTIFACT_IMPORT.md`; artefatos exóticos ou malformados podem falhar validação de forma explícita.

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
- **API `/v1/`:** clientes devem tolerar campos opcionais adicionados sem quebra em minor releases da série `0.x`.
