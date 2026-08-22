# Product Requirements Document

## ParcelPilot AI Support Agent

**Version:** 1.0  
**Status:** Development  
**Product Type:** AI-powered B2B Customer Support and Operations Platform

---

# 1. Product Overview

## 1.1 Product Vision

ParcelPilot AI Support Agent is an intelligent support and operations platform for a B2B logistics company.

The platform helps customers and authorised internal support teams answer complex questions involving:

- Customer account entitlements
- Customer-specific contract terms
- Shipment cancellations
- Cancellation fees
- Service credits
- Support SLAs
- Product issues
- Orders
- Support tickets
- Operational patterns

Unlike a simple chatbot, the product acts as a multi-step AI agent capable of deciding which data source or tool to use, retrieving relevant information, performing calculations, resolving conflicts between sources, and escalating issues when human judgment is required.

The system must prioritise **accuracy, trust, access control, and explainability** over simply generating an answer.

---

# 2. Problem Statement

ParcelPilot's customer operations team currently investigates support requests manually across multiple disconnected sources:

- Support policies
- Customer agreements
- SOPs
- Product documentation
- Known issues
- Historical support tickets
- Account data
- Order data
- Ticket data

This creates several problems:

1. Support resolution takes time because information is distributed across multiple sources.
2. Sources may conflict with each other.
3. Some policies are outdated or deprecated.
4. Customer-specific agreements may override general policies.
5. Historical ticket resolutions may contain incorrect guidance.
6. Customers must never access another customer's data.
7. Some issues require multiple investigation steps before an answer can be given.
8. Support teams currently react to issues instead of proactively identifying patterns.

The product must solve these problems through a reliable AI agent and supporting operations interface.

---

# 3. Target Users

## 3.1 Customer User

A customer using ParcelPilot who needs support related to their own account.

The customer can:

- Ask questions about their orders.
- Check cancellation eligibility.
- Understand cancellation fees.
- Ask about service credits.
- Check shipment or support information available to their account.
- Report product or operational issues.
- Request escalation.

The customer must only access data belonging to their own account.

---

## 3.2 Internal Support Agent

An authorised ParcelPilot customer support employee.

The internal agent can:

- Investigate customer issues.
- Search support policies and agreements.
- Look up accounts, orders, and tickets.
- Investigate SLA risks.
- Identify applicable policies.
- Compare agreements against general policies.
- Prepare escalations.
- Update support tickets.
- Create follow-up tasks.

Access should depend on the user's authorised role.

---

## 3.3 Operations User

An authorised internal operations or support manager.

The operations user can:

- Monitor recurring issues.
- Identify ticket spikes.
- Detect SLA risks.
- Identify unusual operational patterns.
- Investigate issues affecting multiple customers.
- Understand which problems require attention.

---

# 4. Product Goals

The product must demonstrate:

### Goal 1 — Reliable AI Support

Provide useful answers to natural-language questions using only the supplied ParcelPilot data sources.

### Goal 2 — Multi-Step Agent Reasoning

Allow the AI agent to combine multiple tools and information sources to resolve complex questions.

### Goal 3 — Trustworthy Answers

Treat different sources according to their authority, freshness, and reliability.

### Goal 4 — Data Privacy

Enforce account and role access controls in the application and tool layer.

### Goal 5 — Safe Actions

Require explicit user confirmation before any state-changing operation.

### Goal 6 — Proactive Operations

Help internal teams identify urgent, recurring, unusual, or high-risk issues before users manually investigate them.

### Goal 7 — Production-Quality Experience

Provide a polished, interactive, modern interface that makes the AI system understandable and easy to use.

---

# 5. Non-Goals

The first version will intentionally not attempt to:

- Replace human support agents completely.
- Automatically execute irreversible actions without confirmation.
- Invent information outside the supplied data pack.
- Provide unsupported business exceptions.
- Allow customers to access data from other accounts.
- Treat all retrieved documents as equally authoritative.
- Automatically make subjective business decisions that require human judgment.

When confidence is insufficient or human judgment is required, the system should escalate appropriately.

---

# 6. Core User Experience

The application will support two primary workspaces.

## 6.1 Customer Support Workspace

A customer-facing AI chat interface.

The user can ask questions such as:

> Can I cancel ORD-1001 without a cancellation fee?

The agent may perform the following internally:

1. Identify the order.
2. Identify the associated account.
3. Confirm that the logged-in customer is authorised to access that order.
4. Retrieve the customer's agreement.
5. Retrieve the current support policy or cancellation SOP.
6. Compare the applicable rules.
7. Perform any required calculation.
8. Generate an answer with supporting sources.
9. Escalate if the system cannot answer confidently.

---

## 6.2 Internal Operations Workspace

An internal interface for authorised ParcelPilot users.

It includes:

- AI Support Agent
- Operational Insights
- SLA Risk Monitoring
- Recurring Issue Detection
- Ticket Investigation
- Account and Order Investigation
- Action Management

---

# 7. Core Functional Requirements

## 7.1 AI Chat

The platform must provide a conversational interface where users can ask natural-language questions.

The agent should:

- Understand the user's request.
- Determine whether tools are required.
- Select the appropriate tools.
- Perform multiple steps where necessary.
- Return a clear answer.
- Explain the reasoning at a useful level.
- Show relevant source references.
- Escalate when the answer is uncertain or outside system capability.

The chatbot must use the supplied ParcelPilot data as its information base.

---

## 7.2 Agent Tool System

The agent must have at least three categories of tools.

### Tool A — Document Retrieval

Search:

- Current support policy
- Deprecated support policy
- Cancellation and service credit SOP
- Product operations guide
- Known issues
- Customer agreements

The retrieval system should return relevant passages together with source metadata.

---

### Tool B — Structured Data

Query and calculate information from:

- Accounts
- Orders
- Tickets

Supported operations may include:

- Order lookup
- Account lookup
- Ticket lookup
- SLA calculation
- Cancellation fee calculation
- Service credit calculation
- Time-based calculations

The workbook snapshot time must be used as the reference for time-based questions.

---

### Tool C — State-Changing Actions

The system should support:

- Creating an escalation.
- Updating a ticket.
- Creating a follow-up task.

Actions may be mocked locally but must behave as actual state changes within the application.

---

# 8. Action Confirmation Flow

No state-changing action may execute immediately after the user requests it.

The required workflow is:

### Step 1 — User Requests Action

Example:

> Escalate this issue.

### Step 2 — Agent Investigates

The agent gathers the required information and prepares the action.

### Step 3 — Action Preview

The UI displays:

- Action type
- Target ticket/order/account
- Reason
- Relevant details
- Expected result

### Step 4 — Explicit Confirmation

The user must explicitly select:

- Confirm
- Cancel

### Step 5 — Execute

Only after confirmation should the state-changing tool execute.

The action workflow should follow a clear **Prepare → Preview → Confirm → Execute** pattern.

---

# 9. Access Control and Privacy

Access control must be enforced below the LLM layer.

## Customer Context

A customer:

- Can only retrieve their own account.
- Can only retrieve their own orders.
- Can only retrieve their own tickets.
- Cannot access another customer's structured data.

## Internal Context

Internal users should have role-based access.

Example roles:

- Support Agent
- Operations Manager
- Administrator

The system must not rely solely on prompts such as:

> Do not show unauthorised information.

The actual data and tool layer must enforce access restrictions.

---

# 10. Source Authority and Reliability

The AI system must explicitly understand that sources have different levels of authority.

Recommended authority hierarchy:

### Priority 1 — Customer-Specific Agreement

A customer agreement can override general policies for that specific customer.

### Priority 2 — Current Support Policy

The latest current policy is authoritative when no customer-specific agreement overrides it.

### Priority 3 — Current SOP

Operational procedures and service-credit rules.

### Priority 4 — Product Documentation

Useful for product behavior and known issues.

### Priority 5 — Deprecated Policies

Deprecated documents should not be used as the primary basis for current decisions.

They may be surfaced for historical context with a clear warning.

### Priority 6 — Historical Ticket Resolutions

Historical resolutions are context only.

They must not override authoritative policies or agreements.

---

# 11. Conflict Detection

When sources disagree, the agent should not silently choose one.

The system should:

1. Detect the conflict.
2. Identify the competing sources.
3. Compare source authority.
4. Select the authoritative source when the hierarchy makes the answer clear.
5. Explain the decision.
6. Escalate if the conflict cannot be safely resolved.

Example:

> The current general policy states X. However, Northstar's enterprise agreement contains a customer-specific exception, so the agreement takes precedence.

The UI should visually indicate when:

- A source conflict exists.
- A deprecated source was retrieved.
- A customer-specific agreement overrides a general rule.
- Human review is recommended.

This directly addresses the assessment's trust and reliability concern.

---

# 12. Multi-Step Agent Workflow

The agent must support complex requests requiring multiple tools.

Example workflow:

**User Question**

> Can Northstar cancel ORD-1001 without a cancellation fee?

**Possible Agent Workflow**

1. Structured data tool → Find ORD-1001.
2. Access control → Confirm authorised account access.
3. Structured data tool → Identify Northstar account.
4. Document retrieval → Retrieve Northstar enterprise agreement.
5. Document retrieval → Retrieve current cancellation policy/SOP.
6. Authority engine → Determine which source takes precedence.
7. Calculation tool → Determine any applicable fee.
8. Agent → Generate explanation.
9. Action tool → Prepare escalation if necessary.

The agent should visibly communicate useful tool activity to the user without exposing unnecessary internal chain-of-thought.

Example:

- Searching order data
- Checking customer agreement
- Reviewing current cancellation policy
- Calculating cancellation eligibility

The assessment specifically expects multi-tool, multi-source workflows rather than a simple single-step chatbot.

---

# 13. Proactive Issue Detection

The product will address the additional client problem of proactive issue detection.

The internal Insights workspace should identify:

## 13.1 Ticket Spikes

Detect sudden increases in similar support issues.

Example:

> Pickup delay complaints increased significantly compared with the previous period.

---

## 13.2 SLA Risk

Identify:

- Tickets approaching SLA deadlines.
- Tickets exceeding SLA.
- High-severity unresolved tickets.

---

## 13.3 Recurring Product Issues

Cluster or group similar problems.

Example:

> Multiple customers are reporting the same tracking synchronization issue.

---

## 13.4 Cross-Customer Issues

Identify issues affecting multiple accounts simultaneously.

---

## 13.5 Operational Anomalies

Detect unusual patterns involving:

- Orders
- Delays
- Cancellations
- Support activity

These capabilities align with the proactive issue detection problem described in the assessment.

---

# 14. User Interface Requirements

## 14.1 Design Philosophy

The interface should feel like a modern, premium AI operations product.

The visual direction should be:

- Clean
- Confident
- Minimal
- Highly polished
- Professional
- Technical
- Calm
- Trustworthy

The interface should not feel:

- Overly colorful
- Like a generic dashboard template
- Like a student project
- Cluttered
- Heavy with unnecessary cards

---

# 15. Theme System

The application must support:

- Light mode
- Dark mode
- System preference detection
- Persistent theme selection

Theme transitions should be smooth.

Dark mode should feel intentionally designed, not simply invert the colors.

---

# 16. Visual Language

Use a restrained design system with a strong neutral foundation.

Recommended direction:

### Base

- Neutral background
- High-quality typography
- Strong contrast
- Clear visual hierarchy

### Accent

Use one primary accent family throughout the application.

Possible direction:

- Deep indigo / electric blue
- Slate / graphite base
- Controlled cyan or violet highlights

Avoid multiple unrelated accent colors.

Status colors should be reserved for:

- Success
- Warning
- Risk
- Error

---

# 17. Animation and Interaction

Animations should improve understanding rather than exist only for decoration.

Include:

### Page Transitions

Subtle entrance transitions when changing major views.

### Chat

- Smooth message appearance
- Typing/loading states
- Tool execution progress
- Streaming response effect where supported

### Tool Activity

When the agent uses a tool, display an animated status element.

Example:

> Searching documents...

Then:

> Checking customer agreement...

Then:

> Calculating service credit...

Completed tools should collapse into a clean summary that users can expand.

### Cards and Lists

- Subtle hover elevation
- Small motion on interaction
- Smooth loading skeletons
- Animated state changes

### Insights

Charts and insight cards should animate into view subtly.

All motion should remain fast and restrained.

---

# 18. Main Application Screens

## Screen 1 — Authentication

Purpose:

Allow users to enter the correct product context.

Features:

- Customer login/demo account
- Internal support login/demo account
- Clear role/context indication

The screen should be visually polished but simple.

---

## Screen 2 — AI Support Chat

Main layout:

### Left Sidebar

- ParcelPilot branding
- Navigation
- User role/context
- New conversation
- Theme toggle
- User profile/logout

### Main Area

- Conversation header
- Context indicator
- Chat messages
- Tool activity
- Source references
- Action confirmation cards
- Message input

### Optional Right Context Panel

For relevant queries, display:

- Account
- Order
- Ticket
- Retrieved sources
- Reliability indicators

The right panel should appear contextually rather than permanently occupying space.

---

## Screen 3 — Internal Insights

A modern operations dashboard containing:

### Summary Metrics

- Open tickets
- SLA at risk
- High severity
- Recurring issues

### Insight Feed

Prioritised cards explaining:

- What happened
- Why it matters
- Which customers are affected
- Recommended next step

### Investigation Entry Points

Each insight should allow the user to:

- Investigate with AI
- View related tickets
- Create follow-up
- Escalate

---

## Screen 4 — Action Confirmation

State-changing actions should use a focused confirmation experience.

Example:

### Create Escalation

**Issue:** Pickup delay for ORD-1001

**Reason:** Carrier fault with SLA risk

**Action:** Create escalation for operations team

Buttons:

Cancel | Confirm Escalation

The confirmation UI should make it impossible for the user to accidentally misunderstand what will happen.

---

# 19. AI Response Experience

AI responses should be structured for clarity.

Recommended answer format:

### Direct Answer

A concise response first.

### Why

A short explanation.

### Evidence

Relevant source references.

### Important Context

Warnings about:

- Agreement overrides
- Deprecated policies
- Conflicting information
- Uncertainty

### Next Step

If appropriate:

- Escalate issue
- Create follow-up
- Investigate further

The system should never expose hidden chain-of-thought.

Instead, it should expose concise tool activity and evidence.

---

# 20. Technical Product Architecture

## Frontend

The frontend is responsible for:

- Authentication UI
- Role-aware navigation
- Chat experience
- Tool activity visualisation
- Insights dashboard
- Theme system
- Action confirmation
- Responsive design

Recommended existing direction:

- Next.js
- TypeScript
- Tailwind CSS
- Modern component architecture
- Motion library for restrained animation

---

## Backend

The backend is responsible for:

- Authentication and user context
- Access control
- AI agent orchestration
- Tool execution
- RAG/retrieval
- Structured data access
- Deterministic calculations
- Action staging and confirmation
- Insights generation

Recommended existing direction:

- FastAPI
- Python
- Modular service architecture

---

## AI Agent

The AI agent should:

1. Receive the user request and context.
2. Determine whether tools are needed.
3. Select one or more tools.
4. Execute tools within access restrictions.
5. Evaluate retrieved information.
6. Apply source authority rules.
7. Perform calculations where required.
8. Determine confidence and escalation needs.
9. Generate the final response.

The agent should support multiple tool rounds when required.

---

# 21. Existing Development Direction

The existing ParcelPilot implementation should be preserved and improved rather than replaced.

The current architecture already includes the major functional areas required for the assessment:

- Authentication
- Access control
- Agent orchestration
- Tool specifications
- Structured data tools
- Calculation tools
- Action tools
- Document retrieval
- Authority handling
- Proactive insights
- Frontend chat
- Internal insights interface
- Deployment configuration
- Automated tests

The next development phase should focus primarily on:

1. Improving the frontend experience.
2. Making the agent workflow visually understandable.
3. Strengthening end-to-end integration.
4. Verifying all assessment scenarios against the supplied data.
5. Improving the presentation and demo quality.

The goal is refinement, not unnecessary architectural rewrites.

---

# 22. Success Criteria

The application will be considered ready when the following scenarios work reliably.

## Scenario 1 — Customer Cancellation Question

A customer asks about an order.

The system:

- Verifies account access.
- Finds the order.
- Retrieves the applicable agreement.
- Retrieves current policy/SOP.
- Applies source precedence.
- Calculates the answer.
- Explains the result.

---

## Scenario 2 — Unauthorised Access Attempt

A customer attempts to access another customer's order.

The data layer blocks access.

The AI must not receive or expose the unauthorised information.

---

## Scenario 3 — Service Credit

A user reports a late pickup caused by carrier fault.

The system:

- Retrieves order information.
- Determines delay duration.
- Checks applicable agreement and policy.
- Calculates service credit eligibility.
- Explains the result.

---

## Scenario 4 — Escalation

A user requests escalation.

The system:

- Investigates the issue.
- Prepares the escalation.
- Shows a preview.
- Waits for explicit confirmation.
- Executes only after confirmation.

---

## Scenario 5 — Source Conflict

A deprecated policy conflicts with a current policy or customer agreement.

The system:

- Detects the conflict.
- Applies authority ranking.
- Explains which source was used and why.

---

## Scenario 6 — Proactive Insight

An internal user opens the Insights dashboard.

The system highlights:

- SLA risks
- Ticket spikes
- Recurring issues
- Cross-customer operational patterns

The user can investigate an insight through the AI agent.

---

# 23. Future Roadmap

If development continued beyond the assessment, priorities would be:

## Priority 1 — Production Data Integrations

Connect to real:

- CRM systems
- Ticketing systems
- Shipment/carrier APIs
- Customer databases

## Priority 2 — Monitoring and Evaluation

Add:

- Agent quality evaluation
- Tool success rates
- Hallucination monitoring
- Access control monitoring
- Escalation accuracy
- Retrieval quality metrics

## Priority 3 — Human Feedback Loop

Allow support agents to:

- Approve answers
- Correct answers
- Flag incorrect guidance
- Improve knowledge sources

## Priority 4 — Advanced Proactive Detection

Introduce stronger anomaly detection and issue clustering.

## Priority 5 — Analytics

Track:

- Resolution time
- Escalation rate
- AI answer acceptance
- Tool usage
- Repeated issues

---

# 24. Primary Product Metric

The primary metric for measuring usefulness will be:

## Reliable Resolution Rate

**Percentage of support requests that are resolved correctly without requiring unnecessary human escalation.**

This should be measured alongside:

- Incorrect answer rate
- Escalation precision
- Average resolution time
- User feedback
- Access control failures

Reliability is more important than simply maximising automation.

---

# 25. Submission Checklist

Before submission, ensure:

- [ ] Public GitHub repository is available.
- [ ] README contains setup and run instructions.
- [ ] Hosted frontend is working.
- [ ] Hosted backend is working.
- [ ] End-to-end chat is tested.
- [ ] Access control is tested.
- [ ] Multi-step requests are tested.
- [ ] Document retrieval is tested.
- [ ] Structured data calculations are tested.
- [ ] Action confirmation is tested.
- [ ] Proactive insights are working.
- [ ] Architecture note is included.
- [ ] Product note is included.
- [ ] AI tool usage is documented.
- [ ] Approximately 5-minute demo video is recorded.
- [ ] The project is tested against scenarios beyond the example IDs.

---

# 26. Final Product Principle

ParcelPilot AI Support Agent should not feel like a chatbot placed on top of a dataset.

It should feel like a **reliable AI operations system**.

Every major product decision should reinforce four principles:

**Understand the request.**

**Use the right tools and data.**

**Respect authority and access boundaries.**

**Act safely and transparently.**