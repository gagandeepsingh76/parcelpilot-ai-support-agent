# Architecture

One FastAPI backend, one Next.js frontend, three storage engines (SQLite,
Chroma, nothing else). The guiding constraint: **the LLM is a reasoning
component, never an authority** - every fact, amount and side effect passes
through deterministic, access-controlled code.

```
┌──────────────────────────┐         ┌────────────────────────────────────┐
│ Next.js UI (Vercel)      │  HTTP   │ FastAPI (Render)                   │
│  /chat    tool badges    │────────>│  /api/session/login  mock auth     │
│           citations      │         │  /api/chat          agent turn     │
│           conflict banner│         │  /api/actions/{id}/confirm|cancel  │
│           confirm/cancel │         │  /api/insights/summary             │
│  /insights dashboard     │         └───────────────┬────────────────────┘
└──────────────────────────┘                         │
                                                     │
                              ┌──────────────────────▼─────────────────────┐
                              │ AgentOrchestrator (app/agent/)             │
                              │  Claude Messages API, native tool_use      │
                              │  max 6 rounds; LLM client injectable       │
                              └───────┬──────────────┬──────────────┬──────┘
                                      │              │              │
                       Tool 1         │   Tool 2     │   Tool 3     │
                 search_documents     │  data_lookup │  stage_action│
                                      ▼              ▼              ▼
                            ┌──────────────┐ ┌───────────┐ ┌──────────────┐
                            │ Chroma RAG   │ │ SQLite +  │ │ pending_     │
                            │ authority-   │ │ rules.py  │ │ actions table│
                            │ reranked     │ │ calc in   │ │ preview ONLY │
                            │ CURRENT-only │ │ python,   │ │ confirm via  │
                            │ by default   │ │ never LLM │ │ HTTP endpoint│
                            └──────────────┘ └───────────┘ └──────────────┘
                                      ▲              ▲
                                      └── app/access.py guards EVERY call ──┘
```

## Layer responsibilities

| Layer | Files | Responsibility |
|-------|-------|----------------|
| Ingestion | `app/ingestion/` | PDFs → sectioned corpus with metadata contract (`doc_type`, `version`, `status`, `customer_scope`); XLSX → SQLite. Rebuild-from-scratch, idempotent. |
| Retrieval | `app/rag/` | Chroma semantic search + authority rerank (`0.7*similarity + 0.3*tier`). Filters: CURRENT-only unless explicitly flagged; customers scoped to own agreement + global docs. |
| Rules & calc | `app/rules.py`, `app/tools/calculations.py` | Every fee/threshold/SLA as data with provenance. Per-account overrides from agreements. All math in Python, all "now" = dataset snapshot time. |
| Actions | `app/tools/actions.py` | Stage → preview → explicit confirm/cancel. `actions_log` audit trail. Runtime tables survive re-ingestion. |
| Access control | `app/access.py` | Caller model, role→action scopes, scoped wrappers around **every** read and action. Denials are raised in code, not requested politely of the model. |
| Orchestration | `app/agent/` | Tool schemas (exactly 3), separate customer/internal system prompts, structured `TurnResult`. |
| Insights | `app/insights/service.py` | Deterministic daily-brief: spikes, SLA watchlist, service quality, credit exposure, cross-customer patterns. No LLM involved. |
| API | `app/api/routes.py` | Thin HTTP shell over the above; 403/409 mapping. |

## Design decisions worth defending

1. **Confirmation lives outside the LLM loop.** The agent can only *stage*
   actions; applying requires a second HTTP call to `/api/actions/{id}/confirm`,
   which re-checks the original caller's session and role. A hallucinated
   "done!" cannot mutate state.

2. **Access control at the data layer.** Prompts ask the model to behave;
   `scoped_*` wrappers make disobedience impossible. Customers physically
   cannot read another account's rows or stage actions; viewers can read
   everything internal but stage nothing.

3. **Authority is a reranking signal, surfaced structurally.** A customer's
   signed agreement outranks general policy; CURRENT outranks DEPRECATED.
   Conflicts are returned as descriptors (`agreement_vs_general_policy`,
   `current_vs_deprecated`) that the UI renders as banners - the model is told
   which governs but the evidence is shown either way.

4. **Historical tickets are context-only by construction.** Ticket text is
   excluded from the vector index entirely. Precedent search exists only as an
   internal `data_lookup` variant whose rows arrive pre-stamped
   `verified=false`; prompts forbid quoting them.

5. **Deterministic time.** All SLA/latency/window logic uses the snapshot time
   declared in the workbook, overridable per-test. Insights and credits are
   reproducible bit-for-bit.

6. **Injectable LLM client.** `AgentOrchestrator` accepts any object with a
   `messages.create()` surface, so the whole orchestration path is tested
   offline with scripted responses; the eval suite runs without an API key.

## Data flow example (customer asks about a late order)

1. UI posts question + bearer token to `/api/chat`.
2. Registry resolves token → `Caller(kind=customer, account_id=ACC-001)`.
3. Claude calls `data_lookup(late_delivery_credit, ORD-1001)`.
4. Dispatcher routes through `scoped_get_order` (ownership check) then
   `late_delivery_credit` → rule lookup finds Northstar's clause needs a field
   absent from the dataset → `requires_manual_review=true`.
5. Orchestrator marks the turn escalated; reply cites the agreement section;
   UI shows the escalation badge.
