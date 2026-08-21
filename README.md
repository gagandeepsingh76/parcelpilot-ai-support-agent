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
```

### Frontend (Node 20+)

```bash
cd frontend
npm install
cp ../.env.example .env.local    # set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev                      # http://localhost:3000
```

## Environment variables

See `.env.example`. Never commit real secrets.

## Status / roadmap

- [x] Step 0 - scaffold
- [x] Step 1 - data ingestion (PDFs -> chunked corpus, XLSX -> SQLite)
- [x] Step 2 - document retrieval with source-authority ranking
- [ ] Step 3 - structured-data lookup + SLA/credit calculations
- [ ] Step 4 - action tools with confirmation gating
- [ ] Step 5 - access-control layer + cross-account denial tests
- [ ] Step 6 - agent orchestration + escalation policy
- [ ] Step 7 - chat UI with tool visibility
- [ ] Step 8 - proactive issue-detection dashboard
- [ ] Step 9 - trust hardening (citations, conflict flags)
- [ ] Step 10 - evaluation suite
- [ ] Step 11 - hosted deployment
- [ ] Step 12 - architecture/product notes
