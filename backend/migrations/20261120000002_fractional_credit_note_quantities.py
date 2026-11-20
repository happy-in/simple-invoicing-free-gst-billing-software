"""Store fractional credit note quantities without changing existing whole units."""

from sqlalchemy import text


def up(conn) -> None:
    # Keep enough integral digits for any quantity from the previous INTEGER column.
    conn.execute(text(
        "ALTER TABLE credit_note_items ALTER COLUMN quantity TYPE NUMERIC(13, 3)"
    ))
