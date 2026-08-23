# Product Note

## The Additional Client Problem Chosen

We have selected **Proactive Issue Detection** as the additional client problem. 

In B2B logistics, customers relying on support to inform them of delayed shipments or missed SLAs often results in breached contracts and damaged relationships. 

We addressed this by building **Model Insights**, an internal dashboard (`/insights`) accessible only to authorized staff. This dashboard bypasses the chat UI to deterministically analyze the entire operational database, surfacing real-time risks before customers even reach out.

## Why This Problem Matters

Relying purely on a reactive chatbot—no matter how accurate—forces the customer to discover the problem first. In enterprise logistics, missed SLAs trigger service credits and financial penalties. Proactive detection allows operations teams to:
- Identify and expedite shipments nearing their SLA boundary.
- Recognize systemic issues (e.g., a regional warehouse delay affecting multiple accounts) rather than treating each ticket in isolation.
- Forecast financial exposure from claimable service credits.

## Current Product Capabilities

- **SLA Risk Monitoring**: Automatically flags open tickets that are nearing or have breached their resolution SLA.
- **Systemic Cluster Detection**: Identifies cross-account patterns where multiple customers report issues with matching keywords (e.g., "damaged packaging", "late pickup").
- **Service Quality Metrics**: Tracks rolling windows of late pickups and late deliveries across all active shipments.
- **Credit Exposure Calculation**: Aggregates the total USD amount of service credits currently eligible to be claimed, providing a financial risk snapshot.
- **Secure Internal View**: Ensures these insights are strictly gated behind staff credentials, preventing cross-tenant leakage.

## What I Would Build Next

| Priority | Improvement | Why It Matters |
|---|---|---|
| P0 | Alerting Integrations | Push anomalies and SLA risks directly into Slack or PagerDuty to ensure immediate operational response. |
| P1 | Enhanced Anomaly Thresholds | Allow staff to dynamically configure what constitutes an "anomaly" (e.g., volume spikes > 2x the rolling average). |
| P1 | Feedback Learning Loop | Allow staff to tag insights as "helpful" or "noise" to tune the clustering algorithms. |
| P2 | Predictive SLA Risk | Train a small regression model to predict the *likelihood* of an SLA breach based on historical ticket resolution times. |

## What Was Intentionally Left Out

- **Real-time Event Streaming**: The current dashboard relies on a time-anchored dataset snapshot and requires manual refreshes. Implementing Kafka or webhooks for real-time updates was omitted to keep the deployment simple and testable for the assessment.
- **LLM-driven Insight Generation**: We intentionally chose deterministic SQL aggregation over asking the LLM to summarize the entire database. This avoids token limits, hallucinations in arithmetic, and massive API costs.

## Success Metric

**Primary Metric:** "Reduction in average time-to-resolution (TTR) for high-priority tickets, driven by proactive intervention before the customer escalates."

This metric measures the actual business impact of the proactive dashboard, proving that the support team is solving issues earlier in the lifecycle.
