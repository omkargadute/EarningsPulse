# EarningsPulse frontend

Next.js 16 (App Router) web UI for playbook generation, live agent traces, the reaction chart workspace, and earnings calendar.

## Quick start

```bash
bun install
bun run dev
```

Open http://localhost:3000. The backend API defaults to `http://localhost:8000` via `NEXT_PUBLIC_BACKEND_URL`.

## Routes

| Path | File | Purpose |
|------|------|---------|
| `/` | `src/app/page.tsx` | Hero, ticker input, Demo AAPL, calendar preview |
| `/playbook/[id]` | `src/app/playbook/[id]/page.tsx` | Live run + completed playbook viewer |
| `/calendar` | `src/app/calendar/page.tsx` | Upcoming earnings list |
| `/api/health` | `src/app/api/health/route.ts` | Frontend liveness (Docker / deploy) |

Global shell: `src/app/layout.tsx` — fonts, `ThemeProvider`, disclaimer, metadata.

## User flows

### Generate playbook

1. User enters a ticker on `/` (or picks one from `/calendar`).
2. `TickerInput` calls `generatePlaybook()` → `POST /api/playbook/generate`.
3. Router navigates to `/playbook/{job_id}`.
4. `PlaybookPageClient` mounts `usePlaybookStream(jobId)`.
5. Hook opens `EventSource` on `GET /api/playbook/stream/{job_id}`; `RunPanel` renders trace events.
6. On `playbook_ready`, hook fetches `GET /api/playbook/{job_id}` and renders `PlaybookView`.

### Demo AAPL

`DemoButton` calls `POST /api/playbook/demo/AAPL` and navigates to the returned `job_id` (instant completed job).

## Scripts

| Command | Purpose |
|---------|---------|
| `bun run dev` | Development server (Turbopack) |
| `bun run build` | Production build (Node runtime) |
| `bun run start` | Production server |
| `bun run lint` | oxlint |
| `bun run lint:fix` | oxlint with auto-fix |
| `bun run typecheck` | TypeScript (`tsc --noEmit`) |
| `bun run knip` | Unused files, deps, exports |
| `bun run doctor` | React Doctor health scan |
| `bun run test:property` | Hegel property tests (Vitest) |
| `bun run test:e2e` | Playwright (starts backend + frontend) |
| `bun run test:e2e:ui` | Playwright UI mode |

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | Backend API base URL (baked at build on Vercel) |

Set in repo-root `.env` for local dev or in the Vercel dashboard for production. Redeploy after changing this value.

## Architecture

```
src/
├── app/                    # App Router pages and global CSS
├── components/
│   ├── playbook/           # Section layout (ReportForecast, ReactionAnalysis, …)
│   ├── reaction/           # ReactionWorkspace, candles, histogram
│   ├── PlaybookView.tsx    # Full playbook assembly
│   ├── PlaybookPageClient.tsx  # Stream hook + loading/error states
│   ├── RunPanel.tsx        # SSE trace viewer (always-dark surface)
│   ├── TickerInput.tsx     # Generate CTA
│   ├── DemoButton.tsx      # Instant demo
│   ├── ScenarioTree.tsx    # If/then scenario probabilities
│   ├── PeerSpilloverTable.tsx
│   ├── ExportToolbar.tsx   # JSON + bundle + print
│   ├── EarningsCalendarPreview.tsx
│   ├── ThemeProvider.tsx / ThemeToggle.tsx
│   └── …                   # Header, footer, badges, backend status
├── hooks/
│   └── usePlaybookStream.ts   # EventSource + REST fallback
└── lib/
    ├── api.ts              # Backend fetch helpers
    ├── types.ts            # Shared TS types mirroring backend schemas
    ├── export.ts           # Client-side download helpers
    ├── format.ts           # Numbers, dates, probabilities
    ├── theme.ts            # Chart palette by theme
    └── reactionChartTheme.ts
```

### SSE hook

`usePlaybookStream`:

- Loads initial job state via `fetchPlaybookJob`.
- Connects `EventSource` to `getPlaybookStreamUrl(jobId)`.
- Maps SSE `type` fields to trace events for `RunPanel`.
- On `playbook_ready`, fetches the completed playbook.
- Optionally loads full trace via `fetchTraceLog` for export.

Playbook live progress uses **SSE**, not WebSockets.

## Key components

| Area | Files |
|------|-------|
| Playbook viewer | `PlaybookView.tsx`, `playbook/PlaybookSection.tsx`, `playbook/ReportForecastSection.tsx`, `playbook/ReactionAnalysisSection.tsx` |
| Reaction workspace | `reaction/ReactionWorkspace.tsx`, `ReactionCandleChart.tsx`, `ReactionMoveHistogram.tsx`, `ReactionPathHero.tsx` |
| Agent trace | `RunPanel.tsx` |
| Theme | `ThemeProvider.tsx`, `ThemeToggle.tsx`, `lib/theme.ts` |
| Charts | [lightweight-charts](https://tradingview.github.io/lightweight-charts/) v5 |

Typography: system UI sans stack in `globals.css`; IBM Plex Mono via `next/font` for tickers and figures.

## Design system

Defined in `tailwind.config.ts` and `src/app/globals.css`:

| Token | Value | Use |
|-------|-------|-----|
| `max-w-page` | `85rem` (1360px) | Header, footer, home, calendar, playbook shell |
| `max-w-measure` | `42rem` | Long-form prose on marketing pages and disclaimers |
| `--up` / `--down` / `--caution` | CSS variables | Direction-only colour (beat/miss, charts, badges) |
| `glass-panel` / `glass-panel-strong` | Tailwind utilities | Frosted section cards |

**Layout rules:**

- Light stone paper (`#eef2fb`) or dark navy (`#0b0f16`) via `ThemeProvider`.
- Navy / white ink tokens; colour reserved for direction.
- Playbook pages use a wide data-workspace layout: section cards fill the page shell.
- Section titles stack above content until `xl`, then sit in a sticky left rail.
- Internal grids (odds strip, forecast cases, reaction stats) expand to the full content column.
- `RunPanel.tsx` is the **only** always-dark surface; charts follow the active theme.

## Tooling

| Tool | Config | Role |
|------|--------|------|
| oxlint | `.oxlintrc.json` | Primary linter (ESLint removed) |
| Knip | `knip.json` | Dead code and unused dependencies |
| TypeScript 7 | `tsconfig.json` | Strict typecheck |
| React Compiler | `babel-plugin-react-compiler`, `reactCompiler: true` in `next.config.ts` | Automatic memoization |
| Playwright | `playwright.config.ts`, `e2e/` | Browser E2E |
| Hegel | `tests/*.property.test.ts` | Property-based tests |
| React Doctor | `bun run doctor` | Advisory health scan on PRs |

Use **Bun** (`bun` / `bunx`) for installs and scripts — not npm or npx.

## Deployment

- **Vercel:** set Root Directory to `frontend`.
- Install: `npm exec bun@1.4.0 install --frozen-lockfile` (from `vercel.json`).
- Build runs on Node 24.x; do not enable the Bun Function runtime.
- Repo-root `vercel.json` / `package.json` exist as zero-config fallback if Root Directory is unset.

See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md).

## Testing

```bash
bun run test:property    # Hegel / Vitest
bun run test:e2e         # Playwright (6 scenarios in e2e/playbook.spec.ts)
bun run lint && bun run typecheck && bun run knip && bun run build
```

E2E starts the API with system `python -m uvicorn` (see `playwright.config.ts`) — ensure backend deps are available in CI.

## Docs

| Doc | Contents |
|-----|----------|
| [README.md](../README.md) | Monorepo overview, API, env vars, testing |
| [PROJECT_SPEC.md](../docs/PROJECT_SPEC.md) | Product spec and UX |
| [IMPLEMENTATION_PLAN.md](../docs/IMPLEMENTATION_PLAN.md) | §10 frontend flows and design system |
| [DEMO_SCRIPT.md](../docs/DEMO_SCRIPT.md) | 3-minute demo walkthrough |

`frontend/AGENTS.md` is Next.js-generated agent rules from `next dev` — not project memory. See root [AGENTS.md](../AGENTS.md) for workspace conventions.
