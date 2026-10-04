# Guide: Log rotation

## Configuration

We use `logrotate` with daily rotation and 14 days of retention. Logs
are compressed with gzip from the second day.

## Containerized services

Containers write to standard output and Docker applies the limit
`max-size=50m` with `max-file=5`. Do not write logs to files inside
the container.

## Verification

Check that the file `/etc/logrotate.d/andescloud` exists on every new
server. A server without that rule fills its disk within weeks.
