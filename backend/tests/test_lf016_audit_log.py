"""LF-016 Audit log: search by application, access rules, entry contents (docs/01, docs/04)."""

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.user import Role

from .test_lf004_submit import submit
from .test_lf005_upload import JPEG, upload

EXPECTED_KEYS = {
    "seq",
    "id",
    "created_at",
    "actor_id",
    "actor_email",
    "actor_role",
    "action",
    "target_type",
    "target_id",
    "application_id",
    "ip_address",
}


def search(client, headers, **params):
    return client.get("/audit-logs", headers=headers, params=params)


def actions(response):
    return [e["action"] for e in response.json()]


def new_application(client, make_user):
    owner, headers = make_user(Role.BORROWER)
    response = submit(client, headers)
    assert response.status_code == 201
    return owner, headers, response.json()["id"]


@pytest.fixture
def story(client, make_user):
    """One application with a full history, plus a second application that must stay separate."""
    owner, owner_headers, app_id = new_application(client, make_user)
    document = upload(client, owner_headers, app_id, JPEG).json()
    officer, officer_headers = make_user(Role.OFFICER)
    client.get(f"/applications/{app_id}/documents", headers=officer_headers)
    client.get(f"/applications/{app_id}/documents/{document['id']}/file", headers=officer_headers)
    intruder, intruder_headers = make_user(Role.BORROWER)
    client.get(f"/applications/{app_id}", headers=intruder_headers)
    _, other_headers, other_app = new_application(client, make_user)
    upload(client, other_headers, other_app, JPEG)
    supervisor, supervisor_headers = make_user(Role.SUPERVISOR)
    return {
        "app_id": app_id,
        "document_id": document["id"],
        "other_app": other_app,
        "owner": owner,
        "officer": officer,
        "officer_headers": officer_headers,
        "intruder": intruder,
        "supervisor": supervisor,
        "supervisor_headers": supervisor_headers,
        "owner_headers": owner_headers,
    }


# --- AC3: full history of one application, in order ----------


def test_lf016_search_by_application_returns_full_history_in_order(client, story):
    response = search(client, story["supervisor_headers"], application_id=story["app_id"])

    assert response.status_code == 200
    assert actions(response) == [
        "consent.give",
        "application.submit",
        "document.upload",
        "document.list",
        "document.download",
        "application.access_denied",
    ]


def test_lf016_history_includes_document_entries_and_excludes_other_applications(client, story):
    body = search(client, story["supervisor_headers"], application_id=story["app_id"]).json()

    assert {e["application_id"] for e in body} == {story["app_id"]}
    upload_entry = next(e for e in body if e["action"] == "document.upload")
    assert upload_entry["target_type"] == "document"
    assert upload_entry["target_id"] == story["document_id"]
    other = search(client, story["supervisor_headers"], application_id=story["other_app"]).json()
    assert story["document_id"] not in {e["target_id"] for e in other}


def test_lf016_entries_with_identical_timestamps_still_come_back_in_insertion_order(client, story):
    # The fake clock never advances, so every entry has the same created_at.
    body = search(client, story["supervisor_headers"]).json()

    assert len({e["created_at"] for e in body}) == 1
    assert [e["seq"] for e in body] == sorted(e["seq"] for e in body)
    assert len({e["seq"] for e in body}) == len(body)


@pytest.mark.parametrize("page_size", [1, 2, 3, 5])
def test_lf016_paging_never_skips_or_repeats_an_entry(client, story, page_size):
    everything = search(client, story["supervisor_headers"], limit=200).json()

    collected, offset = [], 0
    while True:
        page = search(client, story["supervisor_headers"], limit=page_size, offset=offset).json()
        collected += page
        if len(page) < page_size:
            break
        offset += page_size

    assert [e["id"] for e in collected] == [e["id"] for e in everything]


@pytest.mark.parametrize(("limit", "ok"), [(1, True), (200, True), (0, False), (201, False)])
def test_lf016_limit_bounds(client, story, limit, ok):
    response = search(client, story["supervisor_headers"], limit=limit)

    assert (response.status_code == 200) is ok
    if not ok:
        assert "limit" in response.text


# --- Filters ----------


def test_lf016_filter_by_actor(client, story):
    body = search(client, story["supervisor_headers"], actor_id=str(story["officer"].id)).json()

    assert body and {e["actor_id"] for e in body} == {str(story["officer"].id)}


def test_lf016_filter_by_action(client, story):
    body = search(client, story["supervisor_headers"], action="document.upload").json()

    assert len(body) == 2 and {e["action"] for e in body} == {"document.upload"}


def test_lf016_filter_by_time_range(client, story, clock):
    headers, target = story["supervisor_headers"], story["intruder"].id
    # Steps stay under the 30-minute idle timeout so the supervisor's session survives.
    before = clock().isoformat()
    clock.advance(minutes=20)
    client.patch(f"/users/{target}/role", headers=headers, json={"role": "officer"})
    clock.advance(seconds=1)  # keep the boundary clear of both entries
    between = clock().isoformat()
    clock.advance(minutes=20)
    client.patch(f"/users/{target}/role", headers=headers, json={"role": "borrower"})
    role_changes = {"action": "user.role_change"}

    from_start = search(client, headers, **role_changes, **{"from": before}).json()
    first_only = search(client, headers, **role_changes, **{"from": before}, to=between).json()
    second_only = search(client, headers, **role_changes, **{"from": between}).json()
    before_all = search(client, headers, **role_changes, to=before).json()

    assert len(from_start) == 2
    assert len(first_only) == 1 and len(second_only) == 1
    assert first_only[0]["id"] != second_only[0]["id"]
    assert before_all == []


def test_lf016_time_range_is_inclusive_at_both_ends(client, story):
    headers = story["supervisor_headers"]
    stamp = search(client, headers, action="application.submit").json()[0]["created_at"]

    exact = search(client, headers, action="application.submit", **{"from": stamp}, to=stamp)

    assert exact.status_code == 200 and len(exact.json()) >= 1
    assert all(e["created_at"] == stamp for e in exact.json())


def test_lf016_invalid_filter_values_rejected(client, story):
    headers = story["supervisor_headers"]

    assert search(client, headers, application_id="not-a-uuid").status_code == 422
    assert search(client, headers, actor_id="nope").status_code == 422
    assert search(client, headers, **{"from": "yesterday-ish"}).status_code == 422


# --- Access (permission matrix: supervisor all, officer own actions) ----------


def test_lf016_supervisor_sees_entries_from_every_actor(client, story):
    body = search(client, story["supervisor_headers"], limit=200).json()

    assert len({e["actor_id"] for e in body}) >= 4


def test_lf016_officer_sees_only_their_own_actions(client, story):
    body = search(client, story["officer_headers"], limit=200).json()

    assert body and {e["actor_id"] for e in body} == {str(story["officer"].id)}


def test_lf016_officer_cannot_widen_the_view_by_filtering_on_someone_else(client, story):
    body = search(client, story["officer_headers"], actor_id=str(story["owner"].id)).json()

    assert body == []


def test_lf016_officer_searching_an_application_sees_only_their_own_entries_on_it(client, story):
    body = search(client, story["officer_headers"], application_id=story["app_id"]).json()

    assert actions_of(body) == ["document.list", "document.download"]


def actions_of(entries):
    return [e["action"] for e in entries]


def test_lf016_borrower_is_refused_and_the_refusal_is_audited(client, db, story):
    response = search(client, story["owner_headers"])

    assert response.status_code == 403
    denied = db.scalars(
        select(AuditLog).where(
            AuditLog.action == "access.denied", AuditLog.actor_id == story["owner"].id
        )
    ).all()
    assert any(d.target_type == "route:/audit-logs" for d in denied)


def test_lf016_unauthenticated_request_401(client):
    assert client.get("/audit-logs").status_code == 401


# --- AC1: what an entry contains ----------


def test_lf016_entries_carry_actor_action_target_time_and_ip(client, story):
    body = search(client, story["supervisor_headers"], application_id=story["app_id"]).json()

    for entry in body:
        assert set(entry) == EXPECTED_KEYS
        assert entry["actor_id"] and entry["actor_email"] and entry["actor_role"]
        assert entry["action"] and entry["target_type"] and entry["target_id"]
        assert entry["created_at"] and entry["ip_address"]


def test_lf016_status_change_is_recorded_with_actor_and_application(client, story):
    submit_entry = next(
        e
        for e in search(client, story["supervisor_headers"], action="application.submit").json()
        if e["application_id"] == story["app_id"]
    )

    assert submit_entry["actor_id"] == str(story["owner"].id)
    assert submit_entry["actor_role"] == "borrower"
    assert submit_entry["target_id"] == story["app_id"]


def test_lf016_role_change_is_recorded(client, story):
    headers = story["supervisor_headers"]
    client.patch(f"/users/{story['intruder'].id}/role", headers=headers, json={"role": "officer"})

    (entry,) = search(client, headers, action="user.role_change").json()

    assert entry["actor_id"] == str(story["supervisor"].id)
    assert entry["target_type"] == "user" and entry["target_id"] == str(story["intruder"].id)
    assert entry["ip_address"] and entry["application_id"] is None


def test_lf016_staff_document_view_is_recorded(client, story):
    entries = search(client, story["supervisor_headers"], action="document.download").json()

    (entry,) = entries
    assert entry["actor_id"] == str(story["officer"].id)
    assert entry["target_id"] == story["document_id"]
    assert entry["application_id"] == story["app_id"]


def test_lf016_response_never_contains_personal_data_from_applications(client, story):
    text = search(client, story["supervisor_headers"], limit=200).text

    assert "012345678901" not in text  # national id
    assert "Nguyen Van An" not in text  # full name
    assert "Home renovation" not in text  # purpose
