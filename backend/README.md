# EarningsPulse backend

FastAPI + LangGraph API for playbook generation, SSE streaming, earnings calendar, and PRISM observability.

## Quick start

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Layout

```
app/
├── main.py                 # FastAPI app, CORS, router registration
├── config.py               # pydantic-settings from .env
├── api/
│   ├── routes/
│   │   ├── health.py       # GET /health, GET /ready
│   │   ├── playbook.py     # generate, stream, export, fetch job
│   │   ├── demo.py         # POST /api/playbook/demo/{ticker}
│   │   ├── calendar.py     # GET /api/calendar
│   │   └── trace.py        # GET /api/trace/{job_id}
│   ├── deps.py             # FastAPI dependencies (settings, stores, services)
│   ├── errors.py           # Exception handlers
│   └── rate_limit.py       # 10 req/min per IP on generate
├── agents/
│   ├── orchestrator.py     # LangGraph StateGraph
│   ├── research.py         # Tavily + EDGAR + calendar
│   ├── forecast.py         # LLM sentiment forecast
│   ├── reaction.py         # Historical pattern analysis
│   ├── spillover.py        # Peer correlation map
│   ├── synthesis.py        # Final playbook assembly
│   ├── llm.py              # OpenAI / Google with heuristic fallback
│   ├── mappers.py          # Agent output → playbook sections
│   └── trace_utils.py      # Trace event helpers
├── services/
│   ├── playbook_runner.py  # Background job execution
│   ├── job_store.py        # In-process job + trace state
│   ├── sse_events.py       # Trace → SSE payload mapping
│   ├── trace_store.py      # Local JSON trace files + bundle export
│   ├── prism_client.py     # PRISM SDK + local stub mode
│   ├── demo_store.py       # Bundled demo/ JSON cache
│   ├── tavily_client.py    # Web research
│   ├── edgar_client.py     # SEC filings
│   ├── earnings_calendar.py# Finnhub + yfinance fallback
│   ├── yfinance_client.py  # Async yfinance wrapper
│   ├── price_data.py       # OHLCV around earnings dates
│   ├── reaction_analyzer.py# Archetype classification engine
│   ├── reaction_validation.py # Out-of-sample pattern stability
│   ├── monte_carlo.py      # Bootstrap reaction path simulation
│   ├── reaction_chart.py   # Chart workspace payload builder
│   ├── peer_map.py         # Sector taxonomy + correlation
│   └── company_names.py    # Ticker → company name lookup
├── models/
│   ├── playbook.py         # Playbook, JobStatus, request/response schemas
│   ├── agent_state.py      # LangGraph TypedDict state
│   ├── analysis.py         # Reaction events, Monte Carlo, validation
│   ├── data.py             # Calendar, OHLCV, research bundles
│   └── trace.py            # PRISM-compatible trace events
└── utils/
    ├── cache.py            # TTL in-memory cache
    └── confidence.py       # Confidence tier scoring
```

## Agent pipeline

LangGraph runs this graph for each `POST /api/playbook/generate` job:

```
gather_parallel (Research ∥ Reaction)
    → run_forecast
    → run_spillover
    → run_synthesis
    → Playbook
```

- **Research** pulls Tavily news, EDGAR filing links, and the next earnings date.
- **Reaction** fetches price history, classifies archetypes per past earnings, runs Monte Carlo bootstrap and chronological validation, and builds the reaction chart payload.
- **Forecast** calls the LLM (or heuristic) on the research bundle for beat/inline/miss probabilities and narratives.
- **Spillover** ranks peers by historical co-movement and enriches with relationship types.
- **Synthesis** merges all agent outputs, assigns confidence tiers, attaches sources, and produces the final `Playbook` model.

Trace events append to `JobStore` throughout; the SSE route streams them to clients.

## Key services

### Reaction intelligence

| Module | Role |
|--------|------|
| `reaction_analyzer.py` | Per-event dip/recovery metrics; aggregate archetype |
| `monte_carlo.py` | Bootstrap p10/p50/p90 move and dip bands from history |
| `reaction_validation.py` | Train/test split to flag overfit patterns |
| `reaction_chart.py` | Candles, path overlays, support/resistance for the frontend chart |

### Data clients

| Client | Fallback |
|--------|----------|
| Tavily | EDGAR + lower-confidence research |
| Finnhub calendar | yfinance earnings dates |
| OpenAI LLM | Google LLM → deterministic heuristic |
| PRISM | Local trace JSON only (`local_mode`) |

Yahoo Finance I/O runs in `asyncio.to_thread` to avoid blocking the event loop.

## Configuration

Settings load from repo-root `.env` via pydantic-settings. See [`.env.example`](../.env.example) and the [root README environment table](../README.md#environment-variables).

Notable defaults in `config.py`:

- `llm_provider`: `openai`
- `google_llm_model`: `gemini-2.5-flash` (with model fallback chain in `llm.py`)
- `reaction_history_limit`: 40
- `monte_carlo_simulations`: 1000
- `validation_train_ratio`: 0.7
- `prism_required`: false (set true for hackathon `/ready` gate)

## API summary

| Route | Handler |
|-------|---------|
| `POST /api/playbook/generate` | Creates job, schedules `PlaybookJobRunner.execute_job` |
| `GET /api/playbook/stream/{job_id}` | SSE from `JobStore.iter_traces` |
| `GET /api/playbook/{job_id}` | Job status + playbook when complete |
| `POST /api/playbook/demo/{ticker}` | Loads `demo/{ticker}.json` instantly |
| `GET /api/calendar` | Upcoming earnings (empty list if Finnhub not configured) |
| `GET /api/trace/{job_id}` | Assembled trace log for export / PRISM |

Full reference: [README.md § API](../README.md#api-reference).

## Testing

```bash
uv run python -m pytest              # all tests (use -m pytest, not bare pytest)
uv run ruff check app tests
uv run ruff format --check app tests
uv run ty check
uv run deptry .
```

Tests live in `tests/` — API routes, agents (mocked), reaction analyzer, Monte Carlo, validation, property tests with Hypothesis, and job/SSE lifecycle.

## Deployment

| Target | Entry |
|--------|-------|
| Docker | `backend/Dockerfile` — used by docker-compose and Railway/Render |
| Railway | Set root directory to `backend`; uses `railway.toml` |
| Render | `render.yaml` web service pointing at `backend/Dockerfile` |
| Modal | `modal_app.py` — `uv run modal deploy modal_app.py` |

See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) for env vars, CORS, and Modal secrets.

## Scripts (repo root)

| Script | Purpose |
|--------|---------|
| `scripts/seed_demo.py` | Generate or refresh `demo/aapl.json` |
| `scripts/backtest_reactions.py` | Print archetype labels for validation tickers |
| `scripts/verify_deployment.sh` | Health + Demo AAPL smoke test |
| `scripts/run_tests.sh` | Full monorepo test suite |

## Operational notes

- **Job storage** is in-process (`JobStore`). Restarts drop jobs and playbooks; export bundles before relying on a saved run.
- **Trace files** write to `logs/traces/` (or `/tmp/logs/traces` on Modal). They are audit logs, not playbook recovery.
- **Demo cache** ships at `demo/aapl.json` and is copied into Docker/Modal images.
- **Rate limit** on generate: 10 requests/minute/IP.

Further reading: [PROJECT_SPEC.md](../docs/PROJECT_SPEC.md), [IMPLEMENTATION_PLAN.md](../docs/IMPLEMENTATION_PLAN.md), [MAINTAINABILITY_REVIEW.md](../docs/MAINTAINABILITY_REVIEW.md).
