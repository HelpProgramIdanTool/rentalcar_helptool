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

## Add-on installed and checked

After the initial automatic approval rejection, Idan explicitly approved installing
and checking prc-bilingual on poland-rent-car.com. The add-on was deployed and is
active as 0.1.0. All nine admin-only health checks passed; synthetic private requests
were cleaned up, with no mail sent. Quote draft 25961 now renders the original
shortcode in English with 14 categories and no untranslated visible Hebrew text.
The English request page was then published at Idan's explicit request, using
the new no-sidebar template in add-on 0.1.1:
https://poland-rent-car.com/english/request-quote/ . Five other pages remain drafts.
Anonymous HTTP checks passed for HTTP 200, absence of sidebar markup, English
document/form, 14 categories, language/return-page fields, responsive CSS and
self-canonical. LiteSpeed caches were purged and all nine health checks passed.
The theme's shared menu/footer are still Hebrew pending full language setup.
Polylang is still inactive. App importer changes
are still pending Render deployment. Visual/mobile interaction remains unverified.

## Remaining work

1. Completed: deploy add-on and check server health. A health check is not a live
   submission or proof that a real notification email arrived.
2. Completed: replace quote draft's placeholder with the original English shortcode.
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
