import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_items_crud_lifecycle(client: AsyncClient) -> None:
    """Verify item creation, retrieval, listing, and deletion."""
    # 1. List items initially (should be empty)
    list_response = await client.get("/api/v1/items")
    assert list_response.status_code == 200
    assert list_response.json() == []

    # 2. Create item
    payload = {"title": "Test Item", "description": "This is a test description"}
    create_response = await client.post("/api/v1/items", json=payload)
    assert create_response.status_code == 201
    created_data = create_response.json()
    assert created_data["title"] == payload["title"]
    assert created_data["description"] == payload["description"]
    assert "id" in created_data

    # 3. Get item by ID
    item_id = created_data["id"]
    get_response = await client.get(f"/api/v1/items/{item_id}")
    assert get_response.status_code == 200
    assert get_response.json() == created_data

    # 4. List items (should contain the created item)
    list_response = await client.get("/api/v1/items")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0] == created_data

    # 5. Delete item
    delete_response = await client.delete(f"/api/v1/items/{item_id}")
    assert delete_response.status_code == 204

    # 6. Retrieve deleted item (should 404)
    get_deleted_response = await client.get(f"/api/v1/items/{item_id}")
    assert get_deleted_response.status_code == 404

    # 7. Delete non-existent item (should 404)
    delete_missing_response = await client.delete(f"/api/v1/items/{item_id}")
    assert delete_missing_response.status_code == 404
