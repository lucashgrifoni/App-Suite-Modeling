# Matriz de Coleta de Insights - Test Apps

| Dominio | Cobertura funcional | Cobertura estrutural | Cobertura de ameacas | Aderencia ao dominio | Qualidade do output | Clareza | Consistencia | Profundidade | Falsos positivos | Gaps | Qualidade das recomendacoes | Priorizacao de risco de negocio | Facilidade de uso como fixture | Decisao final por app |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Financas | Alta (smoke + validate + analyze + report OK) | Alta (atores, ativos, boundaries e integracoes explicitas) | Boa (35 heuristicas; cenarios de replay e idempotencia agora exercitaveis) | Alta | Boa | Alta | Alta | Media-alta | Baixo-moderado (ainda ha ruido generico) | Saida ainda pode subdetalhar abuso economico fino | Boa | Media-alta | Alta | Parcial |
| Saude | Alta (todos passos OK) | Alta (estrutural completa) | Alta (80 heuristicas + lente LINDDUN + bloqueios por papel no fixture) | Alta | Boa | Alta | Alta | Alta | Baixo | Profundidade de notificacao sensivel pode evoluir mais | Boa | Boa | Alta | Aprovado |
| E-commerce/Assinatura | Alta (todos passos OK) | Alta (estrutural completa) | Boa (48 heuristicas + lente PASTA + cenarios de cupom/replay/entitlement) | Alta | Boa | Alta | Alta | Media-alta | Moderado (parte generica repetitiva) | Fraude economica avancada ainda parcial | Boa | Media | Alta | Parcial |
