import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_full_flow():
    async with AsyncClient(base_url="http://localhost:8000") as ac:
        # 1. Register user
        resp = await ac.post("/auth/register", json={
            "name": "Test User",
            "email": "5@5.com",
            "password": "testpass123"
        })
        assert resp.status_code == 201
        user_id = resp.json()["user_id"]

        # 2. Login
        resp = await ac.post("/auth/login", json={
            "email": "5@5.com",
            "password": "testpass123"
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create automation
        resp = await ac.post("/automations", json={
            "name": "auto1",
            "module_path": "modules.comercial.dashboard.run_comercial",
            "func_name": "main"
        }, headers=headers)
        assert resp.status_code == 200
        auto_id = resp.json()["id"]

        # 4. Create schedule (interval)
        resp = await ac.post("/schedules", json={
            "automation_id": auto_id,
            "owner_type": "user",
            "owner_id": user_id,
            "type": "interval",
            "interval_seconds": 60,
            "enabled": True
        }, headers=headers)
        assert resp.status_code == 201
        schedule_id = resp.json()["id"]

        # 5. Trigger run (async)
        resp = await ac.post("/runs", json={
            "automation_id": auto_id,
            "mode": "async"
        }, headers=headers)
        assert resp.status_code == 200
        run_id = resp.json()["id"] if "id" in resp.json() else resp.json().get("run_id")

        # 6. List runs
        resp = await ac.get("/runs", headers=headers)
        assert resp.status_code == 200
        runs = resp.json()
        assert any(str(run_id) == str(r.get("id")) for r in runs)

        # 7. List schedules
        resp = await ac.get("/schedules", headers=headers)
        assert resp.status_code == 200
        assert any(str(schedule_id) == str(s.get("id")) for s in resp.json())

        # 8. Get user info
        resp = await ac.get("/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "5@5.com"
