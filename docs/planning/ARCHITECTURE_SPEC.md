# ParcelPilot AI Support Agent — System Architecture

**Version:** 1.0  
**Status:** Active Development  
**Architecture Style:** Modular AI Agent System with Retrieval, Structured Data Tools, Access Control, and Safe Action Execution

---

# 1. Architecture Overview

ParcelPilot AI Support Agent is an AI-powered support and operations system designed around a multi-step agent architecture.

The system combines:

- Natural-language AI interaction
- Agent orchestration
- Document retrieval
- Structured operational data
- Deterministic business calculations
- Source authority and conflict handling
- Role-based access control
- Safe state-changing actions
- Proactive operational insights

The architecture is designed so that the LLM is **not directly trusted to access data or perform actions**.

Instead, the AI agent operates through controlled application tools.

```text
┌─────────────────────────────────────────────────────────────┐
│                         USERS                               │
│                                                             │
│   Customer             Support Agent       Operations User  │
└──────────────┬──────────────────┬───────────────────────────┘
               │                  │
               ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND                               │
│                                                             │
│  Next.js + TypeScript + Tailwind                            │
│                                                             │
│  • Authentication                                           │
│  • Role-aware UI                                            │
│  • AI Chat                                                  │
│  • Tool Activity                                            │
│  • Source Evidence                                          │
│  • Action Confirmation                                      │
│  • Insights Dashboard                                       │
│  • Dark / Light Mode                                        │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS / REST API
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                       BACKEND API                            │
│                                                             │
│                        FastAPI                              │
│                                                             │
│  • Authentication                                           │
│  • Request Validation                                       │
│  • User Context                                             │
│  • Role / Account Context                                   │
│  • Agent API                                                │
│  • Insights API                                             │
│  • Action API                                               │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATOR                       │
│                                                             │
│  1. Understand Request                                      │
│  2. Determine Required Tools                                │
│  3. Execute Tool Calls                                      │
│  4. Apply Access Control                                    │
│  5. Retrieve Evidence                                       │
│  6. Resolve Source Conflicts                                │
│  7. Perform Calculations                                    │
│  8. Decide Answer / Escalation                              │
│  9. Generate Final Response                                 │
└────────────────────────────┬────────────────────────────────┘
                             │
             ┌───────────────┼────────────────┐
             ▼               ▼                ▼
┌─────────────────┐ ┌────────────────┐ ┌───────────────────┐
│ DOCUMENT TOOLS  │ │ STRUCTURED DATA│ │  ACTION TOOLS     │
│                 │ │ TOOLS          │ │                   │
│ • RAG Search    │ │ • Accounts     │ │ • Escalation      │
│ • Policies      │ │ • Orders       │ │ • Ticket Update   │
│ • Agreements    │ │ • Tickets      │ │ • Follow-up Task  │
│ • SOPs          │ │ • Calculations │ │ • Confirmation    │
└────────┬────────┘ └────────┬───────┘ └─────────┬─────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌────────────────┐ ┌───────────────────┐
│ VECTOR DATABASE │ │ SQLITE / DATA  │ │ ACTION STATE      │
│                 │ │ LAYER          │ │                   │
│ ChromaDB        │ │ Accounts       │ │ Pending Actions   │
│                 │ │ Orders         │ │ Confirmed Actions │
│ Documents       │ │ Tickets        │ │ Audit Records     │
└─────────────────┘ └────────────────┘ └───────────────────┘
```

---

# 2. Architectural Principles

The architecture follows several core principles.

## 2.1 The AI Model Does Not Directly Access Data

The LLM should not directly query databases or read arbitrary files.

Instead:

```text
LLM
 ↓
Agent Tool Selection
 ↓
Controlled Tool
 ↓
Access Validation
 ↓
Data Retrieval
 ↓
Structured Result
 ↓
LLM
```

This allows the application to control:

- Which data is accessible
- Which user can access it
- What information reaches the model
- Which actions can be executed

---

## 2.2 Access Control Happens Before Data Retrieval

The system must not rely only on prompts such as:

> Never reveal another customer's data.

Instead:

```text
User Request
      ↓
Authenticated User
      ↓
Role / Account Context
      ↓
Access Validation
      ↓
Authorised Tool Query
      ↓
Filtered Result
```

For example:

```text
Customer A requests ORD-2001
          ↓
Order belongs to Customer B
          ↓
Access layer rejects request
          ↓
No Customer B data returned to agent
```

---

## 2.3 Retrieval Does Not Mean Authority

A retrieved document is not automatically correct.

The system separates:

```text
Retrieval
    ↓
Source Identification
    ↓
Authority Evaluation
    ↓
Conflict Detection
    ↓
Applicable Evidence
```

This prevents:

- Deprecated policies overriding current policies
- Historical tickets being treated as authoritative
- General policies overriding customer agreements

---

## 2.4 Actions Are Staged Before Execution

The LLM cannot directly mutate system state.

All actions follow:

```text
User Request
      ↓
Agent Investigation
      ↓
Prepare Action
      ↓
Store Pending Action
      ↓
Return Preview
      ↓
User Confirmation
      ↓
Execute Action
      ↓
Persist Result
```

---

# 3. High-Level System Components

The system is divided into the following major layers.

```text
Frontend Layer
        ↓
API Layer
        ↓
Authentication and Context Layer
        ↓
Agent Orchestration Layer
        ↓
Tool Layer
        ↓
Data and Retrieval Layer
        ↓
Authority / Safety Layer
        ↓
Persistence Layer
```

---

# 4. Frontend Architecture

## 4.1 Technology

The frontend uses:

- Next.js
- TypeScript
- Tailwind CSS
- React component architecture

The frontend is responsible for the user experience and should not contain sensitive business logic or security enforcement.

---

## 4.2 Frontend Application Structure

Recommended structure:

```text
frontend/
│
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── globals.css
│   │
│   ├── insights/
│   │   └── page.tsx
│   │
│   └── api/                    # Optional future frontend routes
│
├── components/
│   ├── LoginScreen.tsx
│   │
│   ├── chat/
│   │   ├── ChatInterface.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── ChatInput.tsx
│   │   ├── ToolActivity.tsx
│   │   ├── SourceEvidence.tsx
│   │   └── ActionConfirmation.tsx
│   │
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   └── ThemeToggle.tsx
│   │
│   ├── insights/
│   │   ├── InsightCard.tsx
│   │   ├── MetricCard.tsx
│   │   ├── SLAWatchlist.tsx
│   │   └── IssueCluster.tsx
│   │
│   └── ui/
│
├── lib/
│   ├── api.ts
│   └── utils.ts
│
├── hooks/
│   ├── useChat.ts              # Recommended
│   ├── useTheme.ts             # Recommended
│   └── useUserContext.ts       # Recommended
│
└── types/
    ├── agent.ts                # Recommended
    ├── insights.ts             # Recommended
    └── auth.ts                 # Recommended
```

The existing application should preserve its current structure where possible. The additional folders above are recommended as the frontend grows.

---

# 5. Frontend User Experience Architecture

## 5.1 Authentication Context

After login, the frontend receives a user context such as:

```json
{
  "user_id": "user_123",
  "role": "customer",
  "account_id": "northstar",
  "permissions": [
    "chat",
    "view_own_orders"
  ]
}
```

For internal users:

```json
{
  "user_id": "agent_123",
  "role": "support_agent",
  "permissions": [
    "chat",
    "view_accounts",
    "view_orders",
    "view_tickets",
    "create_escalation"
  ]
}
```

The frontend uses this context for the UI.

The backend remains responsible for enforcing the permissions.

---

## 5.2 Chat Request Flow

```text
User
 ↓
Chat Input
 ↓
Frontend API Client
 ↓
POST /chat
 ↓
FastAPI
 ↓
Authenticated Context
 ↓
Agent Orchestrator
 ↓
Tool Execution
 ↓
Response
 ↓
Chat UI
```

---

## 5.3 Tool Activity UI

The backend should return structured tool events.

Example:

```json
{
  "type": "tool_started",
  "tool": "order_lookup",
  "label": "Checking order information"
}
```

Then:

```json
{
  "type": "tool_completed",
  "tool": "order_lookup",
  "status": "success"
}
```

The frontend converts these events into visual states.

Example:

```text
✓ Order information checked
✓ Customer agreement reviewed
✓ Current cancellation policy checked
✓ Cancellation eligibility calculated
```

The user sees what the system is doing without exposing hidden reasoning.

---

# 6. Theme Architecture

The application should support:

```text
System Theme
      │
      ├── Light
      └── Dark
```

Recommended theme state:

```text
theme:
    light
    dark
    system
```

Theme preference should persist using local storage or an equivalent client-side persistence mechanism.

Recommended component:

```text
ThemeProvider
     ↓
Application
     ↓
ThemeToggle
```

Theme transitions should be smooth but fast.

---

# 7. Backend Architecture

## 7.1 Technology

The backend uses:

- Python
- FastAPI
- Pydantic
- SQLite / structured data layer
- ChromaDB for document retrieval

The backend acts as the trusted control plane for the application.

---

## 7.2 Backend Structure

Based on the existing repository architecture:

```text
backend/
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── auth.py
│   ├── access.py
│   │
│   ├── agent/
│   │   ├── orchestrator.py
│   │   └── toolspec.py
│   │
│   ├── tools/
│   │   ├── data.py
│   │   ├── calculations.py
│   │   └── actions.py
│   │
│   ├── rag/
│   │   ├── retrieval.py
│   │   └── authority.py
│   │
│   ├── insights/
│   │   └── service.py
│   │
│   └── schemas/                # Recommended expansion
│       ├── chat.py
│       ├── actions.py
│       └── insights.py
│
├── tests/
│   ├── test_access.py
│   ├── test_actions.py
│   ├── test_agent.py
│   ├── test_auth.py
│   ├── test_health.py
│   ├── test_metadata.py
│   ├── test_rag.py
│   ├── test_tools.py
│   ├── test_insights.py
│   ├── test_trust.py
│   └── evaluation/
│
└── requirements.txt
```

The exact existing filenames should be retained where already implemented.

---

# 8. API Layer

The FastAPI application acts as the boundary between the frontend and the agent system.

Recommended API groups:

```text
/api
│
├── /auth
│   ├── login
│   ├── logout
│   └── me
│
├── /chat
│   ├── POST /
│   └── POST /confirm-action
│
├── /insights
│   ├── GET /
│   └── GET /{insight_id}
│
├── /health
│   └── GET /
│
└── /metadata
    └── GET /
```

The exact endpoint naming can follow the current implementation.

The important architectural separation is:

```text
Frontend
    ↓
API
    ↓
Authentication
    ↓
Access Context
    ↓
Agent / Services
```

---

# 9. Authentication Architecture

Authentication creates the trusted user context.

```text
Login Request
      ↓
Authentication Service
      ↓
Validate User
      ↓
Generate Session / Token
      ↓
Return Authenticated Context
```

Each backend request should resolve:

```text
User ID
Role
Account ID
Permissions
```

Example internal representation:

```text
UserContext
├── user_id
├── role
├── account_id
└── permissions
```

This context is passed to tools during execution.

---

# 10. Access Control Architecture

The `access.py` layer acts as the central authorisation boundary.

Tool execution should follow:

```text
Agent requests tool
        ↓
Tool receives UserContext
        ↓
Access Layer validates request
        ↓
Authorised?
   ┌────┴────┐
   │         │
 YES        NO
   │         │
   ▼         ▼
Execute    Reject
Tool       Request
```

Important principle:

```text
The model cannot bypass access.py.
```

All sensitive data tools must use the access layer.

---

# 11. AI Agent Architecture

The agent orchestrator coordinates the entire AI workflow.

Existing core component:

```text
agent/orchestrator.py
```

The orchestrator is responsible for:

1. Receiving the user request.
2. Receiving authenticated user context.
3. Determining which tools are needed.
4. Executing one or multiple tools.
5. Handling tool results.
6. Applying authority logic.
7. Determining whether another tool call is required.
8. Preparing the final answer.
9. Detecting when escalation is necessary.

---

# 12. Agent Execution Loop

The agent operates as a controlled loop.

```text
┌────────────────────┐
│ User Request       │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Agent Orchestrator │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Need Tool?         │
└──────┬────────┬────┘
       │        │
      Yes       No
       │        │
       ▼        ▼
┌────────────┐  ┌──────────────┐
│ Select Tool│  │ Final Answer │
└─────┬──────┘  └──────────────┘
      ▼
┌────────────────────┐
│ Access Validation  │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Execute Tool       │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Evaluate Result    │
└─────────┬──────────┘
          │
          └───────────────► Repeat if required
```

---

# 13. Tool Architecture

The tool layer is divided into three primary categories.

```text
Agent Tools
│
├── Document Tools
│
├── Structured Data Tools
│
└── Action Tools
```

---

# 14. Document Retrieval Architecture

Primary components:

```text
rag/
├── retrieval.py
└── authority.py
```

Flow:

```text
Source Documents
      ↓
Document Ingestion
      ↓
Chunking
      ↓
Metadata Assignment
      ↓
Embedding
      ↓
ChromaDB
      ↓
User Query
      ↓
Semantic Retrieval
      ↓
Relevant Documents
      ↓
Authority Evaluation
      ↓
Final Evidence
```

Documents include:

```text
01_Support_Policy_v3_CURRENT.pdf
02_Support_Policy_v2_DEPRECATED.pdf
03_Cancellation_and_Service_Credit_SOP_v4.pdf
04_Product_Operations_Guide_and_Known_Issues.pdf
05_Northstar_Logistics_Enterprise_Agreement.pdf
06_LumenWorks_Service_Agreement.pdf
```

---

# 15. Document Metadata Architecture

Every document should contain metadata such as:

```json
{
  "document_id": "policy_v3",
  "document_type": "support_policy",
  "version": "v3",
  "status": "current",
  "authority_level": 2,
  "customer_scope": null
}
```

Customer agreement:

```json
{
  "document_id": "northstar_agreement",
  "document_type": "customer_agreement",
  "status": "active",
  "authority_level": 1,
  "customer_scope": "northstar"
}
```

Deprecated policy:

```json
{
  "document_id": "policy_v2",
  "document_type": "support_policy",
  "status": "deprecated",
  "authority_level": 5
}
```

This metadata enables deterministic source handling.

---

# 16. Authority Engine

Primary component:

```text
rag/authority.py
```

The authority engine evaluates retrieved evidence.

Recommended hierarchy:

```text
Customer Agreement
        ↓
Current Policy
        ↓
Current SOP
        ↓
Product Documentation
        ↓
Deprecated Documents
        ↓
Historical Ticket Resolutions
```

Conflict workflow:

```text
Retrieved Evidence
        ↓
Are Sources Compatible?
        │
   ┌────┴────┐
   │         │
  YES        NO
   │         │
   ▼         ▼
Use Evidence  Compare Authority
                    ↓
              Higher Authority Exists?
                    │
               ┌────┴────┐
               │         │
              YES        NO
               │         │
               ▼         ▼
          Use Source   Escalate /
                        Flag Conflict
```

---

# 17. Structured Data Architecture

Primary component:

```text
tools/data.py
```

The structured data layer handles:

```text
Accounts
Orders
Tickets
```

Source:

```text
ParcelPilot_Assessment_Data.xlsx
```

Data ingestion flow:

```text
Excel Workbook
      ↓
Parser / Loader
      ↓
Validation
      ↓
Structured Database
      ↓
Controlled Data Tools
```

The workbook's snapshot time should be treated as the reference point for time-based calculations.

---

# 18. Structured Data Tools

Recommended tool operations:

```text
get_account(account_id)

get_order(order_id)

get_ticket(ticket_id)

get_account_orders(account_id)

get_account_tickets(account_id)

search_orders(filters)

search_tickets(filters)
```

Every operation receives user context.

Example:

```text
get_order(
    order_id,
    user_context
)
```

The access layer determines whether the result can be returned.

---

# 19. Deterministic Calculation Architecture

Primary component:

```text
tools/calculations.py
```

Calculations should not rely entirely on LLM reasoning.

Examples:

```text
Cancellation Fee Calculation

Service Credit Calculation

SLA Deadline Calculation

Delay Duration Calculation
```

Flow:

```text
Structured Data
      +
Applicable Policy
      +
Customer Agreement
      ↓
Deterministic Calculation Function
      ↓
Structured Result
      ↓
Agent Explanation
```

Example:

```json
{
  "eligible": true,
  "fee": 0,
  "reason": "Customer agreement overrides general cancellation policy"
}
```

---

# 20. Action Architecture

Primary component:

```text
tools/actions.py
```

Supported actions:

```text
Create Escalation

Update Ticket

Create Follow-up Task
```

Actions should be represented as objects.

Example:

```json
{
  "action_id": "act_123",
  "type": "create_escalation",
  "status": "pending_confirmation",
  "payload": {
    "ticket_id": "TCK-1001",
    "reason": "SLA risk"
  }
}
```

---

# 21. Pending Action State Machine

```text
┌──────────┐
│ PREPARED │
└────┬─────┘
     │
     ▼
┌──────────────────────┐
│ PENDING CONFIRMATION │
└──────┬────────┬──────┘
       │        │
 Confirm       Cancel
       │        │
       ▼        ▼
┌──────────┐ ┌───────────┐
│ EXECUTED │ │ CANCELLED │
└──────────┘ └───────────┘
```

The action executor should reject execution when the action is not explicitly confirmed.

---

# 22. Insights Architecture

Primary component:

```text
insights/service.py
```

The insights engine operates on structured operational data.

Flow:

```text
Accounts
Orders
Tickets
      ↓
Data Aggregation
      ↓
Pattern Detection
      ↓
Risk Scoring
      ↓
Insight Generation
      ↓
Insights API
      ↓
Dashboard
```

---

# 23. Insight Types

The system can generate:

## 23.1 SLA Risk

```text
Ticket Priority
+
Current Status
+
SLA Deadline
+
Current Snapshot Time
=
SLA Risk
```

---

## 23.2 Ticket Spike

```text
Current Issue Volume
        vs
Historical / Baseline Volume
        ↓
Spike Detection
```

---

## 23.3 Recurring Issues

```text
Ticket Categories
+
Issue Text / Metadata
        ↓
Grouping
        ↓
Repeated Pattern
```

---

## 23.4 Cross-Customer Impact

```text
Similar Issue
        ↓
Multiple Accounts?
        ↓
Cross-Customer Insight
```

---

# 24. Data Flow: Customer Question

Example:

> Can I cancel ORD-1001 without a cancellation fee?

```text
Customer
   ↓
Frontend Chat
   ↓
POST /chat
   ↓
Authentication
   ↓
Customer Account Context
   ↓
Agent Orchestrator
   ↓
Order Lookup Tool
   ↓
Access Validation
   ↓
Order Retrieved
   ↓
Customer Agreement Retrieval
   ↓
Current Policy / SOP Retrieval
   ↓
Authority Resolution
   ↓
Cancellation Calculation
   ↓
Final Answer
   ↓
Sources + Explanation
   ↓
Frontend
```

---

# 25. Data Flow: Unauthorised Request

Example:

> Show me LumenWorks order details.

```text
Customer User
      ↓
Agent requests order lookup
      ↓
Access Layer
      ↓
Order belongs to different account
      ↓
Access Denied
      ↓
No data returned
      ↓
Safe Response Generated
```

---

# 26. Data Flow: State-Changing Action

Example:

> Escalate this ticket.

```text
User
 ↓
Chat Request
 ↓
Agent Investigation
 ↓
Prepare Escalation
 ↓
Create Pending Action
 ↓
Frontend Preview
 ↓
User clicks Confirm
 ↓
POST /confirm-action
 ↓
Validate User + Action
 ↓
Execute Action
 ↓
Persist Action Result
 ↓
Return Success
```

---

# 27. Proactive Insights Data Flow

```text
Scheduled / On-Demand Request
          ↓
Insights Service
          ↓
Load Tickets + Orders
          ↓
Apply Detection Rules
          ↓
Calculate Risk / Frequency
          ↓
Generate Insight Objects
          ↓
Insights API
          ↓
Frontend Dashboard
```

---

# 28. Persistence Architecture

Current logical persistence layers:

```text
Structured Data
├── Accounts
├── Orders
└── Tickets

Vector Store
└── Document Embeddings

Action State
├── Pending Actions
├── Executed Actions
└── Action History
```

For the assessment, local or lightweight persistence is acceptable.

---

# 29. Recommended Additional Persistence Components

These are recommended improvements if not already implemented.

## Conversation Storage

```text
conversations
├── conversation_id
├── user_id
├── created_at
└── updated_at

messages
├── message_id
├── conversation_id
├── role
├── content
└── timestamp
```

This allows:

- Conversation history
- Context continuity
- Auditability

---

## Agent Execution Audit

Recommended:

```text
agent_runs
├── run_id
├── user_id
├── request_id
├── started_at
├── completed_at
└── status

tool_runs
├── tool_run_id
├── run_id
├── tool_name
├── status
├── duration
└── error
```

This would improve debugging and evaluation.

---

# 30. Error Handling Architecture

All major layers should provide controlled failures.

```text
Frontend
    ↓
API Error Boundary
    ↓
FastAPI Exception Handling
    ↓
Service / Tool Exception
    ↓
Structured Error
    ↓
Safe User Message
```

The system should distinguish between:

```text
Authentication Error
Access Denied
Data Not Found
Tool Failure
Retrieval Failure
LLM Failure
Action Failure
Unknown Error
```

The user should receive a clear message without exposing internal stack traces.

---

# 31. Testing Architecture

The existing repository already contains tests across multiple areas.

Testing should be organised into:

```text
Unit Tests
├── Access Control
├── Calculations
├── Authority Rules
├── Actions
└── Data Tools

Integration Tests
├── Authentication
├── Agent + Tools
├── Retrieval
└── Insights

End-to-End Tests
├── Customer Chat
├── Internal Chat
├── Access Denial
├── Multi-Step Request
└── Action Confirmation

Evaluation Tests
├── Answer Correctness
├── Retrieval Quality
├── Authority Handling
├── Escalation Decisions
└── Safety
```

---

# 32. Evaluation Architecture

Recommended evaluation scenarios:

```text
Question
   ↓
Expected Data Sources
   ↓
Expected Tool Usage
   ↓
Expected Answer
   ↓
Actual Agent Run
   ↓
Compare Result
```

Evaluation should measure:

- Answer correctness
- Correct source selection
- Tool selection
- Access control
- Escalation correctness
- Action safety

---

# 33. Observability — Recommended Enhancement

A future production-ready architecture should include:

```text
Request Logs
Agent Runs
Tool Calls
Errors
Latency
Token Usage
Retrieval Results
Action Events
```

Recommended flow:

```text
Request
   ↓
Request ID
   ↓
Agent Run ID
   ↓
Tool Run IDs
   ↓
Structured Logs
```

This is particularly useful for debugging multi-step AI systems.

---

# 34. Security Architecture

Security boundaries:

```text
Internet
   ↓
Frontend
   ↓ HTTPS
Backend API
   ↓
Authentication
   ↓
Authorisation
   ↓
Controlled Tools
   ↓
Data
```

Security principles:

- Validate API input.
- Authenticate users.
- Resolve role and account context server-side.
- Enforce access at the tool/data layer.
- Never trust frontend role information alone.
- Prevent direct model access to unrestricted data.
- Require explicit confirmation for mutations.
- Keep secrets in environment variables.
- Avoid exposing backend credentials to the frontend.

---

# 35. Environment Configuration

Recommended:

```text
.env.example
```

Backend variables may include:

```text
LLM_API_KEY
CHROMA_PATH
DATABASE_URL
CORS_ORIGINS
ENVIRONMENT
```

Frontend variables may include:

```text
NEXT_PUBLIC_API_URL
```

Production secrets must never be committed to Git.

---

# 36. Deployment Architecture

Recommended deployment:

```text
                    ┌───────────────┐
                    │    Users      │
                    └───────┬───────┘
                            │
                  ┌─────────▼─────────┐
                  │      Vercel       │
                  │                   │
                  │ Next.js Frontend  │
                  └─────────┬─────────┘
                            │ HTTPS API
                  ┌─────────▼─────────┐
                  │      Render       │
                  │                   │
                  │ FastAPI Backend   │
                  │ AI Agent          │
                  │ RAG               │
                  └─────────┬─────────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
        ChromaDB       Structured DB    Documents
```

The existing repository contains deployment configuration for this architecture.

---

# 37. Repository Architecture

Recommended final repository structure:

```text
parcelpilot-ai-support-agent/
│
├── README.md
├── ARCHITECTURE.md
├── PRODUCT.md
├── ASSUMPTIONS.md
├── AI_TOOL_USAGE.md
├── .env.example
├── render.yaml
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   ├── types/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   ├── rag/
│   │   ├── tools/
│   │   ├── insights/
│   │   ├── schemas/
│   │   ├── auth.py
│   │   ├── access.py
│   │   └── main.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── evaluation/
│   │
│   └── requirements.txt
│
├── data_pack/
│
├── fixtures/
│   └── synthetic_datapack/
│
└── scripts/
```

---

# 38. Recommended Additional Files

The following files are recommended to improve the project documentation and production quality.

## `ARCHITECTURE.md`

This document.

Purpose:

Explain the complete end-to-end technical architecture.

---

## `PRODUCT.md`

Purpose:

Explain:

- Product decisions
- Additional problem addressed
- Future roadmap
- Intentional trade-offs
- Product success metric

---

## `ASSUMPTIONS.md`

Already present in the project.

Purpose:

Document assumptions made because the assessment intentionally leaves some implementation decisions open.

---

## `AI_TOOL_USAGE.md`

Recommended as a dedicated file if not already separated.

Purpose:

Clearly state:

- Which AI coding tools were used.
- How they were used.
- Which work was reviewed or modified manually.
- How AI-generated code was validated.

---

## `API.md`

Recommended enhancement.

Purpose:

Document:

- Authentication
- API endpoints
- Request formats
- Response formats
- Error responses

---

## `EVALUATION.md`

Recommended enhancement.

Purpose:

Document:

- Test scenarios
- Expected results
- Agent evaluation methodology
- Known limitations

---

# 39. Major Technical Trade-Offs

## Local / Lightweight Data Infrastructure

For an assessment project, local or lightweight persistence is used to reduce unnecessary infrastructure complexity.

### Trade-off

Simple deployment versus full production scalability.

---

## Controlled Tools Instead of Free Database Access

The LLM accesses data through predefined tools.

### Benefit

Improves:

- Security
- Predictability
- Auditability

### Trade-off

Requires explicit tool implementation.

---

## Authority Rules Alongside Semantic Retrieval

Vector similarity alone is insufficient because the most semantically similar source may not be the authoritative source.

Therefore:

```text
Semantic Retrieval
+
Metadata
+
Authority Rules
=
Reliable Evidence
```

---

## Explicit Confirmation for Actions

Actions require an additional confirmation step.

### Benefit

Prevents unintended state changes.

### Trade-off

Adds one interaction step.

---

# 40. End-to-End Architecture Summary

The complete system operates as follows:

```text
┌──────────────────────────────────────────────────────┐
│                       USER                           │
│ Customer / Support Agent / Operations User           │
└───────────────────────┬──────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────┐
│                    NEXT.JS FRONTEND                  │
│                                                      │
│ Authentication • Chat • Tool Activity • Insights     │
│ Sources • Action Confirmation • Dark/Light Theme     │
└───────────────────────┬──────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────┐
│                     FASTAPI API                      │
│                                                      │
│ Request Validation • Authentication • User Context   │
└───────────────────────┬──────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────┐
│                  ACCESS CONTROL                      │
│                                                      │
│ Role Validation • Account Scoping • Permissions      │
└───────────────────────┬──────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────┐
│                 AI AGENT ORCHESTRATOR                │
│                                                      │
│ Understand → Plan → Select Tools → Execute           │
│ Evaluate → Repeat → Answer / Escalate                │
└──────────────┬─────────────────┬─────────────────────┘
               │                 │
               ▼                 ▼
      ┌────────────────┐ ┌──────────────────────┐
      │ DOCUMENT TOOLS │ │ STRUCTURED DATA TOOLS│
      │                │ │                      │
      │ RAG            │ │ Accounts             │
      │ Policies       │ │ Orders               │
      │ Agreements     │ │ Tickets              │
      │ SOPs           │ │ Calculations         │
      └───────┬────────┘ └──────────┬───────────┘
              │                     │
              ▼                     ▼
      ┌────────────────┐   ┌────────────────────┐
      │ AUTHORITY      │   │ ACTION TOOLS       │
      │ ENGINE         │   │                    │
      │                │   │ Stage              │
      │ Conflict       │   │ Preview            │
      │ Resolution     │   │ Confirm            │
      │ Reliability    │   │ Execute            │
      └───────┬────────┘   └─────────┬──────────┘
              │                      │
              └──────────┬───────────┘
                         ▼
              ┌─────────────────────┐
              │ FINAL RESPONSE     │
              │                     │
              │ Answer              │
              │ Evidence            │
              │ Warnings            │
              │ Next Action         │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │  POLISHED UI        │
              │                     │
              │ Chat Response       │
              │ Tool Timeline       │
              │ Source Evidence     │
              │ Confirmation        │
              │ Insights            │
              └─────────────────────┘
```

---

# 41. Final Architecture Principle

The architecture is intentionally designed so that ParcelPilot is not simply:

```text
User → LLM → Answer
```

Instead, it is:

```text
User
 ↓
Authentication and Context
 ↓
Controlled AI Agent
 ↓
Authorised Tool Selection
 ↓
Document Retrieval + Structured Data
 ↓
Source Authority and Conflict Handling
 ↓
Deterministic Calculations
 ↓
Confidence / Escalation Decision
 ↓
Safe Action Confirmation
 ↓
Reliable Response
```

The system therefore behaves as a controlled AI workflow rather than an unrestricted chatbot.

**Primary architectural goal:**

> Build an AI support system that can reason across multiple sources and tools while remaining secure, explainable, reliable, and safe to use.