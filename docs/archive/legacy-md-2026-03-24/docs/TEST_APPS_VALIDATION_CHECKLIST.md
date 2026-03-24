# Checklist Geral de Validacao dos Test Apps

## 1) Estrutura e isolamento
- [x] Apps criados em area isolada (`fixtures/apps` e `examples/test-apps`)
- [x] Sem alteracao da arquitetura principal
- [x] Sem regressao aparente no projeto existente
- [x] Cada app com README proprio e escopo controlado

## 2) Validacao funcional minima por app
### Financas
- [x] Login/cadastro
- [x] Leitura de saldo
- [x] Transferencia
- [x] Historico
- [x] Exportacao de extrato
- [x] Webhook de pagamento
- [x] Segregacao user/admin
- [x] Replay de webhook bloqueado
- [x] Dupla submissao de transferencia bloqueada
- [x] Extrato de terceiro bloqueado
- [x] Eventos criticos bloqueados auditaveis

### Saude
- [x] Login/cadastro
- [x] Agendamento
- [x] Cancelamento
- [x] Prontuario
- [x] Upload/listagem de documento
- [x] Acesso por papeis
- [x] Notificacoes mockadas
- [x] Bloqueio de prontuario sem vinculo
- [x] Bloqueio de documentos de terceiros
- [x] Cancelamento por perfil incorreto bloqueado
- [x] Notificacoes sem excesso de dados sensiveis

### E-commerce/Assinatura
- [x] Login/cadastro
- [x] Catalogo
- [x] Carrinho
- [x] Checkout
- [x] Cupom
- [x] Assinatura
- [x] Entitlement premium
- [x] Webhook de pagamento
- [x] Reutilizacao de cupom bloqueada
- [x] Empilhamento de desconto bloqueado
- [x] Replay de webhook bloqueado
- [x] Entitlement revogado no cancelamento
- [x] Consistencia billing x entitlement validada

## 3) Cobertura estrutural
- [x] Atores identificados corretamente
- [x] Ativos identificados corretamente
- [x] Trust boundaries identificadas
- [x] Fluxos principais identificados
- [x] Integracoes externas identificadas
- [x] Regras de negocio criticas representadas

## 4) Cobertura de ameacas
- [x] Ameacas relevantes por dominio capturadas
- [x] Diferenciacao entre falha tecnica e fraude/abuso (melhorada via cenarios de abuso no fixture)
- [x] Autenticacao/autorizacao tratadas
- [x] Integridade de dados tratada
- [x] Exposicao de dados sensiveis tratada
- [x] Webhook/billing/entitlement tratados quando aplicavel
- [x] STRIDE aplicado como base
- [x] Attack Trees aplicadas para billing/webhook/entitlement (nos docs de app)

## 5) Qualidade dos outputs
- [x] Output claro
- [x] Output consistente entre os 3 apps
- [x] Output acionavel
- [x] Recomendacoes uteis
- [ ] Baixa genericidade excessiva (ainda ha genericidade parcial no motor)
- [ ] Sem omissoes graves (melhorou em fixture, mas saida ainda pode omitir fraude economica fina)
- [x] Falsos positivos mapeados

## 6) Robustez do projeto
- [x] Nada quebrou durante execucao
- [x] Sem inconsistencias criticas entre dominios
- [x] Sem alucinacao arquitetural relevante
- [x] Sem perda grave de contexto de dominio
- [x] Escalou bem do primeiro ao terceiro caso
