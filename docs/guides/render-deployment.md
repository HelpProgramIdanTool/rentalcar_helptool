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

## Independent backup setup (added 29 October 2026)

Google Drive OAuth and an encrypted test-file round trip have been verified.
The Render rclone binary is installed under `/var/data/backup-tools/rclone`.
The operator supplied its configuration as the secret file
`/etc/secrets/rclone.conf`. Never print that file or commit it.

First run manually in Render Shell:

`uv run python scripts/render_backup.py`

It exports PostgreSQL, checks the dump's table of contents, archives private
uploads, uploads dated encrypted files, and reads them back for comparison.
It never deletes remote copies. The working temporary archives are removed
after the run; credentials and private diagnostic logs stay on the private disk.
A manifest provides SHA-256 checksums and sizes. `pg_restore --list` and remote
read-back do not constitute a full database restore test.

After a successful manual run, enable `BACKUP_ENABLED=1` and change the web
service's Start Command to `uv run python scripts/run_render.py`.
This starts the web app and the backup scheduler in the same disk-owning service.
The approved schedule is daily at 03:00 Europe/Warsaw (including DST), with
catch-up if the service was offline then. A failed attempt retries after an hour.
Status is `/var/data/backup-private/status.json`; errors are recorded in the
private `last-run.log`. Logs show failure events, but independent failure
notifications are not configured yet. Monitor status until those are configured.

The existing web Start Command leaves scheduling disabled. Deployment of this
code alone does not enable it. Do not switch until the manual run succeeds.
Keep the encryption recovery key separately from Render and Google Drive.
Before transferring real data, test restoration in an isolated destination and
agree retention/deletion and failure notifications. Pause writes for the final
consistent migration; routine snapshots are not a substitute for that pause.

References: https://render.com/docs/deploy-django and
https://whitenoise.readthedocs.io/en/stable/django.html
