Controlled homepage experiment: move the existing Divi deferred layout style element
from the page body to the end of the document head. CSS contents are preserved byte for byte.
No CSS properties, stored pages, theme files, fonts, video or analytics settings are changed.
Changing style order can affect the CSS cascade; a visual comparison is still required.

Only logged-out homepage requests are affected. Previews and Divi editing are excluded.
Unexpected documents, missing styles and multiple matching blocks are left unchanged.

Rollback: deactivate **PRC Early Styles**, then purge LiteSpeed Cache.
Keep **PRC Page Speed** disabled during this experiment.

Validate PHP syntax with the existing temporary php-parser QA package.
After deployment, compare the live page against the baseline: the moved style must occur
once in the head, its contents must match, and removing it from both documents must leave
the same sequence of style elements. This checks preservation, not visual correctness or speed.
