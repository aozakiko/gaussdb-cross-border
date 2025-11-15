"""FastAPI entrypoint with API + 轻量可视化后台."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, Form, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Base, engine, get_db
from .models import Record
from .routers import records

settings = get_settings()
TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
STATUS_CHOICES = [
    ("awaiting_fulfillment", "待履约"),
    ("picking", "拣货中"),
    ("in_transit", "跨境在途"),
    ("delivered", "已签收"),
    ("exception", "异常处理"),
]
ALLOWED_STATUSES = {value for value, _ in STATUS_CHOICES}


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/health", tags=["System"])
    def health_check():
        return {"status": "ok", "environment": settings.environment}

    @app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
    def dashboard(request: Request, db: Session = Depends(get_db)):
        latest_records: List[Record] = db.scalars(
            select(Record).order_by(Record.order_date.desc())
        ).all()

        total = db.scalar(select(func.count()).select_from(Record)) or 0
        revenue_total = db.scalar(select(func.coalesce(func.sum(Record.order_amount), 0))) or Decimal(0)
        status_rows = db.execute(
            select(Record.status, func.count()).group_by(Record.status)
        ).all()
        owner_count = db.scalar(select(func.count(func.distinct(Record.owner)))) or 0
        in_transit_count = db.scalar(
            select(func.count()).select_from(Record).where(Record.status == "in_transit")
        ) or 0
        exception_count = db.scalar(
            select(func.count()).select_from(Record).where(Record.status == "exception")
        ) or 0

        status_labels = []
        status_counts = []
        status_text = dict(STATUS_CHOICES)
        for status_value, count in status_rows:
            status_labels.append(status_text.get(status_value, status_value))
            status_counts.append(count)

        records_payload = [
            {
                "id": item.id,
                "title": item.title,
                "order_number": item.order_number,
                "sales_channel": item.sales_channel,
                "destination_market": item.destination_market,
                "status": item.status,
                "priority": item.priority,
                "owner": item.owner,
                "order_amount": str(item.order_amount),
                "currency": item.currency,
                "tracking_number": item.tracking_number,
                "order_date": item.order_date.strftime("%Y-%m-%d"),
            }
            for item in latest_records
        ]

        analytics = [
            {"label": "履约专员", "value": owner_count},
            {"label": "跨境在途", "value": in_transit_count},
            {"label": "异常/滞留", "value": exception_count},
            {"label": "GMV (合计)", "value": f"${revenue_total:,.2f}"},
        ]

        context = {
            "request": request,
            "records": records_payload,
            "stats": {
                "total": total,
                "revenue": f"${revenue_total:,.2f}",
                "in_transit": in_transit_count,
                "exception": exception_count,
            },
            "chart": {"labels": status_labels, "counts": status_counts},
            "analytics": analytics,
            "now": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status_choices": STATUS_CHOICES,
        }
        return templates.TemplateResponse("dashboard.html", context)

    @app.post("/admin/records", response_class=HTMLResponse, tags=["Dashboard"])
    def create_record_form(
        request: Request,
        title: str = Form(..., max_length=120),
        description: str = Form(None),
        order_number: str = Form(..., max_length=64),
        sales_channel: str = Form("Amazon"),
        destination_market: str = Form("US"),
    status_value: str = Form("awaiting_fulfillment", alias="status"),
        priority: int = Form(1),
        owner: str = Form("ops-global"),
        currency: str = Form("USD"),
        order_amount: float = Form(0),
        tracking_number: str = Form(None),
        order_date: str = Form(None),
        db: Session = Depends(get_db),
    ):
        if status_value not in ALLOWED_STATUSES:
            status_value = "awaiting_fulfillment"
        parsed_order_date = None
        if order_date:
            try:
                parsed_order_date = datetime.fromisoformat(order_date)
            except ValueError:
                parsed_order_date = datetime.now(timezone.utc)
        record = Record(
            title=title,
            description=description or None,
            status=status_value,
            priority=max(1, min(5, priority or 1)),
            owner=owner or "system",
            order_number=order_number,
            sales_channel=sales_channel,
            destination_market=destination_market,
            currency=currency,
            order_amount=Decimal(str(order_amount)),
            tracking_number=tracking_number,
            order_date=parsed_order_date or datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/admin/records/{record_id}/status", tags=["Dashboard"])
    def change_status(
        record_id: int,
        status_value: str = Form(..., alias="status"),
        db: Session = Depends(get_db),
    ):
        if status_value not in ALLOWED_STATUSES:
            status_value = "awaiting_fulfillment"
        record = db.get(Record, record_id)
        if record:
            record.status = status_value
            db.add(record)
            db.commit()
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/admin/records/{record_id}/delete", tags=["Dashboard"])
    def remove_record(record_id: int, db: Session = Depends(get_db)):
        record = db.get(Record, record_id)
        if record:
            db.delete(record)
            db.commit()
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    app.include_router(records.router)

    return app


app = create_app()

# Run migrations on import (fast path for demo; for production prefer Alembic)
Base.metadata.create_all(bind=engine)
