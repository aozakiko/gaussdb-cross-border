"""Flink job wrappers for analytics."""

from __future__ import annotations

from sqlalchemy import func, select

from ..config import get_settings
from ..database import SessionLocal
from ..models import Record

try:  # pragma: no cover - optional dependency for runtime environment
    from pyflink.table import DataTypes, EnvironmentSettings, TableEnvironment
    from pyflink.table.expressions import col
except Exception:  # pragma: no cover - pyflink missing locally
    TableEnvironment = None


def _sql_fallback(reason: str):
    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(Record)) or 0
        status_rows = db.execute(select(Record.status, func.count()).group_by(Record.status)).all()
        owner_rows = db.execute(select(Record.owner, func.count()).group_by(Record.owner)).all()

    return {
        "total_records": total,
        "by_status": {row[0] or "unknown": row[1] for row in status_rows},
        "by_owner": {row[0] or "未分配": row[1] for row in owner_rows},
        "engine": "sql_fallback",
        "detail": reason,
    }


def _collect_dimension_counts(table, column_name: str):
    result = (
        table.group_by(col(column_name))
        .select(col(column_name), col(column_name).count.alias("cnt"))
        .execute()
        .collect()
    )
    return {row[0]: row[1] for row in result}


def run_flink_summary():
    settings = get_settings()

    if TableEnvironment is None:
        return _sql_fallback("未安装 PyFlink")

    with SessionLocal() as db:
        rows = db.execute(select(Record.status, Record.owner)).all()

    if not rows:
        return {
            "total_records": 0,
            "by_status": {},
            "by_owner": {},
            "engine": "flink",
            "detail": "records 表暂无数据",
        }

    normalized_rows = [
        (
            row[0] or "unknown",
            row[1] or "未分配",
        )
        for row in rows
    ]

    try:
        env_settings = EnvironmentSettings.in_batch_mode()
        table_env = TableEnvironment.create(env_settings)
        table_env.get_config().set("parallelism.default", str(settings.flink_parallelism))

        dataset_table = table_env.from_elements(
            normalized_rows,
            DataTypes.ROW(
                [
                    DataTypes.FIELD("status", DataTypes.STRING()),
                    DataTypes.FIELD("owner", DataTypes.STRING()),
                ]
            ),
        )

        status_counts = _collect_dimension_counts(dataset_table, "status")
        owner_counts = _collect_dimension_counts(dataset_table, "owner")

        return {
            "total_records": len(normalized_rows),
            "by_status": status_counts,
            "by_owner": owner_counts,
            "engine": "flink",
            "detail": None,
        }
    except Exception as exc:  # pragma: no cover - depends on runtime Flink env
        return _sql_fallback(f"Flink 作业失败: {exc.__class__.__name__}")
