Homepage-only performance changes for poland-rent-car.com.

- Preloads the existing first Divi section background, reading its URL from the saved page.
- Replaces YouTube embeds with an accessible link and thumbnail. Clicking loads the original player.
- Preserves the original video's aspect ratio and title. Other iframe hosts are untouched.
- Skips previews and Divi editing. Does not change page content, theme files, analytics, ads or form settings.

Rollback: deactivate **PRC Page Speed** in WordPress, then purge the homepage cache.
No database restore is needed because this plugin does not write page content or settings.

Verification from the repository root:

```
npm.cmd install --prefix tmp/wordpress-qa --no-audit --no-fund php-parser jsdom
node --test --test-isolation=none wordpress/tests/video.test.cjs
```

The QA packages stay inside the ignored temporary directory, not in global packages.
Visual and PageSpeed comparisons must be done separately; successful HTTP responses do not prove either.
