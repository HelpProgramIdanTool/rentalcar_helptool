# Request form submission guard

Prepared for the live `poland_car_request_form` shortcode and the publicly served
form plugin 1.6.1. This separate plugin prevents repeat browser submit events and
disables submit buttons after validation. Back navigation restores the form.
It does not send test email or modify saved requests.

Run `node --test --test-isolation=none wordpress/tests/submit_guard.test.cjs`.

Deployment is pending authenticated website access. This is the browser-side
protection only. Server-side deduplication still requires inspecting the original
PHP handler and its success/failure redirects, validation and mail handling.
Do not claim this plugin prevents replayed HTTP requests or duplicate submissions
from separate tabs. Test those against the PHP handler with email intercepted.
