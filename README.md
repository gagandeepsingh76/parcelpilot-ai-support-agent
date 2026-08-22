# ParcelPilot AI Support Agent

AI support system for **ParcelPilot**, a B2B logistics platform. Built as two
scoped contexts over one backend:

1. **Customer-facing support agent** - answers questions about the customer's
   own orders, entitlements, contract terms and support SLAs; escalates to
   humans when confidence is low.
2. **Internal support/operations agent + insights dashboard** - helps
   authorised ParcelPilot staff investigate issues across accounts, take
   audited actions, and proactively see what deserves attention today.

## Key capabilities (mapping to assignment requirements)

| Req | Capability | Where |
|-----|------------|-------|
| 1 | Natural-language chatbot with escalation policy | `backend/app/agent/` |
| 2 | Access control enforced in data/tool layer | `backend/app/access.py`, SQL scoping |
| 3 | Tools: doc retrieval, structured lookup/calc, state-changing action | `backend/app/tools/` |
| 4 | Mandatory confirmation before state-changing actions | pending-action flow in agent |
| 5 | Multi-step requests across sources | agent orchestration loop |
| 6 | Chat UI showing tool use per turn | `frontend/` |
| P1 | Proactive issue-detection dashboard (internal) | `/insights` route |
| P2 | Trust: citations, conflict banners, source authority tiers | retrieval + UI |

## Repository layout

```
backend/          FastAPI app (agent, tools, ingestion, access control)
  app/            application code
  tests/          pytest suite
frontend/         Next.js chat UI + internal insights page
data_pack/        drop the candidate pack here (not committed)
docs/             architecture & product notes (Step 12)
```

## Setup

### Backend (Python 3.13)

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp ../.env.example .env          # then fill ANTHROPIC_API_KEY
# put the candidate data pack into ../data_pack/
python -m app.ingestion.run      # parse PDFs + load XLSX -> SQLite/vector store
uvicorn app.main:app --reload    # http://localhost:8000  (/docs for OpenAPI)
pytest                           # run test suite
python evals/run_evals.py        # 15 NL scenarios (offline, no API key needed)
python evals/run_evals.py --live # same suite against real Claude (needs key)
```

### Frontend (Node 20+)

```bash
cd frontend
npm install
cp ../.env.example .env.local    # set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev                      # http://localhost:3000
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - system diagram, layer
  responsibilities, design decisions with rationale.
- [`docs/PRODUCT.md`](docs/PRODUCT.md) - product framing, 3-minute demo
  script, deliberate limitations.
- [`docs/AI_TOOL_USAGE.md`](docs/AI_TOOL_USAGE.md) - declaration of how AI
  tools were used and what was verified by hand.
- [`ASSUMPTIONS.md`](ASSUMPTIONS.md) - running log of assumptions made while
  building.

## Authentication

Two login paths, both enforced through the same access-control layer:

1. **Username / password** (`POST /api/auth/login`) - real credential auth
   with PBKDF2-hashed passwords and HMAC-signed tokens. Seeded demo users:

   | Username    | Password   | Identity |
   |-------------|------------|----------|
   | northstar   | demo1234   | Customer, ACC-001 |
   | lumenworks  | demo1234   | Customer, ACC-002 |
   | brightcart  | demo1234   | Customer, ACC-003 |
   | agent       | staff1234  | Internal, support_agent |
   | ops         | staff1234  | Internal, ops |
   | admin       | staff1234  | Internal, admin |
   | viewer      | staff1234  | Internal, viewer (read-only) |

2. **One-click mock sessions** (kept for reviewers/tests) - identical RBAC
   identities via `POST /api/session/login`.

Customers can self-register against an existing account via
`POST /api/auth/register`; staff accounts are provisioned out-of-band.

## Environment variables

See `.env.example`. Never commit real secrets.

## Deployment (free tier) — LIVE

- **Frontend**: https://parcelpilot-frontend.vercel.app
- **Backend API**: https://parcelpilot-agent-api.onrender.com (health: `/health`, docs: `/docs`)
- **Backend -> Render**: created from `render.yaml` settings. Free-tier disks are
  ephemeral, so `app/deploy_bootstrap.py` re-ingests on boot - from
  `data_pack/` when the real pack is present, else from the committed
  synthetic fixtures.
- **Frontend -> Vercel**: project `parcelpilot-frontend`, root directory
  `frontend`, with `NEXT_PUBLIC_API_BASE_URL` pointing at the Render URL.
- Note: Render free instances sleep after ~15 min idle; first request may
  take ~50 s to cold-start and rebuild the index.

## Status / roadmap

- [x] Step 0 - scaffold
- [x] Step 1 - data ingestion (PDFs -> chunked corpus, XLSX -> SQLite)
- [x] Step 2 - document retrieval with source-authority ranking
- [x] Step 3 - structured-data lookup + SLA/credit calculations
- [x] Step 4 - action tools with confirmation gating
- [x] Step 5 - access-control layer + cross-account denial tests
- [x] Step 6 - agent orchestration + escalation policy
- [x] Step 7 - chat UI with tool visibility
- [x] Step 8 - proactive issue-detection dashboard
- [x] Step 9 - trust hardening (citations, conflict flags)
- [x] Step 10 - evaluation suite
- [x] Step 11 - hosted deployment
- [x] Step 12 - architecture/product notes
