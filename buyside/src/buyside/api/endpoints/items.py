from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from buyside.api import schemas
from buyside.db.session import get_db
from buyside.services.items import ItemService

router = APIRouter()


@router.get("", response_model=list[schemas.Item])
async def read_items(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[schemas.Item]:
    """Retrieve items with pagination parameters."""
    return await ItemService.get_items(db, skip=skip, limit=limit)


@router.post(
    "", response_model=schemas.Item, status_code=status.HTTP_201_CREATED
)
async def create_item(
    item: schemas.ItemCreate,
    db: AsyncSession = Depends(get_db),
) -> schemas.Item:
    """Create a new item."""
    return await ItemService.create_item(db, item=item)


@router.get("/{item_id}", response_model=schemas.Item)
async def read_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
) -> schemas.Item:
    """Retrieve an item by id."""
    db_item = await ItemService.get_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    return db_item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an item by id."""
    success = await ItemService.delete_item(db, item_id=item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
