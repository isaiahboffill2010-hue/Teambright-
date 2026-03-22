# Design System

## Typography
- **Font**: `system-ui, -apple-system, sans-serif` (set globally in `globals.css`)
- **Smoothing**: `-webkit-font-smoothing: antialiased`

## Color Tokens
Defined in `src/app/globals.css` via Tailwind v4 `@theme` and `:root`.

| Token | Class | Value | Usage |
|---|---|---|---|
| Background | `bg-slate-50` | `#f8fafc` | App pages |
| Foreground | `text-slate-900` | `#0f172a` | Body text |
| Sidebar | `bg-slate-900` | — | Nav sidebar |
| Primary | `bg-blue-600` | — | Buttons, active nav |
| Brand Green | `text-brand-green` / `bg-brand-green` / `border-brand-green` | `#00ff9d` | Landing page accent |
| Brand Gold | `text-brand-gold` / `border-brand-gold` | `#f5a623` | Compliance Officer CTA |

## Spacing & Layout
- Page padding: `p-8`
- Max content width: `max-w-6xl mx-auto`
- Card gap: `gap-4` (stats), `gap-6` (main grid)

## Components
| Component | File | Variants |
|---|---|---|
| Button | `src/components/ui/Button.tsx` | `primary`, `secondary`, `ghost`, `danger` |
| Card | `src/components/ui/Card.tsx` | — |
| Badge | `src/components/ui/Badge.tsx` | `success`, `neutral` |
| Sidebar | `src/components/layout/Sidebar.tsx` | `advisor`, `compliance_officer` |

## Page Structure
- **Landing** (`/`): Full-screen black, centered, brand-green + brand-gold accents
- **Advisor app** (`/dashboard`, etc.): `bg-slate-900` sidebar + `bg-slate-50` main area
- **Compliance officer app** (`/review`, etc.): same shell, different nav
