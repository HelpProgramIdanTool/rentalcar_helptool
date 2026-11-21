# Hebrew rental company pages — 21 November 2026

Published after owner approval:

| Page | WordPress ID | URL |
| --- | --- | --- |
| Comparison and Idan service | 26044 | https://poland-rent-car.com/rental-companies/ |
| Car Free | 26042 | https://poland-rent-car.com/car-free/ |
| MM Cars | 26043 | https://poland-rent-car.com/mm-cars/ |

Primary Hebrew menu item 24920 now points to the comparison page. Its existing
Kaizen and One Rent children are preserved; Car Free and MM Cars were added.
The separate mobile menu also links to the comparison and all four companies;
its outdated Rentis link was replaced with MM Cars. No old article was deleted.

SEO titles, descriptions, self-canonical URLs, index/follow directives and social
titles/descriptions were saved through AIOSEO. Public HTML confirms Hebrew RTL,
one H1 per page, a viewport, responsive styles, menu links and valid JSON-LD
including WebPage and BreadcrumbList. Existing English pages were not rewritten;
no fictitious English translation links were added for the new profiles.

Layout styles are scoped to the company content. The sidebar is hidden on these
pages; comparison tables scroll within their container on narrow screens.
Browser discovery returned no connected browser. Consequently visual/mobile
browser inspection remains unverified; HTML/CSS checks are not a screenshot test.

Rebuild the review with `uv run python scripts/build_company_profiles_review.py`.
Prepare publication content with `uv run python scripts/prepare_company_pages_publication.py`.
Neither script publishes to WordPress. Generated artifacts stay in ignored output/.
