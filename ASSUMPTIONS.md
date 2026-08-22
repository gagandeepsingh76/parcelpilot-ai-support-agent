# Assumptions

Running log of assumptions made while building. Each entry notes the step it
affected and can be revisited without hunting through commit messages.

| # | Assumption | Why | Affects |
|---|------------|-----|---------|
| 1 | The candidate data pack was **not available on disk** when the repo was scaffolded. The ingestion pipeline is built against the documented pack layout (filenames listed in `data_pack/README.md`) and will be validated against the real files as soon as they are dropped into `data_pack/`. | Assignment brief references a downloadable pack whose link was not included in the paste; blocking only Steps 1+, so scaffolding proceeded. | Step 1 onward |
| 2 | The raw data pack is kept out of git (public repo, proprietary assessment material). Graders/peers reproduce by dropping the pack into `data_pack/`. | Safety default; trivially reversible if the pack is meant to be public. | Repo hygiene |
| 3 | Authentication is mocked: customer sessions carry an `account_id`; internal sessions carry a role (`support_agent`, `ops`, `admin`). No real IdP. Enforced in the data/tool layer regardless. | Brief explicitly allows mocked auth. | Step 5 |
| 4 | "Now" for all time-based logic = snapshot timestamp declared in the workbook's README sheet, cached at ingestion. `SNAPSHOT_TIME_OVERRIDE` env var exists purely for tests. | Brief requirement; keeps every calculation deterministic. | Steps 3+ |
| 5 | Deployment target: backend on Render free tier, frontend on Vercel free tier. | Tech-choice constraints (free-tier hosting). | Step 11 |
| 6 | Git identity for this submission is `Gagandeep Singh <169297060+gagandeepsingh76@users.noreply.github.com>` (repo-local config). | Submission lives under the gagandeepsingh76 account. | All commits |
| 7 | Vector store: Chroma local persistence with its bundled ONNX MiniLM embedding function; hybrid keyword (BM25-style) scoring layered on top because policy/agreement text is dense with exact terms and numbers that dense retrieval alone misses. | Free, local, no embedding-API dependency or cost. | Step 2 |
| 8 | Historical ticket resolutions are excluded from the authoritative retrieval index and only ever surfaced as "similar past ticket - not verified" context. | Brief Problem 2 (trust) requirement. | Steps 2, 9 |
| 9 | Insights windows are fixed heuristics: volume spikes compare trailing 7 days vs the prior 7 (flag when >=2 tickets AND >2x prior); service-quality scans a 14-day window; SLA watchlist uses wall-clock minutes with a 120-minute near-breach margin. | Simple, explainable thresholds a reviewer can audit; all anchored to snapshot time. | Step 8 |
| 10 | Free-tier hosts have ephemeral disks, so deployment rebuilds SQLite + Chroma from source documents at every boot (`app/deploy_bootstrap.py`), falling back to the committed synthetic fixtures when `data_pack/` is empty. A persistent disk or volume mount would remove the ~40s cold-start cost. | Only free-tier hosting allowed; demo must work without proprietary files in git. | Step 11 |
| 11 | The agent speaks to whichever provider `LLM_PROVIDER` names: `anthropic` (assignment default) natively, or `gemini` via Google's OpenAI-compatible endpoint through a translation adapter. A Gemini key was the only credential available during development (free tier: 20 requests/day), so live verification used it; all judgment-dependent checks remain runnable offline via scripted clients. | Unblocks live testing without violating the Claude-first requirement; grader flips one env var. | Step 6, 10 |
