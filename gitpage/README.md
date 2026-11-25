# App Suite Modeling — GitHub Page

Premium marketing landing for **App Suite Modeling**, built with React, TypeScript, Vite, Tailwind CSS, and Framer Motion. All assets and code are **self-contained in this folder** for easy GitHub Pages deployment.

## Prerequisites

- Node.js 18+ (recommended: current LTS)
- npm (bundled with Node)

## Install

```bash
cd gitpage
npm install
```

Scripts call local binaries via `node ./node_modules/...` so `dev`, `build`, and `preview` work reliably even when global `vite` / `npx` shims are misconfigured on Windows.

## Local development

```bash
npm run dev
```

Open the URL shown in the terminal (typically `http://localhost:5173`).

## Production build

```bash
npm run build
```

Output is written to `gitpage/dist/`.

## Preview the production build locally

```bash
npm run preview
```

## Repository URLs (required for a fork)

By default, every primary link points to this project's own repository,
`https://github.com/lucashgrifoni/App-Suite-Modeling` — see `src/config/site.ts`, which explains why
the fallback is a real repository and not a neutral placeholder. The GitHub Pages workflow never
sets `VITE_REPO_URL`, so that default always applies.

A fork that skips this step publishes a page whose every call to action — "View on GitHub",
"Documentation", "Explore the repository", "Contribute", the footer link, and the derived docs and
issues URLs — sends visitors to someone else's project. To point them at your repository, create
`gitpage/.env`:

```bash
cp .env.example .env
```

Set:

```env
VITE_REPO_URL=https://github.com/your-org/your-repo
```

Rebuild after changing environment variables.

## Deploy to GitHub Pages

`vite.config.ts` uses `base: './'` so **relative asset URLs** work on both user sites (`username.github.io`) and **project sites** (`username.github.io/repo-name/`).

### Option A — GitHub Actions (recommended)

The repository includes **`.github/workflows/deploy-github-pages.yml`**, which:

- runs on **every push** to `main` or `master`, and on **Run workflow** (manual) in the Actions tab;
- runs `npm ci` and `npm run build` inside `gitpage/`;
- publishes `gitpage/dist` to GitHub Pages.

**One-time setup in GitHub**

1. **Settings → Pages → Build and deployment**: **Source** = **GitHub Actions** (as in your screenshot).
2. Commit and push the workflow file (repo root `.github/workflows/`, not inside `gitpage/` — GitHub only loads workflows from there).
3. Open **Actions** → **Deploy GitHub Pages (gitpage)** → confirm the latest run is **green** (both **build** and **deploy** jobs). The site URL appears on the run summary and under Pages (for a project repo, e.g. `https://lucashgrifoni.github.io/App-Suite-Modeling/` — use the exact name of your repository in the path).

If GitHub asks to approve the **`github-pages` environment** on first deploy, approve it once in **Settings → Environments**.

### If you see “404 — There isn’t a GitHub Pages site here”

That message means **no successful deploy** has completed yet, not that the Vite `base` is wrong. Check:

1. **Actions** → **Deploy GitHub Pages (gitpage)** → open the latest run. Fix any red step (often `npm ci` / `npm run build` in `gitpage/`).
2. The workflow file must be on the **default branch** (`main` or `master`).
3. Run **Deploy GitHub Pages (gitpage)** manually: **Actions** → workflow name → **Run workflow**.
4. After a green **deploy** job, wait 1–2 minutes and hard-refresh the site (Ctrl+F5).

**Do not merge** Dependabot **major** Vite upgrades for `gitpage` until the stack is migrated (Vite 8 needs a newer `@vitejs/plugin-react`). The repo Dependabot config ignores major Vite bumps under `/gitpage` for that reason.

More templates: [GitHub Pages + Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

### Option B — `gh-pages` branch

1. Run `npm run build` inside `gitpage`.
2. Push the contents of `gitpage/dist` to the branch configured for Pages (often `gh-pages`), or use the `gh-pages` npm package to automate.

### Option C — User or org site (`username.github.io`)

If the site is served from the repo root, you can still keep the Vite project in `gitpage/` and configure CI to publish only `gitpage/dist` as the site root.

## Stack

- React 18 + TypeScript
- Vite 8
- Tailwind CSS 3
- Framer Motion
- `lucide-react` (icons)
- Hero visual: CSS + SVG + Motion (sem WebGL)

## Project structure

```
gitpage/
├── public/              # Static assets (favicon)
├── src/
│   ├── components/      # Layout, sections, effects, UI primitives
│   ├── config/          # Site URLs (env-aware)
│   ├── data/            # Marketing copy
│   ├── hooks/
│   ├── lib/
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── tailwind.config.js
├── vite.config.ts
└── README.md
```

## License

Follow the license of the parent **App Suite Modeling** repository.
