# Plano Mestre de Validacao de Apps de Teste

## Objetivo da iniciativa
Validar, de forma pratica, se o projeto analisa corretamente cenarios realistas e pequenos de tres dominios criticos (Financas, Saude e E-commerce/Assinatura), sem alterar o core da arquitetura e sem regressao.

## Hipotese de validacao
Se o projeto estiver funcional e consistente, entao os 3 dominios devem:
- validar schema sem erro;
- produzir analise sem quebra;
- gerar relatorio consumivel;
- manter consistencia estrutural entre outputs;
- expor ameacas de dominio com variacao coerente entre metodologias.

## Por que estes 3 dominios
- **Financas:** exercita integridade, autorizacao entre contas, dados sensiveis e webhook.
- **Saude:** exercita privacidade, segregacao de acesso por papel e exposicao de documentos/prontuario.
- **E-commerce/Assinatura:** exercita billing, cupom/fraude, webhook e entitlement premium.

## Escopo de cada app
- **Financas:** login, saldo, transferencia, historico, exportacao, webhook, papeis user/admin.
- **Saude:** login, agenda, cancelamento, prontuario, upload/listagem docs, notificacao mock, papeis patient/professional/admin.
- **E-commerce/Assinatura:** login, catalogo, carrinho, checkout, cupom, assinatura, entitlement, webhook, papeis client/admin.

## O que esta sendo validado
- Cobertura estrutural de atores, ativos, trust boundaries, fluxos e integracoes externas.
- Cobertura de ameacas sob lente principal **STRIDE**.
- Aplicacao de **Attack Trees** em billing, webhook e entitlement/acesso.
- Apoio de priorizacao de risco de negocio com **PASTA**.
- Consistencia, clareza e acionabilidade dos outputs.

## O que nao esta sendo validado
- Performance, escalabilidade e hardening de producao.
- UX/front-end rico.
- Integracoes reais com provedores externos.
- Compliance formal completo (LGPD/HIPAA/PCI em profundidade).

## Criterios de aceite
- Apps isolados, sem alterar arquitetura principal.
- Fluxos minimos executados ou validados estruturalmente.
- Analise do projeto executada para os tres apps.
- Outputs comparaveis e documentados.
- Sem regressao evidente no repositório.

## Quality gates de aprovacao
- **Gate 1 - Escopo:** exatamente 3 apps, pequenos e sem features extras.
- **Gate 2 - Isolamento:** sem contaminacao do core; rollback simples.
- **Gate 3 - Qualidade de codigo:** legivel, coeso, sem dependencia inutil.
- **Gate 4 - Executabilidade:** fixtures executam; modelo valida e analisa.
- **Gate 5 - Testabilidade:** fluxo minimo automatizado com evidencias.
- **Gate 6 - Valor de validacao:** cenarios realmente exercitam risco.
- **Gate 7 - Anti-regression:** sem quebra evidente do comportamento principal.
- **Gate 8 - Documentacao:** todos os artefatos obrigatorios presentes.

## Estrategia de execucao
1. Rodar smoke de cada app fixture (`python fixtures/apps/.../app.py`).
2. Rodar `otm validate`, `otm analyze` e `otm report` em cada `.otm.yaml`.
3. Salvar artefatos por dominio em `artifacts/test-app-validation/<app>/`.
4. Consolidar observacoes na matriz e no relatorio final.

## Estrategia de comparacao
- Comparar os 3 dominios pelas mesmas dimensoes:
  - cobertura funcional;
  - cobertura estrutural;
  - cobertura de ameacas;
  - clareza/consistencia/profundidade;
  - qualidade de recomendacoes;
  - priorizacao de risco de negocio.
- Usar `docs/TEST_APPS_INSIGHTS_MATRIX.md` como base unica de decisao.

## Forma de coleta de insights
- Evidencias objetivas: exit code, arquivos gerados, contagem de achados.
- Analise qualitativa: relevancia das ameacas, profundidade do output e falsos positivos percebidos.
- Comparacao cruzada por dominio usando matriz unica.

## Limitacoes conhecidas
- Fixtures sao simplificadas e in-memory por design.
- Attack trees sao documentadas como cenarios e caminhos de ataque, nao como modelagem formal extensa.
- Resultado depende do estado local de instalacao da CLI e dependencias Python.
- Nao substitui uma validacao completa de release global do repositorio.
