"""Queue repayment reminders that are due (LF-014).

Usage:  uv run python -m scripts.send_reminders
Run it once a day. Each reminder is queued once, so running it more often is harmless.
"""

from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.db import get_engine
from app.services import reminder_service


def main() -> None:
    with Session(get_engine()) as db:
        queued = reminder_service.send_due_reminders(db, now=utcnow())
    print(f"{queued} reminder(s) queued")


if __name__ == "__main__":
    main()
