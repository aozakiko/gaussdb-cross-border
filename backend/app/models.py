"""SQLAlchemy models."""

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text, func

from .database import Base


class Record(Base):
    __tablename__ = "records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=1)
    owner = Column(String(64), nullable=False, default="system")
    order_number = Column(String(64), nullable=False, unique=True, index=True)
    sales_channel = Column(String(64), nullable=False, default="Amazon")
    destination_market = Column(String(64), nullable=False, default="US")
    currency = Column(String(8), nullable=False, default="USD")
    order_amount = Column(Numeric(12, 2), nullable=False, default=0)
    tracking_number = Column(String(64), nullable=True)
    order_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Record id={self.id} title={self.title!r} status={self.status}>"
