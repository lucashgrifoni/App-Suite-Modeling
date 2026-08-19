# Exemplo — API de pedidos

Serviço REST com fila e banco.

**Responsável:** equipe-plataforma

- **Schema:** 1.1.0
- **Tipo de sistema:** web_application
- **Setor:** saas

## Ativos

- **Registos de pedidos** (`orders_data`) — order_record
- **Contexto de sessão utilizador** (`session_ctx`) — session

## Componentes

- **Usuário** (`user`) — user, fronteira `internet`
- **API** (`api`) — process — REST, fronteira `vpc`
- **Worker** (`worker`) — process, fronteira `vpc`
- **Pedidos** (`db`) — datastore — PostgreSQL, fronteira `vpc`

## Fluxos de dados

- **HTTPS** (`http_in`): `user` → `api`
- **to_worker** (`to_worker`): `api` → `worker`
- **to_db** (`to_db`): `worker` → `db`

## Fronteiras de confiança

- **Internet** (`internet`)
- **Conta cloud / VPC** (`vpc`)
