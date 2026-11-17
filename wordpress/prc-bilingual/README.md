# Poland Rent a Car: Hebrew / English rollout

Idan approved Polylang's free base on 17 November 2026. Hostinger AI installation
was separately approved and completed. Polylang 3.9.2 is installed, not activated.
The English request page was published at Idan's explicit request on 17 November.
URL: https://poland-rent-car.com/english/request-quote/ (page 25961).
It uses the add-on's registered no-sidebar page template, with the theme header
and footer retained and responsive page gutters. Only this page is published.

`content/en-pages.json` holds reviewable first-release text and SEO metadata.
Six corresponding drafts have been created in WordPress, IDs 25956–25961;
`content/draft-pages.json` records their editor links. Their SEO and social-preview
metadata were written to AIOSEO with no skipped fields. Five remain unpublished;
the request form page is published for Idan to review on the real site.
These are drafts. Quote draft 25961 now contains the translated original shortcode
`[poland_car_request_form language="en"]`. Do not insert a generic contact form.

`prc-bilingual.php`, `form.js`, `form.css` and `content/form-en.json` implement a
separate add-on to the existing shortcode, not a replacement handler. Explicit
`[poland_car_request_form language="en"]` supports English previews before
Polylang activation. Server-rendered English preserves submitted Hebrew option
values; existing validation and deduplication remain authoritative. Dynamic errors
are translated without changing input values. Saved `_prc_client_language` is
attached to the request before mail and read again on retries. Internal notification
field labels stay Hebrew for the existing application parser, with an explicit
`Client language: English` header. The application importer patch is prepared but
still needs the next Render update before language selection becomes automatic.

Installation was initially rejected by automatic approval review; Idan then
explicitly approved installing and checking this add-on on poland-rent-car.com.
It is now installed and active as version 0.1.2. Polylang remains inactive.
Hostinger AI was installed with separate approval; Polylang installation was approved.

An admin-only `prc-bilingual/health` ability checks server rendering, input values,
saved language and retry headers. It creates and removes one synthetic private
request; it never calls wp_mail. All nine server checks passed after deployment:
rendered translation, preserved values, language field, unchanged Hebrew, inline
spaces, dynamic footer translation, saved language, retry language, unrelated mail.
The complete rendered draft includes 14 categories, the English language field and
no untranslated visible Hebrew text. No real customer requests were altered.
Visual/mobile verification has NOT run yet and remains a release gate.

After publication, anonymous HTTP checks passed: HTTP 200, registered full-width
template, no sidebar markup, English document/form, all 14 categories, saved-language
and return-page fields, responsive stylesheet and self-canonical. LiteSpeed cache
was purged. All nine server health checks passed again, with no mail sent.
Version 0.1.2 adds editable DD.MM.YYYY date presentation (original slash-format
submission retained), accessible calendar overlay and 48 half-hour time choices.
English request page now has an English header and paired language links; the
Hebrew form has paired links too. The footer and other pages await full Polylang
setup. Public checks and all 11 server health checks passed. Seven Node tests pass.
An additional check executed the published form's inline scripts together with the
original form/date scripts in a DOM environment: 20.12.2030 00:30 to 21.12.2030
23:30 kept the dot display, original server dates, exact times and two rental days.
No request was submitted. This checks script interaction, not real phone rendering.

Local verification: five Node tests pass (PHP syntax, content/SEO fields, 14
categories, dynamic English messages, unchanged Hebrew values and presentation).
All 23 inquiry-import tests pass, including explicit language markers.

Run `node --test --test-isolation=none wordpress/tests/bilingual.test.cjs` and
`uv run python manage.py test quotes.test_inquiry_import --noinput`.

The existing English landing page ID 25371 at `/english/` must retain its address.
The landing-page draft has a temporary slug; its content goes into that existing
page only after review. English child pages belong under that page.
Hebrew front page: 579. Hebrew request form: 25453. Preserve Hebrew addresses.

## Language setup

- Hebrew is default, hidden from existing URL paths. English is the other language.
- Keep `/english/` as the landing URL. Decide and verify the Polylang language URL
  settings against a backup before activation; do not accidentally produce
  `/en/english/` or redirect existing Hebrew pages.
- Assign Hebrew to existing Hebrew pages, English to English content; backup-app
  English disclosures are not Hebrew translations and must not be misclassified.
- Pair only true translated equivalents. The broad travel page and insurance page
  need their scope matched to the Hebrew originals before hreflang pairing.
- Use native-language switch labels `עברית / English`; preserve matching pages.
- Separate English menus, including mobile navigation, footer and the logo link.
- Validate AIOSEO title, description, self-canonical, locale and JSON-LD language
  separately; inspect rendered HTML, hreflang reciprocity and XML sitemaps.
- No automatic redirect based on visitor location or browser language.

## Original form and application integration

The existing plugin is `poland-car-request-form`, version 1.6.2. Its private backup
is ignored under private_uploads. Keep its recipient configuration, server date
checks, private request storage, retries and submission deduplication.

Translate headings, labels, option labels, help, placeholders, validation messages,
summary, buttons, errors and receipt. Use left-to-right layout and 24-hour local
times. Preserve category count and established machine values. Save language with
the request and carry it through retry emails and application import; the current
application parser defaults to Hebrew, so translating only visible fields is
insufficient. Verify English preferred_language without guessing from a name.

Do not submit a live request or email customers for testing. Intercept mail and use
synthetic test records. Check save-before-send, retries, failures, duplicates,
foreign routes, date limits, all categories and both languages on mobile.

## Publication gates

1. Back up site settings, menus, pages, SEO data and original form source.
2. Prepare drafts, form translation, integration and preview checks.
3. Obtain any deployment confirmation required by the Hostinger skill for the
   concrete plugin and target domain; do not replace the whole WordPress site.
4. Publish and read back public desktop/mobile pages, links and SEO output.
5. Verify form receipt and saved language with intercepted test mail.

No made-up prices, fleet sizes or universal deposit/payment guarantees. Company
comparison follows Idan's stated differences and must stay aligned across languages.
