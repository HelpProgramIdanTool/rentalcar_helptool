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

## Isolated restoration test

Create a separate empty PostgreSQL 18 instance in Frankfurt, named
`rentalcar-restore-test` (Free compute was selected for the initial test).
Add its internal URL to the application as `RESTORE_TEST_DATABASE_URL`, keeping
the existing `DATABASE_URL` unchanged. Do not display or paste either secret.
Disable external access on the test instance as well.

Deploy the latest code, then run in the application's Shell:

`uv run python scripts/test_render_restore.py`

The command refuses the original database server (including its external alias),
requires a test database name beginning `rentalcar_restore_test`, and refuses
any target already containing user tables. It restores the last successfully
recorded backup using a single transaction and never uses `--clean` or `--create`.
Files go into a new private `restore-test-*` directory, not the application's
working upload directory. SHA-256 checks, restored table counts and voucher file
references are checked. A private report records counts without record contents.

Do not interpret a zero-file restore as proof of recovery of real vouchers:
that means the selected backup had no uploaded files. File extraction is tested
separately with invented files. Actual account login on the restored database,
working prices after migration and real attachments require later acceptance
checks. The command must not be rerun against the now-populated test database.
Clean up test data and the temporary database only with Idan's approval after
reviewing the report. The Free instance expires after 30 days; it is not a
replacement for the original database or independent backups.

## Backup failure email

The operator approved `idan.caliber@gmail.com` as recipient. Configure the separate
Render secret file `backup-alerts.json` with `sender`, `recipient`, and `password`
(Gmail app password). Keep this file out of Git and chat. It does not enable the
customer mail backend or change customer email settings.

After deployment run `uv run python scripts/backup_alerts.py` in Render Shell and
confirm the test message arrives. Real backup failures send one message and
repeat no more often than every six hours. Successful retries send one recovery
message if an outage notification was delivered. Mail delivery failures are
logged without secrets and do not turn a failed backup into a successful one.

These alerts depend on the backup process and Gmail being reachable. They cannot
detect a complete service stop, a killed scheduler, or all network outages.
An independent external monitor for missing backup heartbeats remains to be
configured; do not claim complete missed-run monitoring from email alerts alone.

## Independent missing-backup monitor

Idan selected Healthchecks.io Hobbyist ($0) on 30 October 2026. Account setup and
live notification delivery still require verification. Create a Cron check with
schedule `0 3 * * *`, timezone `Europe/Warsaw`, and a one-hour grace period.
Enable its email integration for the operator. Store its UUID-based
`https://hc-ping.com/...` endpoint as `BACKUP_HEARTBEAT_URL` on Render; it is a
secret and must not be pasted into chat or committed.

Code sends an empty HTTPS POST only after export, encrypted upload and remote
read-back verification succeed. No start/failure pings or diagnostic data are
sent. A network failure retries three times, logs a generic warning and leaves
the valid backup marked successful. Healthchecks will then warn about missing
confirmation. This also catches a stopped scheduler or Render service at the
next expected backup deadline, not immediately when the website goes down.

After configuring the endpoint, run a real manual backup and confirm the check
shows a received success ping. Test Healthchecks email delivery and, in a
separate temporary check, its missing-ping alert. Do not declare setup complete
until those independent notifications are received. Normal schedule expects a
success at 03:00 and alerts after the grace period (approximately 04:00 Poland).

References: https://healthchecks.io/pricing/ and
https://healthchecks.io/docs/http_api/

## Retention policy approved 30 October 2026

Keep every completed run from the latest 30 Polish calendar dates, the latest
verified run from each of the current and previous 11 calendar months, and the
latest successful verified backup regardless of age. Missing months cannot be
created retroactively. Copies without a `verified.json` completion marker,
unknown directory names and unrelated files are not eligible for deletion.

New backups upload a completion marker only after their full remote read-back
passes, then verify that marker as well. Existing earlier copies do not have
markers and are deliberately retained until separately reviewed.

First deploy and run a new manual backup. Run the read-only preview:

`uv run python scripts/backup_retention.py`

It writes a private retention report and prints counts without deleting files.
Only after reviewing it, enable `BACKUP_RETENTION_ENABLED=1` on Render and deploy.
Cleanup then runs after each successful backup. It refuses cleanup if the last
success is older than 24 hours, missing, unverified or failed. It deletes only
the four known files in an expired managed backup folder, then removes the
empty folder, never a recursive directory purge. A changed directory stops
cleanup. Provider trash rules still apply; no permanent trash purge is used.

Retention failure is logged separately and does not invalidate the new verified
backup. Review `retention-report.json` and any private `retention-error.log` under
`/var/data/backup-private`. Automatic cleanup remains disabled until the explicit
environment flag is set. Update public backup disclosures once enabled.

## PDF file recovery verification

After deployment run `uv run python scripts/test_upload_restore.py` in Render
Shell. It creates a uniquely named valid PDF containing only invented test text
under the private uploads directory, makes a new encrypted backup and downloads
it into a separate private test directory. It checks the manifest, safely
extracts the uploads archive, compares the PDF's exact SHA-256 checksum and opens
the restored PDF to verify its test text. No database records are created or
changed. After success it removes only the unique source probe from this run.
On failure it leaves the probe for diagnosis and removes no existing vouchers.

This verifies the real storage/backup/decryption/extraction path for a PDF. It
does not itself test attaching a voucher to a booking through the web interface
or opening a restored file through an authenticated application session.

References: https://render.com/docs/deploy-django and
https://whitenoise.readthedocs.io/en/stable/django.html
