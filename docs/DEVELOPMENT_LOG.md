# AI prompts and development log

Project: HomeServe Technologies booking platform  
Date: 4 November 2026  
Workspace: `HOME_SERVE_OFC`  
Tool: Cursor, in this chat  
Specification used: the Home Services SaaS capstone document supplied for the build

This log records the prompts that were actually given in the session and what was produced from them. It does not add prompts that were not asked.

## Prompts

### 1. Build the working product

The request was to turn the capstone document into one working project in a single pass: the four roles, the modules written in the document, a usable interface, and a live deployment. GitHub, Netlify, and Render could be used, and a login page could be opened for the student to sign in. The time box was about one hour because the work was for a competition.

What was produced:

- `frontend/` React, Vite, and Tailwind
- `backend/` FastAPI, SQLAlchemy, JWT, bcrypt
- Customer, provider, technician, and admin screens
- Catalog, booking, assignment, payment, review, complaint, notification, and admin report flows
- Seeded demo accounts with password `Demo@1234`
- README, MySQL schema, security notes, and the first test report

### 2. Real database and a free Render API

The request was to connect a real database to the live API, not leave the live API on local test data, to use Render, to deploy the API at zero charge, and to cover every item written in the document from A to Z.

What was produced:

- `psycopg2` driver and URL rewrite for Postgres and MySQL in `backend/app/database.py`
- `render.yaml` for a free web service and a free Postgres database in Singapore
- Health check that runs `SELECT 1` and returns the database dialect
- Optional Cloudinary upload path
- `docs/ER.md`, `docs/USER_STORIES.md`, Postman collection, Playwright spec
- Commit `6674245` pushed to `main`

What did not finish: the Render dashboard required a GitHub sign-in and a captcha. No workspace was created, so the free Postgres database is configured in the repo and is not the database behind the current public URL.

### 3. Swagger, and deploy it

The request was to have a Swagger document and to deploy that too.

What was produced:

- Swagger UI at `/docs`, ReDoc at `/redoc`, spec at `/openapi.json`, short link `/swagger`
- The site header links to Swagger
- The single-page app cannot swallow those paths
- Netlify redirects for `/docs`, `/redoc`, `/swagger`, and `/openapi.json`
- Commit `a4e06be` pushed to `main`
- Public check: `GET /docs` returned HTTP 200 and the page title was HomeServe API - Swagger UI

### 4. Prepare the ten submission items

The request was to prepare the full submission set:

1. Complete source code
2. GitHub repository
3. Live deployed application or deployment evidence
4. Database schema and ER diagram
5. API documentation
6. Test cases and test reports
7. Security checklist
8. Project documentation
9. AI prompts and development log
10. Final presentation

What was produced: this file, `submission/README.md`, `docs/PROJECT.md`, `docs/API.md`, `docs/openapi.json`, `docs/ER.md`, `docs/schema.sql`, `docs/TEST_REPORT.md`, `docs/SECURITY.md`, `docs/presentation.html`, and `docs/evidence/health.json`.

## Decisions

| Decision | Reason |
| --- | --- |
| Demo accounts are inserted once into an empty database | The examiner needs a login. Later bookings are real rows, not a reset on every restart |
| Public URL currently reports `database: sqlite` | That process is the app on this machine. Render login was not completed |
| MySQL script stays in `docs/schema.sql` | The written schema is MySQL. Render's free database is Postgres. SQLAlchemy supports both |
| Swagger is served by the API process | One deploy covers the site and the API document |
| Playwright spec is in the repo but was not run | The browser package was not installed. Pytest covers the booking path |

## Git history for this build

| Commit | What it contains |
| --- | --- |
| `be52c81` | First working HomeServe app |
| `6674245` | Postgres driver, Render blueprint, ER, user stories, Postman, Playwright spec |
| `a4e06be` | Swagger page kept available next to the site |
| Submission commit | This documentation pack. See `git log -1` on `main` |
