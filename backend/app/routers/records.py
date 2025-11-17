"""跨境电商订单 API."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services.flink_job import run_flink_summary

router = APIRouter(prefix="/records", tags=["Records"])
ALLOWED_STATUSES = {"awaiting_fulfillment", "picking", "in_transit", "delivered", "exception"}


@router.get("/", response_model=schemas.PaginatedRecords)
def list_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    owner: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    sales_channel: Optional[str] = Query(None, alias="channel"),
    destination_market: Optional[str] = Query(None, alias="destination"),
    db: Session = Depends(get_db),
):
    stmt = select(models.Record)
    count_stmt = select(func.count()).select_from(models.Record)

    if owner:
        stmt = stmt.where(models.Record.owner == owner)
        count_stmt = count_stmt.where(models.Record.owner == owner)
    if status_filter:
        stmt = stmt.where(models.Record.status == status_filter)
        count_stmt = count_stmt.where(models.Record.status == status_filter)
    if sales_channel:
        stmt = stmt.where(models.Record.sales_channel == sales_channel)
        count_stmt = count_stmt.where(models.Record.sales_channel == sales_channel)
    if destination_market:
        stmt = stmt.where(models.Record.destination_market == destination_market)
        count_stmt = count_stmt.where(models.Record.destination_market == destination_market)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(stmt.order_by(models.Record.created_at.desc()).offset(skip).limit(limit)).all()
    return schemas.PaginatedRecords(total=total, items=items)


@router.post("/", response_model=schemas.RecordOut, status_code=status.HTTP_201_CREATED)
def create_record(payload: schemas.RecordCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_none=True)
    if data.get("status") not in ALLOWED_STATUSES:
        data["status"] = "awaiting_fulfillment"
    data.setdefault("order_date", datetime.now(timezone.utc))
    record = models.Record(**data)
    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:  # pragma: no cover - rare path
        db.rollback()
        raise HTTPException(status_code=400, detail="订单号已存在") from exc
    db.refresh(record)
    return record


@router.get("/{record_id}", response_model=schemas.RecordOut)
def get_record(record_id: int, db: Session = Depends(get_db)):
    record = db.get(models.Record, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    return record


@router.put("/{record_id}", response_model=schemas.RecordOut)
def update_record(record_id: int, payload: schemas.RecordUpdate, db: Session = Depends(get_db)):
    record = db.get(models.Record, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("status") and updates["status"] not in ALLOWED_STATUSES:
        updates["status"] = "awaiting_fulfillment"
    for field, value in updates.items():
        setattr(record, field, value)

    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:  # pragma: no cover - rare path
        db.rollback()
        raise HTTPException(status_code=400, detail="订单号已存在") from exc
    db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, db: Session = Depends(get_db)):
    record = db.get(models.Record, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    db.delete(record)
    db.commit()


@router.get("/analytics/flink", response_model=schemas.FlinkAnalyticsResult)
def flink_analytics():
    return run_flink_summary()


@router.get(
    "/analytics/spark",
    response_model=schemas.FlinkAnalyticsResult,
    tags=["Records"],
    summary="Deprecated Spark analytics endpoint",
)
def legacy_spark_analytics():
    """Backward compatible shim for clients that still hit the legacy Spark route."""
    payload = schemas.FlinkAnalyticsResult(**run_flink_summary())
    payload.engine = f"{payload.engine or 'flink'} (via spark alias)"
    return payload
