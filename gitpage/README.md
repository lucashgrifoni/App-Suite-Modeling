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

## Optional: repository URLs

By default, primary links point to `https://github.com`. To wire CTAs to your real repository, create `gitpage/.env`:

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

1. Build output must be published from `gitpage/dist` (or copy `dist` to the branch GitHub Pages serves).
2. In your repository settings → **Pages** → set **Source** to **GitHub Actions** (or the branch/folder you use).
3. Add a workflow **in the main repository** (not required to live inside `gitpage/`) that:

   - Checks out the repo
   - Runs `cd gitpage && npm ci && npm run build`
   - Uploads `gitpage/dist` with `actions/upload-pages-artifact`
   - Deploys with `actions/deploy-pages`

Use the official [“Static HTML” / Node workflow templates](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) as a base and adjust paths to `gitpage`.

### Option B — `gh-pages` branch

1. Run `npm run build` inside `gitpage`.
2. Push the contents of `gitpage/dist` to the branch configured for Pages (often `gh-pages`), or use the `gh-pages` npm package to automate.

### Option C — User or org site (`username.github.io`)

If the site is served from the repo root, you can still keep the Vite project in `gitpage/` and configure CI to publish only `gitpage/dist` as the site root.

## Stack

- React 18 + TypeScript
- Vite 5
- Tailwind CSS 3
- Framer Motion
- `@react-three/fiber`, `@react-three/drei`, `three` (hero 3D)
- `lucide-react` (icons)

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
