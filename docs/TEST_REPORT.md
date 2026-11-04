# Test cases and test report

Date: 4 November 2026  
Command: `python -m pytest backend/tests -q`  
Result: **9 passed**, 58 warnings.  
Raw output: `docs/pytest_output.txt`.

Warnings are from `datetime.utcnow()` and from the short JWT secret used only inside the test process. They do not fail the suite.

The suite uses a fresh temporary SQLite file, `DEMO_MODE=true`, and no Razorpay keys.

## Automated cases

| Test | File | What it proves |
| --- | --- | --- |
| test_percent_coupon_and_commission | `backend/tests/test_billing.py` | 10% off 1000, GST 162, commission 135, total 1062, earning 765 |
| test_flat_coupon_respects_minimum | `backend/tests/test_billing.py` | FLAT150 does not apply below the minimum of 500 |
| test_percent_coupon_respects_cap | `backend/tests/test_billing.py` | 20% off 2000 is capped at 300, commission uses 10% |
| test_slots_are_hourly | `backend/tests/test_billing.py` | 09:00–12:00 gives three hourly slots; a window shorter than 60 minutes gives none |
| test_health_and_catalog | `backend/tests/test_api.py` | Health is ok, at least 8 categories, at least 10 services |
| test_customer_cannot_open_admin | `backend/tests/test_api.py` | Priya receives HTTP 403 on `/api/admin/stats` |
| test_full_booking_payment_and_review_flow | `backend/tests/test_api.py` | Book a free slot with WELCOME10, second booking of that slot is 409, another customer cannot read it, provider accepts and assigns, technician arrives and completes, success test card pays, invoice exists, review is stored |
| test_forgot_password_demo_code | `backend/tests/test_api.py` | Forgot-password returns a demo code and reset accepts it |
| test_admin_report_and_provider_approval | `backend/tests/test_api.py` | Admin stats, bookings CSV, and approving the pending provider |

## End-to-end spec

`tests/e2e/customer.spec.js` and `playwright.config.js` describe a customer login and a booking page check. Playwright browsers were not installed in this session, so that spec was not executed. The API test above covers the same booking path.

Postman collection: `docs/HomeServe.postman_collection.json`.

## Manual UI check

On the running app, these screens worked:

- Landing page
- Login as Priya
- Service catalog
- Fan installation booking, offer id 2, slot 16 Dec 2026 at 10:00
- New pending booking shown with pay actions
- Swagger UI at `/docs` returned HTTP 200 and listed the operations

## How to repeat

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```
