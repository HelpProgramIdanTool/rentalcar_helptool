# Poland Rent a Car — Hebrew and English

Started 17 November 2026 at Idan's request. The target is poland-rent-car.com.
Idan selected Polylang's free base. Existing Hebrew URLs must remain unchanged;
the existing English landing page /english/ must retain its address.

## Completed

- Hostinger reconnected. Hostinger AI installed with explicit user approval.
- Read installed plugins, current site settings, pages, menus and original form.
- Polylang 3.9.2 installed, not activated/configured.
- Six English drafts created in WordPress: 25956 home, 25957 company comparison,
  25958 insurance/deposit, 25959 collection/return/travel abroad, 25960 contact,
  25961 quote request. SEO title, description, focus keyword and social metadata
  written and returned by AIOSEO without skipped fields.
- Text, metadata, editor links and form translation source saved under
  wordpress/prc-bilingual. No fabricated price or deposit amounts.
- Separate English-form add-on prepared. It retains the original shortcode,
  validation, storage, deduplication and notification recipient. No real requests
  or emails have been submitted by this task.
- Application import reads explicit Client language markers. Prepared locally,
  not installed on Render. 23 importer tests and five Node tests pass.

## Immediate dependency

Automatic approval review rejected deploying the local prc-bilingual add-on:
new executable code on production needs separate user approval. The approval
question is pending. Do not retry by another route without that approval.

## Remaining work

1. After approval, deploy only the add-on folder, activate it, run its admin-only
   health ability and inspect English form output. A health check is not a live
   submission or proof that a real notification email arrived.
2. Replace quote draft's placeholder with the original English-enabled shortcode.
3. Back up WordPress pages, SEO, menus and settings before Polylang activation.
   A Render backup does not back up WordPress.
4. Configure Hebrew default/English, preserve current paths and /english/, assign
   languages to existing content correctly; do not assign English backup-app
   disclosure pages to Hebrew. Pair only actual equivalent translations.
5. Build English desktop/mobile menus and footer; add the native-name switcher.
6. Verify AIOSEO language/schema, self-canonicals, reciprocal hreflang, sitemap,
   logo links, translated field errors, receipt and retained data after errors.
7. Install importer patch on Render together with pending invoice-email fix using
   the normal fresh-backup and versioned-release workflow.
8. Review/publish the complete English route and read public output back. Until
   then, do not claim the site is bilingual or that the English form is live.

See wordpress/prc-bilingual/README.md for implementation details and draft links.
