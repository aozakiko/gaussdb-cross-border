"""Spark job wrappers for analytics."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select

from ..config import get_settings
from ..database import SessionLocal
from ..models import Record

try:  # pragma: no cover - optional dependency for runtime environment
    from pyspark.sql import SparkSession
except Exception:  # pragma: no cover - pyspark missing locally
    SparkSession = None


def _build_jdbc_url(sqlalchemy_url: str) -> str:
    if sqlalchemy_url.startswith("postgresql+psycopg2"):
        return sqlalchemy_url.replace("postgresql+psycopg2", "jdbc:postgresql", 1)
    if sqlalchemy_url.startswith("postgresql"):
        return sqlalchemy_url.replace("postgresql", "jdbc:postgresql", 1)
    if sqlalchemy_url.startswith("gaussdb"):
        return sqlalchemy_url.replace("gaussdb", "jdbc:gaussdb", 1)
    return sqlalchemy_url


def _sql_fallback(reason: str):
    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(Record)) or 0
        status_rows = db.execute(select(Record.status, func.count()).group_by(Record.status)).all()
        owner_rows = db.execute(select(Record.owner, func.count()).group_by(Record.owner)).all()

    return {
        "total_records": total,
        "by_status": {row[0]: row[1] for row in status_rows},
        "by_owner": {row[0]: row[1] for row in owner_rows},
        "engine": "sql_fallback",
        "detail": reason,
    }


def run_spark_summary():
    settings = get_settings()

    if SparkSession is None:
        return _sql_fallback("未安装 PySpark")

    jdbc_url = _build_jdbc_url(settings.get_database_url())
    spark = None

    try:
        spark = (
            SparkSession.builder.appName(settings.spark_app_name)
            .master(settings.spark_master)
            .config("spark.jars", settings.spark_jar_path or "")
            .getOrCreate()
        )

        reader = (
            spark.read.format("jdbc")
            .option("url", jdbc_url)
            .option("dbtable", "records")
            .option("user", settings.gauss_user)
            .option("password", settings.gauss_password)
        )
        if settings.gauss_sslmode:
            reader = reader.option("sslmode", settings.gauss_sslmode)

        df = reader.load()
        if df.head(1):
            total_records = df.count()
            by_status = {row[0]: row[1] for row in df.groupBy("status").count().collect()}
            by_owner = {row[0]: row[1] for row in df.groupBy("owner").count().collect()}
        else:
            total_records = 0
            by_status = {}
            by_owner = {}

        return {
            "total_records": total_records,
            "by_status": by_status,
            "by_owner": by_owner,
            "engine": "spark",
            "detail": None,
        }
    except Exception as exc:  # pragma: no cover - depends on runtime spark env
        return _sql_fallback(f"Spark 作业失败: {exc.__class__.__name__}")
    finally:
        if spark is not None:
            spark.stop()
