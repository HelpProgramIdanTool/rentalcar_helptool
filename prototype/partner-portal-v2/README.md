# Partner cabinet — design and browser presentation

## Current version: one scrolling workspace (19 November 2026)

Idan rejected the separate-screen flow and low contrast. `index.html` now loads
`cities.js`, `workspace.js`, `workspace-main.js`, and `workspace.css`. The entire
journey, company comparison/vehicle selection, saved offer and driver/invoice
form remain mounted on ONE page. Choosing a vehicle scrolls to its order form;
the final review expands below it. Input edits invalidate that review. The
header links jump within the page. Stronger navy/blue section headings, yellow
number markers, darker input borders and primary actions replace the pale layout.

Both date fields have a real native calendar input and editable DD.MM.YYYY text,
kept in sync. Time lists contain all 48 half-hour values. Each city list includes
the union of the operator's fallback cities and active local OfferCity records:
24 public names, plus OTHER. No prices, customers or secrets were exported.
Regenerate the list with `uv --cache-dir .uv-cache run python scripts/export_partner_design_cities.py`.
Cities/services are separate; address, foreign-country, invoice and extra-driver
fields expand as required. Unknown routes are directed to Idan in the design.

Current tests: `node --test --test-isolation=none prototype/partner-portal-v2/workspace.test.cjs`
(six checks: persistent single-page fields, complete city union, native calendar
sync/half-hour controls, no duplicate groups, inline invoice/order and invalid
dates/review invalidation). Live HTTP/JSDOM confirms all scripts load and both
native calendars are present. Actual browser screenshots/device checks remain
unavailable. The five-point presentation now explains the same scrolling page.

The earlier screen-based `design.js` and its tests remain as a historical design
reference only and are no longer loaded by index.html. Details below describe
that earlier iteration, not the current active entry point.

Approved workflow: `docs/tasks/partner-portal.md`, 18 November 2026.
Design reference: the Hebrew/English poland-rent-car.com foundation and Idan's
approved DSC08781 portrait. Interface in Hebrew; ten-step presentation commentary
in Russian for Idan's design review. This is a local HTML presentation, not PPTX.

Run with the project's isolated Python environment:

```powershell
uv --cache-dir .uv-cache run python scripts/preview_partner_portal_v2.py
```

- Design: http://127.0.0.1:8778/
- Presentation: http://127.0.0.1:8778/?presentation=1
- Login screen: http://127.0.0.1:8778/#login
- Owner screen: http://127.0.0.1:8778/#owner

The prototype also opens directly from `index.html`; all assets are local.
It contains no real customer records, users, passwords or supplier prices.
Example records use DEMO numbers and example.invalid addresses. The owner's
explicitly requested copy address is shown in mail previews. No network calls,
emails, authentication, actual quote calculations or actual orders are performed.
State is memory-only and resets on reload. This prototype must not be used as
the real product; implement approved designs through the existing Django app.

## Screens and interactions

Revision 19 November: company comparison moved to the vehicle-selection screen
and opens there by default. A saved offer follows the operator's existing
`inquiry_saved.html` pattern: numbered variants, each with its own “choose and
create order” button. There is no shared radio selection/order button. Selected
company/group remain visible in the driver form and final confirmation. Entered
details survive returning to correct the form. Offer-mail controls are separate
from ordering. Final dispatch is a distinct action after reviewing recipient,
vehicle, trip, driver and invoice details.

Login → dashboard → trip → 14 categories → offer/recipients → single-option
booking → order details/change/cancellation request. Separate manual-request and
owner screens. Invoice and second-driver fields expand when needed. Shared
group selection synchronises across categories and marks an existing selection.
The tour explains the seven-day price protection, supplier-specific price-list
updates and mandatory owner copies without fabricating money values.

Limitations: available group rows are a small layout sample, not a complete
supplier catalogue. Where the real representative models have not been checked,
the design says they will come from the price list. Young-driver calculations,
supplier price-list versions, account isolation and mail retries remain backend
work; the design routes exceptional declarations to manual review rather than
claiming to calculate an unknown charge. The real implementation must calculate
known young-driver rules automatically as specified in the approved brief.

## Verification

`node --test --test-isolation=none prototype/partner-portal-v2/design.test.cjs`
uses the existing ignored WordPress QA dependency folder. Ten interaction checks:
14 categories/no duplicate group, explicit client email, dates/48 time slots,
invoice/second-driver fields, requests through Idan, all ten presentation steps,
and owner switching between distinct cabinet histories in the demonstration.
Additional checks cover comparison placement, the exact selected vehicle through
order details/confirmation, retained correction fields and supplier-specific
blocking after a price-list update outside the protected period.
HTTP checks confirm HTML, CSS, JavaScript and portrait are served. No connected
browser was available for screenshot or real-device verification; responsive
CSS is prepared but visual approval remains with Idan.
