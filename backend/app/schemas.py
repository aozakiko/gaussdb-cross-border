"""Pydantic schemas for request/response bodies."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RecordBase(BaseModel):
    title: str = Field(..., max_length=120, description="任务/订单标题")
    description: Optional[str] = Field(None, description="备注")
    status: str = Field("awaiting_fulfillment", max_length=32, description="物流/履约状态")
    priority: int = Field(1, ge=1, le=5)
    owner: str = Field("system", max_length=64)
    order_number: str = Field(..., max_length=64, description="订单号")
    sales_channel: str = Field("Amazon", max_length=64, description="销售渠道")
    destination_market: str = Field("US", max_length=64, description="目的市场")
    currency: str = Field("USD", max_length=8, description="币种")
    order_amount: Decimal = Field(0, ge=0, description="订单金额")
    tracking_number: Optional[str] = Field(None, max_length=64, description="运单号")
    order_date: Optional[datetime] = Field(None, description="下单时间")


class RecordCreate(RecordBase):
    pass


class RecordUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=120)
    description: Optional[str] = None
    status: Optional[str] = Field(None, max_length=32)
    priority: Optional[int] = Field(None, ge=1, le=5)
    owner: Optional[str] = Field(None, max_length=64)
    order_number: Optional[str] = Field(None, max_length=64)
    sales_channel: Optional[str] = Field(None, max_length=64)
    destination_market: Optional[str] = Field(None, max_length=64)
    currency: Optional[str] = Field(None, max_length=8)
    order_amount: Optional[Decimal] = Field(None, ge=0)
    tracking_number: Optional[str] = Field(None, max_length=64)
    order_date: Optional[datetime] = None


class RecordOut(RecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedRecords(BaseModel):
    total: int
    items: List[RecordOut]


class FlinkAnalyticsResult(BaseModel):
    total_records: int
    by_status: dict
    by_owner: dict
    engine: str = Field("flink", description="计算引擎: flink 或 sql_fallback")
    detail: Optional[str] = Field(None, description="若发生降级，记录原因")
