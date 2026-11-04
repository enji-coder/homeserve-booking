import os
import tempfile
from pathlib import Path

db_file = Path(tempfile.gettempdir()) / "homeserve_pytest.db"
if db_file.exists():
    db_file.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["DEMO_MODE"] = "true"
os.environ["RAZORPAY_KEY_ID"] = ""
os.environ["RAZORPAY_KEY_SECRET"] = ""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def login(email):
    response = client.post("/api/auth/login", json={"email": email, "password": "Demo@1234"})
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_and_catalog():
    assert client.get("/api/health").json()["ok"] is True
    categories = client.get("/api/categories").json()
    assert len(categories) >= 8
    services = client.get("/api/services").json()
    assert services["total"] >= 10


def test_customer_cannot_open_admin():
    headers = login("priya@homeserve.test")
    response = client.get("/api/admin/stats", headers=headers)
    assert response.status_code == 403


def test_full_booking_payment_and_review_flow():
    customer = login("priya@homeserve.test")
    services = client.get("/api/services?q=fan").json()["items"]
    assert services
    detail = client.get(f"/api/services/{services[0]['id']}").json()
    offer = detail["providers"][0]
    slots = client.get("/api/slots", params={"provider_id": offer["id"], "scheduled_date": "2026-12-15"}).json()
    free = next(slot["time"] for slot in slots if slot["available"])
    addresses = client.get("/api/addresses", headers=customer).json()
    payload = {
        "provider_service_id": offer["offer_id"],
        "scheduled_date": "2026-12-15",
        "scheduled_time": free,
        "address_id": addresses[0]["id"],
        "problem_note": "Fan box is ready.",
        "coupon_code": "WELCOME10",
    }
    first = client.post("/api/bookings", json=payload, headers=customer)
    assert first.status_code == 200, first.text
    booking = first.json()
    assert booking["status"] == "Pending"
    assert booking["discount"] > 0
    second = client.post("/api/bookings", json=payload, headers=customer)
    assert second.status_code == 409

    other = login("rahul@homeserve.test")
    hidden = client.get(f"/api/bookings/{booking['id']}", headers=other)
    assert hidden.status_code == 404

    provider = login("kiran@homeserve.test")
    accepted = client.post(f"/api/bookings/{booking['id']}/accept", headers=provider)
    assert accepted.status_code == 200
    techs = client.get("/api/provider/technicians", headers=provider).json()
    assigned = client.post(f"/api/bookings/{booking['id']}/assign", json={"technician_id": techs[0]["id"]}, headers=provider)
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "Provider Assigned"

    tech = login("amit@homeserve.test")
    too_soon = client.post(f"/api/bookings/{booking['id']}/arrive", headers=tech)
    assert too_soon.status_code == 400
    accepted = client.post(f"/api/bookings/{booking['id']}/accept-job", headers=tech)
    assert accepted.status_code == 200
    assert accepted.json()["job_accepted"] is True
    arrived = client.post(f"/api/bookings/{booking['id']}/arrive", headers=tech)
    assert arrived.status_code == 200
    done = client.post(f"/api/bookings/{booking['id']}/complete", json={"remarks": "Fan fitted and tested."}, headers=tech)
    assert done.status_code == 200
    assert done.json()["status"] == "Completed"

    checkout = client.post("/api/payments/checkout", json={"booking_id": booking["id"], "mode": "full"}, headers=customer)
    assert checkout.status_code == 200, checkout.text
    paid = client.post("/api/payments/verify", json={
        "booking_id": booking["id"],
        "order_id": checkout.json()["order_id"],
        "outcome": "success",
        "test_card": "4111111111111111",
    }, headers=customer)
    assert paid.status_code == 200, paid.text
    assert paid.json()["payment_status"] == "Paid"
    invoice = client.get(f"/api/bookings/{booking['id']}/invoice", headers=customer)
    assert invoice.json()["invoices"]

    review = client.post("/api/reviews", json={"booking_id": booking["id"], "rating": 5, "comment": "On time."}, headers=customer)
    assert review.status_code == 200, review.text
    notes = client.get("/api/notifications", headers=customer).json()
    assert any(item["title"] == "Please review your visit" for item in notes)


def test_put_profile_and_invalid_contact():
    bad_email = client.post("/api/auth/register", json={"full_name": "Test User", "email": "not-an-email", "password": "Demo@1234", "role": "customer", "phone": "9898000099"})
    assert bad_email.status_code == 400
    bad_phone = client.post("/api/auth/register", json={"full_name": "Test User", "email": "new.user@homeserve.test", "password": "Demo@1234", "role": "customer", "phone": "12345"})
    assert bad_phone.status_code == 400
    headers = login("rahul@homeserve.test")
    updated = client.put("/api/profile", json={"phone": "9898033302"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["phone"] == "9898033302"


def test_forgot_password_demo_code():
    response = client.post("/api/auth/forgot", json={"email": "priya@homeserve.test"})
    assert response.status_code == 200
    code = response.json()["demo_reset_code"]
    changed = client.post("/api/auth/reset", json={"email": "priya@homeserve.test", "code": code, "password": "Demo@1234"})
    assert changed.status_code == 200


def test_admin_report_and_provider_approval():
    admin = login("admin@homeserve.test")
    stats = client.get("/api/admin/stats", headers=admin)
    assert stats.status_code == 200
    assert stats.json()["bookings"] >= 1
    report = client.get("/api/reports/bookings.csv", headers=admin)
    assert report.status_code == 200
    assert "code" in report.text.splitlines()[0]
    users = client.get("/api/admin/users?role=provider", headers=admin).json()
    pending = next(user for user in users if user["verification_status"] == "pending")
    approved = client.post(f"/api/admin/providers/{pending['provider_id']}/verify", json={"status": "approved"}, headers=admin)
    assert approved.status_code == 200
