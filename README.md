# LendFlow

> A digital lending application built as an end-to-end portfolio project: **business analysis + fullstack engineering**, designed around Vietnamese lending and data-protection rules.

**Status:** All 20 backlog stories are Done, Won't or Deferred; the AI features (LF-006, LF-009) are deferred (D-026) and e-signature (LF-015) is out of this release. Per-story status is in the [backlog](docs/04-user-stories-backlog.md#1-backlog-overview-moscow), and the reasons behind each choice are in the [decisions log](docs/08-decisions-log.md).
**Live demo:** _coming soon_ · **Demo video:** _coming soon_

> LendFlow is a **fictional lender** for educational purposes. It uses **synthetic data only** and is not a financial product or legal advice.

## The problem

Borrowers don't know how much they can borrow or where their application stands. Loan officers re-type the same ID number three times, wait minutes for credit checks with no feedback, and phone supervisors for non-standard income. Approvals stall, and nobody can easily show who decided what and why.

## The solution

**Borrower**
- Public **loan calculator** (reducing-balance annuity): 100,000,000 VND over 24 months at 16% is 4,896,311 VND a month.
- Online **application with explicit consent** (the AI-processing purpose is retained for a later release).
- **Document upload** (JPG, PNG, PDF, up to 5 MB) with **required documents by income type** (salaried, freelance, self-employed, rental). *(AI extraction of ID fields is deferred, D-026.)*
- **Status tracker** with the reason and conditions for a rejection.
- **Repayment schedule** once approved, and **reminder emails** 7 and 1 days before each due date, with an opt-out.
- **My data**: view, export and request deletion (data-subject rights).

**Loan officer**
- **Queue** of files in review, **mock credit-bureau check** with a progress indicator and retry.
- **Decisions**: approve, reject, request information or refer. A rejection needs a reason code and a plain-language explanation.
- **CSV bulk import** of applications as drafts.
- **Disbursement** of approved loans. Above 10M VND a **simulated face match** is required (single-use, 5 minutes); a failed match blocks the payout and is logged.

**Supervisor**
- Decides referred files, approves loans at or above the officer limit and corrects earlier decisions.
- **SLA escalation** marks files overdue after 24 hours; **operations dashboard** (status counts, decision time, approval rate); **audit log**; user administration.

**Across the app**
- **Human decisions only**: the AI never approves or rejects, and no code path does either automatically. *(The advisory AI review summary is deferred, D-026.)*
- **Role-based access** enforced in the API. Decisions, audit rows and disbursements are **append-only** (database triggers).

**Not built yet:** recorded payments, a borrower claim flow for imported drafts, and the `high_dti` / `fast_track` queue flags.

## What this project demonstrates

| Skill area | Evidence in this repo |
|---|---|
| **Business analysis** | Brief, stakeholder analysis, business rules, As-Is/To-Be process, 20-story backlog with MoSCoW, compliance matrix, traceability |
| **Fullstack** | Next.js + TypeScript frontend; FastAPI + PostgreSQL backend; JWT auth with RBAC; CRUD; file upload and CSV import; CI/CD |
| **Applied AI** | Deferred (D-026). Design kept: mock mode, cost controls, human-in-the-loop |
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

## Architecture

```mermaid
flowchart LR
  B[Borrower / Officer browser] --> F[Next.js frontend]
  F -->|REST + JWT| API[FastAPI backend]
  API --> DB[(PostgreSQL)]
  API --> FS[(File storage)]
  API -.->|deferred, D-026| AG[AI agent service]
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
| 5 | Upload, CSV import, mock CIC (AI review agent deferred, D-026) |
| 6 | Tests, security pass, UAT cases (evals deferred, D-026) |
| 7 | README polish, demo video, case study |

## Getting started

You need [Docker](https://www.docker.com/) (for Postgres) and [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 for you).

```bash
docker compose up -d --wait               # Postgres 16 on host port 5433 (lendflow + lendflow_test)

cp .env.example backend/.env              # then set JWT_SECRET (32+ characters), e.g.
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

cd backend
uv sync
uv run alembic upgrade head               # create the schema and seed the document rules
uv run python -m scripts.seed_users       # synthetic officer and supervisor (prints a password)
uv run fastapi dev app/main.py            # API on http://localhost:8000, docs at /docs

uv run pytest                             # tests (migrates and uses lendflow_test)
uv run ruff check .                       # lint

# frontend (the backend must be running)
cd ../frontend
npm install && cp .env.example .env.local
npm run dev                               # http://localhost:3000
npm test                                  # unit tests
npm run test:e2e                          # browser tests; WIPES and re-seeds lendflow_test
```

Notes:

- Uploaded files are stored under `STORAGE_DIR` (default `backend/storage`, git-ignored).
- The audit log is append-only by design, so its rows cannot be deleted. To reset the dev database, run `docker compose down -v` and start again from the top.
- AI features (LF-006, LF-009) are deferred to a later release (D-026); `AI_MODE` defaults to `mock`.

## Responsible-use notes

- The AI never approves or rejects; humans decide and every AI output is logged.
- Only synthetic data is accepted; do not upload real documents.
- Legal references were compiled from secondary sources and need verification against official texts (see the compliance matrix).

## Author

**Vy**
