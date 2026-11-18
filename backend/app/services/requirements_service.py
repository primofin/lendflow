"""LF-007 document requirements and checklist (BR-06).

`evaluate` is a pure function: given the requirements, the documents on file and the
requirements an officer waived, it says which are satisfied, waived or missing. It checks the
*type* of uploaded documents only; whether "3 months of payslips" really covers three months
is for a human or the AI review (LF-009).
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound
from app.models.application import Application
from app.models.application_exception import ApplicationException
from app.models.document import Document
from app.models.requirement_rules import (
    IncomeTypeRule,
    RequiredDocumentOption,
    RequiredDocumentRule,
)
from app.schemas.requirements import ChecklistOut, ChecklistRequirementOut, PanelOut, RequirementOut


@dataclass(frozen=True)
class RequirementRule:
    id: uuid.UUID
    label: str
    mandatory: bool
    doc_types: tuple[str, ...]  # any ONE of these satisfies the requirement
    sort_order: int


@dataclass(frozen=True)
class ChecklistItem:
    rule: RequirementRule
    state: str  # "satisfied" | "waived" | "missing"
    document_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class ChecklistResult:
    status: str  # "complete" | "exception" | "incomplete"
    items: tuple[ChecklistItem, ...]


def evaluate(
    rules: Sequence[RequirementRule],
    documents: Sequence[tuple[uuid.UUID, str]],
    waived: set[uuid.UUID],
) -> ChecklistResult:
    """A document beats a waiver; only mandatory requirements decide the overall status."""
    items = []
    for rule in sorted(rules, key=lambda r: r.sort_order):
        matches = tuple(doc_id for doc_id, doc_type in documents if doc_type in rule.doc_types)
        if matches:
            state = "satisfied"
        elif rule.id in waived:
            state = "waived"
        else:
            state = "missing"
        items.append(ChecklistItem(rule=rule, state=state, document_ids=matches))

    mandatory_states = {i.state for i in items if i.rule.mandatory}
    if mandatory_states <= {"satisfied"}:
        status = "complete"
    elif mandatory_states <= {"satisfied", "waived"}:
        status = "exception"
    else:
        status = "incomplete"
    return ChecklistResult(status=status, items=tuple(items))


# --- loading rules -------------------------------------------------------------------------------


def get_income_rule(db: Session, income_type: str) -> IncomeTypeRule:
    rule = db.get(IncomeTypeRule, income_type)
    if rule is None:
        raise NotFound("Unknown income type")
    return rule


def load_requirements(db: Session, income_type: str) -> list[RequirementRule]:
    rules = db.scalars(
        select(RequiredDocumentRule)
        .where(RequiredDocumentRule.income_type == income_type)
        .order_by(RequiredDocumentRule.sort_order)
    ).all()
    options: dict[uuid.UUID, list[str]] = {r.id: [] for r in rules}
    for rule_id, doc_type in db.execute(
        select(RequiredDocumentOption.rule_id, RequiredDocumentOption.doc_type)
        .where(RequiredDocumentOption.rule_id.in_(options))
        .order_by(RequiredDocumentOption.doc_type)
    ):
        options[rule_id].append(doc_type)
    return [
        RequirementRule(
            id=r.id,
            label=r.label,
            mandatory=r.mandatory,
            doc_types=tuple(options[r.id]),
            sort_order=r.sort_order,
        )
        for r in rules
    ]


def panel(db: Session, income_type: str) -> PanelOut:
    """The list shown as soon as an income type is chosen (LF-007 AC1, AC2)."""
    income_rule = get_income_rule(db, income_type)
    requirements = load_requirements(db, income_type)

    def out(rule: RequirementRule) -> RequirementOut:
        return RequirementOut(id=rule.id, label=rule.label, doc_types=list(rule.doc_types))

    return PanelOut(
        income_type=income_type,
        label=income_rule.label,
        supervisor_always=income_rule.supervisor_always,
        needs_supervisor_if_missing=income_rule.needs_supervisor_if_missing,
        mandatory=[out(r) for r in requirements if r.mandatory],
        optional=[out(r) for r in requirements if not r.mandatory],
    )


def application_income_type(application: Application) -> str:
    if application.income_type is None:
        raise Conflict("This application has no income type, so it has no document checklist.")
    return application.income_type


def evaluate_application(db: Session, application: Application) -> ChecklistResult:
    income_type = application_income_type(application)
    documents = [
        (doc_id, doc_type)
        for doc_id, doc_type in db.execute(
            select(Document.id, Document.doc_type).where(Document.application_id == application.id)
        )
    ]
    waived = set(
        db.scalars(
            select(ApplicationException.requirement_id).where(
                ApplicationException.application_id == application.id
            )
        )
    )
    return evaluate(load_requirements(db, income_type), documents, waived)


def checklist(db: Session, application: Application) -> ChecklistOut:
    """LF-007 AC4: the application's checklist. Personal data and identities are not included."""
    result = evaluate_application(db, application)
    return ChecklistOut(
        application_id=application.id,
        income_type=application_income_type(application),
        status=result.status,
        requirements=[
            ChecklistRequirementOut(
                id=item.rule.id,
                label=item.rule.label,
                mandatory=item.rule.mandatory,
                state=item.state,
                doc_types=list(item.rule.doc_types),
                document_ids=list(item.document_ids),
            )
            for item in result.items
        ],
        exception_flag=application.exception_flag,
        supervisor_assigned=application.assigned_supervisor is not None,
    )
