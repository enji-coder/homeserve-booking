# API documentation

The live Swagger UI is the API document. It lists all 75 operations, request bodies, and the demo logins.

| Page | URL |
| --- | --- |
| Swagger UI | https://juvenile-pleased-capability-scales.trycloudflare.com/docs |
| Same page, short link | https://juvenile-pleased-capability-scales.trycloudflare.com/swagger |
| ReDoc | https://juvenile-pleased-capability-scales.trycloudflare.com/redoc |
| OpenAPI file, live | https://juvenile-pleased-capability-scales.trycloudflare.com/openapi.json |
| OpenAPI file in the repo | `docs/openapi.json` |
| Postman collection | `docs/HomeServe.postman_collection.json` |

Locally the same pages are on `http://127.0.0.1:8000`.

## How to call a protected endpoint

1. `POST /api/auth/login` with `{"email":"priya@homeserve.test","password":"Demo@1234"}`.
2. Copy the `token` field from the response.
3. In Swagger, click **Authorize** and paste the token.
4. From code or Postman, send `Authorization: Bearer <token>`.

Password for every demo account is `Demo@1234`.

| Role | Email |
| --- | --- |
| Customer | priya@homeserve.test |
| Customer | rahul@homeserve.test |
| Provider | kiran@homeserve.test |
| Provider, pending approval | neha@homeserve.test |
| Technician | amit@homeserve.test |
| Admin | admin@homeserve.test |

## Groups

| Tag | What it covers |
| --- | --- |
| Meta | `GET /api/health` returns `ok`, `service`, and the database dialect |
| Auth | Register, login, logout, forgot, reset, change password, profile |
| Catalog | Categories, services, providers, offers, public stats, slots |
| Booking | Create, list, cancel, reschedule, accept, reject, assign, arrive, complete, images |
| Customer | Dashboard, addresses, favourites |
| Provider | Services, hours, areas, technicians, earnings, reviews, plan |
| Technician | Dashboard and assigned jobs |
| Payments | Coupon preview, checkout, verify, list, invoice |
| Reviews | Create a review, provider reply, admin hide |
| Complaints | Create, list, update |
| Notifications | List, mark read, admin announcement |
| Files | Upload JPG, PNG, WEBP, or PDF up to 5 MB |
| Admin | Users, verification, listings, coupons, plans, stats, CSV reports |

## Booking and money

`POST /api/bookings` needs a logged-in customer, a provider offer, a free slot, and an address.

- GST is 18% of the taxable amount.
- Commission comes from the provider plan: Starter 20%, Growth 15%, Scale 10%.
- Coupons: `WELCOME10` (10%), `FLAT150` (flat 150, minimum 500), `MONSOON20` (20%, minimum 800, cap 300).
- The same provider slot booked twice returns HTTP 409.
- Status path: Pending, Confirmed, Provider Assigned, In Progress, Completed. Cancelled and Rejected free the slot.

## Payments

Without Razorpay keys the API uses test checkout.

- Success card: `4111 1111 1111 1111`
- Failure card: `4000 0000 0000 0002`
- Any future expiry, CVV `123`

A successful verify creates the payment, the invoice, and the provider earning. `GET /api/bookings/{id}/invoice` returns the invoice.

## Reports

Admin, with the admin token:

- `GET /api/reports/bookings.csv`
- `GET /api/reports/payments.csv`
- `GET /api/reports/customers.csv`

Provider:

- `GET /api/provider/earnings.csv`
