# Handoff — README & GitHub publication prep

## Executive summary

The repository **root `README.md`** was rewritten in **English** for GitHub: scannable sections (what/who/problem, features, flow, quick start, templates, CLI, API, methodologies, use cases, limitations, contributing, license). **`docs/PRODUCT_POSITIONING.md`** captures tagline, short and long descriptions, and differentiators for **AppSec / DevSecOps**. **`docs/SCREENSHOT_GUIDE.md`** defines ideal capture state per screen; **`docs/screenshots/`** is ready for PNGs. **`apps/web/index.html`** meta tags (including **Twitter**) and **`public/og-image.svg`** align public-facing copy with the product story. **`docs/README.md`** indexes the new docs.

## Decisions

| Topic | Rationale |
|-------|-----------|
| English README | Standard for OSS reach and portfolio use; technical clarity. |
| Portuguese UI unchanged | `lang="pt-BR"` kept; no broad i18n pass in this round. |
| `og-image.svg` vs PNG | SVG ships immediately; some social networks prefer **1200×630 PNG**—see `SCREENSHOT_GUIDE.md` + `docs/PRODUCT_POSITIONING.md`. |
| CI badge | README note to add badge after repo URL is known (avoid broken `OWNER/REPO`). |

## Strengths of the README

- Single narrative: **canonical model → analysis → exports → diff**  
- Honest **limitations** and pointer to `KNOWN_LIMITATIONS.md`  
- **Methodology table** without overclaiming maturity  
- Links to deep docs without duplicating architecture  

## Limitations

- **Screenshots** are documented as placeholders until PNGs are added under `docs/screenshots/`.  
- **Twitter/OG** image URL is absolute path `/og-image.svg`—ensure production base URL is correct when deployed.

## Next steps

1. Capture PNGs per `SCREENSHOT_GUIDE.md` and embed in README.  
2. Replace `og-image.svg` with **og-image.png** 1200×630 if needed for LinkedIn/legacy crawlers.  
3. Add GitHub **CI badge** when the repository is public.  

## Final decision

**READY** — Documentation and metadata are ready for public GitHub; build and smoke E2E verified in the same session as the validation doc update.
