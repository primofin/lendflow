"""Mark files that missed the supervisor SLA and queue the notices (LF-017, BR-11).

Usage:  uv run python -m scripts.sla_sweep
The queue and file views already do this when read; run this on a schedule so notices go out
even when nobody opens the app. Safe to run repeatedly.
"""

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.db import get_engine
from app.services import sla_service


def main() -> None:
    with Session(get_engine()) as db:
        marked = sla_service.sweep(db, now=utcnow())
    print(f"{len(marked)} file(s) newly overdue")


if __name__ == "__main__":
    main()
