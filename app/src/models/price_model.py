import datetime
from src.db.postgres import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, DateTime


class Price(Base):
    ticker: Mapped[str] = mapped_column(String(50), index=True)
    price: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, index=True
    )
