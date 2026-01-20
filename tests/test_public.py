import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_public_docks():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/public/docks-groups")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
