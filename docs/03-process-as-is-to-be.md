# Process Analysis: As-Is and To-Be

> The diagrams below are written in **Mermaid** so they render on GitHub and can be version-controlled. For the BPMN 2.0 deliverable required by the bootcamp homework, redraw them in **draw.io** (BPMN shapes, swimlanes, gateways) using these as the specification, and export PNGs into `docs/img/`.

## 1. As-Is: current lending process (paper and manual)

Swimlanes: Customer, Loan Officer (RM), Credit Analyst/Supervisor, Manager.

```mermaid
flowchart TD
  subgraph CUS[Customer]
    A1([Start: needs a loan]) --> A2[Bring paper documents to branch]
    A9[Sign paper contract] --> A10([End: funds released])
    A5[Re-submit missing documents]
  end
  subgraph LO[Loan Officer / RM]
    B1[Receive documents] --> B2[Check against Excel checklist]
    B2 --> G1{Documents complete?}
    G1 -- No --> A5
    A5 --> B2
    G1 -- Yes --> B3[Key data into core system<br/>ID typed 3 times]
    B3 --> B4[Run CIC check<br/>wait 3-7 min, no progress bar]
    B4 --> B5[Copy results to Excel and assess manually]
    B5 --> B6[Email file to supervisor]
    B6 --> B7[Phone supervisor to ask if viewed]
    B8[Notify customer by phone or SMS<br/>no standard template]
  end
  subgraph CA[Credit Analyst / Supervisor]
    C1[Review file] --> G2{Credit approval?}
    G2 -- Reject --> B8
    G2 -- Approve --> M1
  end
  subgraph MG[Manager]
    M1[Final review] --> G3{Manager approval?}
    G3 -- Reject --> B8
    G3 -- Approve --> B8
  end
  A2 --> B1
  B7 --> C1
  B8 --> A9
```

### As-Is pain points (from elicitation)

| # | Step | Pain point | Root cause | Addressed by |
|---|---|---|---|---|
| 1 | Documents | Missing documents discovered late; customer returns | No automated checklist | LF-007 |
| 2 | Data entry | ID typed 3 times | No data sharing between forms | LF-006 |
| 3 | CIC check | 3-7 minute wait with no feedback | No progress indicator | LF-008 |
| 4 | Assessment | Copying between screens and Excel | No integrated view | LF-009 |
| 5 | Hand-off | Unknown whether supervisor saw the file | No tracking or notification | LF-012 |
| 6 | Approval | Files wait up to 3 days | No SLA or escalation | LF-017 |
| 7 | Notification | Inconsistent messages to customers | No templates | LF-011 |
| 8 | Non-standard income | About 30% of files need a phone call | No rule for freelance / self-employed | LF-007 |
| 9 | Rejection | Customer gets no reason | No reason-code requirement | LF-011 |
| 10 | Governance | No audit trail | Manual steps | LF-016 |

## 2. To-Be: LendFlow process

Swimlanes: Customer, System (including the AI agent), Loan Officer, Supervisor.

```mermaid
flowchart TD
  subgraph CUS[Customer]
    A1([Start: opens calculator]) --> A2[Apply online and give consent]
    A2 --> A3[Upload documents]
    A8[Provide extra info]
    A12[Track status in app] --> A13([End])
  end
  subgraph SYS[System and AI agent]
    S1[Validate data automatically] --> S2[Extract ID fields from images<br/>pre-fill form]
    S2 --> G1{Required documents complete?}
    G1 -- No --> A8
    A8 --> S1
    G1 -- Yes --> S3[Call mock CIC with progress indicator]
    S3 --> S4[Compute DTI, apply business rules]
    S4 --> S5[AI writes review summary and flags]
    S5 --> G2{Fast-track criteria met?}
  end
  subgraph LO[Loan Officer]
    L1[Review summary and evidence] --> G3{Officer decision}
    G3 -- Request info --> A8
    G3 -- Reject with reason code --> N1
    G3 -- Approve --> G4{Needs supervisor?}
    G3 -- Refer --> H1
    G4 -- No --> N1
  end
  subgraph SUP[Supervisor]
    H1[Review exception or large loan] --> G5{Supervisor decision}
    G5 -- Approve --> N1
    G5 -- Reject --> N1
    G5 -- Request info --> A8
  end
  subgraph NOTIF[System notifications]
    N1[Record decision, notify customer, write audit log] --> A12
  end
  A3 --> S1
  G2 -- Yes --> L1
  G2 -- No --> L1
  G4 -- Yes --> H1
```

Notes:

- Fast-track (BR-09) changes **routing**, not the need for a human decision. It sends the file to the officer with a "one-step confirm" view and skips the supervisor.
- Every transition writes an **audit log** entry (LF-016).

## 3. Gap analysis (As-Is to To-Be)

| Dimension | As-Is | To-Be | Gap closed by |
|---|---|---|---|
| Intake | Paper | Online application with consent | LF-004, LF-005 |
| Data entry | Typed repeatedly | Extracted once, editable | LF-006 |
| Document check | Excel checklist | Rules by income type | LF-007 |
| Credit check | Opaque wait | Progress with estimate | LF-008 |
| Assessment | Manual copy to Excel | AI summary + rules | LF-009 |
| Routing | Email and phone | Queue, thresholds, escalation | LF-010, LF-017 |
| Decision | Unstructured | Four outcomes with reason codes | LF-011 |
| Customer feedback | Phone call | Live status tracker | LF-012 |
| Governance | None | Immutable audit log | LF-016 |

## 4. Application status state machine

```mermaid
stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> SUBMITTED: borrower submits with consent
  SUBMITTED --> NEEDS_INFO: documents incomplete
  NEEDS_INFO --> SUBMITTED: borrower resubmits
  SUBMITTED --> IN_REVIEW: checks done, queued for officer
  IN_REVIEW --> NEEDS_INFO: officer requests info
  IN_REVIEW --> REFERRED: officer refers
  IN_REVIEW --> APPROVED: officer approves (within limit)
  IN_REVIEW --> REJECTED: officer rejects with reason
  REFERRED --> APPROVED: supervisor approves
  REFERRED --> REJECTED: supervisor rejects
  REFERRED --> NEEDS_INFO: supervisor requests info
  DRAFT --> WITHDRAWN: borrower withdraws
  SUBMITTED --> WITHDRAWN
  NEEDS_INFO --> WITHDRAWN
  APPROVED --> [*]
  REJECTED --> [*]
  WITHDRAWN --> [*]
```

**Borrower-facing status mapping** (from LOAN-02): Received (SUBMITTED) → Under assessment (IN_REVIEW, NEEDS_INFO) → Awaiting approval (REFERRED) → Completed (APPROVED, REJECTED).
