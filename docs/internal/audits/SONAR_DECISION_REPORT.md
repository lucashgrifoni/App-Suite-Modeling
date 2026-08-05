# Relatório de decisão — Sonar no pipeline (B-07 / P2)

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


## Decisão tomada

**Opção B — remoção honesta** do ficheiro `sonar-project.properties` e **sem** job SonarCloud/SonarQube no GitHub Actions.

## Justificativa

- Existia configuração Sonar **órfã** (sem integração real no CI), gerando a falsa impressão de quality gate.
- Não há, neste repositório, runner SonarQube self-hosted nem tokens/organização SonarCloud documentados para uso seguro em CI público.
- Preferiu-se **estado explícito**: qualidade é garantida por **Ruff, Mypy (alvo), pytest, pip-audit, npm audit, E2E** — gates presentes em `.github/workflows/github-ci-cd.yml` + `.github/workflows/security-ci-cd.yml`.

## Impacto

- Menos ficheiros de configuração enganadores na raiz.
- Equipa não perde tempo a assumir análise Sonar em PR até existir integração real.

## Próximos passos (se Sonar voltar a fazer sentido)

1. Decidir SonarCloud (repos públicos) vs SonarQube self-hosted.
2. Adicionar secrets (`SONAR_TOKEN`, etc.) e job com `sonar-scanner` ou action oficial.
3. Restaurar `sonar-project.properties` **no mesmo PR** que o job, com quality gate acordado.
4. Actualizar este documento e o CHANGELOG.

## Estado final verificado — **actualizado 2026-08-05**

A decisão original (remover o ficheiro) **foi revertida na prática** e este documento ficou
a afirmar o contrário durante meses. O estado real, verificado:

- **`sonar-project.properties` existe e está versionado na raiz.** Foi reposto para suportar
  a campanha de qualidade Sonar corrida localmente (0 issues, quality gate OK), e as suas
  exclusões de cobertura estão afinadas a ficheiros concretos deste repositório — não é
  configuração órfã abandonada, é configuração usada manualmente.
- **Nenhum workflow referencia Sonar** (`git grep -i sonar .github/workflows/` não devolve
  nada). Continua a não haver quality gate Sonar em CI, e isso é deliberado: não há runner
  self-hosted nem organização SonarCloud documentada para uso seguro num repositório público.
- Logo, a preocupação original mantém-se parcialmente válida: **a presença do ficheiro pode
  sugerir a um leitor que existe um gate Sonar em PR, e não existe.** Quem ler a raiz do
  repositório deve assumir que a qualidade é garantida por Ruff, Mypy, pytest, os scanners
  de `security-ci-cd.yml` e os E2E — não por Sonar.

Se Sonar voltar a ser ligado ao CI, seguir os "Próximos passos" acima e **actualizar esta
secção no mesmo PR**. A lição desta correcção é que um "estado final verificado" que ninguém
volta a verificar envelhece para falso.
