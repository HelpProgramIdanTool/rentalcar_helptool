# Trip2Poland rental page

19 November 2026: plugin 1.6.3 deployed, page.js asset 7.3. GPS removed from
public choices, summary and restore selection. New POST data sets GPS to no;
notifications omit the field. The rental program's manual GPS service remains.
Live recipient/date checks passed and the public page has no selectable GPS
input. No test requests or emails were sent during verification.

Approved v7 design at `/rent-a-car-in-poland/`, page 85.
The page contains `[trip_car_request_form]`.

The handler is adapted from the existing Poland Rent Car 1.6.2 handler. Requests
are saved privately in `trip_request` before email, with duplicate suppression,
rate limits and retry actions in WordPress admin. The recipient is read from
Calculated Fields Form 18 (`fp_destination_emails`); there is no fallback address.
Rental dates use Europe/Warsaw independently of the site's general timezone.

Run `node wordpress/tests/trip_rental.test.cjs`.
The admin-only `trip-rental/health` ability checks recipient configuration and
server date validation without sending email or creating requests.

Original page backup: ignored `private_uploads/trip-page-backup-20261113.json`.
To restore, replace page 85 content with that backup's `content.raw` first.
Do not deactivate the plugin while the page still uses its shortcode.

Live publication: 13 November 2026. Browser visual checks and actual mailbox
delivery are separate from the automated validation checks.
