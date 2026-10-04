# Runbook: Disk full

## Alert

The `DiskUsageHigh` alert fires at 85% usage. At 95% some services
stop writing and cascading errors begin.

## Steps

Find what uses the space with `du -xh --max-depth=1 /var | sort -h`.
The usual suspects are unrotated logs, old Docker images and
memory dumps. Clean images with `docker system prune`.

## Prevention

Log rotation must be active on every service. See the log rotation
guide.
