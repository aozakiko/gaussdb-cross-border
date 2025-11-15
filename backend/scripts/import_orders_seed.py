"""Load CSV seed orders into the records table."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402


@dataclass
class ImportStats:
    created: int = 0
    skipped: int = 0

    def __iadd__(self, other: "ImportStats") -> "ImportStats":
        self.created += other.created
        self.skipped += other.skipped
        return self


def load_existing_order_numbers(session) -> set[str]:
    rows = session.execute(select(models.Record.order_number))
    return {row[0] for row in rows if row[0]}


def parse_row(row: dict[str, str]) -> models.Record:
    order_amount = Decimal(row["order_amount"]).quantize(Decimal("0.01"))
    order_date = datetime.fromisoformat(row["order_date"])
    return models.Record(
        title=row["title"],
        description=row.get("description"),
        status=row["status"],
        priority=int(row["priority"]),
        owner=row["owner"],
        order_number=row["order_number"],
        sales_channel=row["sales_channel"],
        destination_market=row["destination_market"],
        currency=row["currency"],
        order_amount=order_amount,
        tracking_number=row.get("tracking_number") or None,
        order_date=order_date,
    )


def import_csv(csv_path: Path) -> ImportStats:
    stats = ImportStats()
    with SessionLocal() as session:
        existing = load_existing_order_numbers(session)
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                order_number = row["order_number"]
                if order_number in existing:
                    stats.skipped += 1
                    continue
                record = parse_row(row)
                session.add(record)
                stats.created += 1
        session.commit()
    return stats


def main() -> None:
    csv_path = ROOT.parent / "data" / "orders_seed.csv"
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")

    stats = import_csv(csv_path)
    print(f"Created {stats.created} records, skipped {stats.skipped} duplicates.")


if __name__ == "__main__":
    main()
