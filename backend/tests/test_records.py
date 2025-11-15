from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app import models

settings = get_settings()
SQLALCHEMY_DATABASE_URL = settings.get_database_url()
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, future=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _reset_records_table():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_create_and_list_record():
    _reset_records_table()
    payload = {
        "title": "智能筋膜枪",
        "description": "美国站新品",
        "status": "awaiting_fulfillment",
        "priority": 2,
        "owner": "ops-us",
        "order_number": "ORD-TEST-0001",
        "sales_channel": "Amazon US",
        "destination_market": "US",
        "currency": "USD",
        "order_amount": 199.99,
        "tracking_number": "SF123",
    }
    response = client.post("/records/", json=payload)
    assert response.status_code == 201, response.text
    record_id = response.json()["id"]

    list_resp = client.get("/records/")
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == record_id


def test_update_and_delete_record():
    _reset_records_table()
    payload = {
        "title": "家庭咖啡机",
        "description": "意大利直邮",
        "status": "awaiting_fulfillment",
        "priority": 1,
        "owner": "ops-eu",
        "order_number": "ORD-TEST-0002",
        "sales_channel": "Shopify",
        "destination_market": "IT",
        "currency": "EUR",
        "order_amount": 349.5,
    }
    create_resp = client.post("/records/", json=payload)
    record_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/records/{record_id}",
        json={"status": "in_transit", "priority": 3, "order_amount": 399.0},
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["status"] == "in_transit"
    assert float(body["order_amount"]) == 399.0

    delete_resp = client.delete(f"/records/{record_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/records/{record_id}")
    assert get_resp.status_code == 404

