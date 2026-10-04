# Runbook: PostgreSQL, connections exhausted

## Symptom

The PostgreSQL connection pool is saturated: the logs show
`FATAL: sorry, too many clients already` or
`remaining connection slots are reserved`.

## Diagnosis

Query `pg_stat_activity` grouping by state and by application.
If you see dozens of connections in `idle in transaction`, some code
opens a transaction and never closes it. That is the usual culprit.

## Mitigation

Terminate idle connections with `pg_terminate_backend`. Then check
the pool size in PgBouncer: the default limit is 200 connections
per database. Do not raise `max_connections` without asking the data
team first, because every connection consumes memory.
