import os
from pathlib import Path

from fastapi.testclient import TestClient


DB_PATH = Path(__file__).resolve().parent / "test_hotel_monitor.db"
if DB_PATH.exists():
    DB_PATH.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["AUTO_CREATE_TABLES"] = "true"

from app.main import app  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402


client = TestClient(app)
Base.metadata.create_all(bind=engine)


def _register_and_login():
    register_payload = {
        "username": "tester",
        "email": "tester@example.com",
        "password": "pass1234",
        "hotel_name": "Hotel Demo",
        "hotel_location": {"lat": 31.23, "lng": 121.47},
    }
    r = client.post("/api/v1/auth/register", json=register_payload)
    assert r.status_code == 200
    assert r.json()["code"] == 201

    l = client.post("/api/v1/auth/login", json={"username": "tester", "password": "pass1234"})
    assert l.status_code == 200
    token = l.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_auth_and_competitor_and_extension_report_flow():
    auth_headers = _register_and_login()

    c = client.post(
        "/api/v1/competitors",
        headers=auth_headers,
        json={
            "name": "竞品酒店A",
            "platform": "meituan",
            "external_id": "mt-1001",
            "room_types": ["豪华大床房"],
        },
    )
    assert c.status_code == 200
    assert c.json()["code"] == 201
    competitor_id = c.json()["data"]["id"]

    alias_put = client.put(
        "/api/v1/competitor-aliases",
        headers=auth_headers,
        json={"alias_map": {"Smoke Competitor Alias": "竞品酒店A"}},
    )
    assert alias_put.status_code == 200
    assert alias_put.json()["data"]["count"] == 1

    reg = client.post(
        "/api/v1/extension/register",
        headers=auth_headers,
        json={"device_id": "dev-1", "version": "1.0.0"},
    )
    assert reg.status_code == 200
    ext_token = reg.json()["data"]["extension_token"]

    rule = client.post(
        "/api/v1/alert-rules",
        headers=auth_headers,
        json={"name": "降价告警", "rule_type": "price_drop", "threshold": 10.0, "is_active": True},
    )
    assert rule.status_code == 200
    assert rule.json()["code"] == 201
    rule_id = rule.json()["data"]["id"]

    updated = client.put(
        f"/api/v1/alert-rules/{rule_id}",
        headers=auth_headers,
        json={"threshold": 8.0, "is_active": True},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["threshold"] == 8.0

    report = client.post(
        "/api/v1/extension/report",
        headers={"X-Extension-Token": ext_token},
        json={
            "type": "competitor",
            "source": "meituan_merchant",
            "data": {
                "competitors": [
                    {
                        "name": "竞品酒店A",
                        "room_type": "豪华大床房",
                        "price": 480.0,
                        "availability": True,
                    }
                ],
                "business": {},
                "benchmark": {},
            },
            "url": "https://e.meituan.com/abc",
            "captured_at": "2026-04-09T00:00:00Z",
        },
    )
    assert report.status_code == 200
    assert report.json()["data"]["processed_count"] == 1
    assert report.json()["data"]["unmatched_competitors"] == []

    report2 = client.post(
        "/api/v1/extension/report",
        headers={"X-Extension-Token": ext_token},
        json={
            "type": "competitor",
            "source": "meituan_merchant",
            "data": {
                "competitors": [
                    {
                        "name": "竞品酒店A",
                        "room_type": "豪华大床房",
                        "price": 400.0,
                        "availability": True,
                    }
                ],
                "business": {},
                "benchmark": {},
            },
            "url": "https://e.meituan.com/abc",
            "captured_at": "2026-04-09T00:01:00Z",
        },
    )
    assert report2.status_code == 200

    report_alias = client.post(
        "/api/v1/extension/report",
        headers={"X-Extension-Token": ext_token},
        json={
            "type": "competitor",
            "source": "meituan_merchant",
            "data": {
                "competitors": [
                    {
                        "name": "Smoke Competitor Alias",
                        "room_type": "豪华大床房",
                        "price": 390.0,
                        "availability": True,
                    },
                    {
                        "name": "Unknown Hotel",
                        "room_type": "豪华大床房",
                        "price": 499.0,
                        "availability": True,
                    },
                ],
                "business": {},
                "benchmark": {},
            },
            "url": "https://e.meituan.com/abc",
            "captured_at": "2026-04-09T00:02:00Z",
        },
    )
    assert report_alias.status_code == 200
    assert report_alias.json()["data"]["processed_count"] >= 1
    assert "Unknown Hotel" in report_alias.json()["data"]["unmatched_competitors"]

    history = client.get(f"/api/v1/competitors/{competitor_id}/price-history", headers=auth_headers)
    assert history.status_code == 200
    assert history.json()["data"]["statistics"]["count"] >= 1

    alerts = client.get("/api/v1/alerts", headers=auth_headers)
    assert alerts.status_code == 200
    assert len(alerts.json()["data"]["items"]) >= 1

    notifications = client.get("/api/v1/notifications?page=1&page_size=10", headers=auth_headers)
    assert notifications.status_code == 200
    assert notifications.json()["data"]["page"] == 1
    assert notifications.json()["data"]["page_size"] == 10
    assert "total" in notifications.json()["data"]

    alias_get = client.get("/api/v1/competitor-aliases", headers=auth_headers)
    assert alias_get.status_code == 200
    assert "Smoke Competitor Alias" in alias_get.json()["data"]["alias_map"]

    activity = client.post(
        "/api/v1/activities",
        headers=auth_headers,
        json={
            "title": "国际车展",
            "description": "测试活动",
            "start_time": "2026-05-01T09:00:00Z",
            "end_time": "2026-05-03T18:00:00Z",
            "address": "上海会展中心",
            "source": "fairchina",
            "source_url": "https://example.com/fair",
            "activity_type": "exhibition",
            "demand_level": "HIGH",
            "demand_score": 0.9,
        },
    )
    assert activity.status_code == 200
    assert activity.json()["code"] == 201

    cal = client.get("/api/v1/activities/calendar?activity_type=exhibition", headers=auth_headers)
    assert cal.status_code == 200
    assert cal.json()["data"]["summary"]["total_activities"] >= 1

    deleted = client.delete(f"/api/v1/alert-rules/{rule_id}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True

    dashboard = client.get("/api/v1/dashboard/overview", headers=auth_headers)
    assert dashboard.status_code == 200
    assert "summary" in dashboard.json()["data"]

    devices = client.get("/api/v1/extension/devices", headers=auth_headers)
    assert devices.status_code == 200
    reports = client.get("/api/v1/extension/reports?page=1&page_size=5", headers=auth_headers)
    assert reports.status_code == 200

    db = SessionLocal()
    try:
        me = db.query(User).filter(User.username == "tester").first()
        me.role = "admin"
        db.commit()
    finally:
        db.close()

    admin_login = client.post("/api/v1/auth/login", json={"username": "tester", "password": "pass1234"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['data']['access_token']}"}
    users = client.get("/api/v1/system/users", headers=admin_headers)
    assert users.status_code == 200
    assert len(users.json()["data"]["items"]) >= 1

    logs = client.get("/api/v1/system/audit-logs?page=1&page_size=10", headers=admin_headers)
    assert logs.status_code == 200

    target_id = users.json()["data"]["items"][0]["id"]
    user_update = client.put(
        f"/api/v1/system/users/{target_id}",
        headers=admin_headers,
        json={"role": "manager", "is_active": True},
    )
    assert user_update.status_code == 200
