# AI tool usage

Declaration of how AI coding tools were used to produce this submission, and
how their output was verified.

## What AI tools did

- **Scaffolding and boilerplate.** FastAPI app skeleton, pydantic-settings
  config, Next.js app-router files, pytest fixtures, CI-shaped test wrappers.
- **First drafts of well-patterned code.** SQLite schema DDL, ingestion loops,
  Chroma query plumbing, React client state, CSS.
- **Test generation at volume.** Most of the 84 tests started as AI-drafted
  cases based on a human-supplied list of behaviours that must hold
  (denials, gating, authority ordering, snapshot-time math).
- **Docs and commit drafting.** First passes of README/ASSUMPTIONS text and
  conventional-commit messages, edited by hand afterwards.

## What the human decided

- Product/architecture shape: tool-layer access control, stage-then-confirm
  gate outside the LLM loop, rebuild-not-migrate ingestion, authority as a
  reranking signal rather than a hard filter.
- Extraction of business rules from the source PDFs into `app/rules.py` -
  every threshold, fee and clause mapping was read and transcribed from the
  documents, not generated.
- The synthetic fixture pack: designed so the brief's two example scenarios
  could be tested on *different* records, proving no example-hardcoding.
- Every design trade-off recorded in ASSUMPTIONS.md and commit messages.

## Verification practices

- No AI-generated code landed unverified: 84 backend tests plus a 15-case NL
  evaluation suite must pass; frontend must compile in production mode.
- Security-relevant behaviour (cross-account reads, role scopes, confirmation
  replay) is asserted by dedicated tests written to fail first.
- Live smoke tests ran real servers and HTTP calls against them (login, chat
  503 path, confirm/cancel receipts, insights payload) before each step was
  committed.
- Where AI output conflicted with observed behaviour (e.g. a stale server
  masking new code, or fixture rows dated after snapshot time), the bug was
  chased to ground rather than papered over.

## Honesty notes

- Without an Anthropic API key configured during development, live model
  behaviour was exercised through the scripted-client harness and the eval
  suite's offline mode; `python evals/run_evals.py --live` is provided for
  key-holders to verify judgment-dependent expectations.
- AI tools were used as accelerators under review - they are not the author
  of the architectural decisions, and all third-party claims (library APIs)
  were checked against installed versions.
