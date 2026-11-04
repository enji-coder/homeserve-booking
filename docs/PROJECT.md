# HomeServe project documentation

HomeServe Technologies is a home-services booking platform for Ahmedabad. A customer finds a verified crew, picks a free hour, and pays. The provider accepts the job and assigns a technician. The technician marks arrival and completion. Admin verifies new providers and exports reports.

## Roles

| Role | Can do |
| --- | --- |
| Customer | Register, save addresses, search, book, cancel, reschedule, pay, review, complain, save favourites |
| Provider | Register a business, set prices, hours and areas, accept or reject, assign a technician, see earnings |
| Technician | See only assigned jobs, mark arrival, add a photo, complete the job |
| Admin | Approve providers, manage categories, services, coupons and plans, read complaints, export CSV |

## Modules

1. Authentication and profile, including forgot-password.
2. Service catalog and search.
3. Provider onboarding and admin verification.
4. Working hours, service areas, and hourly slots.
5. Booking from request through completion, cancel, and reschedule.
6. Technician assignment and job updates.
7. Coupons, GST, commission, Razorpay test checkout, and invoices.
8. Reviews and provider replies.
9. Complaints and notifications.
10. Admin stats and CSV reports.

## Stack

| Layer | Choice |
| --- | --- |
| Frontend | React 18, Vite, Tailwind, React Router |
| Backend | FastAPI, SQLAlchemy |
| Database | SQLite on this machine. Postgres via `render.yaml`. MySQL via `docs/schema.sql` |
| Auth | JWT, bcrypt |
| API document | Swagger at `/docs` |
| Tests | Pytest. Playwright spec is included |
| Deploy | Dockerfile serves the built site and the API. Cloudflare tunnel is the current public URL |

## Repository layout

```
frontend/          React app
backend/app/       API, models, billing, seed, security
backend/tests/     Pytest
tests/e2e/         Playwright spec
docs/              Schema, ER, API, tests, security, this file, slides
submission/        One-page map of the ten submission items
render.yaml        Free Render web service and free Postgres
Dockerfile         One image for the site and the API
```

## Screens

| Path | Who |
| --- | --- |
| `/` | Public landing |
| `/services`, `/services/:id`, `/providers/:id` | Public catalog |
| `/login`, `/register`, `/forgot` | Auth |
| `/book/:offerId` | Logged-in customer |
| `/app` | Workspace for the signed-in role |
| `/docs` | Swagger |

## Demo data

Password for every account: `Demo@1234`.

Accounts and sample bookings are inserted once, only when `admin@homeserve.test` is missing. Later bookings stay in the database. SparkleClean (`neha@homeserve.test`) stays pending so admin verification can be shown.

## Five-minute demo

1. Open the public URL and the landing page.
2. Open Services and a service detail page.
3. Log in as `priya@homeserve.test` and open the workspace.
4. Log out. Log in as `kiran@homeserve.test` and show a job.
5. Log in as `amit@homeserve.test` and show assigned work.
6. Log in as `admin@homeserve.test` and show stats, the pending provider, and a CSV.
7. Open `/docs` and authorize with a token from `POST /api/auth/login`.

## Run on a new machine

```powershell
cd backend
python -m venv ..\.venv
..\.venv\Scripts\python -m pip install -r requirements.txt
..\.venv\Scripts\python -m uvicorn app.main:app --port 8000
cd ..\frontend
npm install
npm run dev
```

Site: http://127.0.0.1:5173  
API and Swagger: http://127.0.0.1:8000/docs

## Related files

- User stories: `docs/USER_STORIES.md`
- Schema and ER: `docs/schema.sql`, `docs/ER.md`
- API: `docs/API.md`
- Tests: `docs/TEST_REPORT.md`
- Security: `docs/SECURITY.md`
- Prompts and log: `docs/DEVELOPMENT_LOG.md`
- Slides: `docs/presentation.html`
