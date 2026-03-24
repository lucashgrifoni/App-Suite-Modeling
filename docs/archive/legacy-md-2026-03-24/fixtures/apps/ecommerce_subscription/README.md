# App de Teste - E-commerce Assinatura

## Descricao do dominio
E-commerce simples com carrinho, checkout mockado, cupom, assinatura e entitlement de conteudo premium.

## Atores
- Cliente
- Administrador

## Funcionalidades
- Cadastro/login
- Catalogo simples
- Carrinho
- Checkout mockado
- Aplicacao de cupom
- Ativacao/cancelamento de assinatura
- Gestao de entitlement/acesso premium
- Webhook mockado de pagamento

## Dados sensiveis
- Dados de cobranca (mock)
- Estado de assinatura/entitlement
- Regras de cupom

## Integracoes externas mockadas
- Gateway de pagamento (webhook)

## Trust boundaries principais
- Internet
- Aplicacao ecommerce
- Camada de dados
- Integracao de pagamentos

## Premissas
- Entitlement premium so libera apos webhook pago
- Fluxo em memoria para validacao de comportamento

## Fora de escopo
- Pagamento real
- Antifraude completo
- Catalogo complexo

## Execucao local
```bash
python fixtures/apps/ecommerce_subscription/app.py
```
