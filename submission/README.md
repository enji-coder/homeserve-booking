# Submission index

HomeServe Technologies. Prepared 4 November 2026.  
GitHub: https://github.com/enji-coder/homeserve-booking  
Live app: https://juvenile-pleased-capability-scales.trycloudflare.com  
Swagger: https://juvenile-pleased-capability-scales.trycloudflare.com/docs

Open `docs/presentation.html` in a browser for the final presentation. Arrow keys move between slides. Print to PDF from the browser if a file copy is required.

| # | Required item | Where to open it |
| --- | --- | --- |
| 1 | Complete source code | `frontend/`, `backend/`, `tests/`, `Dockerfile`, `render.yaml` |
| 2 | GitHub repository | https://github.com/enji-coder/homeserve-booking branch `main` |
| 3 | Live deployed application or deployment evidence | Live URL above. Evidence file: `docs/evidence/health.json` |
| 4 | Database schema and ER diagram | `docs/schema.sql` and `docs/ER.md` |
| 5 | API documentation | Live `/docs`, plus `docs/API.md`, `docs/openapi.json`, `docs/HomeServe.postman_collection.json` |
| 6 | Test cases and test reports | `backend/tests/`, `docs/TEST_REPORT.md`, `docs/pytest_output.txt` |
| 7 | Security checklist | `docs/SECURITY.md` |
| 8 | Project documentation | `README.md`, `docs/PROJECT.md`, `docs/USER_STORIES.md` |
| 9 | AI prompts and development log | `docs/DEVELOPMENT_LOG.md` |
| 10 | Final presentation | `docs/presentation.html` |

## Demo logins

Password for every account: `Demo@1234`

| Role | Email |
| --- | --- |
| Customer | priya@homeserve.test |
| Provider | kiran@homeserve.test |
| Technician | amit@homeserve.test |
| Admin | admin@homeserve.test |

## Honest note for the examiner

The public URL is the full application, including Swagger, running from this project and exposed with a Cloudflare tunnel. `GET /api/health` returned `database: sqlite` because the Render sign-in was not completed. `render.yaml` is the zero-cost Render setup: free web service plus free Postgres. Applying that blueprint needs a Render login.
