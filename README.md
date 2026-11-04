# HomeServe

Home services booking platform for HomeServe Technologies. Customers book verified crews in Ahmedabad. Providers accept jobs and assign technicians. Admin verifies providers, watches revenue, and exports reports.

## Demo logins

Password for every account: `Demo@1234`

| Role | Email |
| --- | --- |
| Customer | priya@homeserve.test |
| Customer | rahul@homeserve.test |
| Provider | kiran@homeserve.test |
| Provider (pending) | neha@homeserve.test |
| Technician | amit@homeserve.test |
| Admin | admin@homeserve.test |

Coupons: `WELCOME10`, `FLAT150`, `MONSOON20`.

Razorpay test card: `4111 1111 1111 1111`. Card `4000 0000 0000 0002` fails. Any future expiry, CVV `123`.

## Run locally

```powershell
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --port 8000
cd ..\frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Swagger UI: http://127.0.0.1:8000/docs (same page at `/swagger`). ReDoc: http://127.0.0.1:8000/redoc. Spec: http://127.0.0.1:8000/openapi.json. On the live site those paths are `/docs`, `/swagger`, `/redoc`, and `/openapi.json`.

Locally the app uses SQLite. The live Render service uses a free Render Postgres database. Tables are created on startup and the demo accounts are inserted once into that database, so bookings you create there stay saved. MySQL is supported with `DATABASE_URL=mysql+pymysql://user:pass@host:3306/homeserve` and `docs/schema.sql`.

## Stack

React, Tailwind, FastAPI, SQLAlchemy, JWT, bcrypt. Pytest covers pricing, commission, double-booking, payment and review. Swagger is at `/docs`.

## Deploy

The Docker image serves the React build and the API together. `render.yaml` is the Render blueprint. `netlify.toml` proxies `/api` and `/uploads` to the Render service so the Netlify site stays same-origin.
