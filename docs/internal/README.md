# `docs/internal` — registos datados, não estado corrente

**Leia isto antes de qualquer ficheiro desta pasta.**

Tudo aqui é um **registo pontual**: uma auditoria, um relatório de decisão, um log de execução
ou um checklist, escrito numa data concreta sobre a versão que existia nessa data. São
mantidos porque o raciocínio tem valor histórico — mostram o que se sabia, o que se decidiu e
porquê.

**Não são uma descrição do produto de hoje.** Vários descrevem problemas que já foram
corrigidos, pontuações que já mudaram e riscos que já não se aplicam. Algumas dessas
afirmações eram verdadeiras quando foram escritas e são falsas agora.

Exemplos concretos, para que ninguém precise de descobrir por tentativa:

- Auditorias anteriores a **v7.6.0** descrevem a API como sem autenticação nem limitação de
  ritmo. A API tem hoje autenticação por chave (`OTM_API_KEY`) e *rate limiting*.
- Auditorias anteriores a **v7.9.0** descrevem o pipeline como não tendo SAST, ou dizem que
  Snyk, Trivy, Checkbox/KICS e Semgrep estão "não configurados". Todos correm hoje em
  `security-ci-cd.yml`. As etapas de code scanning só correm quando o repositório é **público** ou tem GitHub Advanced Security — o `preflight` desse workflow calcula-o e salta-as caso contrário, por isso a visibilidade não se afirma aqui: lê-se do repositório.
- Os relatórios que apontam para `.github/workflows/ci.yml` referem-se a um ficheiro que foi
  substituído por `github-ci-cd.yml` e `security-ci-cd.yml`.

## Onde está o estado corrente

| Pergunta | Fonte de verdade |
|---|---|
| O que o projeto faz e como se usa | [`README.md`](../../README.md) |
| O que mudou em cada versão | [`CHANGELOG.md`](../../CHANGELOG.md) |
| Que controlos de segurança correm no CI | [`docs/CI_AND_SECURITY_EVIDENCE.md`](../CI_AND_SECURITY_EVIDENCE.md) |
| Limitações aceites | [`docs/KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md) |
| Como reportar uma vulnerabilidade | [`SECURITY.md`](../../SECURITY.md) |

Se um documento desta pasta contradisser uma das fontes acima, **a fonte acima ganha**.

## Regra para quem escrever aqui

Datar o documento e escrever no passado. Um "estado final verificado" que ninguém volta a
verificar envelhece para falso — foi exatamente o que aconteceu com
[`audits/SONAR_DECISION_REPORT.md`](audits/SONAR_DECISION_REPORT.md), que afirmou durante
meses que um ficheiro tinha sido removido enquanto ele continuava versionado.
