"""LF-007: pure checklist logic. A requirement is met by ANY of its document types."""

import uuid

from app.services.requirements_service import RequirementRule, evaluate


def rule(label, doc_types, *, mandatory=True, order=0):
    return RequirementRule(
        id=uuid.uuid4(),
        label=label,
        mandatory=mandatory,
        doc_types=tuple(doc_types),
        sort_order=order,
    )


def doc(doc_type):
    return (uuid.uuid4(), doc_type)


NATIONAL_ID = rule("National ID", ["national_id"], order=1)
CONTRACT = rule("Contract or confirmation", ["labour_contract", "employer_confirmation"], order=2)
TAX = rule("Tax return", ["tax_return"], mandatory=False, order=3)


def states(result):
    return {item.rule.label: item.state for item in result.items}


def test_lf007_nothing_uploaded_means_everything_missing_and_incomplete():
    result = evaluate([CONTRACT, NATIONAL_ID, TAX], documents=[], waived=set())

    assert result.status == "incomplete"
    assert set(states(result).values()) == {"missing"}
    assert [i.rule.label for i in result.items] == [
        "National ID",
        "Contract or confirmation",
        "Tax return",
    ]


def test_lf007_all_mandatory_present_is_complete():
    national, contract = doc("national_id"), doc("labour_contract")

    result = evaluate([NATIONAL_ID, CONTRACT], documents=[national, contract], waived=set())

    assert result.status == "complete"
    assert states(result) == {"National ID": "satisfied", "Contract or confirmation": "satisfied"}
    assert result.items[0].document_ids == (national[0],)


def test_lf007_either_alternative_satisfies_an_or_requirement():
    for option in ("labour_contract", "employer_confirmation"):
        result = evaluate([CONTRACT], documents=[doc(option)], waived=set())

        assert result.status == "complete", option


def test_lf007_every_matching_document_is_listed():
    a, b = doc("labour_contract"), doc("employer_confirmation")

    result = evaluate([CONTRACT], documents=[a, b], waived=set())

    assert set(result.items[0].document_ids) == {a[0], b[0]}


def test_lf007_optional_documents_never_block_completeness():
    result = evaluate([NATIONAL_ID, TAX], documents=[doc("national_id")], waived=set())

    assert result.status == "complete"
    assert states(result)["Tax return"] == "missing"


def test_lf007_documents_of_unrelated_types_are_ignored():
    result = evaluate(
        [NATIONAL_ID], documents=[doc("business_licence"), doc("other")], waived=set()
    )

    assert result.status == "incomplete"


def test_lf007_waived_mandatory_with_everything_else_satisfied_is_an_exception():
    result = evaluate([NATIONAL_ID, CONTRACT], documents=[doc("national_id")], waived={CONTRACT.id})

    assert result.status == "exception"
    assert states(result)["Contract or confirmation"] == "waived"


def test_lf007_waiver_does_not_hide_other_missing_mandatory_documents():
    result = evaluate([NATIONAL_ID, CONTRACT], documents=[], waived={CONTRACT.id})

    assert result.status == "incomplete"
    assert states(result) == {"National ID": "missing", "Contract or confirmation": "waived"}


def test_lf007_a_waived_requirement_that_later_gets_its_document_shows_satisfied():
    result = evaluate(
        [NATIONAL_ID, CONTRACT],
        documents=[doc("national_id"), doc("labour_contract")],
        waived={CONTRACT.id},
    )

    assert states(result)["Contract or confirmation"] == "satisfied"
    assert result.status == "complete"


def test_lf007_waiving_an_optional_requirement_has_no_effect():
    result = evaluate([NATIONAL_ID, TAX], documents=[doc("national_id")], waived={TAX.id})

    assert result.status == "complete"


def test_lf007_no_mandatory_requirements_is_trivially_complete():
    assert evaluate([TAX], documents=[], waived=set()).status == "complete"
