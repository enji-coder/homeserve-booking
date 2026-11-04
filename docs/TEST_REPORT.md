# Test report

Ran `python -m pytest backend/tests -q` on 4 Nov 2026.

Result: **9 passed**.

Covered:

- Percent, flat and capped coupon math, GST and commission.
- Hourly slot generation.
- Health and the public catalog.
- A customer cannot open the admin stats API.
- Full path: book a slot, second booking of the same slot is rejected, another customer cannot read the booking, provider accepts and assigns a technician, technician arrives and completes, customer pays with the Razorpay test card, invoice is created, review is stored.
- Forgot-password demo code and reset.
- Admin CSV export and provider approval.

Manual UI check on the running app: landing, customer login, service list, booking form, slot selection, and a new pending booking (`Fan installation`, 16 Dec 2026, 10:00) all worked.
