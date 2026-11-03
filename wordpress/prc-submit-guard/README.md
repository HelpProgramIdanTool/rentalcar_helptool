# Request form submission guard

Prepared for the live `poland_car_request_form` shortcode and the publicly served
form plugin 1.6.1. This separate plugin prevents repeat browser submit events and
disables submit buttons after validation. Back navigation restores the form.
It does not send test email or modify saved requests.

Run `node --test --test-isolation=none wordpress/tests/submit_guard.test.cjs`.

Deployed to poland-rent-car.com on 2026-11-03, integrated with the existing
`poland-car-request-form` plugin as version 1.6.2. The optional standalone
`prc-submit-guard.php` wrapper is not activated on that site. The existing plugin
loads `assets/submit-guard.js` itself, after its original validation listeners.

`handler-1.6.2.patch` records the exact changes to the retrieved 1.6.1 PHP handler.
Deploy `request-dedup.php` beside that handler before applying the patch, and place
`submit-guard.js` in its `assets` directory. A private copy of the original handler
is retained outside Git for rollback. Existing requests are not rewritten.

The server hashes all normalized business fields, sorts checkbox selections, and
looks for an identical saved request in the last ten minutes. A MySQL named lock
serializes lookup plus creation. Repeated submissions reuse the saved request ID
without resending email. Changed data creates a new request. A failed save does
not reserve the hash. Existing email failure/retry handling remains unchanged.

The deployed handler was tested with `../tests/request_dedup.integration.php`
through an authenticated, single-use temporary QA wrapper. Three repeated requests
produced one saved request and one intercepted mail attempt. Changed data produced
a separate request; invalid contact data produced none. SMTP was intercepted; no
test mail was sent. The two synthetic posts and the QA endpoint were removed.
The integration test uses a real WordPress database and its MySQL locking path;
parallel HTTP submissions have not been load-tested.
