# Poland Rent a Car — bilingual foundation

Deployed version 0.2.5 on poland-rent-car.com. Polylang 3.9.2 is active; Hebrew is
default and English is the second language. Existing addresses are preserved.

19 November: GPS choice removed from the public Hebrew and English forms.
The handler keeps a hidden canonical no answer and ignores cached public GPS
selections. New notifications omit that field; historical request messages are
not stripped unless they carry the new no-public-GPS marker. Navigation remains
available to operators in the rental program. All 17 live health checks passed,
including removal in both languages. Public forms verified after cache purge.

## Published

Idan's approved portrait (`assets/idan-portrait.jpg`, original DSC08781.JPG) now
appears in a shared author card on Hebrew and English public pages. Home, contact
and quote pages show the introduction first; other pages show it after the article.
Quote forms use a smaller card. Privacy policies are excluded. The main-content
filter excludes feeds, admin and secondary loops and prevents duplicate cards.
Localized copy is initialized from `content/author.json` and editable through
Customizer → PRC — Idan (en/he), stored as WordPress options. The picture is an
unaltered original; circular display uses CSS. Hosting may optimise JPEG transfer.
Public verification checked ten pages with one correctly localized card each,
two privacy pages without it and the served image dimensions/appearance. Local
suite: 12 tests passed. Real-device visual review remains outstanding.

First adapted articles (18 November 2026), linked from the English menu and Guides:

- /english/car-rental-insurance/ (26007; Hebrew source 617).
- /english/car-rental-deposit/ (26008; Hebrew source 647).
- /english/driving-rental-car-abroad/ (26009; Hebrew source 24842).

`content/first-guides.json` records the reviewed publication copy; published text
is editable in WordPress. The scoped `stage-one-activate-guides` admin ability
links these translations, snapshots the English menu/navigation, adds direct
menu links and updates the English footer's representative-service description.
It does not rerun site-wide language configuration or rewrite Hebrew articles.

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

The public contact email is idanrentacar@gmail.com, confirmed by Idan on 18 November.
contact-email.php provides an admin-only dry-run/apply update for the shared option
and explicitly identified old owner addresses in site pages/theme layouts, retaining
WordPress revisions. It excludes request records, SMTP and account/admin settings.

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

Version 0.2.3 explicitly sets English body/header/menu direction to LTR and aligns
them left, including when WordPress keeps its rtl body class. A computed-style
regression test covers that inherited-RTL case. Ten local tests pass. Public home
and request-page checks confirm dir=ltr and the updated versioned stylesheet.

Version 0.2.1 fixes Divi overrides on active language colors and removes the
form-level Hebrew selector. Both languages render footer.php with shared CSS;
the Hebrew theme footer is reversibly hidden. Hebrew footer labels live in the
prc_bilingual_navigation_he option (Customizer → PRC — עברית). Brand, phone and
email stay in the shared navigation option. Empty Hebrew menu selections resolve
to the Hebrew primary menu, not the latest English menu. Public regression checks
confirm no in-content switcher, matching footer structures, correct directions and
11.74:1 active-button contrast. Nine local tests and 15 server checks pass.

Run node --test --test-isolation=none wordpress/tests/bilingual.test.cjs.
Nine tests cover PHP syntax, content/translation mapping, 14 categories, errors,
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

### Mobile language panel — 0.2.6, 21 November 2026

The Hebrew Divi header now copies its existing paired-language selector into the
menu panel beside the mobile trigger. At widths up to 980px the copy is visible
without opening the dropdown and the original dropdown item is hidden. Desktop
menus retain their original selector. The standalone English header is unchanged.
Scripts/styles use version 0.2.6 to refresh cached assets. No language targets are
hardcoded in JavaScript: paired links and the active language come from PHP.

Fourteen local tests pass. Public checks confirm current assets on the Hebrew
homepage, article and English homepage; execution against the actual public
header confirms both Divi menu variants mount the selector. No connected browser
was available for a visual screenshot check. Plugin-only deployment succeeded.
