"""One-off helper to align the records table with the latest ORM schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import text
from sqlalchemy.engine import Connection

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.database import engine  # noqa: E402


@dataclass(frozen=True)
class ColumnPatch:
    name: str
    definition: str
    make_not_null: bool = True
    default_sql: str | None = None
    backfill_sql: str | None = None


COLUMN_PATCHES: tuple[ColumnPatch, ...] = (
    ColumnPatch(
        name="order_number",
        definition="VARCHAR(64)",
        backfill_sql="UPDATE records SET order_number = CONCAT('LEGACY-', id) WHERE order_number IS NULL",
    ),
    ColumnPatch(
        name="sales_channel",
        definition="VARCHAR(64)",
        default_sql="'Amazon'",
        backfill_sql="UPDATE records SET sales_channel = 'Amazon' WHERE sales_channel IS NULL",
    ),
    ColumnPatch(
        name="destination_market",
        definition="VARCHAR(64)",
        default_sql="'US'",
        backfill_sql="UPDATE records SET destination_market = 'US' WHERE destination_market IS NULL",
    ),
    ColumnPatch(
        name="currency",
        definition="VARCHAR(8)",
        default_sql="'USD'",
        backfill_sql="UPDATE records SET currency = 'USD' WHERE currency IS NULL",
    ),
    ColumnPatch(
        name="order_amount",
        definition="NUMERIC(12, 2)",
        default_sql="0",
        backfill_sql="UPDATE records SET order_amount = 0 WHERE order_amount IS NULL",
    ),
    ColumnPatch(
        name="tracking_number",
        definition="VARCHAR(64)",
        make_not_null=False,
    ),
    ColumnPatch(
        name="order_date",
        definition="TIMESTAMP WITH TIME ZONE",
        default_sql="CURRENT_TIMESTAMP",
        backfill_sql="UPDATE records SET order_date = CURRENT_TIMESTAMP WHERE order_date IS NULL",
    ),
)


def column_exists(conn: Connection, column_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'records' AND column_name = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return result.scalar() is not None


def constraint_exists(conn: Connection, constraint_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.table_constraints
            WHERE table_name = 'records' AND constraint_name = :constraint_name
            """
        ),
        {"constraint_name": constraint_name},
    )
    return result.scalar() is not None


def apply_column_patch(conn: Connection, patch: ColumnPatch) -> None:
    if column_exists(conn, patch.name):
        print(f"✓ Column {patch.name} already exists, skipping add.")
    else:
        conn.execute(text(f"ALTER TABLE records ADD COLUMN {patch.name} {patch.definition}"))
        print(f"+ Added column {patch.name} ({patch.definition}).")

    if patch.default_sql:
        conn.execute(text(f"ALTER TABLE records ALTER COLUMN {patch.name} SET DEFAULT {patch.default_sql}"))

    if patch.backfill_sql:
        conn.execute(text(patch.backfill_sql))

    if patch.make_not_null:
        if patch.default_sql:
            conn.execute(text(f"UPDATE records SET {patch.name} = {patch.default_sql} WHERE {patch.name} IS NULL"))
        conn.execute(text(f"ALTER TABLE records ALTER COLUMN {patch.name} SET NOT NULL"))


def ensure_unique_order_number(conn: Connection) -> None:
    constraint_name = "records_order_number_key"
    if constraint_exists(conn, constraint_name):
        print("✓ Unique constraint on order_number already exists.")
        return

    conn.execute(text("ALTER TABLE records ADD CONSTRAINT records_order_number_key UNIQUE (order_number)"))
    print("+ Added unique constraint for order_number.")


def run() -> None:
    with engine.begin() as conn:
        for patch in COLUMN_PATCHES:
            apply_column_patch(conn, patch)
        ensure_unique_order_number(conn)
    print("Schema upgrade completed.")


if __name__ == "__main__":
    run()
