# Render: first test deployment

The local database stays authoritative until the agreed final transfer.
Do not upload customer data or create real orders on the test server yet.

## Dashboard fields

- Region: Frankfurt. Database must use the same region.
- Branch: main; root directory: empty.
- Build command: `bash build.sh`
- Start command: `uv run gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2`
- Pre-deploy command (Advanced): `uv run python manage.py migrate --noinput`
- Set automatic deploys to Off during migration preparation.
- Persistent disk: mount `/var/data`. Never put uploads in the application directory.

## Environment Variables

| Name | Value |
| --- | --- |
| DJANGO_SETTINGS_MODULE | config.render_settings |
| DJANGO_SECRET_KEY | Use Render Generate; never paste it into chat or Git |
| DATABASE_URL | Internal URL of the Render PostgreSQL database; private |
| DJANGO_MEDIA_ROOT | /var/data/private_uploads |

Render supplies RENDER_EXTERNAL_HOSTNAME automatically. For a custom domain add
DJANGO_ALLOWED_HOSTS with exact hostnames, separated by commas. No wildcard.
Do not copy the local development key. The Render configuration refuses that key.

Without SMTP settings the server intentionally discards emails. Do not enable
customer email sending during testing. The local email configuration is unchanged.

## Before using real data

1. Deploy with an empty PostgreSQL database. Check login and static files over HTTPS.
2. Create a test admin through Render Shell, using `uv run python manage.py createsuperuser`.
3. Verify unauthorized visitors cannot read orders or download private attachments.
4. Verify an uploaded invented voucher survives a restart.
5. Arrange automatic backups of both PostgreSQL and the private disk, including
   an independent copy; restore one test backup before relying on it.
6. After local monthly reconciliation: stop data entry, back up local database and
   private files, transfer them using a reviewed migration procedure, compare counts
   and sample bookings, then switch work to the server. Never commit these exports.

This change prepares hosting only. It does not transfer data, set up backups,
enable account two-factor authentication, or complete the public-site security review.

References: https://render.com/docs/deploy-django and
https://whitenoise.readthedocs.io/en/stable/django.html
