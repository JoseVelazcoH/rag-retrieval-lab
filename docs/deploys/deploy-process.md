# Deploy process

## General flow

Every change reaches production through a pull request approved by
at least one person. When merged to `main`, the pipeline builds the
image, runs the tests and deploys to staging automatically.

## Promotion to production

Promotion to production is manual from the deploy tool. Choose the
version, confirm the change and watch the dashboards for 15 minutes.
Rollout is progressive: 5%, 25% and 100% of traffic.

## What to watch

The 5xx error rate, p95 latency and pod restarts. If any of them
gets worse, run the rollback without waiting.
