# E-commerce/Assinatura - App de Teste

## Visao geral
E-commerce minimo com fluxo de assinatura para validar billing, cupom, entitlement premium e webhook de pagamento.

## Atores
- Cliente
- Administrador

## Fluxos principais
- Login/cadastro
- Consulta de catalogo
- Carrinho
- Checkout mockado
- Aplicacao de cupom
- Ativacao/cancelamento de assinatura
- Liberacao de entitlement premium
- Confirmacao via webhook

## Ativos criticos
- Estado de pagamento
- Regras de cupom/desconto
- Estado de assinatura
- Entitlement premium

## Dados sensiveis
- Dados de cobranca (mock)
- Estado de acesso premium

## Integracoes
- Gateway de pagamento mockado (webhook)

## Trust boundaries
- Internet
- Core da aplicacao ecommerce
- Dados internos
- Provedor externo de pagamento

## Regras de negocio criticas
- Premium so libera apos pagamento confirmado.
- Cupom nao pode gerar desconto indevido fora da regra.
- Cancelamento revoga entitlement do cliente.
- Admin pode verificar estado e manter acesso operacional.
- Cupom nao pode ser reutilizado pelo mesmo cliente.
- Empilhamento de cupom (stacking) deve ser bloqueado.
- Webhook exige assinatura valida e `webhook_event_id` unico.
- Billing deve manter consistencia de owner/valor antes de liberar entitlement.

## Cenarios obrigatorios de teste
- Checkout com cupom valido
- Tentativa de acesso premium antes do pagamento
- Webhook de pagamento valida entitlement
- Cancelamento de assinatura revoga acesso
- Segregacao de acesso cliente/admin
- Reutilizacao abusiva de cupom bloqueada
- Empilhamento de descontos bloqueado
- Replay de webhook bloqueado
- Inconsistencia owner pagamento x usuario bloqueada
- Entitlement revogado corretamente apos cancelamento

## Riscos esperados mais relevantes
- Inconsistencia pagamento x entitlement
- Fraude de cupom
- Forja/replay de webhook
- Escalacao de privilegio para conteudo premium

## Attack Tree (resumo)
### Billing
- Objetivo: obter servico sem pagar valor devido
- Caminhos:
  - manipular total no checkout
  - aplicar cupom fora de regra
  - reutilizar cupom de uso unico
  - empilhar descontos para reduzir total indevidamente
  - alterar status de pagamento

### Webhook
- Objetivo: simular pagamento aprovado
- Caminhos:
  - assinatura invalida aceita
  - replay de evento pago sem controle de idempotencia
  - troca de identificador de usuario/pedido

### Entitlement/acesso
- Objetivo: acessar premium sem direito
- Caminhos:
  - bypass de verificacao de assinatura
  - stale cache de entitlement
  - condicao de corrida entre cancelamento e acesso
  - mismatch entre billing confirmado e entitlement ativo
