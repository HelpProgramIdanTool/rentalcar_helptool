# Poland Rent a Car — Hebrew and English

## First stage completed — 17 November 2026

Idan explicitly redirected work to completing the English home, menus, footer,
language switcher and Car Rental Guides before adapting the article archive.
This foundation is now published on poland-rent-car.com.

| Page | WordPress ID | Public address |
| --- | --- | --- |
| English home | 25371 | /english/ |
| Company comparison | 25957 | /english/compare-rental-companies/ |
| Insurance/deposit overview | 25958 | /english/insurance-and-deposit/ |
| Collection/return/abroad overview | 25959 | /english/collection-return-and-travel-abroad/ |
| Contact | 25960 | /english/contact/ |
| Quotation form | 25961 | /english/request-quote/ |
| Car Rental Guides | 25970 | /english/car-rental-guides/ |
| English privacy policy | 25971 | /english/privacy-policy/ |

The old English-home preview 25956 remains an unpublished draft. The English
privacy policy translates the existing Hebrew policy rather than inventing new
legal obligations. Guides links to the available English overviews; detailed
adaptation of the Hebrew article archive has not started.

## Languages, navigation and layout

- Polylang 3.9.2 is active: Hebrew default (he_IL), English (en_GB).
- Content-based language resolution (force_lang=0) preserves existing addresses;
  its supported compatibility option is enabled. Browser-language redirects are off.
  Recheck this mode before any future Polylang upgrade.
- True translation pairs: home, form, contact, guides index and privacy. Combined
  overviews without matching Hebrew content are not assigned false equivalents;
  their switcher falls back to the other language's home.
- English WordPress navigation menu ID 97 is editable in the normal menu admin.
- PRC Bilingual Form 0.2.0 provides shared English header/footer and two no-sidebar
  page templates. English pages do not render the Hebrew theme chrome.
- Footer wording and contact details are stored in a WordPress option and editable
  in Appearance → Customize → PRC — English site. JSON supplies initial defaults.
- All public English pages have English SEO titles/descriptions, self-canonicals,
  English document/schema language and Open Graph locale. Polylang supplies
  reciprocal hreflang only for actual pairs. Hebrew menu language links are paired.

## Preservation and verification

Before changes, an admin-only snapshot preserved 34 pages, the affected SEO fields,
selected language/front-page settings and both original menus. Protected WordPress
option: prc_bilingual_stage_one_backup. Local copy:
private_uploads/prc-foundation-backup-20261117.json (ignored by Git).
This is a scoped rollback snapshot, not a full hosting/database backup.

Anonymous checks verified all eight English pages and reciprocal language pairs.
All 22 previous Hebrew addresses still return HTTP 200 at their original URLs.
English home, form, guides and privacy appear in the XML sitemap. The English form
keeps all 14 categories, DD.MM.YYYY presentation and 48 half-hour time choices.
The server checks validate rendering, retained values, saved language and retry
headers without sending mail; synthetic private test requests are deleted.
Eight local Node tests pass. Combined published-script verification also passed
for exact dates/times and two rental days; no request was submitted by the agent.

No connected browser was available. Real desktop/mobile visual interaction remains
unverified; HTTP/DOM checks must not be described as a real-phone visual test.

## Appearance correction — 18 November 2026

Idan reported unreadable active Hebrew language text, a second selector below the
header and inconsistent Hebrew/English footers. Add-on 0.2.1 is deployed:

- Removed the extra selector prepended to the Hebrew form. Existing desktop/drawer
  header menus keep their selectors; there are no selectors in the page content.
- Protected selected and unselected link colors from Divi's higher-priority menu
  rules. Published active text/background contrast is 11.74:1.
- Both languages use footer.php and the same CSS. Hebrew uses RTL; contact details
  have one shared saved source. Hebrew labels are editable in the Customizer's
  PRC — עברית section. The previous Hebrew theme footer is retained but hidden,
  so disabling the add-on restores it.
- Hebrew menu modules fall back to the Hebrew primary menu instead of the most
  recently created English menu when no menu is selected.
- Nine local tests and all 15 server checks pass, with no mail sent. Anonymous
  page checks confirmed a single shared footer per page, no selector in content,
  matching footer structures and contact links, and RTL/LTR direction.

No connected browser was available for real-device screenshots; these checks cover
published HTML, explicit color priority and contrast, not real-phone visual output.

## Application status

## English alignment correction — 18 November 2026

Idan's screenshot showed English header/menu inheriting RTL layout. Add-on 0.2.2
sets explicit LTR direction on English body, header, navigation and menu list,
left text alignment and normal row order. Header and nav also have dir=ltr.
Ten local tests pass, including computed styles with a deliberately RTL WordPress
body. Public English home and quotation page return 200 with updated CSS 0.2.2.
LiteSpeed cache was purged. Real-device screenshot verification remains unavailable.

Render 2026.11.17.2 is live (737 passing tests), verified by public HTTP 200 and
version output. It includes explicit English website-language import and supplier
invoice details. Idan confirmed a post-deployment encrypted backup with remote
read-back. Historical customer reservations and sent letters were not changed.

## Next stage

Follow docs/tasks/english-editorial-plan.md: adapt insurance, deposit and cross-border
travel first, verifying current supplier rules. Do not substitute literal translation
or present historic supplier amounts as universally current. Existing Hebrew articles
remain available. No indexation or AI-citation guarantees are made.
