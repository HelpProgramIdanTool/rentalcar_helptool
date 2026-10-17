Compatibility fix for the existing poland_car_request_form shortcode.

The real date input becomes visible and directly interactive. This removes the need
to open a hidden date input with showPicker() or a synthetic click. Browser date
formatting may follow the device language. Existing hidden submitted DD/MM/YYYY
values, validation, minimum dates and date-change listeners remain in use.

The original form plugin and stored requests are not modified. Disable this plugin
and purge LiteSpeed Cache to restore the previous form.

Run: node --test --test-isolation=none wordpress/tests/native_dates.test.cjs
Requires the existing temporary QA dependencies in tmp/wordpress-qa.

Before claiming device compatibility, check both dates on a real iPhone and Android,
including changing pickup after selecting return. Do not send a real request as a test.
