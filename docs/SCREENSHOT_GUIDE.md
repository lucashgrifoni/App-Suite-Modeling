# Screenshot guide — App Suite Modeling (web UI)

Purpose: **consistent, low-noise** captures for README, docs, and social posts. The UI defaults to a **dark** theme; use the same theme across all shots.

**Output location:** save PNGs under `docs/screenshots/` (e.g. `home.png`, `wizard.png`). Reference them from the root `README.md` after capture.

**Resolution:** 1600×900 or 1920×1080 (16:9) is readable when scaled; avoid ultra-wide windows that add empty space.

**Data:** use **`examples/minimal.otm.yaml`** or a **built-in template** via `otm init -t …` so the model is **valid and believable**—no fake vendor names or inconsistent IDs.

---

## Global

- **Browser:** Chromium-based, 100% zoom, no extensions visible.  
- **Theme:** `data-theme="dark"` (default).  
- **Noise:** hide bookmarks bar; one tab; no devtools.  
- **API:** run `python scripts/run_dev.py` so the UI shows real validation/analysis (not mocked errors).  
- **Session:** start from **Home → Criar novo modelo** or load a template; avoid half-empty wizard mid-step unless that is the story.

---

## 1. Home (`/`)

**Goal:** Show value proposition and **three primary paths** (new model, import, templates).

**Ideal state:**

- Hero visible: eyebrow, title, short description.  
- CTAs visible: **Criar novo modelo**, **Importar artefacto**, **Explorar templates**.  
- No error banners; **Novo modelo** not required if you prefer a static shot with only the landing.

**Avoid:** Scroll position that hides CTAs; loading spinners.

---

## 2. Wizard (`/wizard`)

**Goal:** Guided modeling—**one clear step** with labels and fields.

**Ideal state:**

- At least **metadata** (title/summary) or **first structural section** filled plausibly.  
- Progress / section headings visible if the layout uses them.

**Avoid:** Empty title “Untitled” everywhere; long Lorem ipsum.

---

## 3. Analysis (`/analysis`)

**Goal:** Methodology + engine output—**metrics and at least one threat row**.

**Ideal state:**

- Methodology selector visible (e.g. STRIDE or PLOT4ai).  
- After **Gerar análise**, show **summary metrics** and a **threats** section with one row.  
- Optional: one **explanation** or insight block—only if it fits without clutter.

**Avoid:** Full-page stack traces; empty state after “run analysis”.

---

## 4. Export (`/export`)

**Goal:** Export formats + **PDF** action.

**Ideal state:**

- **Formatos** card with a few checkboxes selected (e.g. Markdown + JSON).  
- **Relatório (PDF)** card with **Gerar PDF** visible (`data-testid="export-pdf"`).  
- No giant error alert.

**Avoid:** Scrolling so PDF card is off-screen.

---

## 5. Diff (`/diff`)

**Goal:** Semantic / structural comparison—**two sides or a clear summary**.

**Ideal state:**

- Two documents or analyses loaded **or** UI showing **baseline vs revised** labels.  
- At least one **change** visible (component added, threat changed, etc.).

**Avoid:** Empty diff with no explanation; placeholder text “TODO”.

---

## Optional extras

| Route | Use when |
|-------|----------|
| `/review` | Highlight React Flow diagram with **edit mode** and 2–3 nodes |
| `/history` | At least one snapshot card with metrics + **Ver resumo do snapshot** |

---

## Open Graph asset

- `apps/web/public/og-image.svg` — default SVG card for social previews.  
- For **LinkedIn / some crawlers**, replace with **`og-image.png`** 1200×630 and update `index.html` `og:image` / `twitter:image` to `/og-image.png`.
