# English editorial rollout — Poland Rent a Car

Requested 17 November 2026: adapt most Hebrew articles for international English
readers and make their practical information discoverable in search/AI answers.
This is an editorial adaptation, not automatic publication of literal copies.

## First articles — 18 November 2026

Published English adaptations (WordPress pages, editable by Idan):

- Insurance: `/english/car-rental-insurance/` (26007), paired with Hebrew 617.
- Deposit: `/english/car-rental-deposit/` (26008), paired with Hebrew 647.
- Cross-border travel: `/english/driving-rental-car-abroad/` (26009), paired with
  Hebrew 24842; also incorporates the relevant distinction from notice 25423.

The English menu and Guides index link directly to all three. Existing broad
insurance/deposit and collection/return pages remain overviews and link onward.
English home, company comparison, contact and guides explain Idan's representative
role and personal VIP support, whichever supplier the customer selects. The form
intro identifies who receives the request. VIP support is distinguished from a
supplier's separately booked VIP ABROAD assistance package.

No blanket cheapest-price claim, guaranteed upgrades or guaranteed incident
outcome. Historic amounts and Israel-specific bank/licence assumptions were not
copied. Deposit release and issuer processing are explained separately. The
cross-border guide links beside the relevant text to Kaizen's published English
fee schedule and ASFINAG's official vignette explanation. It distinguishes
permission, damage protection, towing and replacement vehicles; prices for Idan's
negotiated packages remain in the individual quote.

Source: `wordpress/prc-bilingual/content/first-guides.json`. Scope-limited admin
ability `prc-bilingual/stage-one-activate-guides` validates IDs/slugs/parents and
existing translation pairs before linking them, snapshots the English menu and
navigation, and does not rerun broad Polylang configuration. A private local
snapshot of changed English page content is excluded from Git.

Local checks cover unique topics, English content, complete SEO fields, links,
translation pairs and menu coverage alongside the existing form checks. Browser
visual verification remains unavailable in this session; public HTML checks do
not establish real-device appearance.

Verification: 11 local tests passed; all 15 live bilingual health checks passed
(synthetic request removed, no mail sent). Public checks passed for the three
articles, three Hebrew originals, English home/Guides/contact/form: HTTP 200,
direct menu links, reciprocal article hreflang, self-canonical, descriptions,
shared footer and sitemap inclusion. LiteSpeed caches were purged. Existing
request-form markup includes an internal heading in addition to the page title;
article single-H1 checks exclude that existing form markup.

## Audience and voice

Start with international visitors renting in Poland, without assuming Israeli
citizenship, an Israeli driving licence, a particular bank or prior knowledge of
Polish rentals. Use clear international English; explain both excess/deductible and
car hire/car rental when helpful. Preserve Idan's real experience and examples;
never invent customers, testimonials, cases or claimed credentials.

## Article queue

| Priority | Existing material | English article / treatment |
| --- | --- | --- |
| 1 | /scdw-insurance/ | Zero-excess car hire insurance in Poland: coverage, exclusions, supplier waiver versus reimbursement |
| 1 | /deposit-what-is-it/ | Why is a deposit required with zero-excess insurance? Amount source, card hold versus charge, release versus bank processing |
| 1 | /go-abroad/ and /go-abroad-insurance/ | Driving a Polish rental car abroad: supplier permission, insurance, permitted countries; merge old announcements into current guidance |
| 1 | /rent-price/ | What affects a car rental quote? Dates, rental periods, delivery, driver details, equipment and route |
| 1 | /price-differences/ and /why-book-through-me/ | Compare direct, agent and comparison-site offers; explain equivalent coverage and service without blanket cheapest-price promises |
| 2 | /roads-toll-in-pl/ | Polish toll roads: current official sources and vehicle/road distinctions |
| 2 | /gas-station-in-poland/ | Refuelling a rental car: fuel identification and supplier-specific return policy |
| 2 | /navigation-in-poland/ | Navigation in Poland: practical options and equipment availability |
| 2 | /fines-in-poland-and-payment-methods/ | Fines and rental administration: distinguish authority payment and supplier handling charges |
| 2 | /it-not-worth-insisting-on-a-hybrid-car/ | Is a hybrid rental worth choosing? Practical trade-offs; no guaranteed model or invented savings |
| 3 | /kaizen-rent/, /one-rent/, /rentis-rent/ | Current supplier profiles; confirm which firms Idan still offers before adapting legacy profiles |
| 3 | /kaizen-offices/ | Current location guidance; verify branches and link to current supplier instructions |
| 3 | /contact-person-and-service/ and /price-offer/ | Update contact and quote process around the actual English request form |

Do not create competing near-duplicate English pages for the same question.
The existing broad insurance/deposit and travel drafts can become overview pages
with links to these detailed guides; pair hreflang only for true equivalents.

## Per-article workflow

1. Read the complete Hebrew source, identify outdated details and Israel-specific
   assumptions, and record what needs owner or supplier confirmation.
2. Check changing rules and prices against current supplier/official sources.
   Separate general practice, supplier terms, Idan's negotiated offer and anecdote.
   Never derive a universal promise from one supplier or one historical booking.
3. Write a direct answer first, then useful headings, examples, a comparison table
   where appropriate, actual limitations and a small set of real follow-up questions.
4. Credit Idan as author for his own material; use a fact-check date only after a
   real check. Keep references beside the facts they support.
5. Give the page its own English title, description and address, a self-canonical,
   appropriate translated-page links, and accurate Article/WebPage schema.
   Structured data must match visible text. Do not promise FAQ rich results.
6. Link from a visible English guides index and related guides to the quote form.
7. Review the draft, publish, and inspect public text, mobile layout, links and SEO.
   Track English impressions, visits, quote requests and bookings separately.

## Search and AI visibility

The objective is retrieval and attribution, not a promise to train any model.
Google says normal SEO principles apply to AI Overviews/AI Mode: indexed content
eligible for snippets, crawl access, internal links, readable text and truthful
structured data. Special AI files or special AI schema are not required, and
meeting the requirements does not guarantee indexing, selection or citation.
Other AI services have their own access and selection policies.

Public robots.txt read on 17 November 2026: generic user-agent rule disallows only
/wp-admin/ (with admin-ajax exception) and lists sitemap.xml/sitemap.rss. This does
not prove indexation or absence of CDN/bot restrictions; verify those separately.
Published posts collection is empty; editorial articles are stored as WordPress
pages. Do not mistake an empty posts result for an empty content archive.

Sources checked:
- https://developers.google.com/search/docs/appearance/ai-features
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://poland-rent-car.com/info/
- https://poland-rent-car.com/scdw-insurance/
- https://poland-rent-car.com/deposit-what-is-it/
- https://poland-rent-car.com/go-abroad/

## First implementation step

Finish the English home, navigation, footer and guides index alongside Polylang
configuration. Then adapt insurance, deposit and cross-border travel as the first
three detailed guides, checking supplier facts before publishing. Existing Hebrew
articles remain available. No existing articles were overwritten by this plan.
