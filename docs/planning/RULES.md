# ParcelPilot AI Support Agent — Development Rules

**Version:** 1.0  
**Status:** Active  
**Purpose:** Development, AI coding, architecture, UI/UX, security, and quality guardrails.

---

# 1. Purpose of This Document

This document defines the mandatory rules for developing and modifying the ParcelPilot AI Support Agent.

These rules apply to:

- Human developers
- AI coding agents
- Vibe coding workflows
- Refactoring tasks
- Frontend development
- Backend development
- AI agent development
- Testing
- Deployment

The purpose is to ensure that future development:

1. Does not break existing functionality.
2. Remains within the assignment requirements.
3. Preserves the existing working architecture.
4. Improves the user experience without adding unnecessary complexity.
5. Keeps AI behavior controlled and reliable.
6. Produces a polished, interactive, production-quality application.

---

# 2. Core Development Principle

Every change must follow this priority order:

```text
1. Assignment Requirements
        ↓
2. Security and Access Control
        ↓
3. Correctness and Reliability
        ↓
4. Existing Working Architecture
        ↓
5. User Experience
        ↓
6. Visual Polish
        ↓
7. Additional Features
```

A visually impressive feature must never break:

- Access control
- Tool safety
- Source authority
- State-changing action confirmation
- Existing API contracts
- Existing tests

---

# 3. Preserve Before Replacing

## Mandatory Rule

Before modifying an existing component:

1. Inspect the existing implementation.
2. Understand its dependencies.
3. Identify its public interface.
4. Preserve working behavior.
5. Make the smallest necessary change.

Do not rewrite a working backend module simply because a different implementation looks cleaner.

### Avoid

```text
Delete existing agent → Build completely new agent
```

### Prefer

```text
Inspect existing agent
        ↓
Identify limitation
        ↓
Add missing capability
        ↓
Preserve existing behavior
        ↓
Test regression
```

---

# 4. Assignment Boundary Rules

The project must remain focused on the ParcelPilot assessment.

Every feature must answer at least one of these questions:

- Does this satisfy a required assessment feature?
- Does this improve reliability?
- Does this improve security?
- Does this improve usability?
- Does this improve demonstration quality?
- Does this strengthen the additional proactive issue detection feature?

If the answer is no, the feature should generally not be added.

---

# 5. Do Not Overengineer

Do not introduce enterprise-scale infrastructure unless it solves a real requirement.

Avoid unnecessary additions such as:

- Kubernetes
- Microservices
- Kafka
- Redis clusters
- Complex event buses
- Multiple databases
- Unnecessary authentication providers
- Complex workflow engines

The project should demonstrate strong engineering judgment, not maximum infrastructure complexity.

Prefer:

```text
Simple
↓
Modular
↓
Testable
↓
Secure
↓
Deployable
```

---

# 6. Existing Technology Stack

The existing architecture should remain the primary technical direction.

## Frontend

Use:

- Next.js
- React
- TypeScript
- Tailwind CSS

Do not replace the frontend framework unnecessarily.

## Backend

Use:

- Python
- FastAPI
- Pydantic

Do not replace the backend framework unnecessarily.

## AI Agent

Preserve the controlled agent architecture built around:

- Agent orchestrator
- Tool specifications
- Controlled tool execution
- Multi-step tool calls

The AI agent must not be converted into a simple:

```text
User → LLM → Response
```

system.

## Retrieval

Preserve the RAG architecture using:

- Document ingestion
- Chunking
- Metadata
- Embeddings
- ChromaDB
- Authority evaluation

## Structured Data

Preserve the existing structured data approach for:

- Accounts
- Orders
- Tickets

Use deterministic functions for business calculations.

---

# 7. Dependency Rules

Before adding a dependency, check:

1. Is the dependency already installed?
2. Can the feature be built using the existing stack?
3. Is the dependency actively maintained?
4. Does it significantly increase bundle size?
5. Does it introduce security or deployment complexity?
6. Is it actually necessary?

Do not install a library for a feature that can be implemented cleanly with existing tools.

---

# 8. Recommended Frontend Libraries

## UI Components

Prefer the existing UI component approach.

If additional primitives are required, use a consistent component system rather than mixing unrelated UI libraries.

Avoid combining multiple design systems.

Example to avoid:

```text
shadcn/ui
+
Material UI
+
Ant Design
+
Chakra UI
```

Use one consistent component foundation.

## Animation

A motion library such as Framer Motion is allowed for:

- Page transitions
- Component entrance
- Chat message appearance
- Tool activity
- Hover states
- Modal transitions
- Insight card transitions

Animation must improve clarity.

Do not animate every element.

## Icons

Use one icon system consistently.

Recommended:

- Lucide React

Do not mix multiple icon libraries without a clear reason.

## Charts

If charts are needed for the Insights dashboard, use one lightweight chart library consistently.

Possible choice:

- Recharts

Use charts only when they communicate operational information more clearly than text.

---

# 9. Forbidden Frontend Patterns

Avoid:

- Random inline styles
- Hardcoded colors throughout components
- Large monolithic components
- Duplicate API logic
- Multiple conflicting theme systems
- Excessive gradients
- Excessive glassmorphism
- Rainbow color schemes
- Overuse of shadows
- Auto-playing distracting animations
- Unnecessary carousels
- Fake loading delays
- Fake data when real API data exists

---

# 10. Design System Rules

The application must use a consistent design system.

Define reusable design tokens for:

- Background
- Surface
- Foreground
- Muted Text
- Border
- Primary Accent
- Success
- Warning
- Error

Avoid hardcoding arbitrary colors in individual components.

Prefer semantic usage:

```text
bg-background
text-foreground
border-border
bg-primary
text-muted-foreground
```

---

# 11. Color Rules

The visual design should be premium and restrained.

Use:

```text
Neutral foundation
+
One primary accent family
+
Reserved semantic status colors
```

Do not use color only for decoration.

### Primary Accent

Use consistently for:

- Primary actions
- Active navigation
- Focus states
- Important interactive elements

### Semantic Colors

Reserve for:

- Green → success/completed
- Amber → warning/attention
- Red → error/high risk
- Blue/primary → interactive/information

Do not introduce multiple competing accent colors.

---

# 12. Dark and Light Mode Rules

The application must support:

- Light mode
- Dark mode
- System preference

Theme selection must persist.

Dark mode must be intentionally designed.

Do not simply invert:

```text
White → Black
Black → White
```

Each theme must maintain:

- Readability
- Contrast
- Hierarchy
- Accessible states

Theme changes should use subtle transitions.

---

# 13. Animation Rules

Animation should communicate:

- Progress
- State changes
- Hierarchy
- Navigation
- System activity

Good example:

```text
Message appears
↓
Tool starts
↓
Progress updates
↓
Tool completes
↓
Answer appears
```

Avoid:

- Constant movement
- Infinite decorative animations
- Long page transitions
- Bouncing cards
- Excessive parallax
- Animation that delays interaction

Prefer fast and subtle motion.

Do not make users wait for animations before interacting.

Respect reduced-motion preferences where possible.

---

# 14. User Engagement Rules

The goal is to create an interface that users want to explore.

Engagement must come from:

- Useful interactions
- Clear feedback
- Progressive disclosure
- Good information hierarchy
- Smooth workflows
- Meaningful insights

Do not use:

- Artificial notifications
- Fake activity
- Fake alerts
- Unnecessary gamification
- Constant popups

The product should be interesting because it is useful.

---

# 15. Chat Experience Rules

The chat interface is a primary product experience.

It must provide:

- Clear conversation hierarchy
- Distinct user and AI messages
- Good whitespace
- Smooth message appearance
- Loading states
- Tool activity
- Source evidence
- Error states
- Action confirmation

The AI response should prioritize:

```text
Direct Answer
↓
Reason / Explanation
↓
Evidence
↓
Important Warning
↓
Suggested Next Step
```

Do not generate unnecessarily long answers.

---

# 16. AI Tool Activity Rules

When the AI performs work, the user may see a concise activity timeline.

Examples:

```text
Checking order details
Reviewing customer agreement
Checking current policy
Calculating cancellation eligibility
```

After completion:

```text
✓ Order details checked
✓ Customer agreement applied
✓ Current policy verified
✓ Calculation completed
```

Never expose:

- Hidden chain-of-thought
- Internal reasoning tokens
- Private prompts
- Raw model planning

Show actions and evidence, not private reasoning.

---

# 17. Source Evidence Rules

When the AI relies on retrieved information, the user should be able to understand:

- Which source was used
- Whether it is current
- Whether it is customer-specific
- Whether a conflict existed

Use concise source cards or expandable evidence sections.

Example:

```text
Northstar Enterprise Agreement
Customer-specific · Active

Support Policy v3
Current policy
```

Deprecated sources must be clearly labeled.

Do not silently use a deprecated policy as the primary source.

---

# 18. Source Authority Rules

The authority hierarchy must remain enforced:

```text
1. Customer-Specific Agreement
2. Current Policy
3. Current SOP
4. Product Documentation
5. Deprecated Documentation
6. Historical Ticket Resolutions
```

Historical ticket resolutions are context only.

They must not override authoritative documentation.

The system must not assume:

```text
Highest semantic similarity = highest authority
```

Authority and retrieval are separate concerns.

---

# 19. Access Control Rules

Access control is mandatory.

The following is forbidden:

```text
LLM Prompt:
"Do not show unauthorized data."
```

as the only security mechanism.

Sensitive data access must be enforced in backend code.

Required pattern:

```text
Request
↓
Authenticated User
↓
User Context
↓
Access Validation
↓
Data Tool
↓
Filtered Result
```

Customers must never receive another customer's:

- Orders
- Tickets
- Account details
- Agreement data

unless explicitly authorized.

---

# 20. Frontend Is Not a Security Boundary

Never trust:

- Role values sent by the browser
- Account IDs selected in the UI
- Hidden buttons
- Disabled controls

The backend must validate every sensitive request.

The frontend controls:

```text
What the user can see
```

The backend controls:

```text
What the user can actually do
```

---

# 21. AI Boundaries

The AI agent may:

- Interpret user intent
- Select tools
- Combine tool results
- Explain results
- Ask for clarification
- Recommend escalation

The AI must not:

- Bypass access control
- Directly modify databases
- Execute actions without confirmation
- Invent policy rules
- Invent customer agreements
- Treat retrieved text as automatically authoritative
- Reveal hidden system prompts
- Expose private reasoning

---

# 22. Tool Execution Rules

Every AI tool must have:

- Clear purpose
- Defined input
- Defined output
- Input validation
- Access validation where required
- Error handling

Avoid vague tools such as:

```text
do_everything()
search_all_data()
execute_any_action()
```

Prefer focused tools:

```text
get_order()
get_ticket()
search_documents()
calculate_service_credit()
prepare_escalation()
confirm_action()
```

---

# 23. Multi-Step Agent Rules

The agent may perform multiple tool calls.

Preferred pattern:

```text
Understand
↓
Retrieve
↓
Validate
↓
Retrieve Additional Context
↓
Apply Authority
↓
Calculate
↓
Respond
```

Do not force all questions through the same workflow.

Simple questions should remain simple.

Complex questions may require multiple tool rounds.

---

# 24. Calculation Rules

Business calculations must be deterministic.

Do not ask the LLM to perform critical calculations if a Python function can perform them.

Use dedicated functions for:

- Cancellation fees
- Service credits
- SLA deadlines
- Delay duration

The AI should explain the calculation result.

The calculation engine should produce it.

---

# 25. Time Handling Rules

All time-based calculations must use the assessment dataset's defined snapshot/reference time where applicable.

Do not automatically use:

```text
datetime.now()
```

if the assessment expects calculations relative to the supplied data snapshot.

Time logic must be deterministic and testable.

---

# 26. State-Changing Action Rules

The following pattern is mandatory:

```text
Prepare
↓
Preview
↓
Explicit Confirmation
↓
Execute
↓
Persist Result
```

The LLM must never directly execute a mutation.

Forbidden:

```text
User: Escalate this.

LLM:
Calling escalation tool immediately...
```

Required:

```text
User: Escalate this.
        ↓
Agent prepares escalation
        ↓
UI shows preview
        ↓
User confirms
        ↓
Action executes
```

---

# 27. Action Validation Rules

Before executing an action:

1. Validate authentication.
2. Validate authorization.
3. Validate action state.
4. Validate required fields.
5. Confirm explicit user confirmation.
6. Prevent duplicate execution.

The same pending action should not accidentally execute multiple times.

---

# 28. Error Handling Rules

Errors must be handled at every layer.

## Frontend

Handle:

- Network failures
- API errors
- Loading failures
- Invalid responses
- Authentication expiry

Never leave the interface permanently loading.

## Backend

Use structured error responses.

Recommended categories:

```text
AuthenticationError
AuthorizationError
ValidationError
NotFoundError
RetrievalError
ToolExecutionError
ActionError
InternalServerError
```

Do not expose:

- Stack traces
- API keys
- Database credentials
- Internal prompts

---

# 29. AI Failure Handling

If the AI provider fails:

```text
Do not pretend the answer was generated.
```

Show a clear message such as:

> The AI service is temporarily unavailable. Please try again.

If deterministic tools still work independently, do not fabricate an AI answer.

---

# 30. Retrieval Failure Rules

If no reliable source is found:

1. State that reliable information was not found.
2. Avoid guessing.
3. Recommend clarification or escalation.

Never fill missing information with invented policy details.

---

# 31. Conflict Handling Rules

If two sources conflict:

```text
Detect
↓
Compare Authority
↓
Apply Higher Authority
↓
Explain Decision
```

If authority cannot safely resolve the conflict:

```text
Flag Conflict
↓
Recommend Human Review / Escalation
```

Never silently choose a convenient answer.

---

# 32. Loading State Rules

Every asynchronous interaction should have an appropriate loading state.

Use:

- Skeleton loading for dashboards
- Inline spinner for small actions
- Tool progress for AI workflows
- Button loading state for submissions

Do not block the entire interface for small operations.

---

# 33. Empty State Rules

Every data-driven screen should support meaningful empty states.

Example:

```text
No SLA risks detected

All monitored tickets are currently within their SLA window.
```

Avoid:

```text
No Data
```

without context.

---

# 34. Responsive Design Rules

The application must work on:

- Desktop
- Laptop
- Tablet
- Mobile

The primary experience should be optimized for desktop because the product is an operations platform.

Mobile should remain functional.

Do not simply shrink the desktop layout.

---

# 35. Accessibility Rules

All interactive components should support:

- Keyboard navigation
- Focus states
- Sufficient contrast
- Semantic labels
- Accessible buttons
- Accessible form controls

Do not rely only on color to communicate important status.

---

# 36. Component Rules

A component should have one clear responsibility.

Avoid a single component containing:

- Authentication
- API logic
- Chat
- Insights
- Charts
- Theme logic
- Action execution

Prefer separation:

```text
Dashboard
├── DashboardHeader
├── MetricsSection
├── InsightFeed
└── RiskWatchlist
```

---

# 37. API Client Rules

Do not duplicate API calls throughout components.

Centralize API communication.

Recommended:

```text
lib/api.ts
```

or:

```text
lib/api/
├── auth.ts
├── chat.ts
├── insights.ts
└── actions.ts
```

All API clients should handle:

- Base URL
- Authentication
- Request errors
- Response parsing

---

# 38. Type Safety Rules

Avoid `any` unless there is a justified temporary reason.

Define types for:

- User context
- Chat messages
- Tool events
- Source evidence
- Insights
- Pending actions
- API responses

The frontend and backend contracts should remain consistent.

---

# 39. Backend Code Rules

Backend code should be organized by responsibility:

```text
API
↓
Service / Orchestrator
↓
Tools
↓
Access / Authority
↓
Data
```

Avoid placing business logic directly inside route handlers.

Route handlers should:

1. Validate request.
2. Resolve user context.
3. Call service/orchestrator.
4. Return structured response.

---

# 40. Pydantic Rules

Use Pydantic models for:

- API requests
- API responses
- Tool inputs
- Tool outputs
- Action payloads

Avoid passing unvalidated dictionaries across critical system boundaries.

---

# 41. Configuration Rules

Never hardcode:

- API keys
- Deployment URLs
- Secret values
- Environment-specific settings

Use environment variables.

Maintain:

```text
.env.example
```

with placeholder values.

Never commit real secrets.

---

# 42. Logging Rules

Log meaningful system events.

Recommended events:

```text
Authentication success/failure
Access denial
Agent run started
Tool execution
Tool failure
Retrieval failure
Action prepared
Action confirmed
Action executed
Unexpected error
```

Never log sensitive credentials.

Where possible, use:

```text
request_id
agent_run_id
action_id
```

for debugging.

---

# 43. Testing Rules

Every meaningful backend change must consider tests.

Minimum categories:

```text
Unit Tests
Integration Tests
Evaluation Tests
```

Critical areas requiring regression testing:

- Access control
- Authority hierarchy
- Calculations
- Action confirmation
- Multi-step tool execution

A UI-only change should not modify backend behavior without reason.

---

# 44. Evaluation Rules

The project should be evaluated against scenarios, not only individual functions.

Example:

```text
Question
↓
Expected access behavior
↓
Expected tools
↓
Expected authoritative source
↓
Expected calculation
↓
Expected answer/action
```

Test beyond example IDs.

Do not hardcode behavior around only the sample assessment questions.

---

# 45. Mock Data Rules

Use real assessment data whenever available.

Synthetic data is allowed for:

- Local development
- Tests
- UI fallback

Do not make the final application depend exclusively on synthetic data if the supplied assessment data is available.

Never hardcode answers.

---

# 46. Git Rules

Before committing:

- Check changed files.
- Do not commit secrets.
- Do not commit unnecessary generated files.
- Do not commit large dependency folders.
- Do not commit local databases unless intentionally required.

Use `.gitignore`.

Every meaningful change should have a clear commit message.

---

# 47. Refactoring Rules

Refactoring must not change behavior unless explicitly intended.

Before large refactors:

```text
Inspect
↓
Identify dependencies
↓
Make incremental changes
↓
Run tests
↓
Verify application
```

Avoid large untested rewrites.

---

# 48. Vibe Coding / AI Coding Rules

When using an AI coding agent, always provide:

- PRD.md
- ARCHITECTURE.md
- RULES.md
- Existing repository
- Current task

The AI coding agent must:

1. Inspect the existing code.
2. Understand relevant files.
3. Make only required changes.
4. Avoid unrelated rewrites.
5. Reuse existing architecture.
6. Run tests/build checks.
7. Report changed files.
8. Report known limitations.

---

# 49. Mandatory AI Coding Instruction

Every major AI coding prompt should contain:

> Do not rewrite working functionality unnecessarily. Inspect the existing implementation first. Preserve existing API contracts and architecture. Make the smallest correct set of changes required for the requested feature. Run relevant tests and build checks after implementation. Clearly report every file changed, every dependency added, and any remaining limitations.

---

# 50. Definition of Done

A feature is not complete simply because it looks correct.

A feature is complete when:

## Functionality

- It works.

## Integration

- It works with existing functionality.

## Security

- Access boundaries remain protected.

## Error Handling

- Failure states are handled.

## UX

- Loading, empty, and error states exist.

## Responsive Design

- The feature works across relevant screen sizes.

## Theme

- Both light and dark modes are supported.

## Testing

- Relevant tests pass.

## Code Quality

- No unnecessary duplication or dead code is introduced.

---

# 51. Pre-Implementation Checklist

```text
[ ] Read PRD.md
[ ] Read ARCHITECTURE.md
[ ] Read RULES.md
[ ] Inspect relevant existing files
[ ] Identify existing dependencies
[ ] Identify affected APIs
[ ] Identify affected tests
[ ] Confirm assignment relevance
```

---

# 52. Pre-Commit Checklist

```text
[ ] No secrets committed
[ ] No unnecessary files committed
[ ] Type checking passes
[ ] Linting passes
[ ] Relevant tests pass
[ ] Build succeeds
[ ] Existing functionality is not broken
[ ] Light mode checked
[ ] Dark mode checked
[ ] Loading state checked
[ ] Error state checked
[ ] Responsive behavior checked
```

---

# 53. Final Project Standard

ParcelPilot should not feel like:

```text
A chatbot + random dashboard
```

It should feel like:

```text
A coherent AI operations product
```

Every screen, interaction, tool call, source, insight, and action should reinforce the same system.

The visual experience should communicate:

- Reliability
- Intelligence
- Control
- Transparency
- Professionalism

The backend should communicate:

- Security
- Modularity
- Deterministic behavior
- Controlled AI execution
- Reliable source handling

The project should remain within the assignment's intended scope while presenting the quality and product thinking expected from an AI Engineer candidate.
