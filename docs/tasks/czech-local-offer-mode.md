# Local Car Free rental in Czechia — 2026.11.21.2 prepared, not deployed

Owner requested a separate entry mode for local Czech rentals. The existing
ordinary workflow remains the default. The mode uses the configured
SupplierLocalBranch, not a hardcoded supplier ID or another calculator.

New fields on a local branch:

- offer_mode_enabled / offer_mode_label / offer_mode_help: editable entry mode.
- offer_mode_pricing_confirmed: explicit permission to reuse the supplier's
  current tariffs and conditions. Defaults to false.

New quotes retain local_rental_branch. It survives editing and copying. In the
form the mode sets the rental country, restricts the supplier/groups and city
choices and explains that crossing the border means leaving the rental country.
The ordinary-mode button preserves customer, dates and route fields. The server
also validates supplier and handover countries; both international directions
are rejected in this local mode. The calculator independently checks the mode
and blocks available prices when supplier, route, country or price confirmation
do not match. Historical ordinary-mode quotes are unchanged.

The existing country wording mechanism continues to localize supplier conditions
and document blocks. The Poland-specific generic comparison is omitted in a
dedicated local quote rather than presenting misleading Polish handover/support
conditions. A future country-specific comparison can be configured separately.

Migrations: suppliers.0060–0063 and quotes.0030. Migration 0061 labels
the existing Czech Car Free branch and enables the UI mode, but deliberately
does NOT confirm its tariffs. No real prices, quotes or bookings were changed.

Owner replied “такие же цены” to the tariff/currency/deposit/supplement question.
Migration 0063 records that confirmation for the Czech Car Free branch only.
It does not copy or alter monetary rates. Future local modes still default to
unconfirmed prices. Production installation requires a fresh verified backup.

Checks: 62 focused Django tests, 71 booking/partner regression tests and one
JavaScript interaction test. The live-price mode forwarding, country wording
and targeted owner-price-confirmation tests are included in the focused suite.
Checks include server validation, route direction, database wording, mode
persistence, price guard, normal-mode return and preservation of customer data.
