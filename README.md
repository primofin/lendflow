# LendFlow

> A digital lending application with an AI document-review agent, built as an end-to-end portfolio project: **business analysis + fullstack engineering + applied AI**, designed around Vietnamese lending and data-protection rules.

**Status:** Documentation complete (v0.1). Implementation in progress, see the [roadmap](#roadmap).
**Live demo:** _coming soon_ · **Demo video:** _coming soon_

> LendFlow is a **fictional lender** for educational purposes. It uses **synthetic data only** and is not a financial product or legal advice.

## The problem

Borrowers don't know how much they can borrow or where their application stands. Loan officers re-type the same ID number three times, wait minutes for credit checks with no feedback, and phone supervisors for non-standard income. Approvals stall, and nobody can easily show who decided what and why.

## The solution

- A public **loan calculator** (reducing-balance annuity).
- Online **application with explicit consent** (purposes including credit scoring and AI processing).
- **Document upload** and **AI extraction** of ID fields, entered once and editable.
- **Rules by income type** (salaried, freelance, self-employed, rental) with required documents.
- **Mock credit-bureau check** with a progress indicator.
- **AI review summary** with confidence scores and flags. It is *advisory*: a human always decides.
- **Officer queue**, **supervisor escalation**, **decision with reason code**, **borrower status tracker**.
- **Audit log**, **data-subject rights**, **CSV bulk import**.

## What this project demonstrates

| Skill area | Evidence in this repo |
|---|---|
| **Business analysis** | Brief, stakeholder analysis, business rules, As-Is/To-Be process, 20-story backlog with MoSCoW, compliance matrix, traceability |
| **Fullstack** | Next.js + TypeScript frontend; FastAPI + PostgreSQL backend; JWT auth with RBAC; CRUD; file upload and CSV import; CI/CD |
| **Applied AI** | Tool-using agent loop, structured output, evaluation set with accuracy numbers, cost controls, mock mode, human-in-the-loop |
| **Product thinking** | Measurable objectives, scope cuts documented in a decisions log |
| **Compliance awareness** | Mapping of Vietnamese lending, e-transaction and personal-data rules to features and tests |

## Documentation

| Document | Purpose |
|---|---|
| [00 Project brief](docs/00-project-brief.md) | Problem, vision, objectives, scope, risks, plan |
| [01 Stakeholders and RBAC](docs/01-stakeholders-and-rbac.md) | Power/interest grid, roles, permission matrix |
| [02 Business rules](docs/02-business-rules.md) | Eligibility, routing, AI and data rules; worked calculation |
| [03 Process: As-Is and To-Be](docs/03-process-as-is-to-be.md) | Process diagrams, pain points, gap analysis, state machine |
| [04 User stories and backlog](docs/04-user-stories-backlog.md) | 20 stories with acceptance criteria, MoSCoW |
| [05 Compliance matrix](docs/05-compliance-matrix.md) | Legal requirement to feature to test |
| [06 Data model](docs/06-data-model.md) | ER diagram and data dictionary |
| [07 Glossary](docs/07-glossary.md) | Bilingual (EN/VI) terms |
| [08 Decisions log](docs/08-decisions-log.md) | Why key choices were made; open questions |

## Architecture (planned)

```mermaid
flowchart LR
  B[Borrower / Officer browser] --> F[Next.js frontend]
  F -->|REST + JWT| API[FastAPI backend]
  API --> DB[(PostgreSQL)]
  API --> FS[(File storage)]
  API --> AG[AI agent service]
  AG -->|tool calls| T1[extract_fields]
  AG --> T2[check_required_documents]
  AG --> T3[lookup_mock_cic]
  AG --> T4[calculate_dti]
  AG -->|LLM API| LLM[Claude API / mock mode]
```

## Tech stack

Next.js · TypeScript · Tailwind · FastAPI · SQLAlchemy · Alembic · PostgreSQL · pytest · Playwright · Docker · GitHub Actions · Anthropic API

## Cost approach

Free-tier hosting, mock AI mode by default, cheapest model that passes the evals, free OCR first, monthly AI spend cap, per-request cost logging.

## Roadmap

| Week | Focus |
|---|---|
| 1 | Discovery, process diagrams, brief |
| 2 | Requirements, rules, RBAC, data model, compliance matrix |
| 3 | Skeleton: auth and roles, deployed shell, calculator |
| 4 | Application workflow, status tracker, officer queue |
| 5 | Upload, CSV import, mock CIC, AI review agent |
| 6 | Evals, tests, security pass, UAT cases |
| 7 | README polish, demo video, case study |

## Getting started

_Setup instructions will be added when the code skeleton lands (week 3)._

## Responsible-use notes

- The AI never approves or rejects; humans decide and every AI output is logged.
- Only synthetic data is accepted; do not upload real documents.
- Legal references were compiled from secondary sources and need verification against official texts (see the compliance matrix).

## Author

**Vy**: frontend developer moving into fullstack and product-focused roles.
