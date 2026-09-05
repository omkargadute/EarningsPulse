# Maintainability review, 2026-09-05

Baseline: `bd596bc`, after the Modal deployment PR. Before the second batch, main gained commits `96358fc` and `b7ec16c` for provider selection, Modal secrets, PRISM SDK fallback, and demo trace syncing. The cleanup preserves those additions and tests both provider orders. The Modal and variance tasks were idle. The only outstanding local content was `.agents/skills/modal/`, which this review leaves untouched.

## Baseline and scope

Ruff lint/format, Deptry, ty, and 155 backend tests passed. Frontend lint, TypeScript, 11 property tests, Knip, and production build passed after installing the frozen dependencies. The direct `pytest` executable failed to import `app`; the repository's `uv run python -m pytest` command passed. The existing five browser tests subsequently passed against the first cleanup batch.

The backend emitted a pre-existing Google SDK deprecation warning. Browser tests emitted existing smooth-scroll and terminal-color warnings. No application source file exceeded 1,000 lines. The largest backend file was `reaction_analyzer.py`, 522 lines; frontend CSS was 643 lines and the largest TSX component was 331 lines. Lockfiles and cached demo JSON are data, not decomposition candidates.

The review traced generation, demo loading, status, SSE, export, trace persistence, provider fallback, graph dependencies, and frontend loading/error state. Automated size, reference, unused-code, and writing scans selected candidates; findings below follow complete call paths. This is a focused foundations review, not a correctness proof of the financial models.

## Ownership and request flow

1. `TickerInput` posts a ticker through `lib/api.ts`. The generation route validates and rate-limits it, creates a job, and schedules `PlaybookJobRunner` using FastAPI background tasks.
2. The runner owns job lifecycle. LangGraph runs research and reaction together, followed by forecast, spillover, and synthesis. Agents own provider fallback and domain outputs; services fetch and analyze source data.
3. `JobStore` owns in-process status and trace history. The SSE route formats trace records and terminal notifications. `usePlaybookStream` combines initial REST status with EventSource updates, then fetches the result. `PlaybookPageClient` fetches the export trace separately.
4. Demo loading creates a completed job from bundled JSON. JSON export serializes the playbook; bundle export adds the job trace. `TraceStore` saves local trace files; PRISM submits the assembled trace. Neither restores generated playbooks after restart.

## Prioritized findings

Line references below identify the baseline commit so later edits do not change the evidence.

| Priority and classification | Evidence | Maintenance cost and simpler structure | Behavior to retain |
|---|---|---|---|
| P1, confirmed defect, SHOULD FIX | `backend/app/api/routes/playbook.py:121`, `backend/app/services/job_store.py:23` | Replay and a shared consuming queue duplicate events and split live events between viewers. Use one trace history and an independent cursor per viewer; derive completion from committed status. | Existing REST routes, SSE field names, history on reconnect, heartbeat and terminal notifications. |
| P1, confirmed defect, SHOULD FIX | `backend/app/agents/research.py:80`, `backend/app/agents/trace_utils.py:83`, `backend/app/services/sse_events.py:52` | Six callers copy tool events before context exit, dropping completion and handled failures. Have the tracing context append directly to the agent trace. Tool failures must not terminate a successful fallback run. | Provider fallback, trace IDs and metadata, terminal `error` for failed jobs. |
| P1, confirmed defect, SHOULD FIX | `backend/app/services/earnings_calendar.py:134`, `backend/app/services/reaction_analyzer.py:95`, `backend/app/services/peer_map.py:223` | Synchronous Yahoo I/O runs inside async methods and blocks unrelated requests. Offload complete synchronous operations with `asyncio.to_thread`. | Request order, cache keys, fallback order, numerical calculations and exception handling. |
| P2, design improvement, SHOULD FIX | `backend/app/services/prism_client.py:70`, `backend/app/agents/llm.py:51` | PRISM buffers events it never reads; LLM invocation duplicates Google fallback branches. Delete the buffer and use an ordered provider loop. | PRISM submission payloads; Configured provider first; existing invalid-JSON heuristic policy and Google model retry policy. |

Baseline review score: 6.0/10, four SHOULD FIX findings, no separate cosmetic deductions. Both focused batches address these findings. The change review passes locally; final approval requires CI on the rebased commit.

## Contract boundaries and remaining concerns

REST request/response models, forecast calculations, demo data, React Compiler, themes, and layout remain unchanged. Intentional trace corrections expose previously missing tool outcomes and map recoverable `tool_call_failed` traces to SSE `tool_call`. Run failures still map to `error`.

Jobs remain unbounded and process-local. Shared durable jobs, retention, cancellation, and multi-container routing require a separate lifecycle design before scaling. Trace JSON writes are synchronous and not atomic; durable audit storage needs its own failure/recovery contract. The frontend still duplicates terminal result fetching and suppresses a failed fetch after `playbook_ready`, which can leave a completed run without a rendered result. These are follow-up concerns rather than reasons to change storage or frontend state architecture in this batch.

The Google SDK warning remains. Provider SDK migration and the financial meaning of Finnhub quarter-end dates need separate validation. Tests use controlled providers; browser generation tests simulate the SSE contract. They do not prove live provider availability or financial forecast accuracy. No variance agent was built in this task.
