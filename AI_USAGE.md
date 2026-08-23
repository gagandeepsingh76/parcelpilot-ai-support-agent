# AI Tool Usage

## Tools Used

During the development and finalization of this project, the following AI tools were utilized:
- **Google Gemini (Antigravity)**
- **Claude (Anthropic)** (Used in earlier phases before migrating the orchestrator to Gemini)

## How AI Tools Were Used

AI tools were employed strictly as coding assistants and productivity multipliers. Their usage included:

- **Repository Analysis**: Quickly auditing the existing codebase to understand the routing, access control layers, and test suites.
- **Debugging & Refactoring**: Identifying the root cause of access scope failures and suggesting structural refactors for the Next.js frontend components.
- **Documentation Drafting**: Generating the initial structural outlines for Markdown documentation (README, Architecture, Product notes) based on specific engineering prompts.
- **UI/UX Iteration**: Assisting with CSS styling choices, particularly around the responsive design and theming (Light/Dark mode) for the Model Insights dashboard.

**Crucially, the final implementation decisions, architecture selection, validation, testing, and review remained the responsibility of the developer.** The AI was not relied upon to design the deterministic calculation logic or the rigid RBAC security boundaries; those were explicitly engineered and verified by hand.

## Validation

Any AI-generated or AI-assisted changes were rigorously validated using the project's actual test and build workflow:
- **Unit Tests**: `pytest` was run consistently to ensure no regressions in access control or calculations.
- **Offline Evals**: The scenario evaluation suite (`python evals/run_evals.py`) was used to verify that the agent's behavior remained correct across 15 distinct support scenarios.
- **Frontend Build**: The Next.js frontend was validated via `npm run build` and `npm run lint` to ensure strict TypeScript compliance.
- **Manual QA**: Staged actions and confirmation flows were tested manually in the browser to confirm UI state transitions.
