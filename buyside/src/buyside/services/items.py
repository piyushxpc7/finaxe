from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from buyside.api.schemas import ItemCreate
from buyside.db.models import Item


class ItemService:
    """Service class for managing Items."""

    @staticmethod
    async def get_item(db: AsyncSession, item_id: int) -> Item | None:
        """Fetch a single Item by its ID."""
        result = await db.execute(select(Item).where(Item.id == item_id))
        return result.scalars().first()

    @staticmethod
    async def get_items(
        db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[Item]:
        """Fetch multiple Items with pagination."""
        result = await db.execute(select(Item).offset(skip).limit(limit))
        return list(result.scalars().all())

    @staticmethod
    async def create_item(db: AsyncSession, item: ItemCreate) -> Item:
        """Create a new Item."""
        db_item = Item(title=item.title, description=item.description)
        db.add(db_item)
        await db.commit()
        await db.refresh(db_item)
        return db_item

    @staticmethod
    async def delete_item(db: AsyncSession, item_id: int) -> bool:
        """Delete an Item by ID. Returns True if deleted, False if not found."""
        result = await db.execute(select(Item).where(Item.id == item_id))
        db_item = result.scalars().first()
        if db_item:
            await db.delete(db_item)
            await db.commit()
            return True
        return False
