# Requirements trace

This maps the capstone brief to the code a reviewer can open. Live app and Swagger are served together.

| Brief item | Where it is |
| --- | --- |
| 4 roles | `customer`, `provider`, `technician`, `admin` in `backend/app/models.py` and `frontend/src/App.jsx` |
| React and Tailwind | `frontend/` |
| FastAPI and SQLAlchemy | `backend/app/main.py`, `backend/app/database.py` |
| MySQL | `docs/schema.sql`. The app reads `DATABASE_URL`. `mysql://` is rewritten to `mysql+pymysql://` |
| JWT and bcrypt | `backend/app/security.py` |
| Swagger | `/docs`, `/swagger`, `/redoc`, `docs/openapi.json` |
| Postman | `docs/HomeServe.postman_collection.json` |
| Playwright | `tests/e2e/customer.spec.js`, `playwright.config.js` |
| Pytest | `backend/tests/` |
| GitHub | https://github.com/enji-coder/homeserve-booking |
| Render blueprint | `render.yaml` |
| Netlify proxy | `netlify.toml` |
| Razorpay test mode | `/api/payments/checkout` and `/api/payments/verify`. Success card `4111111111111111` |
| Cloudinary or equivalent | Cloudinary when the three env keys are set. Otherwise files are stored under `/uploads` |
| Module 1 auth | Register, login, forgot, reset, logout, profile, RBAC |
| Module 2 customer | Dashboard, addresses, favourites, history, account suspend |
| Module 3 catalog | 8 categories, 2 subcategories, search, filter, pagination, detail page |
| Module 4 provider | Profile, document upload, approve or reject, areas, hours, pricing |
| Module 5 booking | Unique code, all 7 statuses, cancel, reschedule, no double booking |
| Module 6 technician | Add, assign, accept job, arrive, complete, photos, remarks, history |
| Module 7 payments | GST 18%, plan commission, coupons, advance 30%, invoice, refund on cancel, earnings |
| Module 8 notifications | Confirm, cancel, assign, reminder, completion, payment, review request, announcements |
| Module 9 reviews and complaints | Rating, reply, hide, complaint status |
| Module 10 analytics | Admin, provider, and customer dashboards, bar charts, CSV |
| 20 required tables | All present, plus plans, favourites, and password resets. See `docs/ER.md` |
| Phase 1 planning | `docs/PLANNING.md`, `docs/USER_STORIES.md` |
| Security | `docs/SECURITY.md`, `docs/SECURITY_REPORT.md` |
| Tests | `docs/TEST_REPORT.md` |
| AI log | `docs/DEVELOPMENT_LOG.md` |
| Presentation | `docs/presentation.html` |
