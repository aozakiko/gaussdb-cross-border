"""Backward compatibility shim for legacy Spark imports.

The project 已切换到 Flink 分析，该模块仅用于兼容旧引用。
"""

from __future__ import annotations

from .flink_job import run_flink_summary as run_spark_summary
