# Final evidence

Every figure below came from a command run against the commit named next to it.
Where something was not run, this file says so.

- Date: 2026-11-17
- Branch: `main`, in sync with `origin/main`
- Verified commit: `60e0b67` (full: `60e0b673ffeb2b23fcc49358863e52888a9e4c63`)
- Deployed API build: `60e0b67` — the live `commit` field equals this SHA exactly
- The commit that adds *this file* is documentation-only: no code, CSS, test or
  config change, so it reproduces every result below.

`docs/RELEASE-EVIDENCE.md` describes an older `release/sentinelai-v1.1` branch and
is **superseded by this file** for current `main`.

---

## 1. Commit chain for this pass

```
$ git log --oneline a20aa3f..HEAD
60e0b67 refactor(design): tokenise the legacy emerald family
accc706 docs(design): refresh golden-path screenshots
388fa27 docs: align README with verified capabilities
de77eaf fix(ui): make the report badge text visible
2a56f15 refactor(design): finish tokenising every shipped UI surface

$ git status --porcelain
(empty)
$ git rev-list --left-right --count origin/main...HEAD
0	0
```

---

## 2. Encoding: nothing to repair

An earlier hand-off reported mojibake in `README.md` and `docs/EVIDENCE-FINAL.md`.
That was checked rather than assumed, and it is **not present**:

```
scanned 46 docs md files; files with mojibake: 0      # byte scan for â€ / Ã / U+FFFD

README.md:  BOM: False   bytes: 4519   mojibake hits: none   em dashes: 11
```

All 82 tracked `*.md` files decode as UTF-8; none carries a BOM.

---

## 3. README aligned with the code

The README claimed **"Passive URL checks | Ongoing"**. There is no such feature —
`docs/LIMITATIONS.md` and the Coverage page both say the scanner never sends
traffic to a target. That row is gone, and the unsupported work is now an explicit
"what it does not do" list linking `docs/LIMITATIONS.md`.

Counts were re-derived from the registries, not copied:

```
$ python -c "from app.core.sast_engine import rules as r; print(len(r.ALL_RULES))"
PYTHON_RULES 23
JAVASCRIPT_RULES 14
JAVA_RULES 11
ALL_RULES 48

$ grep -n "API1\|API10" app/core/security_engine/scanner.py
scanner.py:6:    "API1": "Broken Object Level Authorization",
scanner.py:15:    "API10": "Unsafe Consumption of APIs",
```

So "48 rules" and "API1–API10" are true as written. The dependency row now says the
scanner reads a manifest and queries OSV.dev, instead of claiming it
"cross-references installed packages".

---

## 4. Design system — finished across every shipped surface

### 4.1 Source

```
$ grep -RInoE '#00ffaa|#00d4ff|#aa66ff' src --include=*.css --include=*.jsx --include=*.js | wc -l
0
$ grep -RInoE '#00ff88|#ff2244|#ff3355|#ff6622|#ffaa00' src --include=*.css --include=*.jsx --include=*.js | wc -l
0
$ grep -RInoE '#10b981|#059669|#009966|#003322|#002218|#004433' src --include=*.css --include=*.jsx --include=*.js | wc -l
0
```

Work done, in two sweeps:

```
# alpha-form neon tints and hot severity hexes
replacements: {'rgba->--severity-critical': 32, 'rgba->--severity-high': 7,
 'hex->--severity-critical': 10, 'hex->--severity-low': 9,
 'rgba->--severity-medium': 12, 'hex->--severity-medium': 8, 'hex->--severity-high': 2}
color-mix calls: 162

# legacy emerald family (last off-palette hue still rendering)
replacements: {'rgba->--volt-500': 39, 'hex->--volt-500': 31, 'hex->--fig-900': 25,
 'hex->--fig-700': 7, 'hex->--severity-low': 8, 'rgba->--fig-700': 9} total: 119
```

Charts are token-driven: `--chart-1`…`--chart-6` (plus `--chart-grid`,
`--chart-axis`, `--chart-tick`) live in `frontend/src/styles/tokens.css` with
dark-mode values, and `Charts.jsx` resolves them through `getComputedStyle`
because an SVG presentation attribute cannot resolve `var()`.

`frontend/src/App.css` was deleted: 978 lines, **0** brand-neon hits, **0**
importers.

### 4.2 Build

```
$ npm run test
 Test Files  6 passed (6)
      Tests  35 passed (35)
   Duration  32.33s

$ npm run build
dist/assets/Charts-Cb0-ryrQ.js   409.81 kB │ gzip: 118.14 kB
✓ built in 30.50s
BUILD_EXIT=0
```

### 4.3 Built output

```
$ grep -ohE '#00ffaa|#00d4ff|#aa66ff' dist/assets/*.css dist/assets/*.js | wc -l
0
$ grep -ohE '#00ffaa|#00d4ff|#aa66ff|#10b981|#009966|#003322' dist/assets/*.css dist/assets/*.js | wc -l
0
$ grep -oh 'color-mix(in srgb' dist/assets/*.css | wc -l
228
```

### 4.4 Deployed CSS — every stylesheet, every route

Collected by loading 26 routes in Chrome and reading every `link[rel=stylesheet]`:

```
deployed stylesheets: 15 | neon+legacy hex: 0 | hits: none
color-mix across all deployed CSS: 200
main css: index-C-nZdB15.css
```

And at runtime, no legacy hue is actually painted anywhere:

```
RENDERED legacy-emerald uses across 26 routes: 0
```

This covers the whole deployed CSS surface, not just the main bundle. The earlier
"legacy page chunks are out of scope" caveat is no longer true and has been removed
from this document.

---

## 5. The grey artifact over the logo strip — found, explained, fixed

It was ours, and it was not an overlay. `.report-header-badge` set
`color: var(--fig-500)` — a raw palette value instead of a role token — while its
background is `var(--bg-surface-alt)`; in dark mode `--bg-surface-alt` **is**
`--fig-500`. Text was therefore painted in its own background and the badge
rendered as an empty grey pill directly under the logo.

Identity from the live DOM:

```
outerHTML: <div class="report-header-badge"><svg …lucide-file-text…></svg> REPORT CENTER</div>
text: " REPORT CENTER"    innerTextLen: 13
rect: { x: 0, y: 64, w: 141.5, h: 26 }
color: rgb(74, 58, 99)   background: rgb(74, 58, 99)   ratio: 1.00
```

A contrast sweep of 11 authenticated pages at 1440x900 found exactly one such node:

```
{"path":"/reports","text":"REPORT CENTER","cls":"report-header-badge","ratio":1}
DISTINCT invisible text: 1
```

Fix (`de77eaf`): the text uses the `--text-secondary` role and the border
`--border-subtle`, as the Coverage badge already did. Layout, markup and copy
untouched. After the deploy:

```
badge={"text":"REPORT CENTER","color":"rgb(201, 197, 255)","bg":"rgb(74, 58, 99)","ratio":6.22}
FIX_LIVE

$ same contrast sweep over the same 11 pages, after the fix
DISTINCT invisible text: 0
```

Crops of exactly that strip (300x48):

| Before | After |
|---|---|
| `docs/screenshots/reports-badge-before.png` — empty pill, 16 sampled colours | `docs/screenshots/reports-badge-after.png` — readable label, 22 sampled colours |

---

## 6. Backend gates (code unchanged, re-run for the record)

```
$ python -m mypy app --no-incremental
Success: no issues found in 168 source files
MYPY_EXIT=0

$ python -m ruff check app tests
All checks passed!
RUFF_EXIT=0

$ python -m black --check app tests
All done! ✨ 🍰 ✨
219 files would be left unchanged.
BLACK_EXIT=0
```

```
$ git diff --stat a20aa3f..HEAD -- backend
(empty)
```

Full suite for the shipped backend (`.tmp-mypy/pytest-final.log`):

```
1090 passed, 2 skipped, 17 deselected, 785 warnings in 1525.57s (0:25:25)
```

Not re-run, because nothing under `backend/` changed in this pass; the only later
backend commit in this repository's history was the annotation-only `_scope`
declaration in `3c27b66`, which adds no runtime code.

---

## 7. CI

Run [44136881866](https://github.com/shashu123456/SentinelAI/actions/runs/44136881866)
on `60e0b67`, conclusions straight from the Actions API:

```
success	Backend tests
success	Secret scanning
success	CodeQL analysis (python)
success	Backend lint & type check
success	CodeQL analysis (javascript)
success	Frontend test & build
success	Docker build
success	Deployment smoke test
```

Docker build and the deployment smoke test both ran and passed — the two jobs that
were skipped while an earlier lint failure blocked them.

---

## 8. Deployment

```
$ curl -s https://sentinelai-api.vercel.app/api/v1/version
{"success":true,"data":{"commit":"60e0b673ffeb2b23fcc49358863e52888a9e4c63","env":"production","build":"60e0b67"},"meta":null}

$ git rev-parse HEAD
60e0b673ffeb2b23fcc49358863e52888a9e4c63
```

The deployed commit is HEAD, byte for byte.

```
$ curl -s https://sentinelai-web.vercel.app/
assets/index-C-nZdB15.css   assets/index-_bNO2RIZ.js
fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap
theme-color" content="#211831"
```

---

## 9. Live functional checks

```
/security.txt                  -> 200
/.well-known/security.txt      -> 200
POST /api/auth/demo-login      -> HTTP 200
```

Demo data intact (read through the demo session):

```
demo-login: 200 | scans: [
 {"id":6,"name":"demo-code.zip","kind":"code","findings":2},
 {"id":5,"name":"demo-requirements.txt","kind":"deps","findings":74},
 {"id":4,"name":"Demo Petstore API","kind":"spec","findings":12}]
```

---

## 10. Screenshots

All captured from `https://sentinelai-web.vercel.app` at device pixel ratio 1 with
Chrome via Playwright, after the final design deploy. Each file was decoded and
checked for real content.

| File | Route | Session | Viewport | Distinct colours |
|---|---|---|---|---|
| `landing.png` | `/` | anonymous | 1440x900 | 1006 |
| `landing-mobile.png` | `/` | anonymous | 390x844 | 931 |
| `login.png` | `/login` | anonymous | 1440x900 | 378 |
| `coverage.png` | `/coverage` | demo | 1440x900 | 794 |
| `authorized-use.png` | `/authorized-use` | demo | 1440x900 | 514 |
| `reports.png` | `/reports` | demo | 1440x900 | 538 |
| `scans-new.png` | `/scans/new` | demo | 1440x900 | 495 |
| `beta-dashboard.png` | `/beta/dashboard` | demo | 1440x900 | 548 |
| `copilot.png` | `/beta/copilot` | demo | 1440x900 | 634 |
| `reports-badge-before.png` | crop of `/reports` | — | 300x48 | 16 |
| `reports-badge-after.png` | crop of `/reports` | — | 300x48 | 22 |

`/coverage`, `/authorized-use` and `/beta/*` sit behind `ProtectedRoute`, so those
captures use a demo session token held only in the browser's `localStorage`.
No token was written to a file, a log, or this document.

**Correction:** an earlier note described the login screen as "legacy palette". It
is not — `Login.css` has zero legacy hits and the page uses the volt/fig/bloom
tokens. The screenshot above is the current build.

---

## 11. AgentGuard

Not enabled. The probe is not shipped as a working feature, the Coverage page states
"AI agent prompt-injection probing is not enabled in this build", and nothing routes
to it. Runbook P7 remains the only deliberately-off optional item.

---

## 12. Safe to claim / not safe to claim

| Safe to claim (evidence above) | Not safe to claim |
|---|---|
| CI is 8/8 green on `60e0b67`, including Docker build and Deployment smoke | CI has always been green |
| mypy is clean under `--no-incremental` (168 files); ruff and black pass | mypy was clean all along |
| Full suite `1090 passed / 2 skipped / 17 deselected` on the shipped backend | The suite was re-run after every commit in this pass |
| Zero brand neon and zero legacy emerald in source, in `dist`, and in all 15 deployed stylesheets | Every colour is a token (see residue below) |
| No legacy hue is rendered on any of 26 audited routes | Every pixel of every page was audited |
| The report badge defect is fixed; no invisible text remains on 11 audited pages | The whole UI has been contrast-audited |
| Deployed API commit equals HEAD (`60e0b67`, full SHA match) | Web and API deploy at the same instant |
| 9 page screenshots plus before/after crops, all from the deployed build | Screenshots cover every page |
| README counts match the registries (48 rules, API1–API10) | Rule counts prove detection quality |
| AgentGuard is documented as not enabled | AgentGuard works |

### Known cosmetic residue (documented, not defects)

- 273 six-hex literals remain in `src`. They are neutrals — `#ffffff` (26),
  Tailwind greys such as `#e5e7eb`/`#6b7280`/`#0f172a` — in older surfaces
  (`Timeline.css`, `ExecutionDetails.css`, legal pages). They are not brand hues and
  not neon, so they pass the colour rule, but they are not role tokens yet.
- `/reports` has no horizontal page padding (`.report-page { padding: 0 0 40px }`),
  so its header sits flush at x=0 while `/scans/new` is inset by 16px. Layout was out
  of scope for this pass and was deliberately left alone.
- The beta banner renders "…core workflow.Back to the app" with no space before the
  link.
