# Business Rules

> **All thresholds and rates below are illustrative values for the fictional lender LendFlow.** They are configurable and must be confirmed by the (simulated) Chief Credit Officer before build. Rules marked **[OPEN]** need a stakeholder decision.

## 1. Product parameters

| ID | Rule | Value |
|---|---|---|
| BR-01 | Loan amount range | 1,000,000 to 500,000,000 VND |
| BR-02 | Terms offered | 6, 12, 24, 36, 60 months |
| BR-03 | Applicant age | 18 to 60 at application; maximum 65 at maturity |
| BR-04 | National ID format | 12 digits. Legacy 9-digit ID routed to manual review **[OPEN: confirm with Compliance]** |
| BR-05 | Interest (illustrative, reducing balance, annual) | Up to 12 months: 14%; 13 to 36 months: 16%; over 36 months: 18% |

### Repayment calculation (annuity, reducing balance)

```
r   = annual_rate / 12
PMT = P * r / (1 - (1 + r)^-n)
```

**Worked example** (used as a calculator test case): P = 100,000,000 VND, 24 months, 16%/year.

| Item | Value (VND) |
|---|---|
| Monthly payment | 4,896,311 |
| Total repaid | 117,511,465 |
| Total interest | 17,511,465 |
| Month 1 interest / principal | 1,333,333 / 3,562,978 |

For contrast, a **flat-rate** quote with the same nominal 16% gives 5,500,000 per month, because interest is charged on the original balance throughout. The calculator must state clearly which method it uses (see transparency requirement in the backlog, LF-003).

## 2. Eligibility and routing

| ID | Rule |
|---|---|
| BR-06 | Required documents depend on income type (table in section 3). |
| BR-07 | **DTI** = (existing monthly debt payments + new instalment) / verified monthly income. DTI <= 50% passes; above 50% routes to officer with a "high DTI" flag. |
| BR-08 | **CIC debt group:** group 1 passes; group 2 flags for officer attention; groups 3, 4 or 5 produce a "recommend reject" flag. The system never rejects automatically. |
| BR-09 | **Fast-track:** amount < 50,000,000 VND, salaried, CIC group 1, all mandatory documents present, DTI <= 40%. Officer confirms in one step; no supervisor needed. |
| BR-10 | **Supervisor approval required** when the amount is >= 200,000,000 VND, or any exception applies (missing mandatory document, freelance income without invoices, CIC group 2 or worse). |
| BR-11 | **SLA:** officer reviews within 4 business hours; supervisor within 24 hours; otherwise the item is escalated (LF-017). |

## 3. Documents required by income type

| Income type | Mandatory | Optional |
|---|---|---|
| Salaried | National ID; labour contract or employer confirmation; 3 months of payslips or bank statements | Tax return |
| Freelance | National ID; invoices or service contracts (last 3 months); 6 months of bank statements | Business licence; personal income tax return |
| Self-employed (household business) | National ID; 6 months of bank statements; business licence | Tax return |
| Rental income | National ID; rental contract; proof of ownership | Bank statements |
| Other | National ID; case-specific evidence; supervisor assigned automatically | n/a |

*Source: story LENDING-103 (elicitation workshop). Rule for freelance income acceptance **[OPEN]**: needs sign-off from the Chief Credit Officer and Risk.*

## 4. Decisions

| ID | Rule |
|---|---|
| BR-12 | Outcomes: **Approve**, **Reject**, **Request more information**, **Refer to supervisor**. |
| BR-13 | Every **rejection** must contain a reason code, a plain-language explanation, and the documents or conditions that could change the outcome. |
| BR-14 | Decisions are immutable; a correction is a new, linked entry. |
| BR-15 | The AI review is **advisory only**. A human decision is mandatory for every application, including fast-track. |

## 5. AI usage rules

| ID | Rule |
|---|---|
| BR-16 | For each AI output store: model name and version, prompt/config version, timestamp, input document references, and the output. |
| BR-17 | AI output shows per-field confidence; low-confidence fields are highlighted for human check. |
| BR-18 | AI must not use protected or irrelevant attributes in a recommendation (e.g. gender, ethnicity, religion). Prompts and tests enforce this. |
| BR-19 | AI cost per application and monthly total are logged; processing stops at the monthly cap. |
| BR-20 | In development and demos, a **mock mode** returns stored responses and costs nothing. |

## 6. Data and consent

| ID | Rule |
|---|---|
| BR-21 | No processing before explicit consent. The consent text lists each purpose, including **credit scoring and assessment** and **AI-assisted document processing**. |
| BR-22 | Borrowers can view, correct, export and request deletion of their data; requests are tracked with due dates. |
| BR-23 | Uploaded documents are retained for a configurable period (default 12 months after final decision in this demo) and then deleted. |
| BR-24 | Only synthetic data may be uploaded; the upload screen warns users. |

## 7. Open questions for stakeholders

1. What is the acceptance rule for freelance and self-employed income (CCO, Risk)?
2. How should legacy 9-digit IDs be handled (Compliance)?
3. What is the officer's own approval limit (suggested: up to 200,000,000 VND)?
4. What is the SLA for the (mock) CIC call and the timeout behaviour (IT)?
5. Which rate tiers apply by customer segment (Product)?

*Traceability: BR-01 to BR-05 feed LF-003; BR-06 to LF-007; BR-07 to BR-11 to LF-008, LF-009, LF-011, LF-017; BR-16 to BR-20 to LF-009; BR-21 to BR-24 to LF-004, LF-018.*
