# Relatório de decisão — Sonar no pipeline (B-07 / P2)

## Decisão tomada

**Opção B — remoção honesta** do ficheiro `sonar-project.properties` e **sem** job SonarCloud/SonarQube no GitHub Actions.

## Justificativa

- Existia configuração Sonar **órfã** (sem integração real no CI), gerando a falsa impressão de quality gate.
- Não há, neste repositório, runner SonarQube self-hosted nem tokens/organização SonarCloud documentados para uso seguro em CI público.
- Preferiu-se **estado explícito**: qualidade é garantida por **Ruff, Mypy (alvo), pytest, pip-audit, npm audit, E2E** — gates presentes em `.github/workflows/ci.yml`.

## Impacto

- Menos ficheiros de configuração enganadores na raiz.
- Equipa não perde tempo a assumir análise Sonar em PR até existir integração real.

## Próximos passos (se Sonar voltar a fazer sentido)

1. Decidir SonarCloud (repos públicos) vs SonarQube self-hosted.
2. Adicionar secrets (`SONAR_TOKEN`, etc.) e job com `sonar-scanner` ou action oficial.
3. Restaurar `sonar-project.properties` **no mesmo PR** que o job, com quality gate acordado.
4. Actualizar este documento e o CHANGELOG.

## Estado final verificado

- Não há `sonar-project.properties` no repositório.
- O workflow CI não referencia Sonar.
