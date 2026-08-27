# SentinelAI — Complete Product Design Document

> **Version:** 2.0  
> **Status:** Design Specification  
> **Audience:** Senior UI/UX Team, Frontend Engineers, Product Managers  
> **Classification:** Internal — Confidential

---

## Table of Contents

1. [Product Vision](#1-product-vision)
2. [Design System](#2-design-system)
3. [Navigation Architecture](#3-navigation-architecture)
4. [Page Designs](#4-page-designs)
5. [Visualization Catalog](#5-visualization-catalog)
6. [Enterprise Interactions](#6-enterprise-interactions)
7. [Animation & Motion Language](#7-animation--motion-language)
8. [Responsive Behavior](#8-responsive-behavior)
9. [Accessibility](#9-accessibility)
10. [Self-Critique & Revision](#10-self-critique--revision)

---

# 1. Product Vision

## What SentinelAI Is

SentinelAI is an **AI-Native Application Security Intelligence Platform**. It is the single pane of glass through which security teams, developers, and executives understand and act on application security risk.

## What SentinelAI Is NOT

- It is not a dashboard. Dashboards are read-only summaries. SentinelAI is an action platform.
- It is not an admin panel. Admin panels manage settings. SentinelAI manages risk.
- It is not a college project. Every pixel must communicate commercial-grade trust.

## Product Philosophy

**"Security clarity in an uncertain world."**

Every screen answers one question: **"What should I do next?"**

If a screen doesn't help someone act, it shouldn't exist.

## Target Users

| Persona | Role | Primary Need | Daily Usage |
|---------|------|-------------|-------------|
| **Security Analyst** | SOC L2/L3 | Triage, investigate, remediate vulnerabilities | 6-8 hours |
| **DevSecOps Engineer** | Pipeline Security | Integrate scans into CI/CD, fix findings | 2-4 hours |
| **Security Lead** | Team Management | Prioritize, assign, track remediation progress | 1-2 hours |
| **CTO/CISO** | Executive | Risk posture, compliance status, trends | 15 min/day |
| **Developer** | Application Dev | Understand findings, get fix guidance | 30 min/day |

---

# 2. Design System

## 2.1 Color System

### Dark Mode (Primary)

SentinelAI is **dark mode first**. Security analysts work in SOC environments with multiple monitors in dim lighting. Dark mode is not a theme — it is the product.

```
Backgrounds:
  --bg-void:        #050810     Deepest background (behind everything)
  --bg-page:        #0a0f18     Page background
  --bg-surface:     #0d1219     Card/panel background
  --bg-elevated:    #111820     Elevated surfaces (modals, drawers)
  --bg-overlay:     #0a0f18cc   Modal overlay (80% opacity)
  --bg-hover:       rgba(0, 255, 170, 0.04)  Subtle hover
  --bg-active:      rgba(0, 255, 170, 0.08)  Active/selected state
  --bg-input:       #0c1017     Form input background

Borders:
  --border-subtle:  rgba(255, 255, 255, 0.04)   Hairline dividers
  --border-default: rgba(255, 255, 255, 0.08)   Card borders
  --border-strong:  rgba(255, 255, 255, 0.12)   Focused elements
  --border-accent:  rgba(0, 255, 170, 0.20)     Accent borders

Text:
  --text-primary:   #e8f0ec     Headings, primary content
  --text-secondary: #a0b0a8     Body text, descriptions
  --text-muted:     #5a6a62     Labels, metadata, timestamps
  --text-inverse:   #0a0f18     Text on light backgrounds

Accent Colors:
  --accent-cyan:    #00ffaa     Primary accent (brand color)
  --accent-blue:    #00d4ff     Links, interactive elements
  --accent-purple:  #aa66ff     AI/ML features
  --accent-orange:  #ff8800     Warnings, medium severity
  --accent-red:     #ff2244     Critical, errors, destructive
  --accent-green:   #00ff88     Success, healthy, low severity
  --accent-yellow:  #ffcc00     Informational, medium

Severity Palette (Critical — these colors MUST remain consistent):
  --sev-critical:   #ff2244     P0 — Immediate action required
  --sev-high:       #ff6622     P1 — Fix within 24 hours
  --sev-medium:     #ffaa00     P2 — Fix within 1 week
  --sev-low:        #00ff88     P3 — Fix when convenient
  --sev-info:       #5a8a80     P4 — Informational only
```

### Light Mode

Light mode inverts backgrounds and adjusts text contrast. Severity colors remain identical. Accent colors shift slightly for contrast:

```
  --bg-page:        #f8faf9
  --bg-surface:     #ffffff
  --bg-elevated:    #ffffff
  --text-primary:   #0f172a
  --text-secondary: #475569
  --text-muted:     #94a3b8
  --border-default: rgba(0, 0, 0, 0.08)
```

### Color Rules

1. **Severity colors are sacred.** Never change `--sev-critical` from red. Users build muscle memory around these colors.
2. **Accent cyan is brand.** Used for primary actions, selected states, and the brand mark. Never used for errors or warnings.
3. **Never use color alone to convey meaning.** Always pair with icons, text labels, or patterns.
4. **Contrast ratio minimum: 4.5:1** for body text, **3:1** for large text and UI components.

## 2.2 Typography

### Type Scale

```
Display:     36px / 40px / -1.2 tracking / 700 weight    Hero titles only
H1:          28px / 34px / -0.8 tracking / 700 weight    Page titles
H2:          22px / 28px / -0.4 tracking / 700 weight    Section titles
H3:          16px / 22px / -0.2 tracking / 600 weight    Card titles
H4:          14px / 20px / 0 tracking / 600 weight       Subsection titles
Body:        14px / 20px / 0 tracking / 400 weight       Default body text
Body Small:  13px / 18px / 0 tracking / 400 weight       Secondary content
Caption:     12px / 16px / 0.2 tracking / 500 weight     Labels, metadata
Overline:    10px / 14px / 1.5 tracking / 700 weight     Section labels, overlines
Code:        13px / 18px / 0 tracking / 400 weight       Monospace for code/data
```

### Font Stacks

```
Display/UI:   'Space Grotesk', -apple-system, sans-serif     (Headings, hero text)
Body:         'DM Sans', -apple-system, sans-serif            (Body, UI elements)
Monospace:    'JetBrains Mono', 'SF Mono', monospace          (Code, data, timestamps)
```

### Typography Rules

1. **Display font is used sparingly.** Only page titles and hero numbers. Overusing it makes everything feel like a poster.
2. **Monospace for data.** Timestamps, IDs, scores, code snippets, and status labels use monospace. This creates visual distinction between "data" and "narrative."
3. **Overlines for sections.** Every major section starts with an overline label in uppercase monospace: `// THREAT GAUGE`, `// SEVERITY DISTRIBUTION`. This is the brand voice.
4. **Never use bold for emphasis in body text.** Use color (accent cyan) or icons instead.

## 2.3 Spacing System

```
Space unit: 4px

  --space-1:   4px      Tight internal padding
  --space-2:   8px      Icon gaps, small padding
  --space-3:   12px     Compact card padding
  --space-4:   16px     Standard card padding
  --space-5:   20px     Panel padding
  --space-6:   24px     Section spacing
  --space-8:   32px     Page margins
  --space-10:  40px     Major section spacing
  --space-12:  48px     Page-level spacing
  --space-16:  64px     Hero spacing
```

### Spacing Rules

1. **Cards use 16px internal padding.** Never less for content cards.
2. **Section spacing is 24px.** Between major page sections.
3. **Related items are 8px apart.** Unrelated items are 16px+ apart.
4. **Page content has 32px horizontal padding** on desktop, 16px on mobile.

## 2.4 Elevation & Depth

```
Level 0:   No shadow                                  Page background
Level 1:   0 1px 3px rgba(0,0,0,0.12)                Cards, surfaces
Level 2:   0 4px 12px rgba(0,0,0,0.20)               Elevated panels, dropdowns
Level 3:   0 8px 32px rgba(0,0,0,0.30)               Modals, drawers
Level 4:   0 16px 64px rgba(0,0,0,0.40)               Command palette, toast stack
```

### Glass Effect (Used Sparingly)

```css
backdrop-filter: blur(16px) saturate(1.2);
background: rgba(13, 18, 25, 0.8);
border: 1px solid rgba(255, 255, 255, 0.06);
```

**Only used for:** Command palette, floating toolbars, pinned filter bars. Never for main content cards.

## 2.5 Border Radius

```
  --radius-sm:    4px     Badges, tags, small elements
  --radius-md:    6px     Buttons, inputs, small cards
  --radius-lg:    8px     Cards, panels, modals
  --radius-xl:    12px    Large cards, hero sections
  --radius-full:  9999px  Avatars, pills, circular elements
```

### Border Rules

1. **No element has radius 0.** Even the smallest tag gets 4px.
2. **Modals and drawers use 12px.** This signals "overlay" to the user.
3. **Cards use 8px.** Consistent across the entire product.
4. **Buttons use 6px.** Matches input fields.

## 2.6 Component Catalog

### Buttons

```
Primary:     bg: accent-cyan / text: bg-void / font: 600 weight
             Used for: Main CTA (New Scan, Save, Confirm)
             
Secondary:   bg: transparent / border: border-default / text: text-secondary
             Used for: Cancel, Back, Less important actions
             
Danger:      bg: rgba(255,34,68,0.08) / border: rgba(255,34,68,0.2) / text: accent-red
             Used for: Delete, Remove, Destructive actions
             
Ghost:       bg: transparent / text: text-muted
             Used for: Tertiary actions, icon-only buttons
             
Icon Button: 32x32 / radius: 6px / bg: transparent
             Used for: Toolbar actions, inline actions
             
Size:        SM: 28px height / 12px font
             MD: 32px height / 13px font (default)
             LG: 40px height / 14px font
```

**Hover states:** All buttons get a subtle border-color shift and 1px upward translation. Active state: scale(0.98).

### Inputs

```
Height:      36px
Padding:     0 12px
Background:  --bg-input
Border:      1px solid --border-default
Radius:      6px
Font:        13px / --font-body
Placeholder: --text-muted at 50% opacity

Focus:       border-color: accent-cyan
             box-shadow: 0 0 0 2px rgba(0, 255, 170, 0.1)
             
Error:       border-color: accent-red
             box-shadow: 0 0 0 2px rgba(255, 34, 68, 0.1)
```

### Cards

```
Padding:     16px
Background:  --bg-surface
Border:      1px solid --border-default
Radius:      8px
Shadow:      Level 1

Hover:       border-color shifts to accent-cyan at 15% opacity
             translateY(-1px)
             shadow increases to Level 2
```

**Card header pattern:** Every card can optionally have a header bar:
- Left: 6px green dot (pulsing) + overline label in monospace
- Separator: 1px border-bottom

### Tables

```
Header:      bg: --bg-surface / border-bottom: 1px solid --border-default
             Font: 10px / uppercase / monospace / --text-muted
             
Row:         height: 44px
             border-bottom: 1px solid --border-subtle
             hover: bg: --bg-hover
             
Selected:    bg: --bg-active
             
Cell:        padding: 0 16px
             font: 13px / --text-primary
             
Sticky:      First column sticky on horizontal scroll
```

**Table features:**
- Column sort: Click header → sort asc → click again → sort desc → click again → remove sort
- Sort indicator: Small chevron icon in header
- Row selection: Checkbox in first column (when bulk actions available)
- Row click: Opens detail drawer or navigates to detail page
- Right-click: Context menu with Copy ID, View, Export, Delete

### Badges / Tags

```
Default:     bg: rgba(255,255,255,0.04) / border: 1px solid --border-default / text: --text-muted
Severity:    bg: sev-color at 8% opacity / border: 1px solid sev-color at 20% / text: sev-color
Status:      bg: status-color at 8% / text: status-color
Count:       bg: --bg-surface / font: monospace / text: --text-primary
```

### Dropdowns / Selects

```
Trigger:     Same as Input styling
Dropdown:    bg: --bg-elevated / border: 1px solid --border-default / radius: 8px / shadow: Level 2
Item:        height: 36px / padding: 0 12px / font: 13px
Hover:       bg: --bg-hover
Selected:    bg: --bg-active / checkmark icon on right
Group:       Overline label in uppercase monospace / padding-top: 8px
```

### Tooltips

```
Trigger:     Hover delay 400ms / disappear delay 100ms
Position:    Above element, centered, 8px gap
Style:       bg: --bg-elevated / border: 1px solid --border-default / radius: 6px
             shadow: Level 2
Font:        12px / --text-secondary
Max-width:   240px
Arrow:       6px triangle pointing to trigger
```

### Modals

```
Overlay:     bg: rgba(0,0,0,0.6) / backdrop-filter: blur(8px)
Container:   max-width: 560px / radius: 12px / shadow: Level 3
Header:      padding: 20px 24px / border-bottom: 1px solid --border-default
Body:        padding: 24px / max-height: calc(100vh - 200px) / overflow-y: auto
Footer:      padding: 16px 24px / border-top: 1px solid --border-default / flex-end gap

Animation:   Scale from 0.95 to 1.0 / opacity from 0 to 1 / 200ms cubic-bezier(0.16, 1, 0.3, 1)
```

### Drawers / Side Panels

```
Width:       480px (standard) / 640px (wide, for detail views)
Position:    Right side (default) / Left side (rare)
Overlay:     Same as modal overlay
Header:      Same as modal header
Body:        Full height scroll
Animation:   translateX from 100% to 0 / 250ms cubic-bezier(0.16, 1, 0.3, 1)

Close:       X button in header / Escape key / Click overlay
```

### Toast Notifications

```
Position:    Bottom-right, 20px from edges
Stack:       Newest on top, max 3 visible
Style:       bg: --bg-elevated / border: 1px solid / radius: 8px / shadow: Level 3
Width:       360px
Duration:    Success: 4s / Error: 8s (manual dismiss) / Info: 5s

Types:
  Success:   border-left: 3px solid accent-green / CheckCircle icon
  Error:     border-left: 3px solid accent-red / XCircle icon
  Warning:   border-left: 3px solid accent-orange / AlertTriangle icon
  Info:      border-left: 3px solid accent-blue / Info icon

Content:     Title (600 weight) + Description (400 weight) + Action button (optional)
Dismiss:     X button / Swipe right / Auto-dismiss
```

## 2.7 Icons

**Library:** Lucide Icons (consistent stroke weight of 1.5px)

**Icon sizing:**
- Inline text: 14px
- Button icons: 16px
- Card/panel icons: 18-20px
- Hero/empty state icons: 32-48px

**Icon rules:**
1. Icons always appear to the left of text labels
2. Icon-only buttons always have a tooltip
3. Status indicators use colored circles, not icons (exception: severity badges)
4. Destructive icons (trash, X) are accent-red only on hover

---

# 3. Navigation Architecture

## 3.1 Primary Navigation (Sidebar)

The sidebar is the navigation spine. It is **always visible** on desktop (240px width). On mobile, it collapses to a hamburger menu.

### Sidebar Structure

```
┌─────────────────────────────┐
│ 🛡️ SENTINEL                 │
│    SOC Platform              │
├─────────────────────────────┤
│ 🔍 Search or jump to... ⌘K  │
├─────────────────────────────┤
│ // MISSION CONTROL           │
│   📊 Dashboard               │
│                              │
│ // SCANNING                  │
│   📡 API Scanner             │
│   📝 SAST Analysis           │
│   📦 Dependencies            │
│   🔒 Container Security      │
│   🔑 Secrets Scanner         │
│                              │
│ // INTELLIGENCE              │
│   ⚠️ Vulnerabilities         │
│   🤖 AI Copilot              │
│   📈 Security Analytics      │
│   🗺️ Attack Graph            │
│                              │
│ // OPERATIONS                │
│   📋 Reports                 │
│   📜 Audit Center            │
│   🔔 Notifications           │
│   💚 System Health           │
│                              │
│ ─────────────────            │
│ // COMING SOON               │
│   🛡️ Compliance  [Soon]      │
│   🏢 Asset Inventory [Soon]  │
│   🔌 Integrations  [Soon]    │
│                              │
│ ─────────────────            │
│ ⚙️ Settings                  │
├─────────────────────────────┤
│ [A] admin                    │
│     SOC Analyst    🌙  🚪   │
└─────────────────────────────┘
```

### Sidebar Behavior

| Interaction | Behavior |
|-------------|----------|
| Click section label | No action (label only) |
| Click nav item | Navigate, highlight active, collapse mobile menu |
| Hover nav item | Background highlight, subtle left border glow |
| Active item | Left 2px accent-cyan border, bg-active background, accent-cyan text |
| Disabled item (Soon) | Muted text, lock icon, no cursor pointer |
| Scroll | Sidebar content scrolls independently, user section pinned to bottom |
| Brand click | Navigate to /dashboard |

### Sidebar States

| State | Visual |
|-------|--------|
| Default | Dark background, muted text |
| Hover | Subtle bg-hover background |
| Active | Accent-cyan left border + bg-active |
| Collapsed (mobile) | Hidden off-screen, hamburger toggle |
| Loading | Skeleton placeholder for nav items |

## 3.2 Top Bar (Context Bar)

Above the main content area, a minimal context bar provides:

```
┌─────────────────────────────────────────────────────────┐
│ // VULNERABILITY EXPLORER                    🔍  ⚙️  👤 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                    [Page Content]                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Contains:**
- Breadcrumb trail (left)
- Context-specific actions (right): Search, Settings, User menu
- **No global search here** — that's in the sidebar (⌘K)

## 3.3 Command Palette (⌘K)

The command palette is the **power user's primary navigation tool**. It replaces traditional menus for keyboard-first users.

### Command Palette Design

```
┌──────────────────────────────────────────┐
│ 🔍 Type a command or search...     ESC   │
├──────────────────────────────────────────┤
│ NAVIGATION                                │
│   Dashboard              ⌘ D             │
│   New API Scan           ⌘ N             │
│   SAST Analysis          ⌘ S             │
│   Vulnerabilities        ⌘ V             │
│   AI Copilot             ⌘ ⇧ C           │
│   Reports                ⌘ R             │
│   Audit Center           ⌘ A             │
│   Settings               ⌘ ,             │
│   System Health          ⌘ H             │
│                                          │
│ ACTIONS                                   │
│   New Scan               ⌘ ⇧ N           │
│   Export Report          ⌘ E             │
│   Toggle Dark Mode       ⌘ ⇧ D           │
│   Keyboard Shortcuts     ?               │
│                                          │
├──────────────────────────────────────────┤
│ ↑↓ Navigate  ↵ Select  ESC Close         │
└──────────────────────────────────────────┘
```

### Command Palette Behavior

| Interaction | Behavior |
|-------------|----------|
| Open | ⌘K or `/` key |
| Type | Fuzzy search across all commands, pages, actions |
| Arrow keys | Navigate results |
| Enter | Execute selected command |
| Escape | Close palette |
| Click outside | Close palette |
| Recent commands | Show top 3 recent commands at top when empty |

---

# 4. Page Designs

---

## 4.1 Mission Control (Dashboard)

### Purpose
The executive overview. The first screen after login. Answers: "How secure are we right now?"

### Primary Goal
Provide immediate security posture awareness and surface the most urgent action.

### Target User
All personas. This is the default landing page.

### Information Hierarchy

```
1. Security Score (hero number) — Am I safe?
2. Critical/High findings count — What needs attention NOW?
3. Severity distribution chart — What's the breakdown?
4. Scan activity trend — Are we scanning regularly?
5. Recent scans — What happened recently?
6. Quick actions — What can I do next?
```

### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ SENTINEL THREAT CENTER                               │
│ Threat Intelligence                                  │
│ Real-time security posture across 24 scanned APIs   │
│                                        [New Scan]    │
├─────────┬─────────┬─────────┬───────────────────────┤
│ Total   │ Findings│ Critical│ Risk Score             │
│ Scans   │         │ Alerts  │ 42/100                 │
│ 24      │ 187     │ 12      │ Medium                 │
├─────────┴─────────┴─────────┴───────────────────────┤
│ ┌──────────────────┐ ┌──────────────────────────────┐│
│ │ SEVERITY         │ │ SCAN ACTIVITY (30D)          ││
│ │ DISTRIBUTION     │ │                              ││
│ │                  │ │  ████                        ││
│ │   [Donut Chart]  │ │  ████ ███                    ││
│ │                  │ │  ████ ███ ████               ││
│ │  ● Critical  12  │ │  ████ ███ ████ ███           ││
│ │  ● High      34  │ │                              ││
│ │  ● Medium    89  │ │  M  T  W  T  F  S  S        ││
│ │  ● Low       52  │ ├──────────────────────────────┤│
│ │  ● Info      20  │ │ RISK TREND                   ││
│ │                  │ │                              ││
│ │                  │ │  ╱╲    ╱╲                    ││
│ │                  │ │ ╱  ╲╱╱  ╲╱╲                 ││
│ │                  │ │           ╲                  ││
│ ├──────────────────┤ ├──────────────────────────────┤│
│ │ OWASP FINDINGS   │ │                              ││
│ │                  │ │  API1 BOLA      ████████  23 ││
│ │                  │ │  API2 Auth      ██████    18 ││
│ │                  │ │  API7 SSRF      ████      12 ││
│ │                  │ │  A03 Injection  ███        8 ││
│ │                  │ │  A05 Misconfig  ██         5 ││
│ └──────────────────┘ └──────────────────────────────┘│
├─────────────────────────────────────────────────────┤
│ QUICK ACCESS                                         │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│ │ 📡 API   │ │ 📝 SAST  │ │ 📦 Deps  │ │ 🤖 AI   ││
│ │ Scanner  │ │ Analysis │ │ Scanner  │ │ Analyst  ││
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘│
├─────────────────────────────────────────────────────┤
│ RECENT OPERATIONS                                    │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 01  Petstore API          14 findings  Score 45 │ │
│ │     3 endpoints · 2024-01-15         [View] [🗑]│ │
│ ├─────────────────────────────────────────────────┤ │
│ │ 02  Payment Gateway       8 findings   Score 72 │ │
│ │     7 endpoints · 2024-01-14         [View] [🗑]│ │
│ ├─────────────────────────────────────────────────┤ │
│ │ 03  User Service          23 findings  Score 31 │ │
│ │     12 endpoints · 2024-01-13        [View] [🗑]│ │
│ └─────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────┤
│ 🟢 SCANNER ENGINE  🟢 THREAT INTEL  🟢 DATABASE     │
└─────────────────────────────────────────────────────┘
```

### Widgets

| Widget | Type | Data Source | Interaction |
|--------|------|------------|-------------|
| Security Score | Hero number | `/api/scans/dashboard` | Click → Threat Gauge detail |
| Severity Donut | Recharts PieChart | `/api/scans/dashboard` | Click segment → Filter vulnerabilities |
| Scan Activity | Recharts BarChart | `/api/scans/analytics` | Click bar → Day's scans |
| Risk Trend | Recharts LineChart | `/api/scans/analytics` | Hover → Tooltip with date/score |
| OWASP Distribution | Recharts horizontal BarChart | `/api/scans/analytics` | Click bar → OWASP filter |
| Quick Access | Link cards | Static | Click → Navigate |
| Recent Scans | List with metadata | `/api/scans/dashboard` | Click → Scan detail |
| Status Bar | Status dots | Static + health check | Click → System Health |

### Charts

| Chart | Visualization | Type | X-Axis | Y-Axis | Color |
|-------|--------------|------|--------|--------|-------|
| Severity Distribution | Donut | PieChart | N/A | Count | Severity palette |
| Scan Activity | Vertical bars | BarChart | Date (30d) | Scan count | Accent cyan |
| Risk Trend | Line | LineChart | Date | Score (0-100) | Accent orange |
| OWASP Distribution | Horizontal bars | BarChart | Category | Finding count | Accent purple |

### Empty State

```
┌─────────────────────────────────────────────────────┐
│ RECENT OPERATIONS                                    │
│                                                      │
│                    🛡️                                 │
│           Welcome to SentinelAI                      │
│    Start securing your applications by running       │
│    your first scan.                                  │
│                                                      │
│    ┌─────────────────────────────────────────────┐   │
│    │ 1  Upload API Spec                          │   │
│    │    Scan your OpenAPI/Swagger for vulns  →   │   │
│    ├─────────────────────────────────────────────┤   │
│    │ 2  Run SAST Analysis                        │   │
│    │    Static code analysis for Py/JS/Java  →   │   │
│    ├─────────────────────────────────────────────┤   │
│    │ 3  Scan Dependencies                        │   │
│    │    Detect known CVEs in packages        →   │   │
│    ├─────────────────────────────────────────────┤   │
│    │ 4  Ask AI Copilot                           │   │
│    │    Get AI-powered security advice        →   │   │
│    └─────────────────────────────────────────────┘   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Loading State

Skeleton layout matching the exact structure above:
- Title: 200px skeleton line
- Metric cards: 4 skeleton cards with icon placeholder + number placeholder + label placeholder
- Chart panels: Skeleton rectangles with panel header
- Recent scans: 3 skeleton rows with metadata

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `N` | New Scan |
| `G D` | Go to Dashboard (refresh) |
| `?` | Show shortcuts |

---

## 4.2 API Scanner

### Purpose
Upload an OpenAPI/Swagger specification and run a comprehensive security scan.

### Primary Goal
Get a complete vulnerability assessment of an API surface in under 60 seconds.

### Target User
Security Analyst, DevSecOps Engineer

### Information Hierarchy

```
1. Upload zone — Drop your spec here
2. Scan configuration — What to check
3. Recent scans — Quick access to previous results
```

### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ API SECURITY SCANNER                                 │
│ Upload OpenAPI or Swagger specifications for         │
│ comprehensive security analysis                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │                                               │  │
│  │           📄                                  │  │
│  │     Drop OpenAPI spec here                    │  │
│  │     or click to browse                        │  │
│  │                                               │  │
│  │     Supports: .json .yaml .yml                │  │
│  │     Max size: 10MB                            │  │
│  │                                               │  │
│  │     ┌──────────────────────────────────┐      │  │
│  │     │  🔍 Quick Scan    │  🤖 Deep Scan│      │  │
│  │     │  Fast, rule-based │  AI-enriched │      │  │
│  │     └──────────────────────────────────┘      │  │
│  │                                               │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  SCAN CONFIGURATION                                  │
│  ┌───────────────────────────────────────────────┐  │
│  │ ☑ OWASP API Top 10                           │  │
│  │ ☑ Authentication Analysis                     │  │
│  │ ☑ Rate Limiting Check                         │  │
│  │ ☑ Injection Vectors                           │  │
│  │ ☑ Business Logic                              │  │
│  │ ☐ Custom Rules (coming soon)                  │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  RECENT SCANS                                        │
│  ┌───────────────────────────────────────────────┐  │
│  │ Petstore API    ✅ Completed  14 findings     │  │
│  │ Payment GW      ✅ Completed  8 findings      │  │
│  │ User Service    🔄 Running    60% complete    │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Upload Zone Behavior

| State | Visual |
|-------|--------|
| Default | Dashed border (2px), icon + text, hover glow |
| Drag over | Border becomes solid accent-cyan, background brightens, icon animates |
| Uploading | Progress bar, percentage, estimated time |
| Success | Green checkmark, auto-navigate to results |
| Error | Red border, error message, retry option |

### Scan Modes

| Mode | Description | Duration | AI |
|------|-------------|----------|-----|
| **Quick Scan** | Rule-based OWASP checks | 5-15 seconds | No |
| **Deep Scan** | Full analysis + AI enrichment | 30-120 seconds | Yes |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `U` | Focus upload zone |
| `Enter` | Start scan (when file selected) |
| `Esc` | Cancel scan |

---

## 4.3 Live Scanner

### Purpose
Real-time view of an in-progress scan with streaming output.

### Primary Goal
Provide transparency into the scanning process and build trust that the scan is thorough.

### Target User
Security Analyst, DevSecOps Engineer

### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ ← Back to Dashboard   LIVE SCAN — Petstore API      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │ SCAN PROGRESS                                  │  │
│  │ ████████████████████░░░░░░  72%               │  │
│  │ Phase: Analyzing authentication endpoints      │  │
│  │ Elapsed: 00:34     ETA: 00:13                  │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │ SCAN OUTPUT                           [Auto ▼] │  │
│  │ ─────────────────────────────────────────────  │  │
│  │ [00:01] Initializing scanner engine...         │  │
│  │ [00:02] Parsing OpenAPI 3.0.3 specification    │  │
│  │ [00:02] Found 24 endpoints across 5 paths      │  │
│  │ [00:03] ▸ GET /pets — Checking rate limiting   │  │
│  │ [00:03]   ⚠ No rate limiting detected          │  │
│  │ [00:04] ▸ POST /pets — Checking auth           │  │
│  │ [00:04]   ⚠ No authentication required         │  │
│  │ [00:05] ▸ GET /pets/{id} — BOLA check          │  │
│  │ [00:05]   🔴 Potential IDOR vulnerability      │  │
│  │ ...                                            │  │
│  │ [00:34] ▸ Analyzing response schemas           │  │
│  │ [00:34]   ℹ Schema validation enabled          │  │
│  │                                              │  │
│  │ █ (cursor)                                    │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  LIVE FINDINGS                                         │
│  ┌───────┬──────────┬──────────┬──────────┬────────┐│
│  │ Found │ Critical │ High     │ Medium   │ Low    ││
│  │  14   │    3     │    5     │    4     │   2    ││
│  └───────┴──────────┴──────────┴──────────┴────────┘│
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Terminal Output Behavior

- Monospace font (JetBrains Mono)
- Dark background (#050810)
- Timestamps in dim gray
- Findings highlighted by severity color
- Auto-scroll to bottom (with "jump to bottom" button when scrolled up)
- Output streams in real-time via WebSocket

### Animations

- Progress bar: Smooth width transition with gradient fill
- Finding counter: Increment with subtle scale animation
- Severity counts: Flash briefly when incremented
- Scan output: Fade-in for each new line

---

## 4.4 SAST Analysis

### Purpose
Static Application Security Testing for Python, JavaScript, and Java source code.

### Primary Goal
Identify security vulnerabilities in source code before deployment.

### Target User
Developer, Security Analyst

### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ STATIC APPLICATION SECURITY TESTING                  │
│ Analyze source code for security vulnerabilities     │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────┐ ┌────────────────────────┐│
│  │ UPLOAD CODE           │ │ SCAN CONFIGURATION     ││
│  │                       │ │                        ││
│  │  📁 Drop files here   │ │ Language: [Auto-detect]││
│  │  or paste code below  │ │ Rules: [40+ enabled]   ││
│  │                       │ │ Severity: [All]        ││
│  │  ┌────────────────┐   │ │                        ││
│  │  │ // Paste code  │   │ │ [Run SAST Scan]       ││
│  │  │ // here...     │   │ │                        ││
│  │  │                │   │ │                        ││
│  │  └────────────────┘   │ │                        ││
│  └──────────────────────┘ └────────────────────────┘│
│                                                      │
│  SCAN RESULTS                                        │
│  ┌───────────────────────────────────────────────┐  │
│  │ Severity: ●●●●○  Score: 45/100  Grade: C     │  │
│  ├───────────────────────────────────────────────┤  │
│  │ 📍 app/auth.py:23                             │  │
│  │ Hardcoded password detected                   │  │
│  │ Severity: High  CWE-798  Confidence: 92%     │  │
│  │                                               │  │
│  │  21 │ def login(user, password):              │  │
│  │  22 │     # TODO: use env var                 │  │
│  │ >23 │     db_pass = "admin123"  ← HERE       │  │
│  │  24 │     if password == db_pass:             │  │
│  │                                               │  │
│  │ Fix: Use os.environ.get("DB_PASSWORD")        │  │
│  │ [Ask AI for help] [Mark as false positive]    │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Code Viewer

- Syntax highlighting (language-aware)
- Line numbers
- Vulnerable line highlighted in severity color
- Context lines (3 before, 3 after)
- Click line → expand inline details
- Copy button for code snippet

---

## 4.5 Dependency Scanner

### Purpose
Detect known CVEs in project dependencies across package managers.

### Primary Goal
Identify vulnerable dependencies and provide safe version recommendations.

### Target User
Developer, DevSecOps Engineer

### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ DEPENDENCY SCANNER                                   │
│ Scan for vulnerable packages and known CVEs          │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │ SUPPORTED FORMATS                              │  │
│  │ 📦 requirements.txt  📦 package.json           │  │
│  │ 📦 pom.xml  📦 go.mod  📦 Cargo.toml          │  │
│  │                                               │  │
│  │ Drop dependency file here or paste contents    │  │
│  │ ┌────────────────────────────────────────┐    │  │
│  │ │ flask==2.0.1                           │    │  │
│  │ │ requests==2.25.0                       │    │  │
│  │ │ django==3.2.0                          │    │  │
│  │ └────────────────────────────────────────┘    │  │
│  │                            [Scan Dependencies]│  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  RESULTS — 3 vulnerable of 24 total                  │
│  ┌───────────────────────────────────────────────┐  │
│  │ Package      Current    CVE          Severity  │  │
│  │ ─────────────────────────────────────────────  │  │
│  │ flask        2.0.1      CVE-2023-... High     │  │
│  │ requests     2.25.0     CVE-2023-... Medium   │  │
│  │ django       3.2.0      CVE-2023-... Critical │  │
│  │                                              │  │
│  │ Safe versions:                                │  │
│  │ flask → 2.3.3  requests → 2.31.0  django→4.2│  │
│  │                                              │  │
│  │ [Copy upgrade commands]  [Export SBOM]        │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Dependency Table

| Column | Type | Sortable | Filterable |
|--------|------|----------|------------|
| Package | Text | Yes | No |
| Current Version | Semver | No | No |
| CVE ID | Link | No | No |
| Severity | Badge | Yes | Yes |
| CVSS Score | Number | Yes | No |
| Fixed Version | Semver | No | No |
| Description | Text (truncated) | No | No |

---

## 4.6 AI Security Copilot

### Purpose
Conversational AI assistant for security questions, explanations, and code generation.

### Primary Goal
Reduce time-to-understanding for security findings and accelerate remediation.

### Target User
All personas

### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ AI SECURITY COPILOT                                  │
│ Ask security questions, get AI-powered answers       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────┐ ┌────────────────────────┐│
│  │ CONVERSATION          │ │ CONTEXT                ││
│  │                       │ │                        ││
│  │ 👤 Explain SSRF       │ │ Current Scan: Petstore ││
│  │                       │ │ Findings: 14           ││
│  │ 🤖 SSRF (Server-Side  │ │ Severity: Medium       ││
│  │ Request Forgery is a  │ │                        ││
│  │ vulnerability where   │ │ Related Findings:      ││
│  │ an attacker can make  │ │ • No rate limiting     ││
│  │ the server send       │ │ • Missing auth         ││
│  │ requests to internal  │ │                        ││
│  │ resources...          │ │ Quick Actions:         ││
│  │                       │ │ [Generate Fix]         ││
│  │ **Impact:** Can lead  │ │ [Threat Model]         ││
│  │ to internal network   │ │ [Explain OWASP]        ││
│  │ scanning, data        │ │ [Attack Simulation]    ││
│  │ exfiltration...       │ │                        ││
│  │                       │ │                        ││
│  │ [Copy] [Ask follow-up]│ │                        ││
│  │                       │ │                        ││
│  ├───────────────────────┤ │                        ││
│  │                       │ │                        ││
│  │ 👤 Generate a fix for │ │                        ││
│  │    the SSRF in the    │ │                        ││
│  │    /webhook endpoint  │ │                        ││
│  │                       │ │                        ││
│  │ 🤖 Here's a secure    │ │                        ││
│  │    implementation...  │ │                        ││
│  │                       │ │                        ││
│  │ ┌──────────────────┐  │ │                        ││
│  │ │ ```python        │  │ │                        ││
│  │ │ import validators│  │ │                        ││
│  │ │                  │  │ │                        ││
│  │ │ ALLOWED_HOSTS =  │  │ │                        ││
│  │ │ ["api.internal"] │  │ │                        ││
│  │ │ ...              │  │ │                        ││
│  │ └──────────────────┘  │ │                        ││
│  │ [Copy Code] [Apply]   │ │                        ││
│  │                       │ │                        ││
│  ├───────────────────────┤ │                        ││
│  │                       │ │                        ││
│  │ ┌─────────────────┐   │ │                        ││
│  │ │ Ask anything... │   │ │                        ││
│  │ └─────────────────┘   │ │                        ││
│  │            [Send] 📎  │ │                        ││
│  └──────────────────────┘ └────────────────────────┘│
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Chat Interface

- **Messages:** User (right-aligned, accent-blue bg) / AI (left-aligned, surface bg)
- **Code blocks:** Monospace, dark background, copy button, syntax highlighting
- **Typing indicator:** Three animated dots while AI generates
- **Sources:** When AI references a finding, show a linked badge
- **Actions:** Each AI response can have inline action buttons (Copy, Apply, Ask Follow-up)
- **Context panel:** Shows current scan context, related findings, quick actions

### Conversation Starters (Empty State)

```
"Explain this vulnerability"
"Generate a fix for this finding"
"What is OWASP API1?"
"How would an attacker exploit this?"
"Create a threat model for my API"
"Summarize my security posture"
```

---

## 4.7 Vulnerability Explorer

### Purpose
Central hub for browsing, filtering, and managing all security findings across all scans.

### Primary Goal
Enable rapid triage and prioritization of vulnerabilities.

### Target User
Security Analyst, Security Lead

### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ ALL FINDINGS                    🔍 Search...  ⚙️    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐                │
│  │ 🔴 │ │ 🟠 │ │ 🟡 │ │ 🟢 │ │ ⚪ │                │
│  │ 12 │ │ 34 │ │ 89 │ │ 52 │ │ 20 │                │
│  │Crit│ │High│ │ Med│ │Low │ │Info│                │
│  └────┘ └────┘ └────┘ └────┘ └────┘                │
│                                                      │
│  Filters: Severity [▼] OWASP [▼] Scan [▼] Sort [▼] │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │ ☐  🔴 Broken Object Auth    API1  Score 9.1  │  │
│  │    /api/users/{id} — Petstore — High conf.   │  │
│  ├───────────────────────────────────────────────┤  │
│  │ ☐  🟠 Missing Rate Limit   API4  Score 7.5  │  │
│  │    /api/login — Petstore — Med conf.         │  │
│  ├───────────────────────────────────────────────┤  │
│  │ ☐  🟡 Hardcoded Password   CWE-798 Score 6.2│  │
│  │    app/auth.py:23 — User Service — 92% conf. │  │
│  ├───────────────────────────────────────────────┤  │
│  │ ☐  🟡 SQL Injection         A03   Score 8.1  │  │
│  │    /api/search — Petstore — 88% conf.        │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  Showing 187 of 187 findings  Page 1 of 10           │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Finding Detail Drawer

When a finding is clicked, a right-side drawer opens:

```
┌─────────────────────────────────┐
│ ✕                               │
│ 🔴 Broken Object Level Auth     │
│ OWASP API1 · CWE-639 · 9.1     │
├─────────────────────────────────┤
│ DESCRIPTION                     │
│ The API endpoint allows access  │
│ to any user's data by changing  │
│ the ID parameter without        │
│ authorization checks.           │
│                                 │
│ AFFECTED ENDPOINT               │
│ GET /api/users/{userId}         │
│                                 │
│ EVIDENCE                        │
│ ┌─────────────────────────────┐ │
│ │ GET /api/users/123          │ │
│ │ Authorization: Bearer <tok> │ │
│ │ → Returns user 456's data   │ │
│ └─────────────────────────────┘ │
│                                 │
│ REMEDIATION                     │
│ Implement object-level access   │
│ control checks before returning │
│ data. Verify the authenticated  │
│ user owns or has access to the  │
│ requested resource.             │
│                                 │
│ CONFIDENCE                      │
│ ████████████████████░░  85%     │
│                                 │
│ REFERENCES                      │
│ • OWASP API1:2023               │
│ • CWE-639                       │
│ • CVE-2023-XXXX                 │
│                                 │
│ [Ask AI for Fix] [Mark FP] [Jira]│
└─────────────────────────────────┘
```

### Filter System

| Filter | Type | Multi-select | Persisted |
|--------|------|-------------|-----------|
| Severity | Checkbox group | Yes | Yes (URL) |
| OWASP Category | Dropdown | Yes | Yes (URL) |
| CWE | Text search | No | Yes (URL) |
| Scan | Dropdown | No | No |
| Confidence | Range slider | No | No |
| Endpoint | Text search | No | No |
| Date Range | Date picker | No | No |

### Saved Filters

Users can save filter combinations:
- "Critical + High only"
- "My scan findings"
- "Unfixed findings"
- "Last 7 days"

---

## 4.8 Audit Center

### Purpose
Complete audit trail of every action in the platform.

### Primary Goal
Provide non-repudiation and compliance evidence.

### Target User
Security Lead, Compliance Officer, CISO

### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ SECURITY EVENT LOG          🔍 Search...  ⬇ Export  │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Filters: All Events [▼] All Users [▼] Date [▼]     │
│                                                      │
│  TODAY — August 20, 2026                             │
│  ┌───────────────────────────────────────────────┐  │
│  │ 14:23  🟢  admin  logged in         192.168.1│  │
│  │ 14:24  🟢  admin  created scan #12            │  │
│  │ 14:25  🟡  admin  exported PDF report         │  │
│  │ 14:30  🔵  admin  invited member (user@...)   │  │
│  │ 14:31  🟢  system scan #12 completed          │  │
│  │ 14:35  🔴  admin  deleted scan #8             │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  YESTERDAY — August 19, 2026                         │
│  ┌───────────────────────────────────────────────┐  │
│  │ 09:00  🟢  analyst  logged in       10.0.0.5 │  │
│  │ 09:15  🟢  analyst  ran SAST scan              │  │
│  │ 10:30  🟡  analyst  updated org settings      │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Event Types

| Event | Icon | Color | Category |
|-------|------|-------|----------|
| Login | LogIn | Green | Auth |
| Logout | LogOut | Gray | Auth |
| Password Reset | Key | Orange | Auth |
| Scan Created | Upload | Cyan | Scan |
| Scan Completed | CheckCircle | Green | Scan |
| Scan Failed | XCircle | Red | Scan |
| Report Exported | FileText | Blue | Report |
| Member Invited | UserPlus | Blue | Org |
| Member Removed | UserMinus | Red | Org |
| Settings Changed | Settings | Orange | Config |
| API Key Created | Key | Cyan | API |
| Finding Status Changed | AlertTriangle | Varies | Finding |

---

## 4.9 Reports

### Purpose
Generate, preview, and download security reports in multiple formats.

### Primary Goal
Produce professional reports for executives, auditors, and development teams.

### Target User
Security Lead, CISO, Compliance Officer

### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ REPORT CENTER                                        │
│ Generate and download security reports               │
├─────────────────────────────────────────────────────┤
│                                                      │
│  REPORT TYPES                                        │
│  ┌──────────────────┐ ┌────────────────────────────┐│
│  │ 📊 Executive     │ │ 📋 Technical               ││
│  │ Summary          │ │ Detail                     ││
│  │                  │ │                            ││
│  │ Risk posture,    │ │ Full findings, code        ││
│  │ trends, KPIs     │ │ snippets, remediation      ││
│  │ for leadership   │ │ for developers             ││
│  │                  │ │                            ││
│  │ [Generate]       │ │ [Generate]                 ││
│  └──────────────────┘ └────────────────────────────┘│
│  ┌──────────────────┐ ┌────────────────────────────┐│
│  │ 🛡️ Compliance    │ │ 📑 Audit                   ││
│  │ Matrix           │ │ Trail                      ││
│  │                  │ │                            ││
│  │ OWASP/NIST/PCI   │ │ Complete event log with    ││
│  │ gap analysis     │ │ timestamps and details     ││
│  │                  │ │                            ││
│  │ [Generate]       │ │ [Generate]                 ││
│  └──────────────────┘ └────────────────────────────┘│
│                                                      │
│  GENERATED REPORTS                                   │
│  ┌───────────────────────────────────────────────┐  │
│  │ Petstore Executive Summary    PDF  1.2MB  📥  │  │
│  │ Petstore Technical Detail     PDF  3.4MB  📥  │  │
│  │ Payment GW Compliance Matrix  JSON 12KB   📥  │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 4.10 Settings

### Purpose
Platform configuration: organization, projects, team, profile, API keys.

### Primary Goal
Enable administrators to configure the platform for their organization.

### Target User
Security Lead, Admin

### Tab Structure

| Tab | Content |
|-----|---------|
| **Organization** | Create/manage orgs, select active org |
| **Projects** | Create/manage projects within org |
| **Team** | Invite/remove members, manage roles |
| **Profile** | User info, avatar, preferences |
| **API Keys** | Generate, rotate, revoke API keys |
| **Integrations** | GitHub, GitLab, Jira, Slack connections |
| **Notifications** | Alert preferences, digest emails |

### Settings Layout

```
┌─────────────────────────────────────────────────────┐
│ PLATFORM CONFIGURATION                               │
│ Settings                                             │
├─────────┬───────────────────────────────────────────┤
│         │                                           │
│ Org ✦   │  ORGANIZATIONS                 [+ New]    │
│ Projects│  ┌─────────────────────────────────────┐  │
│ Team    │  │ Acme Security                       │  │
│ Profile │  │ acme-security · Enterprise tier     │  │
│ API Keys│  │                         [Select →]  │  │
│ Integr. │  ├─────────────────────────────────────┤  │
│ Notif.  │  │ Starter Org                         │  │
│         │  │ starter · Free tier                 │  │
│         │  │                         [Select →]  │  │
│         │  └─────────────────────────────────────┘  │
│         │                                           │
└─────────┴───────────────────────────────────────────┘
```

---

## 4.11 System Health

### Purpose
Real-time operational status of all platform components.

### Primary Goal
Provide transparency into system health for SRE/DevOps teams.

### Target User
DevOps Engineer, Platform Admin

### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│ SYSTEM OBSERVABILITY                                 │
│ System Health                        Last: 14:32:05 │
│                                      [🔄 Refresh]    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  🟢 System Operational                               │
│  All systems are functioning normally                │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Backend  │ │ Database │ │ API      │            │
│  │ API 🟢   │ │ SQLite 🟢│ │ Endpoint 🟢│           │
│  │ v1.0.0   │ │ Connected│ │ /api/health│           │
│  └──────────┘ └──────────┘ └──────────┘            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Frontend │ │ Scanner  │ │ AI       │            │
│  │ React 🟢 │ │ Engine 🟢│ │ Engine 🟢 │            │
│  │ :5173    │ │ 3 active │ │ Optional │            │
│  └──────────┘ └──────────┘ └──────────┘            │
│                                                      │
│  SYSTEM INFORMATION                                  │
│  Platform: SentinelAI v1.0.0                         │
│  Backend: localhost:8000                              │
│  Environment: Development                             │
│  Health Check: 30 seconds                             │
│  Metrics: /metrics (Prometheus)                       │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 4.12 Compliance Center (Future)

### Purpose
Map findings to compliance frameworks and track compliance posture.

### Target User
Compliance Officer, CISO

### Visualizations

| Visualization | Type | Description |
|--------------|------|-------------|
| Compliance Score | Ring gauge (0-100%) | Overall compliance posture |
| Framework Matrix | Heatmap | Findings per framework control |
| Gap Analysis | Table | Missing controls with severity |
| Remediation Timeline | Gantt chart | Planned fix dates |
| Evidence Locker | File grid | Attached compliance evidence |

### Frameworks

- OWASP Top 10 2023
- OWASP API Top 10 2023
- CWE Top 25 2023
- NIST CSF 2.0
- PCI DSS 4.0
- SOC 2 Type II
- ISO 27001:2022
- CIS Controls v8

---

## 4.13 Attack Graph Explorer (Future)

### Purpose
Visualize attack paths through the application's API surface.

### Target User
Security Analyst, Red Team

### Visualization

Interactive node-graph showing:
- **Nodes:** API endpoints, parameters, data stores
- **Edges:** Data flow, auth boundaries, trust relationships
- **Attack paths:** Highlighted in red from entry point to target
- **Blast radius:** Shaded area showing potential impact

### Interactions

- Zoom/pan with trackpad
- Click node → detail panel
- Hover edge → tooltip showing data flow
- Toggle layers: Auth, Data Flow, Attack Paths
- Simulate attack from entry point

---

## 4.14 Knowledge Base (Future)

### Purpose
Security education and reference library.

### Target User
Developer, Junior Security Analyst

### Content

- OWASP Top 10 explanations with examples
- CWE descriptions with fix guidance
- CVE database search
- Secure coding patterns by language
- Threat modeling templates
- Compliance framework guides

---

## 4.15 Notifications Center (Future)

### Purpose
Centralized notification management and alert preferences.

### Layout

```
┌─────────────────────────────────────────────────────┐
│ NOTIFICATIONS                           [Mark all ✓] │
├─────────────────────────────────────────────────────┤
│                                                      │
│  UNREAD (3)                                          │
│  🔴 Critical finding in Payment GW  2 min ago       │
│  🟡 Scan completed: User Service    15 min ago      │
│  🔵 New member joined: analyst@...  1 hour ago      │
│                                                      │
│  EARLIER                                             │
│  🟢 Scan completed: Petstore API    Yesterday       │
│  🟢 Report exported: Executive      Yesterday       │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 4.16 Asset Inventory (Future)

### Purpose
Comprehensive inventory of all scanned assets.

### Assets Tracked

| Asset Type | Properties |
|------------|-----------|
| API | Name, base URL, version, owner, last scan, score |
| Repository | Name, language, branch, owner, last scan |
| Microservice | Name, language, dependencies, owner |
| Dependency | Package, version, vulnerabilities, ecosystem |

### Views

| View | Description |
|------|-------------|
| Table | Sortable, filterable grid |
| Graph | Relationship map between assets |
| Timeline | Scan history per asset |
| Matrix | Asset vs. vulnerability heatmap |

---

## 4.17 Integrations (Future)

### Purpose
Connect SentinelAI to external tools.

### Supported Integrations

| Integration | Type | Purpose |
|-------------|------|---------|
| GitHub | SCM | Auto-scan repos on push |
| GitLab | SCM | Auto-scan repos on push |
| Jira | Issue Tracker | Create tickets for findings |
| Slack | Communication | Send alerts to channels |
| Webhook | Generic | Custom integrations |
| CI/CD | Pipeline | GitHub Actions, GitLab CI |

---

## 4.18 Developer Workspace (Future)

### Purpose
Developer-focused view optimized for fixing findings.

### Layout

```
┌─────────────────────────────────────────────────────┐
│ MY FINDINGS (7)    Assigned to me                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Priority Sort: Critical → Low                       │
│                                                      │
│  🔴 SSRF in /webhook     Payment GW  Due: Tomorrow  │
│  🟠 Missing auth /admin   Petstore   Due: Jan 25    │
│  🟡 SQL Injection         User Svc   Due: Jan 28    │
│  🟡 Hardcoded cred        app/auth   Due: Jan 28    │
│  🟢 Info leak in headers  Petstore   Due: Feb 1     │
│                                                      │
│  [Bulk: Mark Fixed] [Bulk: False Positive]           │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

# 5. Visualization Catalog

## 5.1 Security Score

**Type:** Hero number + ring gauge  
**Range:** 0-100  
**Colors:** 0-30 green → 30-60 yellow → 60-80 orange → 80-100 red  
**Animation:** Counter animates from 0 to score on load  
**Size:** 72px number, 200px ring gauge  
**Context:** Always shown with letter grade (A-F) below

## 5.2 Risk Heatmap

**Type:** 5×5 grid matrix  
**X-axis:** Likelihood (Very Low → Very High)  
**Y-axis:** Impact (Very Low → Very High)  
**Cell color:** Green → Yellow → Orange → Red (diagonal gradient)  
**Cell content:** Count of findings in that risk zone  
**Interaction:** Click cell → filtered vulnerability list

## 5.3 Attack Timeline

**Type:** Horizontal timeline  
**Events:** Color-coded dots on timeline  
**Interaction:** Hover → tooltip with event details  
**Zoom:** Scroll to zoom, drag to pan  
**Time range:** Last 24h / 7d / 30d / 90d

## 5.4 Dependency Graph

**Type:** Force-directed node graph  
**Nodes:** Packages (sized by dependency count)  
**Edges:** Dependency relationships  
**Node color:** Green (safe) → Red (vulnerable)  
**Interaction:** Click node → detail panel, drag to reposition

## 5.5 OWASP Distribution

**Type:** Horizontal bar chart  
**Categories:** OWASP Top 10 items  
**Bar color:** Accent purple  
**Sorting:** By count (descending)  
**Interaction:** Click bar → filtered vulnerability list

## 5.6 CVSS Distribution

**Type:** Histogram  
**X-axis:** CVSS score (0-10, 0.5 increments)  
**Y-axis:** Count of findings  
**Bar color:** Gradient from green to red  
**Overlay:** Mean/median lines

## 5.7 Severity Distribution

**Type:** Donut chart  
**Segments:** Critical, High, Medium, Low, Info  
**Colors:** Severity palette  
**Center:** Total count number  
**Legend:** Below chart with counts  
**Interaction:** Click segment → filtered vulnerability list

## 5.8 Threat Timeline

**Type:** Vertical timeline (newest on top)  
**Events:** Findings, scans, alerts  
**Severity indicators:** Colored left border  
**Interaction:** Click event → detail panel

## 5.9 Historical Trends

**Type:** Multi-line area chart  
**Lines:** Total findings, Critical, High  
**Time range:** Selectable (7d, 30d, 90d, 1y)  
**Interaction:** Hover → crosshair with values  
**Annotation:** Major events marked with vertical lines

## 5.10 Executive KPIs

**Type:** 4-up card grid  
**Cards:** Security Score, Total Findings, Mean Time to Fix, Compliance %  
**Each card:** Icon + number + trend arrow + label  
**Trend:** Green up-arrow (improving) or red down-arrow (worsening)  
**Period:** Compared to previous period

## 5.11 Real-time Queue

**Type:** Live-updating list  
**Items:** Active scans, pending tasks  
**Animation:** New items slide in from top  
**Status:** Pulsing dot for active items

## 5.12 Live Scan Pipeline

**Type:** Horizontal pipeline visualization  
**Stages:** Upload → Parse → Analyze → Report  
**Active stage:** Pulsing glow  
**Completed stages:** Green checkmark  
**Current stage:** Animated progress  
**Upcoming stages:** Muted

## 5.13 API Topology

**Type:** Directed graph  
**Nodes:** API endpoints (sized by call frequency)  
**Edges:** Request flow between endpoints  
**Node color:** Security score (green → red)  
**Edge style:** Solid (authenticated) / Dashed (unauthenticated)

## 5.14 Repository Graph

**Type:** Treemap  
**Size:** By vulnerability count  
**Color:** By primary language  
**Labels:** Repository name + finding count  
**Interaction:** Click → repository detail

## 5.15 Compliance Matrix

**Type:** Grid table  
**Rows:** Compliance controls  
**Columns:** Frameworks  
**Cell:** Green (pass) / Red (fail) / Yellow (partial) / Gray (not assessed)  
**Interaction:** Click cell → gap details

## 5.16 Security Maturity Score

**Type:** Radar/spider chart  
**Axes:** Detection, Prevention, Response, Recovery, Governance  
**Range:** 0-5 (CMM levels)  
**Fill:** Semi-transparent accent color  
**Overlay:** Industry benchmark (dashed line)

---

# 6. Enterprise Interactions

## 6.1 Global Search

**Trigger:** ⌘K or `/` key  
**Scope:** Pages, findings, scans, settings, commands  
**Behavior:** Fuzzy matching across all entities  
**Results:** Grouped by type (Pages, Findings, Scans, Commands)  
**Keyboard:** ↑↓ to navigate, Enter to select, Esc to close

## 6.2 Quick Actions

**Trigger:** `.` key (period)  
**Actions:** New Scan, Export, Toggle Theme, Toggle Sidebar  
**Context:** Actions change based on current page  
**Display:** Popup menu anchored to current position

## 6.3 Bookmarks

**Trigger:** `⌘B` on any scan or finding  
**Storage:** Local + synced to user profile  
**Display:** Star icon appears on bookmarked items  
**Access:** Bookmarks section in Command Palette

## 6.4 Saved Filters

**Trigger:** Save button in filter bar  
**Storage:** Per-user, named filters  
**Access:** Filter dropdown → Saved section  
**Sharing:** Filters can be shared with org members

## 6.5 Pinned Views

**Trigger:** Pin button on any filtered view  
**Behavior:** Pinned views appear as tabs in the page  
**Limit:** Max 5 pinned views per page  
**Access:** Tab bar at top of list pages

## 6.6 Workspace Switching

**Trigger:** Org selector in sidebar  
**Behavior:** Switches entire data context  
**Persistence:** Remembers last workspace per browser  
**Indicator:** Current org name in sidebar

## 6.7 Keyboard Navigation

| Key | Action |
|-----|--------|
| `⌘K` | Command palette |
| `?` | Keyboard shortcuts help |
| `/` | Focus search |
| `Esc` | Close any overlay |
| `G D` | Go to Dashboard |
| `G N` | Go to New Scan |
| `G V` | Go to Vulnerabilities |
| `G C` | Go to Copilot |
| `G R` | Go to Reports |
| `G A` | Go to Audit |
| `G H` | Go to Health |
| `G ,` | Go to Settings |
| `J` / `K` | Navigate list items down/up |
| `Enter` | Open selected item |
| `X` | Toggle selection (in bulk mode) |
| `E` | Export current view |
| `⌘.` | Quick actions |

## 6.8 Context Panels

**Trigger:** Click any finding/scan row  
**Behavior:** Right-side drawer slides in  
**Content:** Detail view with actions  
**Width:** 480px standard, 640px for code-heavy content  
**Close:** X button, Escape key, click overlay

## 6.9 Inspector Panels

**Trigger:** `I` key with item selected  
**Behavior:** Bottom panel slides up  
**Content:** Quick-look metadata without leaving current view  
**Height:** 200-300px  
**Close:** `I` again, Escape, drag down

## 6.10 Compare Mode

**Trigger:** Select 2 scans → "Compare" button  
**Behavior:** Side-by-side view  
**Layout:** Split screen, synchronized scrolling  
**Highlight:** Differences highlighted in yellow  
**Use case:** Before/after remediation comparison

## 6.11 Timeline Mode

**Trigger:** Toggle in vulnerability explorer  
**Behavior:** Switch from list to timeline view  
**Layout:** Vertical timeline with events  
**Use case:** Understanding when findings appeared

## 6.12 Fullscreen Analytics

**Trigger:** Expand icon on any chart  
**Behavior:** Chart goes fullscreen with enhanced controls  
**Controls:** Time range, data source, export, annotations  
**Close:** Escape or collapse icon

## 6.13 Live Streaming Updates

**Trigger:** WebSocket connection on Dashboard, Live Scan  
**Behavior:** New data appears with slide-in animation  
**Visual:** Subtle pulse on changed values  
**Sound:** Optional notification sound for critical findings  
**Control:** Toggle live updates on/off

---

# 7. Animation & Motion Language

## 7.1 Principles

1. **Purpose over decoration.** Every animation communicates something.
2. **Swift and subtle.** 150-300ms for most transitions. Never longer than 500ms.
3. **Consistent easing.** Use `cubic-bezier(0.16, 1, 0.3, 1)` (Apple spring) for all interactive transitions.
4. **Respect reduced motion.** All animations disabled when `prefers-reduced-motion: reduce`.

## 7.2 Transition Library

| Transition | Duration | Easing | Use Case |
|-----------|----------|--------|----------|
| Page enter | 300ms | spring | New page loads |
| Page exit | 200ms | ease-out | Page unmounts |
| Drawer open | 250ms | spring | Side panel slides in |
| Drawer close | 200ms | ease-out | Side panel slides out |
| Modal open | 200ms | spring | Dialog appears |
| Modal close | 150ms | ease-out | Dialog disappears |
| Tooltip show | 150ms | ease | Hover tooltip |
| Tooltip hide | 100ms | ease | Tooltip disappears |
| Button press | 100ms | ease | Active state scale |
| Card hover | 200ms | ease | Hover lift |
| Toast enter | 300ms | spring | Notification slides in |
| Toast exit | 200ms | ease-out | Notification slides out |
| Skeleton pulse | 1.5s | ease-in-out | Loading shimmer |
| Number count | 800ms | spring | Counter animation |
| Chart draw | 600ms | ease-out | Data visualization |
| Progress bar | 300ms | ease | Progress update |

## 7.3 Micro-Interactions

| Element | Interaction | Animation |
|---------|-------------|-----------|
| Button | Hover | translateY(-1px), border-color shift |
| Button | Active | scale(0.98) |
| Card | Hover | translateY(-1px), shadow increase |
| Link | Hover | color shift to accent-cyan |
| Toggle | Click | knob slides, color changes |
| Checkbox | Click | checkmark draws in (SVG animation) |
| Tab | Click | underline slides to active tab |
| Severity badge | Appear | scale from 0.8 to 1.0 |
| Finding count | Increment | Number scales up briefly |
| Status dot | Active | Pulsing glow animation |
| Progress bar | Update | Width transitions smoothly |
| Chart data | Load | Bars/lines draw in from zero |
| Toast | Appear | Slide from right + fade in |
| Toast | Dismiss | Slide to right + fade out |
| Sidebar link | Active | Left border slides in |
| Search result | Highlight | Background flash |

---

# 8. Responsive Behavior

## 8.1 Breakpoints

```
Desktop:     1200px+     Full sidebar, multi-column layouts
Tablet:      768-1199px  Collapsible sidebar, 2-column layouts
Mobile:      <768px      Hidden sidebar (hamburger), single column
```

## 8.2 Desktop (1200px+)

- Sidebar: Fixed 240px, always visible
- Content: Full width minus sidebar
- Charts: 2-column grid
- Cards: 4-column grid for metrics
- Tables: Full horizontal scroll if needed
- Drawers: 480px from right edge

## 8.3 Tablet (768-1199px)

- Sidebar: Collapsed to icons only (64px) or hidden
- Content: Full width
- Charts: 2-column → 1-column below 900px
- Cards: 2-column grid
- Tables: Horizontal scroll
- Drawers: 100% width (overlay)

## 8.4 Mobile (<768px)

- Sidebar: Hidden, hamburger toggle
- Content: Full width, 16px padding
- Charts: Full width, reduced height
- Cards: Full width, stacked
- Tables: Card view (each row becomes a card)
- Drawers: Full screen overlay
- Bottom navigation: Optional (Dashboard, Scan, Copilot, More)
- Floating action button: New Scan

## 8.5 Mobile-Specific Patterns

| Pattern | Desktop | Mobile |
|---------|---------|--------|
| Navigation | Sidebar | Hamburger + bottom nav |
| Tables | Grid rows | Card stack |
| Charts | Side by side | Stacked, reduced detail |
| Filters | Inline bar | Collapsible filter sheet |
| Detail view | Side drawer | Full-screen push |
| Command palette | Centered modal | Full-screen modal |
| Context menu | Dropdown | Action sheet |

---

# 9. Accessibility

## 9.1 WCAG 2.1 AA Compliance

| Criterion | Requirement | Implementation |
|-----------|-------------|----------------|
| Color Contrast | 4.5:1 for text, 3:1 for UI | All text/background pairs verified |
| Focus Visible | Visible focus ring on all interactive elements | 2px accent-cyan outline |
| Keyboard Navigation | All functionality accessible via keyboard | Tab order, arrow keys, shortcuts |
| Screen Reader | Semantic HTML, ARIA labels | `role`, `aria-label`, `aria-live` |
| Motion | Respect `prefers-reduced-motion` | All animations disabled |
| Text Resize | Content readable at 200% zoom | Relative units (rem), fluid layout |
| Error Identification | Errors linked to form fields | `aria-describedby`, visual indicators |

## 9.2 ARIA Patterns

| Component | ARIA |
|-----------|------|
| Sidebar | `role="navigation"`, `aria-label="Main navigation"` |
| Modal | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` |
| Toast | `role="alert"`, `aria-live="polite"` |
| Tab panel | `role="tablist"`, `role="tab"`, `role="tabpanel"` |
| Table | `role="grid"`, `aria-sort`, `aria-selected` |
| Chart | `role="img"`, `aria-label` with data summary |
| Progress | `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |

## 9.3 Keyboard Shortcuts Documentation

All keyboard shortcuts are discoverable via `?` key, which opens the shortcuts modal. The modal itself is keyboard-navigable.

---

# 10. Self-Critique & Revision

## Round 1 Critique

### Question: "Would Apple ship this?"

**No, if:**
- The landing page has a generic grid background
- Typography is inconsistent (mixing too many font families)
- Animations are gratuitous (floating particles everywhere)
- Empty states are bare "No data" messages
- Loading states are generic spinners

**Yes, if:**
- Typography is deliberate and consistent
- Every screen has a clear purpose
- Animations serve communication, not decoration
- Empty states guide the user to action
- Loading states show meaningful progress

### Question: "Would Stripe ship this?"

**No, if:**
- The dashboard is a collection of random charts
- Tables don't support sorting, filtering, or search
- Forms lack validation feedback
- There's no keyboard navigation
- Export/download options are buried

**Yes, if:**
- Every data view has sort, filter, and search
- Forms validate in real-time with clear error messages
- Every list supports keyboard navigation (J/K)
- Export is always one click away
- The command palette replaces traditional menus

### Question: "Would Datadog ship this?"

**No, if:**
- Charts are static and non-interactive
- There's no time range selector
- Metrics don't show trends/comparisons
- There's no correlation between related data
- Real-time data doesn't stream

**Yes, if:**
- Every chart supports hover tooltips, zoom, and time range
- Metrics show period-over-period comparison
- Related data is visually connected (scan → findings → remediation)
- WebSocket drives live updates on relevant pages
- Annotations mark important events on timelines

### Question: "Would GitHub Security ship this?"

**No, if:**
- Findings aren't organized by severity
- There's no way to dismiss/acknowledge findings
- Remediation guidance is generic
- There's no integration with issue trackers
- The UI doesn't help prioritize

**Yes, if:**
- Findings are sorted by severity with clear visual hierarchy
- Users can mark findings as false positive, fixed, or accepted
- Each finding has specific, actionable remediation
- Jira/GitHub Issues integration creates tickets from findings
- The UI surfaces "what to fix first" prominently

## Round 2 Revision

Based on the critique, here are the mandatory changes:

### 1. Remove All Decorative Elements
- Remove floating particles from all backgrounds
- Remove scanline effects
- Remove grid overlays
- Remove gradient glows on non-accent elements
- **Keep:** Status dot pulses, progress animations, page transitions

### 2. Elevate Data Presentation
- Every chart must support hover tooltips
- Every chart must have a time range selector
- Every table must support sort, filter, and search
- Every list must support keyboard navigation (J/K/Enter)
- Every data view must have export options

### 3. Improve Empty States
- Every empty state must have a clear CTA
- Every empty state must explain what the page does
- Every empty state must link to getting-started resources
- Never show "No data" without context

### 4. Strengthen Loading States
- Replace spinners with skeleton screens everywhere
- Show meaningful progress (not just percentages)
- Show what's being loaded (scan phase, data type)
- Allow cancellation of long-running operations

### 5. Add Micro-Interactions That Communicate
- Severity badge: Subtle pulse on critical findings
- Status changes: Color transition animation
- New data: Slide-in from relevant direction
- Success actions: Brief green flash confirmation
- Error actions: Brief red shake

### 6. Consistent Overline Labels
Every section uses the pattern:
```
● SECTION LABEL (in uppercase monospace, accent color)
```
This is the visual anchor that creates brand consistency across all pages.

---

# Appendix A: File Naming Convention

| Type | Convention | Example |
|------|-----------|---------|
| Component | PascalCase.jsx | `VulnerabilityExplorer.jsx` |
| Styles | PascalCase.css | `VulnerabilityExplorer.css` |
| Utility | camelCase.js | `formatSeverity.js` |
| Service | camelCase.js | `api.js` |
| Context | PascalCaseContext.jsx | `ThemeContext.jsx` |
| Test | Component.test.jsx | `Dashboard.test.jsx` |

# Appendix B: Component Architecture Rules

1. **Never create a new file when you can extend an existing one**
2. **Every component does exactly one thing**
3. **State lives in the lowest common ancestor**
4. **Side effects in useEffect, never in render**
5. **Memoize expensive computations with useMemo**
6. **Debounce search/filter inputs (300ms)**
7. **Never store tokens in component state — use context or localStorage**
8. **All API calls go through the centralized api.js service**

# Appendix C: API Design Conventions

1. **All endpoints prefixed with `/api/`**
2. **RESTful naming: `/api/resources`, `/api/resources/:id`**
3. **Pagination: `?page=1&page_size=20`**
4. **Filtering: `?severity=High&status=active`**
5. **Sorting: `?sort_by=created_at&order=desc`**
6. **Search: `?search=term`**
7. **Response envelope: `{ data: ..., meta: { total, page, page_size } }`**
8. **Error format: `{ detail: "Human-readable error message" }`**
9. **Auth: `Authorization: Bearer <token>` header**
10. **Request ID: `X-Request-ID` header on every response**

---

*This document is a living specification. Update it as design decisions evolve.*
*Last updated: August 20, 2026*
