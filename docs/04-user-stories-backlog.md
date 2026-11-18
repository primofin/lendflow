# Product Backlog and User Stories

Format: **As a / I want / So that**, with acceptance criteria in **Given / When / Then**.
Each story traces back to a pain point or source story (column "Source") and forward to code and tests (see [traceability](#traceability-convention)).

## 1. Backlog overview (MoSCoW)

| ID | Story | Source | Priority | Size | Status |
|---|---|---|---|---|---|
| LF-001 | Register and log in | New (access) | **Must** | 5 | Done |
| LF-002 | Role-based access control | New (RBAC, C-12) | **Must** | 5 | Done |
| LF-003 | Loan calculator | LOAN-01 / P1 | Should | 3 | Done |
| LF-004 | Submit application with consent | New (C-08) | **Must** | 8 | Done |
| LF-005 | Upload documents | LOAN-05 / P5 | **Must** | 5 | Done |
| LF-006 | AI extraction of ID fields (enter once) | LENDING-101 | Should | 5 | To do |
| LF-007 | Required documents by income type | LENDING-103 | **Must** | 8 | Done |
| LF-008 | Mock CIC check with progress | LENDING-102 | Should | 5 | To do |
| LF-009 | AI review summary (advisory) | New (core AI) | **Must** | 8 | To do |
| LF-010 | Officer queue | Elicitation (Gap 3) | **Must** | 5 | Done |
| LF-011 | Decision with reason code | P2 / homework | **Must** | 5 | To do |
| LF-012 | Borrower status tracker | LOAN-02 / P2 | **Must** | 5 | To do |
| LF-013 | CSV bulk import | New (file import) | Should | 5 | To do |
| LF-014 | Repayment schedule and email reminders | LOAN-04 / P4 | Could | 5 | To do |
| LF-015 | E-signature of contract | LOAN-03 / P3 | Won't (this release) | n/a | Won't |
| LF-016 | Audit log | New (C-01, Audit) | **Must** | 5 | Done |
| LF-017 | SLA escalation | US-005 | Could | 3 | To do |
| LF-018 | Data-subject rights | New (C-08) | Should | 5 | To do |
| LF-019 | Operations dashboard | Giao an (NPL report) | Could | 5 | To do |
| LF-020 | Biometric step simulation | New (C-07) | Could | 3 | To do |

**Status** is updated as each story is merged to `main`; decisions behind the built stories are in the [decisions log](08-decisions-log.md).

**MoSCoW ratio:** Must 10/20 = 50% (below the 60% guideline), Should 5, Could 4, Won't 1.

### Reconciliation notes versus the training documents

- **E-signature** appeared as *Must Have* in the MoSCoW matrix and *Medium* in the pain-point backlog. Decision: **Won't (this release)**. Real e-signature needs a certified provider and adds cost without proving new skills. The legal basis is documented in the compliance matrix instead.
- **Loan calculator** was "High" in the pain-point backlog and *Should* in the MoSCoW matrix. Decision: **Should**, but scheduled in week 3 because it is cheap and public.
- **LENDING-101** relied on a national-ID lookup API that does not exist in this project. Rewritten as **OCR / AI extraction from an uploaded image** (LF-006).

---

## 2. Must-have stories

### LF-001 Register and log in
**As a** first-time borrower, **I want** to create an account with email and password and log in, **so that** I can save and track my application.

- **Given** an unregistered email and a password meeting the policy (>= 10 characters), **when** I submit the form, **then** the account is created and I am logged in.
- **Given** an email already registered, **when** I register, **then** I see "This email is already registered" and no second account exists.
- **Given** wrong credentials, **when** I log in five times in a row, **then** the account is locked for 15 minutes and the event is logged.
- **Given** I am logged in, **when** the session is idle for 30 minutes, **then** I am logged out.

*Notes: passwords hashed; tokens short-lived with refresh. Size 5.*

### LF-002 Role-based access control
**As a** supervisor/admin, **I want** each user to access only what their role allows, **so that** customer data stays confidential and duties are separated.

- **Given** a borrower, **when** they request another borrower's application by ID, **then** the API returns 403 and the attempt is logged.
- **Given** a loan officer, **when** they try to approve an application at or above 200,000,000 VND, **then** the action is refused with the message "Supervisor approval required".
- **Given** a supervisor, **when** they open user management, **then** they can create users and assign roles; officers and borrowers cannot see this menu or call its API.

*Matrix: see [01-stakeholders-and-rbac.md](01-stakeholders-and-rbac.md). Size 5.*

### LF-004 Submit application with consent
**As a** borrower, **I want** to submit a loan application after reading what data will be used and why, **so that** I stay in control of my personal data.

- **Given** I have not ticked consent, **when** I try to submit, **then** submission is blocked and the consent checkbox is highlighted.
- **Given** the consent screen, **when** it is displayed, **then** it lists each purpose, including credit scoring and AI-assisted document processing, and the retention period.
- **Given** a valid amount (1M to 500M VND), a listed term and a complete form, **when** I submit, **then** the status becomes SUBMITTED and a consent record (version, timestamp) is stored.
- **Given** an amount outside the range, **when** I submit, **then** a red inline error appears under the field and nothing is saved.
- **Given** a loan under 100,000,000 VND, **when** the purpose field is left blank, **then** submission is still accepted (simplified small-loan rule, configurable).

*Size 8.*

### LF-005 Upload documents
**As a** borrower, **I want** to upload photos or PDFs of my documents, **so that** I do not have to visit a branch.

- **Given** a JPG, PNG or PDF up to 5 MB, **when** I upload it, **then** it is stored and listed with its type and upload time.
- **Given** a file over 5 MB or of an unsupported type, **when** I upload it, **then** I see a specific error naming the problem and how to fix it.
- **Given** the upload screen, **when** it loads, **then** it shows a notice that only synthetic/non-real documents may be used in this demo.
- **Given** an upload fails (network drop), **when** I retry, **then** no duplicate is created.

*Size 5.*

### LF-007 Required documents by income type
**As a** loan officer, **I want** the system to show the required documents as soon as an income type is chosen, **so that** I do not phone a supervisor or return incomplete files.

- **Given** income type "Freelance" or "Self-employed", **when** it is selected, **then** a panel lists mandatory and optional documents per [BR-06](02-business-rules.md).
- **Given** income type "Salaried", **when** it is selected, **then** only the standard document list appears.
- **Given** a freelance applicant without invoices, **when** the officer ticks "No invoices available", **then** the file is flagged "exception" and assigned to a supervisor automatically.
- **Given** all mandatory documents are present, **when** the officer opens the checklist, **then** it shows "Complete" in green.

*Dependency: rule sign-off ([OPEN] in business rules). Size 8.*

### LF-009 AI review summary (advisory)
**As a** loan officer, **I want** an AI-generated summary of the application with extracted data, missing items and risk flags, **so that** I can decide faster and with the evidence in one place.

- **Given** a submitted application with documents, **when** the review runs, **then** it returns extracted fields with confidence scores, a list of missing or inconsistent items, and a short plain-language summary.
- **Given** a field with confidence below the threshold, **when** the officer views the summary, **then** the field is highlighted for manual confirmation.
- **Given** any AI output, **when** it is stored, **then** model name, configuration version, timestamp and cost are recorded (BR-16, BR-19).
- **Given** the AI service fails or the monthly cap is reached, **when** the officer opens the file, **then** the application remains reviewable manually and shows "AI review unavailable".
- **Given** any application, **when** it reaches the decision step, **then** the system requires a human decision; the AI cannot approve or reject.

*Evaluation: 30-document synthetic eval set. Size 8.*

### LF-010 Officer queue
**As a** loan officer, **I want** a prioritised list of applications waiting for me, **so that** I handle the right files first.

- **Given** applications in IN_REVIEW, **when** I open the queue, **then** they are listed with applicant, amount, flags and age, sorted by oldest first by default.
- **Given** the queue, **when** I filter by status or flag (exception, high DTI, fast-track), **then** only matching rows are shown.
- **Given** an empty queue, **when** I open it, **then** I see "No applications waiting".
- **Given** 1,000 applications, **when** I open the queue, **then** the first page loads within 2 seconds.

*Size 5.*

### LF-011 Decision with reason code
**As a** loan officer or supervisor, **I want** to approve, reject, request information or refer, with a recorded reason, **so that** the borrower understands the outcome.

- **Given** a rejection, **when** I submit it without a reason code and explanation, **then** it is blocked.
- **Given** a rejection with reason code and explanation, **when** it is saved, **then** the borrower sees the explanation and the documents or conditions that could change the result.
- **Given** an "Approve" action on a fast-track file, **when** I confirm once, **then** the status becomes APPROVED without supervisor steps.
- **Given** a recorded decision, **when** a correction is needed, **then** a new linked entry is created and the original remains visible.

*Size 5.*

### LF-012 Borrower status tracker
**As a** borrower, **I want** to see the step my application is at, **so that** I do not need to call or visit.

- **Given** my submitted application, **when** I open it, **then** I see a progress bar: Received, Under assessment, Awaiting approval, Completed.
- **Given** each step, **when** it is displayed, **then** it shows the timestamp of the last update.
- **Given** the status becomes NEEDS_INFO, **when** I open the application, **then** the exact missing items are listed with an upload button.
- **Given** a status change, **when** it happens, **then** I receive an email notification.

*Size 5.*

### LF-016 Audit log
**As an** internal auditor (via supervisor/admin), **I want** every sensitive action recorded, **so that** I can reconstruct who did what and when.

- **Given** any status change, decision, document view by staff, or role change, **when** it occurs, **then** an entry is appended with actor, action, target, timestamp and IP.
- **Given** the audit log, **when** anyone attempts to edit or delete an entry through the application, **then** it is impossible (append-only).
- **Given** a supervisor, **when** they search the log by application ID, **then** the full history appears in chronological order.

*Size 5.*

---

## 3. Should-have stories

### LF-003 Loan calculator
**As a** prospective borrower, **I want** to enter an amount and term and see my monthly payment and total interest without logging in, **so that** I can decide how much to borrow.

- **Given** amount 100,000,000 VND, term 24 months, **when** I calculate, **then** it shows 4,896,311 VND per month, 117,511,465 total and 17,511,465 interest (rate 16%).
- **Given** a term not in the list, **when** I try to enter it, **then** only the allowed terms (6, 12, 24, 36, 60) can be selected.
- **Given** a non-numeric amount, **when** I enter it, **then** a red message appears below the field.
- **Given** a result, **when** it is displayed, **then** it states "reducing balance method" and shows the rate used.

*Result must appear within 1 second. Size 3.*

### LF-006 AI extraction of ID fields (enter once)
**As a** loan officer, **I want** the system to read the ID image and fill name, date of birth, ID number and address, **so that** nothing is typed more than once.

- **Given** a clear ID image, **when** extraction finishes, **then** name, date of birth, ID number and address are pre-filled with light-blue background, within 5 seconds.
- **Given** a blurred image, **when** extraction fails, **then** a clear message explains why and how to retake the photo.
- **Given** pre-filled fields, **when** I edit one, **then** my value replaces it and the change is logged.
- **Given** an ID number that is not 12 digits, **when** I leave the field, **then** an inline error appears.

*Size 5.*

### LF-008 Mock CIC check with progress
**As a** loan officer, **I want** to see progress and an estimated time while the credit check runs, **so that** I can reassure the customer.

- **Given** the check starts, **when** it runs, **then** a progress bar and "about N seconds remaining" are shown and I can keep using other screens.
- **Given** the check completes, **when** results arrive, **then** the debt group (1 to 5) and summary are shown.
- **Given** the mock service times out, **when** the timeout is reached, **then** a clear message is shown, the file is saved, and the check retries automatically.

*Size 5.*

### LF-013 CSV bulk import
**As a** loan officer, **I want** to import many applications from a CSV, **so that** batch intake is quick.

- **Given** a valid CSV matching the template, **when** I import it, **then** all valid rows become DRAFT applications and a summary shows counts.
- **Given** rows with errors, **when** I import, **then** valid rows are imported and a downloadable error report lists row numbers and reasons.
- **Given** a file over 2 MB or with the wrong columns, **when** I upload it, **then** it is rejected with a specific message.
- **Given** the same file imported twice, **when** I import again, **then** duplicates are detected and skipped.

*Size 5.*

### LF-018 Data-subject rights
**As a** borrower, **I want** to view, correct, export and request deletion of my data, **so that** I can exercise my rights.

- **Given** I open "My data", **when** the page loads, **then** I see all personal data held and the purposes.
- **Given** I request an export, **when** it is ready, **then** I can download a machine-readable file.
- **Given** I request deletion, **when** I confirm, **then** a request with a due date is created and visible to the supervisor/admin.
- **Given** an active application, **when** I request deletion, **then** I am told what must be retained and why.

*Size 5.*

---

## 4. Could-have and Won't-have (summary)

| ID | Story | Key acceptance criteria |
|---|---|---|
| LF-014 | Repayment schedule and email reminders | Schedule shows due date, principal, interest; reminder emails 7 and 1 days before; opt-out in settings |
| LF-017 | SLA escalation | Applications waiting > 24 h at supervisor move to "overdue" and notify the admin; breach is logged |
| LF-019 | Operations dashboard | Applications by status, average decision time, approval rate, AI cost per application; filter by date range |
| LF-020 | Biometric step simulation | Disbursement over 10M VND requires a (simulated) face match; failure blocks the action and logs it |
| LF-015 | **E-signature (Won't, this release)** | Documented in the compliance matrix; revisit with a certified provider |

---

## Traceability convention

Every requirement ID appears in four places:

1. This backlog (story and acceptance criteria)
2. The API route or UI component (code comment or docstring: `# LF-012`)
3. Test names (e.g. `test_lf012_status_tracker_shows_four_steps`)
4. Commit messages (e.g. `feat(LF-012): add status timeline`)

| Pain point | Story | Epic |
|---|---|---|
| P1 Do not know how much I can borrow | LF-003 | Loan calculator |
| P2 Do not know where my application is / why rejected | LF-011, LF-012 | Status and decisions |
| P3 Must go to branch to sign | LF-015 (deferred) | E-contract |
| P4 Forget due dates | LF-014 | Repayment management |
| P5 Upload fails, unclear reason | LF-005, LF-006 | Documents and extraction |
| Officer: ID typed 3 times | LF-006 | Documents and extraction |
| Officer: CIC wait | LF-008 | Credit check |
| Officer: phoning supervisor for freelance income | LF-007 | Rules |
| Officer: unknown supervisor status; 3-day waits | LF-010, LF-017 | Workflow |
