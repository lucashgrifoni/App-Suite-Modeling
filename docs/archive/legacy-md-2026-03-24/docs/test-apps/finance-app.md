# Financas - App de Teste

## Visao geral
Carteira digital minima para validar comportamento do projeto em cenarios de transferencia, integridade de saldo e webhook de pagamento.

## Atores
- Usuario
- Administrador

## Fluxos principais
- Login/cadastro
- Leitura de saldo
- Transferencia entre contas
- Consulta de historico
- Exportacao de extrato
- Confirmacao de pagamento via webhook mockado

## Ativos criticos
- Saldos de conta
- Historico de transacoes
- Trilha de auditoria
- Identificadores de usuario

## Dados sensiveis
- Dados financeiros
- Dados pessoais basicos vinculados a conta

## Integracoes
- Provedor externo mockado de webhook de pagamento

## Trust boundaries
- Internet
- Aplicacao
- Dados internos
- Integracao externa de pagamento

## Regras de negocio criticas
- Usuario comum nao transfere de conta de terceiros.
- Saldo nao pode ficar negativo.
- Confirmacao de pagamento depende de webhook valido.
- Admin pode consultar saldo/historico para operacao.
- Transferencia exige `transfer_request_id` idempotente (anti dupla submissao).
- Evento de webhook exige `webhook_event_id` unico (anti replay).
- Estado de transacao confirmada nao pode regredir por ordem de eventos.
- Bloqueios de autorizacao e fraude devem gerar trilha de auditoria.

## Cenarios obrigatorios de teste
- Transferencia legitima entre contas
- Tentativa de transferencia indevida entre contas de terceiros
- Leitura de saldo por user e admin
- Exportacao de extrato
- Webhook valido e invalido
- Replay de webhook bloqueado por `webhook_event_id` repetido
- Dupla submissao de transferencia bloqueada por `transfer_request_id`
- Tentativa de exportar extrato de conta de terceiro bloqueada
- Registro de eventos bloqueados em `audit_log` (fraude/autorizacao)

## Riscos esperados mais relevantes
- IDOR/autorizacao fraca entre contas
- Manipulacao de webhook
- Tampering de transacao/saldo
- Exposicao de dados financeiros

## Attack Tree (resumo)
### Billing/transferencia
- Objetivo: desviar valor sem autorizacao
- Caminhos:
  - abusar autorizacao de conta origem
  - forjar payload de transferencia
  - dupla submissao sem idempotencia de requisicao
  - corrida de eventos para causar inconsistencia de saldo

### Webhook
- Objetivo: confirmar pagamento falso
- Caminhos:
  - assinatura ausente/invalida
  - replay de evento antigo sem controle de `event_id`
  - alteracao de status em transito
  - regressao de estado (confirmed -> pending) por ordem de eventos
