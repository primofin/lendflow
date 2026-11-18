# Stakeholders and Role-Based Access (RBAC)

## 1. Stakeholder register (Power / Interest grid)

Scores are on a 1-5 scale. **Quadrant rule (applied consistently):** Power >= 4 is "high"; Interest >= 4 is "high".

| Stakeholder | Role in project | Power | Interest | Quadrant | Main concerns |
|---|---|---|---|---|---|
| Board / Executive Sponsor | Funding, risk appetite | 5 | 3 | Keep Satisfied | ROI, risk, regulatory standing |
| Chief Credit Officer (CCO) | Business owner | 5 | 5 | Manage Closely | Credit policy, approval rules, risk model |
| CTO / IT Director | Technical owner | 4 | 5 | Manage Closely | Architecture, security, integration |
| Product Owner | Prioritisation | 4 | 5 | Manage Closely | Roadmap, scope, go-live |
| Compliance / Legal | Internal regulator | 5 | 4 | Manage Closely | KYC/AML, lending and data-protection rules |
| Data Protection Officer (DPO) | Personal-data governance | 4 | 4 | Manage Closely | Consent, retention, data-subject rights, AI processing |
| Risk Management | Risk stakeholder | 4 | 4 | Manage Closely | Scoring model, NPL rate, limits |
| Internal Audit | Assurance | 4 | 2 | Keep Satisfied | Audit trail, logging, data integrity |
| State Bank of Vietnam (SBV) | External regulator | 5 | 2 | Keep Satisfied | Lending circulars, reporting |
| Business Analyst | Requirements lead | 3 | 5 | Keep Informed | Accuracy, traceability |
| Sales | Internal user | 3 | 4 | Keep Informed | Targets, customer experience |
| Loan Officer | End user | 2 | 5 | Keep Informed | Usability, workflow, speed |
| Borrower | External end user | 1 | 5 | Keep Informed | Rates, speed, transparency |
| Dev / QA team | Delivery | 2 | 5 | Keep Informed | Specs, APIs, test cases |
| CIC / credit bureau | Third party | 3 | 2 | Monitor | API uptime, data accuracy |
| Core banking vendor | Third party | 3 | 3 | Monitor | Integration spec, change windows |

### Corrections versus the training template

- The Board (Interest 3) was labelled "Manage Closely" while its strategy said "Keep Satisfied". Under a consistent rule it is **Keep Satisfied**.
- Borrowers (Interest 5, Power 1) sat in "Monitor". They belong in **Keep Informed**: low power but high interest.
- Added **DPO**: required by the personal-data protection regime for credit scoring and AI processing.

### Engagement strategy

| Quadrant | Approach | Channel |
|---|---|---|
| Manage Closely | Early sign-off on rules, weekly review, clear escalation | Meetings, Confluence/docs, issue tracker |
| Keep Satisfied | Periodic summaries; evidence packs (audit trail, compliance matrix) | Email, PDF |
| Keep Informed | Demos each sprint, feedback loop, training | Demo sessions, release notes |
| Monitor | Notify on integration changes | Email |

## 2. Roles in the application

| Role | Who | Notes |
|---|---|---|
| **Borrower** | External customer | Sees only their own data |
| **Loan Officer** | Staff | Works the queue; makes first-line decisions |
| **Supervisor/Admin** | Staff | Approves exceptions and large loans; maintains rules |

## 3. Permission matrix

Legend: **C** create, **R** read, **U** update, **D** delete, **-** no access, **own** only own records.

| Resource / action | Borrower | Loan Officer | Supervisor/Admin |
|---|---|---|---|
| Public loan calculator | R | R | R |
| Own profile | CRU (own) | CRU (own) | CRU (own) |
| Application (create / edit draft) | C, U (own, draft only) | C on behalf of a borrower | - |
| Application (view) | R (own) | R (all assigned or in queue) | R (all) |
| Officer queue (`GET /queue`) | - | R (unassigned and own) | R (all) |
| Application documents (upload) | C (own) | C | - |
| Application documents (view) | R (own) | R | R |
| AI review summary | - | R | R |
| CIC mock result | - | R | R |
| Decision: approve / reject / request info | - | Yes (within limits, see BR-10) | Yes (all, including exceptions) |
| Decision: approve >= 200M VND or exception | - | - | Yes |
| CSV bulk import | - | C | C |
| Income-type rules and thresholds | - | R | CRU |
| User management | - | - | CRU |
| Audit log | - | R (own actions) | R (all) |
| Export or delete "my data" | Yes (own) | - | Process request (view-only on others) |
| Operations dashboard | - | - | R |

### Authorization rules

1. A borrower must never read another borrower's application (enforced in the API, not just hidden in the UI).
2. A loan officer must not approve their own created-on-behalf application above the officer limit.
3. Decisions are immutable once recorded; corrections create a new decision entry.
4. Every read of a borrower's personal data by staff is logged.
5. Staff sessions have a short idle timeout; sensitive actions require re-authentication (stretch goal).

*Implementation note: the queue list is narrowed for officers (LF-010); `GET /applications/{id}` still lets officers read any file until LF-011 (decision D-016).*

*Traceability: stories LF-001, LF-002, LF-010, LF-016; compliance rows C-08 and C-12.*
