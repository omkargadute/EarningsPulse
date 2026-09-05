# EarningsPulse documentation

Index of project documentation. Start with the [root README](../README.md) for setup, API, and testing.

## Product and planning

| Document | Description |
|----------|-------------|
| [PROJECT_SPEC.md](./PROJECT_SPEC.md) | Product definition, agent architecture, hackathon alignment, branding |
| [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) | 10-phase build plan, tech decisions, checklists (all phases complete) |

## Operations

| Document | Description |
|----------|-------------|
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Vercel, Railway, Render, Modal, Docker — env vars and verification |
| [DEMO_SCRIPT.md](./DEMO_SCRIPT.md) | 3-minute hackathon pitch with fallback plans |

## Engineering

| Document | Description |
|----------|-------------|
| [MAINTAINABILITY_REVIEW.md](./MAINTAINABILITY_REVIEW.md) | Baseline review (2026-09-05): SSE, trace, async I/O findings |
| [backend/README.md](../backend/README.md) | Backend modules, agents, services, deployment entry points |
| [frontend/README.md](../frontend/README.md) | Routes, components, design system, frontend tooling |

## Agent / workspace memory

| Document | Description |
|----------|-------------|
| [AGENTS.md](../AGENTS.md) | Cursor agent memory and monorepo conventions |

## Related files

| File | Description |
|------|-------------|
| [`.env.example`](../.env.example) | All environment variables with comments |
| [`scripts/verify_deployment.sh`](../scripts/verify_deployment.sh) | Post-deploy smoke test |
| [`scripts/run_tests.sh`](../scripts/run_tests.sh) | Full local CI equivalent |
