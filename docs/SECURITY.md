# Security checklist

- Passwords are hashed with bcrypt. Plain text is never stored.
- Login uses JWT (HS256) with a 12-hour expiry. Logout revokes the token id in memory.
- Login, register and forgot-password are rate limited.
- Role checks sit on every protected route. Customers only see their bookings. Providers only see their jobs. Technicians only see assigned jobs.
- Queries go through SQLAlchemy, so values are bound parameters.
- Uploads allow JPG, PNG, WEBP and PDF only, capped at 5 MB, saved under a random name.
- Booking image URLs must match `/uploads/<file>`.
- Payment status cannot be flipped to paid without the test card, or without a valid Razorpay signature when live keys are set.
- Errors returned to the client do not include stack traces.
- Secrets belong in environment variables. See `.env.example`. Do not commit `.env`.
- CORS origins come from `CORS_ORIGINS`. Set this to the real frontend origin before a locked-down production launch.
- Password reset codes expire in 15 minutes. Demo mode shows the code because email delivery is optional. Turn `DEMO_MODE` off so the code is not returned by the API.
