"""The four borrower-facing steps and the statuses behind them (docs/03, from LOAN-02).

Pure data, shared by the tracker and the notification emails. "REFERRED" is shown as
"Awaiting approval"; the word "referred" and the supervisor never reach the borrower.
"""

from app.models.application import ApplicationStatus as S

STEPS: tuple[tuple[str, frozenset[str]], ...] = (
    ("Received", frozenset({S.SUBMITTED})),
    ("Under assessment", frozenset({S.IN_REVIEW, S.NEEDS_INFO})),
    ("Awaiting approval", frozenset({S.REFERRED})),
    ("Completed", frozenset({S.APPROVED, S.REJECTED})),
)


def step_index(status: str) -> int:
    """Index of the step a status belongs to, or -1 (e.g. DRAFT: nothing reached yet)."""
    for index, (_, statuses) in enumerate(STEPS):
        if status in statuses:
            return index
    return -1


def step_label(status: str) -> str:
    index = step_index(status)
    return STEPS[index][0] if index >= 0 else "Draft"
