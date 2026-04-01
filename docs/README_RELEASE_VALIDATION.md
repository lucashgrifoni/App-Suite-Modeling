# README & OSS metadata — validation

**Date:** 2026-04-01  
**Scope:** Root `README.md`, `docs/PRODUCT_POSITIONING.md`, `docs/SCREENSHOT_GUIDE.md`, `apps/web/index.html` metadata, `apps/web/public/og-image.svg`.

## Commands

| Command | Result |
|---------|--------|
| `npm run ci:build` (`apps/web`) | **OK** (typecheck + Vite build) |
| `npm run e2e:smoke` (`apps/web`) | **OK** (1 test) |

## Checks

| Check | Status |
|-------|--------|
| README renders as Markdown (headings, tables, code fences) | Manual / GitHub preview |
| Internal links point to existing files (`docs/…`, `LICENSE`, `CONTRIBUTING.md`) | Verified paths |
| `index.html` has `title`, `description`, `og:*`, `twitter:*` | Updated |
| `og-image.svg` exists under `apps/web/public/` | Added |
| Screenshots: placeholders documented; PNGs optional | `SCREENSHOT_GUIDE.md` + `docs/screenshots/.gitkeep` |
| UI language: in-app copy remains **pt-BR**; public README/meta **EN** | Per `PRODUCT_POSITIONING.md` |

## Criteria

- Build and smoke E2E must pass after `index.html` changes (no functional JS change).

## Decision

Record outcome in `docs/README_RELEASE_HANDOFF.md`.
