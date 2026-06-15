from sqlalchemy.orm import Mapped, mapped_column

from buyside.db.base import Base


class Item(Base):
    """Database model representing an Item."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(index=True)
    description: Mapped[str | None] = mapped_column(default=None)
