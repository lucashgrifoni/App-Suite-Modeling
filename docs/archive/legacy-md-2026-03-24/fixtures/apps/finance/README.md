# App de Teste - Financas

## Descricao do dominio
Carteira digital simplificada com conta de saldo, transferencia entre contas e confirmacao via webhook mockado.

## Atores
- Usuario
- Administrador

## Funcionalidades
- Cadastro/login
- Leitura de saldo
- Transferencia entre contas
- Historico de transacoes
- Categorizacao basica de gastos
- Exportacao de extrato CSV
- Webhook mockado de confirmacao de pagamento
- Trilha minima de auditoria em memoria

## Dados sensiveis
- Saldos e historico financeiro
- Identificadores de usuario

## Integracoes externas mockadas
- Provedor de pagamento (webhook com assinatura mock)

## Trust boundaries principais
- Internet (usuarios/admin)
- Aplicacao interna
- Camada de dados (ledger/auditoria)
- Integracao externa de pagamentos

## Premissas
- Fluxo in-memory apenas para validacao
- Sem persistencia real nem criptografia real

## Fora de escopo
- UX/front-end completo
- Integracao bancaria real
- Compliance formal completo

## Execucao local
```bash
python fixtures/apps/finance/app.py
```
