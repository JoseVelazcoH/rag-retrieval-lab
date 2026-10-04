# Observability

## Metrics

Every service exposes metrics in Prometheus format. The four minimum
signals are latency, traffic, errors and saturation.

## Traces and logs

Traces are sent through OpenTelemetry and logs are JSON with the
`request_id` field. With that identifier you can follow a request
across all services.

## Alerts

An alert must be actionable. If nobody knows what to do when it
fires, it is removed or documented in a runbook.
