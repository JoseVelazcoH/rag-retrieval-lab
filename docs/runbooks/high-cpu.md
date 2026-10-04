# Runbook: High CPU on application servers

## Alert

`CpuHigh` fires when the five-minute average exceeds 90%. It
usually comes with elevated latency.

## Diagnosis

Log in to the server and run `top -H` to see threads. If the usage
comes from a single process, capture a profile with `py-spy dump`
before restarting, so the evidence is not lost.

## Common causes

Regular expressions with catastrophic backtracking, loops in the
serialization of large reports, and scheduled tasks that overlap.
