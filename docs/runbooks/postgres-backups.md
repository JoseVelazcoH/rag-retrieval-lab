# Runbook: PostgreSQL backups

## Policy

A full backup runs every night at 02:00, with continuous WAL archiving
every five minutes. Backups are kept for 30 days in the
`andescloud-backups` bucket with encryption at rest.

## If the backup crashes

Check the `pgbackrest` log in `/var/log/pgbackrest/`. The most common
cause is a full disk on the staging volume. If the backup crashes two
nights in a row, a severity 2 incident is opened automatically.

## Restore

A point-in-time restore is done with
`pgbackrest restore --type=time`. We practice a full restore every
quarter in the staging environment and record how long it lasts.
The last test needed 47 minutes for an 800 GB database.
