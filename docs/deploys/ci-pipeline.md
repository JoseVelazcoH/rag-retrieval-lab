# Continuous integration pipeline

## Stages

Lint, unit tests, integration tests, image build, vulnerability
scan and publish. The full pipeline should finish in under 12 minutes.

## Flaky tests

If a test fails intermittently, open a ticket with the `flaky` label
and do not silently retry it. When a test crashes at random, trust in
the pipeline erodes.

## Cache

Dependencies are cached by lock file hash. Changing the lock
file invalidates the cache and the first run is slower.
