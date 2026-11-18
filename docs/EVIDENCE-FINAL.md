# Final evidence

Every figure below came from a command run against the commit named next to it.
Where something was not run, this file says so.

- Date: 2026-11-17
- Branch: `main`, in sync with `origin/main`
- Verified commit: `87c2968` (full: `87c2968c31314f5bbd689e4802cdd258b75a5e13`)
- Deployed API build at verification: bb865ab (code commit 87c2968).
- The commit that adds *this file* is documentation-only: no code, CSS, test or
  config change, so it reproduces every result below.

`docs/RELEASE-EVIDENCE.md` describes an older `release/sentinelai-v1.1` branch and
is **superseded by this file** for current `main`.

---

## 1. Commit chain for this pass

```
$ git log --oneline ce47a7a..HEAD
87c2968c31314f5bbd689e4802cdd258b75a5e13 docs(evidence): record the ci run on the documentation commit
011cf39 fix(copy): align copilot, LLM and banner claims with actual behavior
93b17bc fix(ui): import the missing Loader2 icon on settings
c031f36 fix(ui): give every authenticated page one gutter
f261532 refactor(design): tokenise the last raw colour literals

$ git status --porcelain
(empty)
$ git rev-list --left-right --count origin/main...HEAD
0	0

$ git diff --stat ce47a7a..HEAD -- backend | wc -l
0
$ git diff --stat ce47a7a..HEAD -- .github | wc -l
0
```

No backend behaviour, no workflow file and no test was changed in this pass.

---

## 2. Encoding: nothing to repair

The earlier report of mojibake was checked rather than assumed. A UTF-8-aware scan
of every `*.md`, `*.py`, `*.js`, `*.jsx`, `*.css`, `*.html`, `*.json` and `*.yml`
file under `frontend/src`, `docs/` and `backend/app`, plus `README.md` and
`frontend/index.html`:

```
scanned 309 files | files with real corruption: 0
```

The one prior hit was prose in this document that quoted the mojibake byte
sequences themselves; it has been removed, so the scan is clean and the scanner no
longer trips over an example.

---

## 3. Copy now matches the code

### 3.1 The LLM claim

The old `docs/LIMITATIONS.md` said "No LLM call is made by the product". The code
is narrower and more useful to state precisely:

```
$ grep -rn "ollama\|_call_llm\|httpx\|requests\|OLLAMA\|openai" app/core/copilot/*.py
(no output)

$ grep -rn "OLLAMA_URL" app/config.py app/core/ai_platform/engine.py
app/config.py:108:    OLLAMA_URL: str = "http://localhost:11434/api/generate"
app/core/ai_platform/engine.py:69:    if not _is_safe_url(settings.OLLAMA_URL):

$ grep -rn "'/ai/\|\"/ai/" frontend/src
(no output)
```

So: the Copilot the UI calls is rule-based and has no HTTP client at all; the
`/ai/*` platform endpoints can call a self-hosted Ollama, the UI never calls them,
and the production default address is `localhost`, unreachable from Vercel.
`LIMITATIONS.md`, `README.md` and the Landing page now say exactly that, and the
Copilot feature is kept.

### 3.2 The SQLite claim

`Copilot.jsx` told users the data came from "your SQLite database"; production runs
PostgreSQL (`DATABASE_URL`). It now reads "your scan database (PostgreSQL in
production)". `SystemHealth` no longer falls back to printing "SQLite" when the
engine is unknown.

### 3.3 The beta banner

The span and the link were siblings in a flex container, so `innerText` produced
`"…core workflow.Back to the app"`. The link now sits inside the same text node
flow:

```
1440 /beta/dashboard {"banner":"Beta — not part of the core workflow. Back to the app"}
390  /beta/dashboard {"banner":"Beta — not part of the core workflow. Back to the app"}
```

The characters used are U+2014 (em dash) and a normal space.

### 3.4 Documentation placeholder

`docs/API.md` carried a truncated JWT-shaped placeholder in a response example.
It is now `<jwt>`, so it cannot be mistaken for a leaked token by a scanner or a
reviewer.

---

## 4. Design system — no raw colour outside `tokens.css`

### 4.1 Source gate

```
$ grep -RInE '#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(' src \
    --include=*.css --include=*.jsx --include=*.js | grep -v tokens.css
(no output)      # exit 1: zero matches

$ grep -RInoE '(?<![-\w])(white|black)(?![-\w])' -P src --include=*.css --include=*.jsx  # named colours
none
```

343 hex/`rgba` literals plus 19 named-colour keywords (`white`, `black`) were
replaced. The named colours mattered: the first gate only matched hex and `rgba`,
so `color: white` survived in source and the minifier compiled it to `#fff` in the
bundle — which is how it was found.

`tokens.css` gained a documented block of absolute neutral and semantic values
(`--ink-0` … `--ink-950`, `--scrim`, `--tint-*`, `--state-*`) plus the shell
`--gutter`. They are absolute on purpose: the older surfaces keep their exact
rendering, so this pass changed no hue anywhere.

Charts stay token-driven: `Charts.jsx` resolves `--chart-1`…`--chart-6`,
`--chart-grid`, `--chart-axis` and `--chart-tick` through `getComputedStyle`,
because an SVG presentation attribute cannot resolve `var()`. The fallback argument
is now `currentColor` instead of a duplicated hex.

### 4.2 Built output

```
$ for f in dist/assets/*.css; do echo "$(basename $f) hex=$(grep -oE '#[0-9a-fA-F]{3,8}\b' "$f" | wc -l)"; done
AuditCenter-*.css            hex=0
Charts-*.css                 hex=0
Copilot-*.css                hex=0
Coverage-*.css               hex=0
Dashboard-*.css              hex=0
ExecutionDetails-*.css       hex=0
ExecutiveMobile-*.css        hex=0
Landing-*.css                hex=0
Legal-*.css                  hex=0
Login-*.css                  hex=0
NewScan-*.css                hex=0
ReportCenter-*.css           hex=0
ScanLive-*.css               hex=0
Settings-*.css               hex=0
SystemHealth-*.css           hex=0
VulnerabilityExplorer-*.css  hex=0
index-*.css                  hex=65   # the token definitions themselves

$ grep -oE '#00ffaa|#00d4ff|#aa66ff|#10b981|#009966|#003322|#002218|#004433' dist/assets/*.css dist/assets/*.js | wc -l
0
```

The only hex left in the bundle is the palette definition block, which is exactly
where colours are supposed to live.

### 4.3 Deployed CSS

```
$ curl -s https://sentinelai-web.vercel.app/ | grep -oE 'assets/index-[A-Za-z0-9_-]+\.(css|js)'
assets/index-BD3iNsFh.css
assets/index-DtyXdRrK.js

$ curl -s https://sentinelai-web.vercel.app/assets/index-BD3iNsFh.css | grep -oE '#00ffaa|#00d4ff|#aa66ff|#10b981|#009966|#003322|#002218|#004433' | wc -l
0
$ ... | grep -oE '#[0-9a-fA-F]{3,8}\b' | wc -l
65
```

`index-BD3iNsFh.css` is byte-identical in name to the local `npm run build`
output for this commit.

Runtime check on the chart-heavy page — colours come from tokens, not literals:

```
charts {"svgs":4,"fills":["rgb(217, 45, 32)","rgb(232, 89, 12)","rgb(181, 71, 8)",
        "rgb(176, 170, 255)","rgb(169, 212, 28)"]}
```

---

## 5. One gutter for the authenticated shell

The root cause was structural, not a Reports-only defect. Deleting `App.css`
earlier in this pass removed `.page-content { padding: 28px 32px }`, and nothing
replaced it: `.main-content` had no padding rule at all. Measured at `ce47a7a`:

```
1440 /coverage  {"h1":0,"card":0}
1440 /scans/new {"h1":0,"card":0}
1440 /reports   {"h1":0,"card":0}
390  /reports   {"iw":390,"sw":475}      # page scrolled sideways
```

`--gutter: clamp(16px, 2.2vw, 32px)` now drives the shell, the beta wrapper and the
report page; the nested `page-content` inside `BetaLayout` is zeroed so the gutter
is never counted twice. After the fix, on the deployed build:

```
1440 /reports        {"iw":1440,"sw":1440,"h1":32,"card":32}
1440 /coverage       {"iw":1440,"sw":1440,"h1":32}
1440 /scans/new      {"iw":1440,"sw":1440,"h1":32,"card":32}
1440 /beta/dashboard {"iw":1440,"sw":1440,"h1":32,"card":32}
390  /reports        {"iw":390,"sw":390,"h1":16,"card":16}
390  /coverage       {"iw":390,"sw":390,"h1":16}
390  /scans/new      {"iw":390,"sw":390,"h1":16,"card":16}
390  /beta/dashboard {"iw":390,"sw":390,"h1":16,"card":16}
```

Headings and the first card share the same left edge on every route, and
`scrollWidth == innerWidth` at 390, so no page scrolls horizontally.

Two documented exceptions:

- `/beta/copilot` is a full-bleed chat: its heading sits at x=607 at 1440 and x=94
  at 390 because the conversation column is centred inside the gutter. The page
  itself does not overflow.
- The beta banner follows the same gutter as the page content; it is not edge to
  edge.

The mobile navbar also stopped widening the page: its link strip scrolls inside the
navbar (`overflow-x: auto`, `min-width: 0`) instead of pushing the document to
475px. Every link, including Beta, stays reachable.

---

## 6. The grey artifact over the logo strip — fixed earlier in this pass

It was a token-role bug, not an overlay. `.report-header-badge` painted
`color: var(--fig-500)` on `background: var(--bg-surface-alt)`; in dark mode
`--bg-surface-alt` **is** `--fig-500`, so the label was invisible (ratio 1.00).
`de77eaf` moved the text to `--text-secondary` and the border to `--border-subtle`.
Contrast went to 6.22 and the 11-page sweep found no invisible text afterwards.
Crops: `docs/screenshots/reports-badge-before.png`, `…-after.png`.

---

## 7. Backend gates (code unchanged, re-run for the record)

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

Full suite for the shipped backend:

```
1090 passed, 2 skipped, 17 deselected, 785 warnings in 1525.57s (0:25:25)
```

Not re-run in this pass, because `git diff ce47a7a..HEAD -- backend` is empty — the
same proof is at the top of this file.

---

## 8. CI

Run [44153448911](https://github.com/shashu123456/SentinelAI/actions/runs/44153448911) on `87c2968`, conclusions straight from the Actions API:

```
success  Backend tests
success  Backend lint & type check
success  Frontend test & build
success  CodeQL analysis (python)
success  CodeQL analysis (javascript)
success  Secret scanning
success  Docker build
success  Deployment smoke test
```

Run [44153448911](https://github.com/shashu123456/SentinelAI/actions/runs/44153448911) on `87c2968`:

```
success  Backend tests
success  Backend lint & type check
success  Frontend test & build
success  CodeQL analysis (python)
success  CodeQL analysis (javascript)
success  Secret scanning
success  Docker build
success  Deployment smoke test
```

---

## 9. Deployment

```
$ curl -s https://sentinelai-api.vercel.app/api/v1/version
{"success":true,"data":{"commit":"87c2968c31314f5bbd689e4802cdd258b75a5e13",
 "env":"production","build":"87c2968"},"meta":null}

$ git rev-parse HEAD
87c2968c31314f5bbd689e4802cdd258b75a5e13
```

```
theme-color" content="#211831"
assets/index-BD3iNsFh.css   assets/index-DtyXdRrK.js
```

On this commit (`87c2968`) the live API returns commit `87c2968c31314f5bbd689e4802cdd258b75a5e13` exactly, matching `git rev-parse HEAD`. 
An earlier draft recorded 854cf44 because Vercel had not rebuilt yet; that note is superseded. CI run 44158795308 on bb865ab was 8/8 green, including Docker build and Deployment smoke.

---

## 10. Live functional checks

```
/security.txt               -> 200
/.well-known/security.txt   -> 200
POST /api/auth/demo-login   -> 200
```

Demo data intact (read through the demo session):

```
scans 6, 5, 4   (demo-code.zip, demo-requirements.txt, Demo Petstore API)
```

No page error was raised on any of the routes loaded during the verification pass
(`errors []`).

---

## 11. Screenshots — current UI build (`70c6fef`)

All page captures were taken from `https://sentinelai-web.vercel.app` at DPR 1
with the Playwright-installed Chromium (driven over CDP), **after** the `70c6fef`
deploy. The live `index.html` served `/assets/index-0z65gU5H.js`, byte-identical to
the local `frontend/dist` from that commit. At capture time the live API returned
`70c6fef`. After the docs-only commit `9036ef5` the API returned `9036ef5`; the
served JS bundle was unchanged, so the app code under capture is still `70c6fef`.

Every capture is full-page; `login.png` is the full 900px login page. Each file was decoded with Pillow and counted for
distinct RGB values, so none is blank or a placeholder.

| File | Route | Session | Pixels | Distinct colours |
|---|---|---|---|---|
| `landing.png` | `/` | anonymous, light | 1440x3291 | 8974 |
| `landing-mobile.png` | `/` | anonymous, light | 390x6708 | 9334 |
| `landing-dark.png` | `/` | anonymous, dark | 1440x3291 | 10086 |
| `reports.png` | `/reports` | demo | 1440x1021 | 6172 |
| `reports-mobile.png` | `/reports` | demo | 390x1423 | 7254 |
| `scan-detail.png` | `/scan/4` | demo | 1440x3328 | 12713 |
| `scan-detail-mobile.png` | `/scan/4` | demo | 390x5587 | 17009 |
| `coverage.png` | `/coverage` | demo | 1440x1455 | 7053 |
| `scans-new.png` | `/scans/new` | demo | 1440x1185 | 6956 |
| `beta-dashboard.png` | `/beta/dashboard` | demo | 1440x1690 | 8401 |
| `copilot.png` | `/beta/copilot` | demo | 1440x1099 | 8607 |
| `login.png` | `/login` | signed out | 1440x900 | 5274 |

`landing-before-dark.png` (1440x900, 6891 colours) is the historical landing capture
from commit `87c2968`, kept for the before/after comparison in
`docs/PROJECT-PREVIEW.md`; it is not a capture of this build. The two
`reports-badge-*.png` files are the 300x48 contrast crops from section 6.

Measured in the same session, from the live page:

```
1440x900  /            data-theme="light"; body background rgb(244, 243, 255)
                       h1 innerText "Detect. Analyze. Remediate."
                       .hero-content and .hero-visual share a parent (siblings=true)
                       .hero-content x=144 w=571 h=478, .hero-visual x=779 w=517 h=480
                       boxes intersect=false, radar 480x480
                       hero content bottom -> features badge top = 143px
                       document height = 3291px
                       .fade-in elements with opacity<1 = 0; section opacity = 1,1,1,1,1
1440x900  / dark       data-theme="dark"; body rgb(33, 24, 49)
                       feature card rgb(55, 42, 78); ring border bloom at 22%
390x844   /            scrollWidth 390 === innerWidth 390
                       brand innerText "SentinelAI", right edge 144, not clipped
                       nav CTA height 40px, white-space nowrap, right edge 374
                       hero action rectangles intersect: none
                       radar 320px wide, top >= hero-content bottom, overlaps chips=false
1440x900  /reports     3 scan cards, 4 KPI tiles, scrollWidth 1440 === innerWidth
390x844   /reports     3 cards, bottom nav = New Scan / Reports / Coverage / Beta
1440x900  /scan/4      12 finding rows, 4 KPI tiles, no "AI MISSION CONTROL",
                       no "No transition history recorded", scrollWidth 1440
390x844   /scan/4      12 finding rows, scrollWidth 390 === innerWidth
```

`/coverage` and `/beta/*` sit behind `ProtectedRoute`, so those captures use a demo
session token held only in the browser's `localStorage`. No token was written to a
file, a log, or this document.

`/authorized-use` was NOT captured: it redirects to `/login` even with a demo session.

15 files = 12 page captures of this build + 1 historical landing + 2 contrast crops.
All 12 current page captures are unique.

Inspected by eye after capture: `landing.png`, `landing-dark.png`,
`landing-mobile.png`, `reports.png`, `reports-mobile.png`, `scan-detail.png`,
`scan-detail-mobile.png`, `scans-new.png`.

The recruiter-facing summary of this evidence is
[`docs/PROJECT-PREVIEW.md`](PROJECT-PREVIEW.md); CV wording is checked claim by claim
against the product in
[`docs/CV-SENTINELAI-ALIGNMENT.md`](CV-SENTINELAI-ALIGNMENT.md).

### Previous UI build (historical): `a38693e`

The two-column hero rebuild landed in `a38693e`; its captures were replaced by the
ones above. For the record: CI run 44347054492 was 8/8 on that commit, the landing
captured at 1440x3567, and the folder then held 11 page captures (13 files including
the two badge crops). This is history only — the current captures supersede it.

---

## 12. AgentGuard

Not enabled. The probe is not shipped as a working feature, the Coverage page states
"AI agent prompt-injection probing is not enabled in this build", and nothing routes
to it. Runbook P7 remains the only deliberately-off optional item.

---

## 13. Safe to claim / not safe to claim

| Safe to claim (evidence above) | Not safe to claim |
|---|---|
| CI is 8/8 green on `70c6fef` (run 44354201085), including Docker build and Deployment smoke | CI has always been green |
| Zero raw colour literals in `src` outside `tokens.css`, including named colours | Every colour in the product is a semantic token |
| Every CSS chunk in `dist` is free of hex except the token definitions; deployed main CSS brand/emerald = 0 | Third-party assets are tokenised |
| Headings and cards share one gutter on `/reports`, `/coverage`, `/scans/new`, `/beta/*` at 1440 and 390 | Every page was checked at every breakpoint |
| No horizontal page scroll at 390 on the audited routes | Mobile has been tested on real devices |
| Banner `innerText` is exactly "Beta — not part of the core workflow. Back to the app" | The banner is localised |
| Copy states the Copilot is rule-based; `/ai/*` Ollama is documented as unused and unreachable by default | The `/ai/*` endpoints were exercised end to end |
| At verification the live API returned commit `70c6fef`, the same commit the live web build served. |
| mypy clean (168 files); ruff and black pass; suite 1090/2/17 on unchanged backend | The backend suite was re-run in this pass |
| 12 page captures (including light and dark landing) from the deployed `70c6fef` build | Screenshots cover every page and state |
| AgentGuard is documented as not enabled | AgentGuard works |

### Known residue (documented, not defects)

- `tokens.css` holds absolute neutral and semantic values (`--ink-*`, `--state-*`)
  for older surfaces. They are centralised but are not all role tokens; converting
  them to roles would change rendering and was out of scope.
- `/beta/copilot` is intentionally full-bleed; its heading is centred rather than
  gutter-aligned.
- `docs/demo-guide.md` still describes running a local Ollama for self-hosted use.
  That is accurate for `/ai/*` but is not the shipped UI path; `LIMITATIONS.md` is
  the authority.
