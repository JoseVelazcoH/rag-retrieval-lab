# Runbook: RabbitMQ queues piling up

## Symptom

The `invoices.pending` queue exceeds 10,000 messages and invoice
emails reach customers hours late.

## Diagnosis

Check the management console: how many consumers there are and whether
they are connected. A consumer that fails to process a message
returns it to the queue and can create an infinite loop.

## Action

Move the problematic messages to the dead letter queue
`invoices.dlq` and scale the consumers. Never purge a production
queue without approval from the billing owner.
