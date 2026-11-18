"""LF-007: the seeded rules must equal docs/02-business-rules.md section 3 (BR-06)."""

from sqlalchemy import select

from app.models.document import DocType
from app.models.requirement_rules import (
    IncomeTypeRule,
    RequiredDocumentOption,
    RequiredDocumentRule,
)

# income_type: (label, supervisor_always, mandatory [(label, doc types)], optional [...])
EXPECTED = {
    "salaried": (
        "Salaried",
        False,
        [
            ("National ID", {"national_id"}),
            (
                "Labour contract or employer confirmation",
                {"labour_contract", "employer_confirmation"},
            ),
            ("Payslips or bank statements (last 3 months)", {"payslips", "bank_statements"}),
        ],
        [("Tax return", {"tax_return"})],
    ),
    "freelance": (
        "Freelance",
        False,
        [
            ("National ID", {"national_id"}),
            ("Invoices or service contracts (last 3 months)", {"invoices_contracts"}),
            ("Bank statements (last 6 months)", {"bank_statements"}),
        ],
        [
            ("Business licence", {"business_licence"}),
            ("Personal income tax return", {"tax_return"}),
        ],
    ),
    "self_employed": (
        "Self-employed (household business)",
        False,
        [
            ("National ID", {"national_id"}),
            ("Bank statements (last 6 months)", {"bank_statements"}),
            ("Business licence", {"business_licence"}),
        ],
        [("Tax return", {"tax_return"})],
    ),
    "rental": (
        "Rental income",
        False,
        [
            ("National ID", {"national_id"}),
            ("Rental contract", {"rental_contract"}),
            ("Proof of ownership", {"proof_of_ownership"}),
        ],
        [("Bank statements", {"bank_statements"})],
    ),
    "other": (
        "Other",
        True,
        [("National ID", {"national_id"}), ("Case-specific evidence", {"other"})],
        [],
    ),
}


def load(db, income_type):
    rules = db.scalars(
        select(RequiredDocumentRule)
        .where(RequiredDocumentRule.income_type == income_type)
        .order_by(RequiredDocumentRule.sort_order)
    ).all()
    result = {True: [], False: []}
    for r in rules:
        options = set(
            db.scalars(
                select(RequiredDocumentOption.doc_type).where(
                    RequiredDocumentOption.rule_id == r.id
                )
            )
        )
        result[r.mandatory].append((r.label, options))
    return result


def test_lf007_every_income_type_matches_the_business_rules_table(db):
    for income_type, (label, always, mandatory, optional) in EXPECTED.items():
        income_rule = db.get(IncomeTypeRule, income_type)
        loaded = load(db, income_type)

        assert income_rule.label == label, income_type
        assert income_rule.supervisor_always is always, income_type
        assert income_rule.needs_supervisor_if_missing is True, income_type
        assert loaded[True] == mandatory, income_type
        assert loaded[False] == optional, income_type


def test_lf007_exactly_the_five_documented_income_types_exist(db):
    assert set(db.scalars(select(IncomeTypeRule.income_type))) == set(EXPECTED)


def test_lf007_every_rule_option_is_a_known_document_type(db):
    known = {d.value for d in DocType}

    used = set(db.scalars(select(RequiredDocumentOption.doc_type)))

    assert used and used <= known


def test_lf007_every_requirement_has_at_least_one_option(db):
    for rule in db.scalars(select(RequiredDocumentRule)):
        options = db.scalars(
            select(RequiredDocumentOption).where(RequiredDocumentOption.rule_id == rule.id)
        ).all()
        assert options, rule.label


def test_lf007_every_income_type_requires_a_national_id(db):
    for income_type in EXPECTED:
        labels = [label for label, _ in load(db, income_type)[True]]
        assert "National ID" in labels, income_type


def test_lf007_rule_income_types_match_the_profile_income_types(db):
    from app.models.borrower_profile import IncomeType

    assert set(db.scalars(select(IncomeTypeRule.income_type))) == {i.value for i in IncomeType}
