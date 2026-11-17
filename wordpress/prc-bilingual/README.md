# Poland Rent a Car — bilingual foundation

Deployed version 0.2.0 on poland-rent-car.com. Polylang 3.9.2 is active; Hebrew is
default and English is the second language. Existing addresses are preserved.

## Published

- /english/ — existing landing page updated in place (25371).
- /english/compare-rental-companies/ (25957).
- /english/insurance-and-deposit/ (25958).
- /english/collection-return-and-travel-abroad/ (25959).
- /english/contact/ (25960).
- /english/request-quote/ (25961).
- /english/car-rental-guides/ (25970).
- /english/privacy-policy/ (25971).

English pages use shared WordPress header/footer, English menu 97 and no sidebar.
Templates: prc-english-page.php and prc-request-full-width.php, served by
request-full-width.php. Menu items are editable in WordPress. Footer wording is
stored in prc_bilingual_navigation and editable in Appearance → Customize →
PRC — English site. content/navigation.json is initial/default data, not a second
authoritative copy of the saved settings.

Content source: content/en-pages.json and content/foundation-pages.json. The former
home preview is still draft 25956; the real home remains 25371. Current editor links
and public URLs are in content/draft-pages.json.

## Form compatibility

The add-on retains the original poland-car-request-form handler, storage, recipient,
retries and deduplication. The shortcode supports explicit language="en" and current
Polylang English context. Server HTML translates labels, not submitted option values.
Dynamic errors are translated; customer-entered text is retained.

DD.MM.YYYY is displayed while original slash dates remain the handler's internal
representation. Accessible native calendars remain available. Each time dropdown
has 48 zero-padded half-hour choices. The original handler performs date validation
and day calculations; pickers.js triggers its existing change handlers.

_prc_client_language is saved before the notification and read again on retries.
The internal notification retains Hebrew field labels and includes Client language:
English. Render 2026.11.17.2 imports that marker into the English quote language.

## Setup, SEO and preservation

stage-one.php exposes capability-protected, fixed-scope backup/configure/state
abilities. content/stage-one.json lists the reviewed page IDs and real translation
pairs. It never selects customer request records. Setup first requires a protected
snapshot of affected public pages, selected options, menus and SEO fields.

Polylang content-based URLs (force_lang=0) use the compatibility option
pll_language_from_content_available=yes. This was checked against installed 3.9.2
source and live URLs. Recheck before upgrading Polylang. Browser detection is off;
English backup-app disclosures remain at their original addresses.

English canonical/meta/social fields are saved in AIOSEO. Scoped display filters
keep English schema language and locale consistent. Polylang outputs hreflang for
genuine translation pairs. Broad combined overviews without a Hebrew equivalent
fall back to the Hebrew home in the switcher and do not claim a false pairing.

## Checks

Run node --test --test-isolation=none wordpress/tests/bilingual.test.cjs.
Eight tests cover PHP syntax, content/translation mapping, 14 categories, errors,
unchanged Hebrew values, dot dates and exact times. The admin-only health ability
checks server rendering, language storage/retry headers and English privacy links;
it creates/removes one synthetic private request and sends no mail.

Public verification: eight English pages, header/footer, no sidebar, English text,
canonical/locale, reciprocal language links, sitemap inclusion and all 22 original
Hebrew URLs. Combined published-script controls passed without submitting a form.
No connected browser was available, so real-device visual verification is pending.

Hostinger AI, Polylang and this add-on were installed with user authorization.
Deployment and publication were part of the explicitly requested site rollout.
No original articles, real reservations or sent emails were deleted or resent.
