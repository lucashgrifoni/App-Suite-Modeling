# Cabeçalhos de segurança e CSP — frontend (`apps/web`)

## O que o repositório fornece

| Mecanismo | Finalidade |
|-----------|------------|
| `apps/web/public/_headers` | Netlify, Cloudflare Pages e hosts que copiam este ficheiro para a raiz do artefacto: **CSP**, **X-Frame-Options**, **COOP**, **Permissions-Policy**, etc. |
| `apps/web/public/theme-init.js` | Tema antes do React **sem** `<script>` inline → `script-src 'self'` na CSP. |
| `vite.config.ts` → `server.headers` | Dev (`npm run dev`): headers endurecidos **sem** CSP (evita quebrar HMR/WebSocket). |
| `vite.config.ts` → `preview.headers` | `npm run preview`: mesma CSP que `_headers` para validação local pós-build. |

## Ajustar `connect-src` (API noutro domínio)

O cliente usa `VITE_API_PREFIX` (defeito `/api`). Com **mesmo host** e reverse proxy, `connect-src 'self'` basta.

Se o browser chamar **outro origin** (ex.: `https://api.exemplo.com`), actualize **em simultâneo**:

1. `apps/web/public/_headers` — directiva `connect-src` com esse origin.  
2. `apps/web/vite.config.ts` — string `Content-Security-Policy` em `PREVIEW_SECURITY_HEADERS`.

Exemplo (ilustrativo):

```http
connect-src 'self' https://api.exemplo.com
```

## Produção com Nginx

```nginx
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'" always;
```

Em HTTPS público pode acrescentar `upgrade-insecure-requests` à CSP se não houver clientes HTTP legítimos.

## Report-Only (testes)

Para ensaiar uma CSP mais estrita sem quebrar o site, usar `Content-Security-Policy-Report-Only` com o mesmo valor e monitorizar relatórios (`report-to` / `report-uri` conforme a infra).

## Referências

- [MDN — CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)  
- [OWASP — Secure Headers](https://owasp.org/www-project-secure-headers/)
