# LendFlow: Project Brief

| | |
|---|---|
| **Version** | 0.1 (draft) |
| **Date** | 2026-11-17 |
| **Author** | Vy (Business Analyst / Fullstack Developer) |
| **Status** | Draft for self-review |
| **Nature** | Educational portfolio project. LendFlow is a **fictional lender**. All data is synthetic. |

---

## 1. Context

LendFlow is a digital consumer-lending application for a fictional Vietnamese lender. It is built on the training case study "Digital Lending App" (7-sprint BA bootcamp), reusing its stakeholder analysis, elicitation findings, pain-point backlog and As-is/To-be process homework.

The project has two purposes at once:

1. **Business analysis**: take a lending process from problem framing to requirements, rules, compliance mapping and acceptance criteria.
2. **Engineering**: deliver a working, deployed, tested fullstack application with an AI agent that supports (but never replaces) the loan officer.

## 2. Problem statement

In the As-is process (case-study findings):

- **Borrowers** do not know how much they can borrow, where their application stands, or why it was rejected. They call or visit a branch to find out.
- **Loan officers** re-enter the same national ID number on three screens, wait 3 to 7 minutes for a credit-bureau (CIC) check with no progress indicator, and phone a supervisor for roughly 30% of files because the system has no rule for freelance or self-employed income.
- **Supervisors** have no SLA, so some applications wait up to three days for a decision.
- **Compliance** cannot easily show who saw or changed what, nor that the customer consented to credit scoring.

> **Problem statement.** Borrowers and loan officers lose time and trust because the loan application process is opaque, repetitive and rule-less for non-standard income, making approval slow, hard to audit and hard to explain.

## 3. Vision

*A borrower can see what they can borrow, apply in minutes, and follow the decision in real time. A loan officer sees only the cases that need human judgement, with the evidence already organised and explained. Every decision is auditable.*

## 4. Objectives and success measures

These are **hypotheses to be measured on synthetic data and test users**, not real-world claims.

| # | Objective | Measure | Target |
|---|---|---|---|
| O1 | Remove re-keying | Number of times an ID number is typed per application | 1 (from 3) |
| O2 | Faster officer review | Median officer time per application in a timed test with 5 users | -30% vs. a manual baseline sheet |
| O3 | Accurate AI extraction | Field-level accuracy on 30-document synthetic eval set | >= 90% |
| O4 | Safe AI use | Share of AI outputs followed by an explicit human decision | 100% |
| O5 | Transparency | Applications whose every status change is logged with actor and time | 100% |
| O6 | Explainable rejection | Rejections that carry a reason code and next steps | 100% |
| O7 | Low cost | AI cost per reviewed application; total monthly AI spend | <= US$0.02; <= US$10 hard cap |

## 5. Scope

### In scope (Must / Should for the release)

- Registration and login with role-based access (Borrower, Loan Officer, Supervisor/Admin)
- Public loan calculator
- Loan application with consent screen (data-protection compliant)
- Document upload; AI extraction of ID fields; income-type document requirements
- Mock CIC check with progress feedback
- AI document-review summary with human decision (approve / reject / request more info / refer)
- Loan officer queue; borrower status tracker
- CSV bulk import of applications
- Audit log; data-subject rights (view / correct / delete my data)

### Could have (if time allows)

Email repayment reminders and schedule, SLA escalation, biometric-step simulation, operations dashboard.

### Out of scope (Won't have this release)

Real e-signature integration, real CIC / core-banking integration, real disbursement, SMS, mobile native app, collateral loans, multi-language UI, P2P or group lending.

*(Prioritisation detail and rationale: [04-user-stories-backlog.md](04-user-stories-backlog.md).)*

## 6. Users

| Persona | Goal | Key frustration today |
|---|---|---|
| **Linh, borrower (first-time)**, 28, salaried | Know what she can borrow and track her application | "I applied and don't know where it is." |
| **Minh, loan officer**, 3 years' experience, 10-20 files/day | Process files fast without errors | Re-keying data; waiting on CIC; phoning supervisor |
| **Hoa, supervisor** | Approve exceptions with full context; keep queues moving | Files arrive without context; no deadline |

## 7. Constraints and assumptions

- **Synthetic data only.** No real IDs, bank accounts or customer data anywhere.
- **Free-tier hosting** where possible; AI API spend capped by a monthly limit.
- **Interest rates and thresholds** in [02-business-rules.md](02-business-rules.md) are **illustrative** inventions for the fictional lender, not market data.
- Legal references reflect secondary sources read in November 2026 and **must be re-verified against official texts** before being quoted ([05-compliance-matrix.md](05-compliance-matrix.md)).
- The AI agent **recommends**; a human **decides**.

## 8. Key risks

| Risk | Impact | Mitigation |
|---|---|---|
| Scope creep (building every story) | Never ships | Strict MoSCoW; Must <= 60%; cut list in decisions log |
| AI cost overrun | Unplanned spend | Mock mode, cheapest passing model, monthly cap, request-level cost logging |
| AI extraction errors on documents | Wrong data in applications | Human-editable fields, confidence flags, eval set before release |
| Legal references outdated | Incorrect compliance claims | "Verify" status column; disclaimer; re-check before publishing |
| Real personal data uploaded by a tester | Privacy breach | Warning on upload screen, synthetic data pack, retention limit |
| Time (part-time effort) | Delays | Weekly milestones; deploy skeleton in week 3 |

## 9. Release plan (7 weeks, aligned with the 7-sprint roadmap)

| Week | Sprint theme | Deliverables |
|---|---|---|
| 1 | Discovery & process | Brief, As-is/To-be diagrams, scope |
| 2 | Backlog & requirements | Stakeholders, rules, stories, RBAC, data model, compliance matrix |
| 3 | Skeleton | Repo, CI, auth/roles, deployed shell, calculator |
| 4 | Core workflow | Application CRUD, status tracker, officer queue |
| 5 | Files & AI | Upload, CSV import, mock CIC, AI review agent |
| 6 | Quality | Evals, tests, security pass, UAT cases |
| 7 | Packaging | README, demo video, case study |

## 10. Definition of success (portfolio)

A hiring manager can, in under five minutes: open the live demo, read the README, see the traceability from a pain point to a story to code to a test, and watch the AI agent's accuracy numbers.
