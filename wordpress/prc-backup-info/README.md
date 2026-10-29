# RentalCar Backups public documents

Published on poland-rent-car.com on 29 October 2026:

- `/rentalcar-backups/`
- `/rentalcar-backups-privacy/`
- `/rentalcar-backups-terms/`

The plugin creates only missing pages and never overwrites existing pages.
Published content lives in WordPress and can be edited there. HTML files are
initial content, not automatically reapplied updates. The standalone renderer
handles only pages created with this plugin's ownership marker; the main site
and request form are not rendered by it.

No OAuth secrets, tokens or customer records belong in these public files.
The texts describe drive.file access as the intended configuration and clearly
state that independent encrypted backup automation is still being configured.
Update the disclosures when automation and retention are actually enabled.

Syntax checked with php-parser. Download each live page to
`tmp/backup-{about,privacy,terms}.html` and its response headers to the matching
`.headers` file, then run:

`uv run python wordpress/tests/check_backup_pages.py`

The live checks verify public HTTP success, navigation links, privacy disclosure
sections and absence of scripts, embedded frames or login forms. Google domain
ownership verification and OAuth publication are separate remaining steps.
