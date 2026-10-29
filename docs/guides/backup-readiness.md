# Backup readiness — 29 October 2026

The server is a test copy. Continue entering real orders locally until cutover.

## Verified during setup

- Login works; an incognito visitor is redirected to login.
- The application still reads PostgreSQL after its external IP allow list was cleared.
- A harmless file under `/var/data` survived a service restart.
- Render produced a database export. Downloading and restoring that archive have
  not been independently verified by the agent.
- The dashboard offers three days of database point-in-time recovery.
- Disk snapshots are scheduled every 24 hours with seven-day retention; no first
  snapshot was present at the time of inspection.

## Independent backup requirements

Destination and account access still need to be selected. Nothing is scheduled yet.

- Back up PostgreSQL and private uploads, not just source code.
- Run the uploads backup from the disk-owning service: another Render service
  cannot read its persistent disk.
- Keep database credentials out of commands, logs and archives. Do not include
  `.env` files in upload archives. Store keys in Render environment variables.
- Use a private destination and an upload account limited to the backup area.
- Keep dated copies; one failed run must not overwrite the last good backup.
- Record completion, archive sizes and checksums without customer data in logs.
- Coordinate database and file copies. Before the final transfer, pause writes
  so database references and uploaded documents remain consistent.
- Restore into a separate database and directory. Never overwrite the working
  database as a test. Confirm a test record and attachment can be read.
- Configure failure notifications and check a missed run is detectable.
- Agree schedule and retention with Idan, and confirm the storage cost before
  provisioning any paid resource.

## Still unverified

- Independent backup upload and automatic schedule.
- Recovery from a database export.
- Recovery of private files from an independent copy or disk snapshot.
- Independent copies of the local authoritative database and private uploads.

References:
- https://render.com/docs/postgresql-backups
- https://render.com/docs/disks
- https://render.com/docs/backup-postgresql-to-s3
