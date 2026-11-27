# OTM Design System

**Version:** 1.1.0 · **Derived from:** App Suite Modeling `v7.10.1`
**Source of truth:** `apps/web/src/index.css` (CSS custom properties), `apps/web/tailwind.config.js` (Tailwind bindings), `apps/web/src/design-system/tokens.ts` (TS mirror)
**Accessibility floor:** WCAG 2.2 level AA
**Status:** tokens and primitives documented from shipped code; contrast ratios computed, not asserted. The seven AA failures found in the 1.0.0 audit are **resolved** — see [§9](#9-accessibility-audit--resolved). Verification re-parses `index.css` and checks 80 token pairs; current result is 0 failures.

This document is self-contained. It can be handed to a design tool or another agent as the complete visual contract for the product.

---

## 1. Brand foundation

The product palette is a five-stop mint/emerald ramp on a near-black green ground. It is the official palette, reproduced in `Paleta_Cores_App_Modeling.webp` and declared in the header comment of `apps/web/src/index.css`.

| Stop | Hex | Token | Role |
|---|---|---|---|
| Mint 300 | `#7DFABE` | `--otm-mint-300` | Lightest tint; borders, shine gradient |
| Accent | `#56FF95` | `--otm-accent` | Neon highlight, focus ring, success |
| Mint 400 | `#6AE899` | `--otm-mint-400` | Hover borders, secondary emphasis |
| Mint 500 | `#76DB9B` | `--otm-mint-500` | Muted brand tint |
| Primary | `#30B27F` | `--otm-primary` | Core brand action colour |

**Character:** technical, dark-first, high-contrast. The neon accent carries the "as code" positioning; the desaturated deep-green surfaces keep long analysis sessions readable. Green is used for *brand*, not only for *success* — status semantics are carried by a separate scale (§3.4) so a green product chrome never reads as "everything is fine".

### 1.1 Typography

| Role | Family | Fallback stack | Where |
|---|---|---|---|
| Body / UI | **DM Sans** | `system-ui, sans-serif` | `font-sans` (default) |
| Display / headings | **Outfit** | `"DM Sans", system-ui, sans-serif` | `font-display` |

Loaded from Google Fonts in `apps/web/index.html`: DM Sans 400/500/600/700 + italic 400, Outfit 400/500/600/700.

---

## 2. Theming model

Two themes, switched by `data-theme` on `<html>` (`ThemeContext`, bootstrapped by `public/theme-init.js` before paint to avoid a flash).

- `:root` and `[data-theme="dark"]` — **dark is the default and the designed-for theme.**
- `[data-theme="light"]` — override block; only redefines what must change.
- Tailwind `dark:` variants are bound to the selector `[data-theme="dark"]`, so `dark:` and the CSS variables never disagree.

**Rule:** a colour must never have its only definition inside the light block. Define the full set on `:root`/dark, override the delta in light.

---

## 3. Colour tokens

Raw brand values (§1) are **not** used directly in components. Components consume semantic tokens only.

### 3.1 Neutral ramp (dark ground)

| Token | Hex |
|---|---|
| `--otm-green-950` | `#050807` |
| `--otm-green-900` | `#0a100d` |
| `--otm-green-850` | `#0e1512` |
| `--otm-green-800` | `#121a17` |
| `--otm-green-750` | `#16201c` |
| `--otm-green-700` | `#1a2621` |
| `--otm-green-650` | `#1f2d27` |

### 3.2 Surfaces

| Token | Dark | Light | Use |
|---|---|---|---|
| `--otm-surface-base` | `#0a100d` | `#f4f7f5` | Page ground |
| `--otm-surface-1` | `#0e1512` | `#ffffff` | Inputs, insets |
| `--otm-surface-2` | `#121a17` | `#f8faf9` | Cards, panels |
| `--otm-surface-3` | `#16201c` | `#eef4f1` | Nested / hover surfaces |
| `--otm-surface-glass` | `rgba(22,32,28,.72)` | `rgba(255,255,255,.85)` | Glass over gradients (+16px blur) |

Elevation is expressed by **surface step + shadow**, never by surface step alone.

### 3.3 Foreground

| Token | Dark | Light | Use |
|---|---|---|---|
| `--otm-text` | `#e8f5ef` | `#0b1220` | Primary copy |
| `--otm-text-muted` | `#93b0a3` | `#475569` | Secondary copy, labels |
| `--otm-text-subtle` | `#789684` | `#5a6a7d` | Placeholders, metadata |

### 3.4 Status

| Token | Dark | Light |
|---|---|---|
| `--otm-success` | `#56ff95` | `#047857` |
| `--otm-warning` | `#fbbf24` | `#b45309` |
| `--otm-danger` | `#f87171` | `#b91c1c` |
| `--otm-info` | `#38bdf8` | `#0369a1` |

Each has a `-subtle` companion at 10–12% alpha for tinted backgrounds.

> **These four tokens currently have no consumer.** Every status surface in the app (Badge, StatusPill, Alert) hard-codes raw Tailwind palette colours instead. The tokens define the contract and are AA-correct in both themes; migrating the components onto them is open work — see §9.

### 3.5 Interactive / brand-as-action

| Token | Dark | Light |
|---|---|---|
| `--otm-primary` | `#30b27f` | inherited |
| `--otm-primary-hover` | `#3dd492` | inherited |
| `--otm-primary-active` | `#269466` | inherited |
| `--otm-primary-subtle` | `rgba(48,178,127,.14)` | `rgba(48,178,127,.12)` |
| `--otm-primary-muted` | `rgba(48,178,127,.08)` | `rgba(48,178,127,.06)` |
| `--otm-accent` | `#56ff95` | `#0f766e` |
| `--otm-primary-ink` | `#30b27f` | `#0f766e` |

`--otm-primary` is a **fill** colour — dark ink sits on it, and it is what the primary button gradient is made of. It is *not* safe as a foreground on light surfaces (2.69:1). Whenever the brand colour must be the foreground — an icon, a chart stroke, a meaningful border — use **`--otm-primary-ink`**, which resolves to `--otm-primary` in dark (6.20:1 worst case) and to `#0f766e` in light (4.91:1 worst case).

### 3.6 Lines and focus

| Token | Dark | Light | Bar |
|---|---|---|---|
| `--otm-border` | `rgba(125,250,190,.10)` | `rgba(15,60,40,.12)` | decorative |
| `--otm-border-strong` | `rgba(125,250,190,.18)` | `rgba(15,60,40,.20)` | decorative |
| `--otm-border-control` | `rgba(125,250,190,.40)` | `rgba(15,60,40,.60)` | **≥3:1** (1.4.11) |
| `--otm-ring` | `rgba(86,255,149,.45)` | `#0f766e` | **≥3:1** (1.4.11 / 2.4.11) |

`--otm-border` and `--otm-border-strong` are decorative separators and deliberately sit below 3:1 — they must never be the only thing that identifies a control. Form-control boundaries use `--otm-border-control`.

### 3.7 Gradients and glow

- `--otm-gradient-hero` — two radial washes over a vertical `green-900 → green-950` base. The page background.
- `--otm-gradient-accent` — `135deg, primary → accent`. Primary button fill and `.otm-text-gradient`.
- `--otm-gradient-shine` — 105° sweep used for shimmer/skeleton.
- `--otm-glow` — `0 0 24px rgba(86,255,149,.12)`.

### 3.8 Legacy bridge

`--asm-*` aliases map onto `--otm-*` for pre-v7 components. **Deprecated.** Do not use in new work; see §10.

---

## 4. Scales

### 4.1 Spacing

Tailwind default 4px rhythm, plus two extensions: `18` = `4.5rem`, `22` = `5.5rem`.

Applied rhythm: card padding `p-5` → `md:p-6`; card header margin `mb-4`; title→subtitle gap `mt-1`.

### 4.2 Radius

| Token | Value | Tailwind | Use |
|---|---|---|---|
| `--otm-radius-sm` | `0.5rem` | `rounded-otm-sm` | Badges, small chips |
| `--otm-radius-md` | `0.75rem` | `rounded-otm-md` | Buttons, inputs, alerts, surfaces |
| `--otm-radius-lg` | `1rem` | `rounded-otm` | Default container |
| `--otm-radius-xl` | `1.25rem` | `rounded-otm-xl` | Cards |

Pills use `rounded-full` (StatusPill only).

### 4.3 Elevation

| Token | Value |
|---|---|
| `--otm-shadow-sm` | `0 1px 2px rgba(0,0,0,.35)` |
| `--otm-shadow-md` | `0 8px 24px rgba(0,0,0,.45)` + 1px border ring |
| `--otm-shadow-lg` | `0 24px 48px rgba(0,0,0,.55)` + 1px strong border ring |
| `--otm-shadow-glow` | `0 0 0 1px rgba(125,250,190,.15), 0 12px 40px rgba(48,178,127,.15)` |

Light theme softens `md`/`lg` to slate-tinted shadows at 8–10% alpha.

### 4.4 Motion

| Token | Value |
|---|---|
| `motion.durationFast` | `150ms` |
| `motion.duration` | `220ms` (Tailwind `duration-otm`) |
| `motion.durationSlow` | `320ms` (`duration-otm-slow`) |
| `motion.easing` | `cubic-bezier(0.22, 1, 0.36, 1)` (`ease-otm`) |
| `motion.easingOut` | `cubic-bezier(0.16, 1, 0.3, 1)` (`ease-otm-out`) |

Named animations: `page-enter` (450ms, fade + 8px rise), `shimmer` (1.2s loop), `pulse-soft` (2s loop), `glow` (4s loop).

**Reduced motion is a hard requirement.** A global `@media (prefers-reduced-motion: reduce)` clamps all animation and transition durations to `0.01ms`; hover transforms on `.otm-card-lift` and `.otm-tilt-hover` collapse to `none`. Any new motion must degrade the same way.

### 4.5 Z-index

Canonical scale (`tokens.ts`): `base 0` · `dropdown 40` · `sticky 50` · `modal 100` · `toast 200`.

> ⚠️ **Drift:** `tailwind.config.js` also extends `z-60` and `z-70`, which sit between `sticky` and `modal` and are not in the token scale. Reconcile before adding new layers.

---

## 5. Primitives

Every primitive below exists in `apps/web/src/components/`. States marked *missing* are genuinely absent from the shipped code.

### 5.1 Button — `ui/Button.tsx`

Base: `inline-flex`, `rounded-otm-md`, `px-4 py-2`, `text-sm font-semibold`, `transition duration-otm ease-otm`. Defaults to `type="button"` so it cannot silently submit a surrounding form.

| Variant | Default | Hover | Active | Disabled |
|---|---|---|---|---|
| `primary` | `gradient-accent` fill, `green-950` ink, `shadow-otm-sm` | `brightness-110` | `scale-.98` + `brightness-95` | `opacity-50`, no scale |
| `secondary` | `border-strong` + `surface-2` | `border mint-400/40` + `surface-3` | `scale-.99` | `opacity-50` |
| `ghost` | `text-muted`, transparent | `primary-muted` bg + `text` | `scale-.99` | `opacity-50` |
| `danger` | `red-600/90`, white ink | `red-600` | `scale-.98` | `opacity-50` |

**Focus (all variants):** `ring-2` in `--otm-ring` with `ring-offset-2` against `--otm-surface-base`, and `focus-visible:outline-none`. Focus is ring-based, not outline-based, so it survives the gradient fill.

**Reduced motion:** `motion-reduce:transition-none`, `motion-reduce:active:scale-100`.

**Missing states:** no `loading` (no spinner, no `aria-busy`), no `size` axis, no icon-only affordance with an accessible name contract.

### 5.2 Input — `ui/Input.tsx`

`w-full`, `rounded-otm-md`, `border-otm-border-control`, `bg-otm-surface-1`, `px-3 py-2 text-sm`, placeholder in `--otm-text-subtle`.

| State | Treatment |
|---|---|
| Resting | `border-otm-border-control` — 3.19:1 worst case, clears WCAG 1.4.11 |
| Focus | `border mint-400/50` + `ring-2` in `--otm-ring`, `outline-none` |
| Disabled | `cursor-not-allowed`, `opacity-60` |
| Error | `invalid` prop → `aria-invalid`, `--otm-danger` border and focus ring |

The error **message** is the caller's: pass `aria-describedby` pointing at it so the field satisfies WCAG 3.3.1. The same `--otm-border-control` boundary applies to `Select`, `Checkbox`, `FileDropZone`, and the Diff page textarea.

### 5.3 Card — `ui/Card.tsx`

`rounded-otm-xl`, `p-5 md:p-6`. Optional `title` (`font-display text-lg font-semibold`) + `subtitle` (`text-sm text-otm-text-muted`) in a `<header>`. Renders as `<section>`.

| Variant | Treatment |
|---|---|
| `default` | `border-otm-border`, `surface-2/90`, `shadow-otm-sm` |
| `glass` | `.otm-glass` (blur 16px), `shadow-otm-md` |
| `elevated` | `border-strong`, `surface-2`, `shadow-otm-lg`, 3D lift on hover |

`.otm-card-lift` raises 2px and tilts 2°. **Cards containing interactive controls must add `.otm-card-stable-hover`** — otherwise the element moves under the cursor and the browser fires `mouseenter`/`mouseleave` in a loop, making clicks fail.

### 5.4 Surface — `patterns/Surface.tsx`

`flat` (transparent) · `inset` (`border/60`, `surface-1/50`, inner shadow) · `raised` (`border`, `surface-2`, `shadow-otm-sm`). `rounded-otm-md`.

### 5.5 Badge — `ui/Badge.tsx`

Non-interactive. `rounded-md px-2 py-0.5 text-xs font-medium`. Tones: `neutral` · `warn` · `ok` · `accent`. Warn/ok/accent carry explicit light *and* dark text values (e.g. `text-amber-950 dark:text-amber-100`) so the tint inverts correctly.

### 5.6 StatusPill — `ui/StatusPill.tsx`

Non-interactive. `rounded-full border px-2.5 py-0.5 text-xs font-medium`. Tones: `neutral` · `success` · `warning` · `danger` · `info`.

Each coloured tone carries paired ink, matching Badge: `-950` text on a 12% tint for light (11.2–12.5:1), `dark:` `-200` text on a 10% tint for dark (11.2–12.1:1). Borders are decorative — the pill is a `<span>`, and its meaning is carried by the label, so the 3:1 bar does not apply to them.

### 5.7 Alert — `ui/Alert.tsx`

`role="alert"`, `rounded-otm-md border px-4 py-3 text-sm leading-relaxed`. Variants `error` (default) · `info` · `warning` · `success`, each with paired light/dark text.

### 5.8 Colour is never the only signal

Status is conveyed by tint **plus** text label in every primitive above (WCAG 1.4.1). New status surfaces must keep a text or icon carrier.

---

## 6. Density and layout

- Single density. Control height is `py-2 + text-sm` ≈ **36px**; inputs match.
- Card padding steps once at `md` (`p-5` → `p-6`); no other density breakpoints exist.
- Target size: 36px clears **WCAG 2.2 AA (2.5.8, 24×24)** but not AAA (2.5.5, 44×44). Primary and destructive actions on touch surfaces should be raised to 44px.
- Reflow to 320px (WCAG 1.4.10) is **not verified** — see §9.

---

## 7. Verified contrast — dark theme

Computed with the WCAG 2.x relative-luminance formula. Translucent tints are composited over their real backing surface before measuring.

| Pair | Ratio | AA |
|---|---|---|
| `--otm-text` on surface base→3 | 17.15 → 14.90 | ✅ |
| `--otm-text-muted` on surface base→3 | 8.22 → 7.14 | ✅ |
| `--otm-text-subtle` on surface base→3 | 5.94 → 5.16 | ✅ |
| `--otm-primary` as text on surface-2 | 6.58 | ✅ |
| `--otm-primary-active` as text on surface-2 | 4.65 | ✅ (tight) |
| `--otm-accent` as text on surface-2 | 13.61 | ✅ |
| `--otm-warning` / `--otm-danger` / `--otm-info` on surface-2 | 10.61 / 6.40 / 8.27 | ✅ |
| Button `primary` ink on gradient start → end | 7.47 → 15.45 | ✅ |
| Button `danger` white ink on `red-600` | 4.83 | ✅ (tight) |
| StatusPill success / warning / danger / info | 11.87 / 12.08 / 11.23 / 11.59 | ✅ |
| Focus ring composited on surface-base *(needs 3:1)* | 3.74 | ✅ |

The dark theme has **no AA failures**. It is the reference theme.

---

## 8. Verified contrast — light theme

| Pair | Ratio | AA |
|---|---|---|
| `--otm-text` on surface base→3 | 17.36 → 16.80 | ✅ |
| `--otm-text-muted` on surface base→3 | 7.03 → 6.80 | ✅ |
| `--otm-accent` `#0f766e` on white / base | 5.47 / 5.07 | ✅ |
| `--otm-success` `#047857` on white | 5.48 | ✅ |
| `--otm-text-subtle` `#5a6a7d` on surface base→3 | 5.13 → 4.97 | ✅ |
| `--otm-primary-ink` `#0f766e` on surface base→3 | 5.07 → 4.91 | ✅ |
| `--otm-warning` `#b45309` on surface base→3 | 4.66 → 4.51 | ✅ |
| `--otm-danger` `#b91c1c` on surface base→3 | 6.00 → 5.81 | ✅ |
| `--otm-info` `#0369a1` on surface base→3 | 5.49 → 5.32 | ✅ |
| Focus ring `#0f766e` *(needs 3:1)* | 5.07 → 4.91 | ✅ |
| Control boundary at 60% *(needs 3:1)* | 3.62 → 3.58 | ✅ |

---

## 9. Accessibility audit — resolved

The 1.0.0 audit found seven AA failures. All seven are fixed. Verification re-parses `index.css`, resolves `var()` indirection, composites every translucent token over its real backing surface, and checks **80 token pairs across both themes**. Current result: **0 failures**.

| # | Was | Measured → now | Fix |
|---|---|---|---|
| 1 | Light focus ring effectively invisible (1.4.11 / 2.4.11) | 1.55 → **4.91** | `--otm-ring: #0f766e` in light |
| 2 | `warning` / `danger` / `info` inherited dark neons onto white | 1.67 / 2.77 / 2.14 → **4.51 / 5.81 / 5.32** | Light overrides `#b45309` / `#b91c1c` / `#0369a1` |
| 3 | Control boundary below the 3:1 identification bar (1.4.11) | 1.27 → **3.19** | New `--otm-border-control`; applied to Input, Select, Checkbox, FileDropZone, Diff textarea |
| 4 | `--otm-primary` unusable as a light foreground | 2.69 → **4.91** | New `--otm-primary-ink`; `--otm-primary` stays fill-only |
| 5 | `--otm-text-subtle` failed on two light surfaces | 4.27 → **4.97** | `#5a6a7d`, hierarchy under `--otm-text-muted` preserved |
| 6 | StatusPill had no light ink pairing | — → **11.2–12.5** | `-950` light / `dark:` `-200`, mirroring Badge |
| 7 | Input had no error state (3.3.1) | — | `invalid` prop → `aria-invalid` + danger border and ring |

Fixes 1, 2, 5 are **patch** (values inside the existing contract). Fixes 3, 4 are **minor** (new tokens). Fixes 6, 7 are **minor** (new component behaviour). No consumer edits are required by 1, 2, 5.

### 9.1 Open work

- **Status tokens have no consumer.** Badge, StatusPill and Alert hard-code raw Tailwind colours, so fix #2 corrects the token contract without changing a single pixel today. Migrating those three components onto `--otm-{success,warning,danger,info}` is the follow-up that makes the fix load-bearing.
- **`--otm-{success,warning,danger,info}-subtle`** are declared and unused.
- **`--asm-*` legacy bridge is fully dead** — no consumer in `src/`. It can be removed at the next major rather than waiting out a deprecation window.
- **Z-index drift** between `tokens.ts` and the Tailwind `z-60`/`z-70` extension (§4.5).

### 9.2 Not verified, not claimed

Reflow at 320px (1.4.10), full keyboard traversal order, and screen-reader labelling of icon-only controls were **not** tested. The 0-failure result covers computed colour contrast only.

---

## 10. Governance

### 10.1 Change classification

| Class | Definition | Examples |
|---|---|---|
| **Patch** | Value change inside the declared contract; no consumer edits | Contrast fix that keeps the token name and role |
| **Minor** | Additive | New token, new variant, new primitive |
| **Breaking** | Rename, removal, or role change | Dropping `--asm-*`, making `--otm-primary` fill-only |

All seven fixes in §9 are **patch** except #3 and #4, which add tokens (**minor**).

### 10.2 Deprecation

`--asm-*` (bridge for pre-v7 components) is deprecated. Policy: **warn for one minor, remove in the next major.** Never rename a token silently — ship both names for the full deprecation window.

The bridge currently has **no consumer anywhere in `src/`**, so the window has already been served in practice; it can be dropped at the next major with no migration burden.

### 10.3 Contribution checklist

A new component is not done until:

1. It consumes semantic tokens only — no raw hex, no raw brand ramp.
2. Every variant × state is named, including **focus** and **error**.
3. Contrast is computed against the real backing surface in both themes.
4. Any motion has a `prefers-reduced-motion` fallback.
5. Interactive targets are ≥ 24×24 CSS px (44 on primary/destructive touch actions).
6. Status is carried by text or icon, not colour alone.
7. If it renders secrets, tokens, or uploaded model content, §10.4 applies.

### 10.4 Security-sensitive components

`FileDropZone` (model upload) and the export surfaces handle user-supplied threat-model content. Data-handling contract: **do not log or persist the payload beyond the component lifecycle, and do not echo untrusted content into markup without sanitization.** `utils/diagramSanitize.ts` is the existing sanitizer for diagram content — new render paths for untrusted model data must route through it or an equivalent, and must not reintroduce raw HTML injection into node labels.

---

## 11. Open divergence: the landing page runs a different palette

`gitpage/` (the GitHub Pages site) does **not** use this design system. It defines its own palette in `gitpage/tailwind.config.js` and `gitpage/src/index.css`:

| Token | Hex | Role |
|---|---|---|
| `--color-midnight` | `#0c124c` | Ground (deep indigo, **not** the product's green-black) |
| `--color-mist` | `#d5d8dd` | Body text |
| `--color-mint` | `#08b98b` | Accent (**not** `#30B27F`) |
| `--color-slate` | `#5a6876` | Muted |
| `--color-steel` | `#7c8394` | Muted |
| `--semantic-surface-deep` | `#0a0e38` | Elevated ground |
| font | Inter | vs. DM Sans + Outfit in the product |

Verified contrast on `midnight`: mist **12.18** ✅ · mint **6.90** ✅ · steel **4.58** ✅ · slate **3.05** ❌ (fails AA as text; passes the 3:1 non-text bar).

**Two consequences.** First, an accessibility one: `--color-slate` must be restricted to non-text decorative use, or raised to `#8b95a5` (**5.75:1**). Second, a brand one: a visitor moving from the landing page to the app crosses an indigo→green ground shift and an Inter→DM Sans shift. That is a brand-coherence decision, not a bug — it belongs to `brand`, not to this document. This design system records the divergence and takes no position on which side should move.

A stale `gitpage/ds-bundle/` from a June design-sync run is present with an **empty `tokens/` directory** and a `_ds_needs_recompile` marker. It is not a source of truth and should not be read as one.

---

## 12. Machine-readable token export

Paste-ready for a design tool. Dark theme is the reference; light overrides follow. This mirrors the current `apps/web/src/index.css` — not a target state.

```json
{
  "$meta": { "name": "OTM Design System", "version": "1.1.0", "theme": "dark", "a11y": "WCAG 2.2 AA" },
  "brand": {
    "primary": "#30B27F", "accent": "#56FF95", "primaryInk": "#30B27F",
    "mint300": "#7DFABE", "mint400": "#6AE899", "mint500": "#76DB9B"
  },
  "surface": {
    "base": "#0a100d", "s1": "#0e1512", "s2": "#121a17", "s3": "#16201c",
    "glass": "rgba(22,32,28,0.72)"
  },
  "text": { "default": "#e8f5ef", "muted": "#93b0a3", "subtle": "#789684" },
  "status": { "success": "#56ff95", "warning": "#fbbf24", "danger": "#f87171", "info": "#38bdf8" },
  "line": {
    "border": "rgba(125,250,190,0.10)",
    "borderStrong": "rgba(125,250,190,0.18)",
    "borderControl": "rgba(125,250,190,0.40)",
    "ring": "rgba(86,255,149,0.45)"
  },
  "radius": { "sm": "0.5rem", "md": "0.75rem", "lg": "1rem", "xl": "1.25rem" },
  "shadow": {
    "sm": "0 1px 2px rgba(0,0,0,0.35)",
    "md": "0 8px 24px rgba(0,0,0,0.45)",
    "lg": "0 24px 48px rgba(0,0,0,0.55)",
    "glow": "0 0 0 1px rgba(125,250,190,0.15), 0 12px 40px rgba(48,178,127,0.15)"
  },
  "motion": {
    "fast": "150ms", "base": "220ms", "slow": "320ms",
    "easing": "cubic-bezier(0.22,1,0.36,1)", "easingOut": "cubic-bezier(0.16,1,0.3,1)"
  },
  "type": { "body": "DM Sans", "display": "Outfit" },
  "z": { "base": 0, "dropdown": 40, "sticky": 50, "modal": 100, "toast": 200 },
  "lightOverrides": {
    "surface": { "base": "#f4f7f5", "s1": "#ffffff", "s2": "#f8faf9", "s3": "#eef4f1" },
    "text": { "default": "#0b1220", "muted": "#475569", "subtle": "#5a6a7d" },
    "status": { "success": "#047857", "warning": "#b45309", "danger": "#b91c1c", "info": "#0369a1" },
    "accent": "#0f766e",
    "primaryInk": "#0f766e",
    "ring": "#0f766e"
  }
}
```
