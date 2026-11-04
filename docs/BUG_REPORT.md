# Bug report

Date: 4 November 2026.

| ID | What was wrong | Status |
| --- | --- | --- |
| B1 | A technician could mark arrival without first accepting the assigned job | Fixed. `POST /api/bookings/{id}/accept-job` is required before arrival |
| B2 | A paid booking did not send the review request listed in the notification module | Fixed. A full payment creates "Please review your visit" |
| B3 | Admin stats included cancelled bookings and customer growth, but the overview did not draw them | Fixed on the admin overview |
| B4 | The service list requested 50 rows, so the pagination control never appeared | Fixed. The catalog pages 6 at a time |

No open defects were left from the booking, payment, role, or report checks in `docs/TEST_REPORT.md`.
