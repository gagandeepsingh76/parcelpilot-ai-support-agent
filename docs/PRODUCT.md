# Product notes

## The problem

B2B logistics support is a trust product. Customers are businesses with signed
agreements that sometimes override the general policy; support staff need to
act across many such accounts without stepping on access boundaries; and
managers need to see today's problems before customers report them.

Generic chatbots fail here in three ways: they hallucinate fees, they leak one
customer's data to another, and they execute irreversible actions on a maybe.
This build treats those three failure modes as the design spec.

## Two scoped contexts, one system

**Customer-facing agent** - answers about *your own* orders, tickets, contract
terms, SLAs and credits. Cites documents and records for every claim. Cannot
see other accounts (enforced in code), cannot execute anything (only staff
can stage actions). Escalates to a human when unsure rather than guessing.

**Internal copilot + insights** - authorised staff investigate across all
accounts by explicit id, compute entitlements under each account's governing
terms, stage escalations/ticket updates/follow-ups behind an explicit
confirmation click, and pull historical precedent clearly marked as
unverified context. The insights dashboard proactively surfaces volume spikes,
SLA breaches, late pickups/deliveries, credit exposure and cross-customer
patterns.

## Demo script (~3 minutes)

1. **Clean entitlement answer.** Log in as *Customer - Northstar Logistics*.
   Ask: "Our order ORD-1001 arrived almost ten hours late - what compensation
   do we get?" → tool badge `data_lookup`, escalation badge (their agreement's
   clause needs a field missing from the dataset - honest "needs manual
   review" instead of an invented number).
2. **Fee explanation.** Switch to *Customer - BrightCart Commerce*. Ask:
   "Why was our order ORD-1006 charged a cancellation fee?" → $80, basis
   quoted from standard policy.
3. **Conflict handling.** As Northstar: "If pickup already started, what's the
   cancellation fee?" → conflict banner: agreement governs ($75 flat) over
   general policy; both citations shown, DEPRECATED never leaks in.
4. **Cross-account denial.** Back as Northstar: "What's the status of
   LumenWorks' order ORD-1026?" → clean refusal; no data fragments.
5. **Staff flow with confirmation gate.** Switch to *Internal - Support
   agent*. Ask to open a P1 escalation about the ORD-1001 delay → staged
   action card appears; press Confirm & apply → receipt with ticket id;
   pressing it again → 409 (already decided).
6. **Insights.** Open /insights as staff → SLA watchlist with overdue P2s,
   late pickup/delivery lists, $75 claimable exposure, Northstar
   manual-review flag.

## Deliberate limitations

- Auth is mocked (six fixed sessions) per the brief; enforcement logic is
  real and session-bound.
- SLA clocks use wall-clock minutes; business-hours calendars are future work
  (support-hours metadata is already captured per account).
- Free-tier deploys rebuild their index on boot; ~40s cold start.
- Credit amounts that depend on contract fields absent from the dataset are
  flagged for manual review instead of estimated.
