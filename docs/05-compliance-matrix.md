# Compliance Matrix (Vietnam)

> **Educational document, not legal advice.** LendFlow is a fictional lender and portfolio project. The entries below were compiled from secondary sources (legal news sites, law-firm alerts) in **November 2026**. Before you quote any article number or effective date, check the **official consolidated text** (Vietnamese legal databases, State Bank of Vietnam website). Status column: **V** = found in secondary sources, confirm against official text; **R** = to research (not yet verified).

## How to use this matrix

Each row links **a legal requirement** to **a product feature**, **a user story** and **a test**, which is the traceability that regulators, auditors and hiring managers look for.

| ID | Source (as understood) | Requirement in plain words | LendFlow feature / design response | Story | Test idea | Status |
|---|---|---|---|---|---|---|
| C-01 | Circular 39/2016/TT-NHNN on lending by credit institutions (amended) | Lending follows defined steps (conditions, application, assessment, decision, disbursement, monitoring) with records | Workflow states and records for every step | LF-004, LF-009, LF-011 | State transitions follow the diagram; no skipped step | V |
| C-02 | Circular 06/2023/TT-NHNN (amends 39/2016; effective 1 Sep 2023), added rules for lending by electronic means | Electronic lending must cover the whole chain (application, assessment, decision, disbursement) with identity checks | End-to-end online flow; identity data checked; logged | LF-004 to LF-011 | End-to-end test of the online journey | V |
| C-03 | Circular 12/2024/TT-NHNN | Small loans (under 100 million VND) do not need a capital-use plan | Purpose field optional under threshold (configurable) | LF-004 | Submit 80M without purpose: accepted; 150M: required | V |
| C-04 | Circular 29/2026/TT-NHNN (30 Jun 2026, amends 39/2016) | Digital lending adds a know-your-customer check consistent with known customer information; some earlier e-lending articles repealed | KYC consistency check (ID vs. form data); **effective date to confirm** | LF-005, LF-006 | Mismatch between ID data and form triggers a flag | V |
| C-05 | Law on Credit Institutions 2024 (32/2024/QH15, effective 1 Jul 2024), Art. 15 | Non-mandatory insurance must not be tied to a loan | No insurance upsell or bundled consent in the flow | LF-004 | Automated check: no insurance field in the application | V |
| C-06 | Law on Credit Institutions 2024, Art. 102 | Simplified approval for small consumer loans | Fast-track routing (BR-09); still a human decision | LF-010, LF-011 | Fast-track file approved with one confirmation | V |
| C-07 | Decision 2345/QD-NHNN (from 1 Jul 2024); Circulars 17 and 18/2024/TT-NHNN (from 1 Jan 2025) | Biometric authentication for online transfers above 10M VND per transaction or 20M per day | Simulated face-match before large disbursement | LF-020 | Disbursement 12M requires the step; 5M does not | V |
| C-08 | Personal Data Protection Law 91/2025/QH15 (effective 1 Jan 2026); Decree 356/2025/ND-CP (replaces Decree 13/2023) | Consent with stated purposes (including credit scoring in finance); data-subject rights; AI-related processing provisions | Consent screen with purposes; rights page; AI processing log; retention | LF-004, LF-009, LF-018 | Submission blocked without consent; export and deletion requests work | V |
| C-09 | Law on Electronic Transactions 2023 (20/2023/QH15, effective 1 Jul 2024); Decree 23/2025 | Electronic contracts and signatures have legal value; types of e-signature defined | E-sign deferred (Won't); design keeps contract as a document entity | LF-015 | n/a (deferred) | V |
| C-10 | Circular 11/2021/TT-NHNN, with later changes (a secondary source cites Circular 31/2024/TT-NHNN from 1 Jul 2024) | Debts classified into 5 groups; groups 3 to 5 are bad debt | Mock CIC returns group 1 to 5; BR-08 routing | LF-008 | Group 3 yields "recommend reject" flag | V (confirm which circular is current) |
| C-11 | CIC credit-information rules (secondary sources) | Negative credit history is kept up to 5 years after full repayment | Mock CIC data model reflects this window | LF-008 | Seed data with 6-year-old negative record is ignored | V (not built in LF-008; see D-027) |
| C-12 | Decree 117/2018/ND-CP on confidentiality of customer information | Credit institutions must protect customer information and restrict its disclosure | RBAC, access logging, minimal disclosure | LF-002, LF-016 | Borrower cannot read another's file; staff reads are logged | V |
| C-13 | Anti-Money Laundering Law 2022 | KYC and monitoring duties for financial institutions | Out of scope for the MVP; list as future work | n/a | n/a | R |
| C-14 | Law on Protection of Consumer Rights 2023 | Fair, transparent terms and information to consumers | Calculator states method and rate; rejection explanation | LF-003, LF-011 | Calculator displays method and rate | R |
| C-15 | Civil Code 2015 (provisions on loan interest) | Limits and rules for interest in civil loans | Confirm applicability to credit institutions before stating any claim | n/a | n/a | R |
| C-16 | Rules for consumer finance companies (e.g. Circular 43/2016) | Specific rules for consumer-finance lenders | Decide whether LendFlow models a bank or a finance company; document it | n/a | n/a | R |

## Notes on the training documents

- The backlog document cites **Decree 130/2018** for e-contract legal value. Because the Law on Electronic Transactions was replaced in 2024 (effective 1 Jul 2024), verify whether that decree is still the correct reference; consider citing the 2023 law and its guiding decree.
- The stakeholder template cites **Circular 39** and **Circular 11**. Use the amended and current versions, and add the personal-data regime and the Law on Credit Institutions 2024.

## Maintenance

Review this matrix at each milestone and whenever a new circular appears. Add a "last verified" date per row once you have read the official text.
