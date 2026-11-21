# Offer company comparison — prepared for 2026.11.21.1

The shared offer preview/email/copy template now includes a compact comparison
immediately after the vehicle-options heading. It selects only suppliers present
in included options and shows each supplier once. Rows cover vehicle age,
collection, return, fuel, onboard GPS and foreign handover. Common cover/support
and the distinction between foreign handover and driving abroad appear once.
The plain-text email also carries the comparison and article link.

Hebrew links to `/rental-companies/`; English, Polish and Russian link to
`/english/compare-rental-companies/`. Polish explicitly labels the article English.
The existing English article (WordPress page 25957) was updated and publicly
verified: current company facts, support abroad, SEO description, canonical,
English language and one H1.

Facts come from `partners.SupplierSummary.facts`; translated facts live in its
`translations` dictionary. Labels, article URLs and common wording live in
`PortalConfiguration.content.offer_comparison`, by language. Both models are
editable in admin. Missing translations display the configured unknown label;
Hebrew is never silently inserted into an English/Polish comparison.

Migration 0009 follows 0008. It changes comparison content only, preserving
existing custom translations/configuration; it does not change prices or orders.
The website is published text, not a live Render database feed: future fact edits
must also be republished to WordPress. The English article builder reuses the
same seed facts rather than a second hardcoded comparison table.

Verification: 45 focused tests passed (comparison, email editor, localized offer,
price preview and partner comparison). Checks cover selected companies,
deduplication, all requested languages, database source, custom-content
preservation, placement and plain-text links. No migrations are missing.

Generate review snippets with `uv run python scripts/build_offer_comparison_previews.py`.
No real email was sent. Application installation on Render is still pending a
fresh verified backup and manual deployment. Existing saved/edited email bodies
are historical snapshots and must be regenerated to show the new comparison.
