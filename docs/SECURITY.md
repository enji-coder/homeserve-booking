# Security checklist

Checked against the code in `backend/app/security.py`, `backend/app/main.py`, and `backend/app/database.py` on 4 November 2026.

| # | Control | Status | Where |
| --- | --- | --- | --- |
| 1 | Passwords stored as bcrypt hashes, never plain text | Done | `security.hash_password` |
| 2 | Password rules on register, reset, and change | Done | `check_password` |
| 3 | JWT login token, HS256, 12-hour expiry | Done | `create_token` |
| 4 | Logout revokes the token id (`jti`) | Done | `REVOKED` set |
| 5 | Login, register, and forgot-password are rate limited | Done | `rate_limit`, default 30/min, forgot 5/min |
| 6 | Suspended users cannot log in | Done | login returns 403 |
| 7 | Every protected route checks the role | Done | customer, provider, technician, admin helpers |
| 8 | A customer cannot read another customer's booking | Done | test returns 404 |
| 9 | A customer cannot open admin stats | Done | test returns 403 |
| 10 | Technicians only see jobs assigned to them | Done | booking query filter |
| 11 | Queries use SQLAlchemy bound parameters | Done | no string-built SQL for user input |
| 12 | Uploads limited to JPG, PNG, WEBP, PDF and 5 MB | Done | `/api/uploads` |
| 13 | Saved files use a random name | Done | UUID file name |
| 14 | Image URLs must be `/uploads/...` or a Cloudinary URL | Done | URL checks on booking images and documents |
| 15 | Payment is not marked paid without the success test card, or a valid Razorpay signature when keys exist | Done | `/api/payments/verify` |
| 16 | API errors do not return a stack trace | Done | middleware returns a generic 500 message |
| 17 | Secrets come from environment variables | Done | `.env.example`, `JWT_SECRET`, `DATABASE_URL` |
| 18 | `.env` is gitignored | Done | `.gitignore` |
| 19 | CORS origins come from `CORS_ORIGINS` | Done | set to `*` on the public demo, lock this down for a private launch |
| 20 | Password reset codes expire in 15 minutes | Done | `password_resets.expires_at` |
| 21 | Double booking of one slot is rejected | Done | unique `slot_key`, HTTP 409 |

## Known demo limits

- `DEMO_MODE=true` returns the reset code in the API so the examiner can finish the flow without email. Turn it off before a real launch.
- Logout revocation is stored in process memory. A restart forgets revoked tokens. Tokens still expire after 12 hours.
- The public demo allows any origin. A locked-down launch should set `CORS_ORIGINS` to the real site only.
- The test suite uses a short JWT secret on purpose. The Render blueprint generates a real `JWT_SECRET`.
