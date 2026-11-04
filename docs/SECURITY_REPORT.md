# Security issue report

Date: 4 November 2026. Checklist: `docs/SECURITY.md`.

| ID | Issue | Result |
| --- | --- | --- |
| S1 | Customer opens `/api/admin/stats` | Blocked, HTTP 403. Covered by pytest |
| S2 | One customer reads another customer's booking | Blocked, HTTP 404. Covered by pytest |
| S3 | Technician marks arrival before accepting the job | Blocked, HTTP 400. Covered by pytest |
| S4 | Register with a bad email or a short mobile number | Blocked, HTTP 400. Covered by pytest |
| S5 | Payment marked paid with a card other than the success test card | Blocked when Razorpay keys are empty |
| S6 | Same slot booked twice | Blocked, HTTP 409, unique `slot_key` |

No open security defect was left in these checks. Demo mode still returns the password-reset code so the examiner can finish that flow without email. Turn `DEMO_MODE` off for a private launch. The public demo allows any CORS origin. Lock `CORS_ORIGINS` to the real site before that launch.
