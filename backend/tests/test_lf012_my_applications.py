"""LF-012 (F3): a borrower can list their own applications to return to the tracker."""

from app.models.user import Role

from .test_lf004_submit import submit


def test_lf012_borrower_lists_only_own_applications_newest_first(client, make_user, clock):
    _, mine = make_user(Role.BORROWER)
    _, theirs = make_user(Role.BORROWER)
    first = submit(client, mine).json()["id"]
    clock.advance(minutes=5)
    second = submit(client, mine).json()["id"]
    other = submit(client, theirs).json()["id"]

    body = client.get("/applications", headers=mine).json()

    ids = [a["id"] for a in body]
    assert ids == [second, first]
    assert other not in ids


def test_lf012_empty_list_for_new_borrower(client, make_user):
    _, headers = make_user(Role.BORROWER)

    response = client.get("/applications", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_lf012_list_requires_login(client):
    assert client.get("/applications").status_code == 401


def test_lf012_staff_cannot_use_the_borrower_list(client, make_user):
    for role in (Role.OFFICER, Role.SUPERVISOR):
        _, headers = make_user(role)
        assert client.get("/applications", headers=headers).status_code == 403
