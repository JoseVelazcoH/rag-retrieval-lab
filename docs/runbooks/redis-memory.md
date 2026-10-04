# Runbook: Redis out of memory

## Symptom

Write commands return `OOM command not allowed when used
memory > maxmemory`. The sessions service starts closing active
user sessions.

## What to check

Run `INFO memory` and compare `used_memory` with `maxmemory`. Look for
keys without expiration with `redis-cli --bigkeys`. The configured
eviction policy is `allkeys-lru` for the cache and `noeviction` on
the queue Redis.

## Action

Never run `FLUSHALL` in production. If you need to free space
quickly, delete the `cache:report:*` prefix, which regenerates itself.
