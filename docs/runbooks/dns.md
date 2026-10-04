# Runbook: DNS problems

## Internal resolution

Internal services use the `andescloud.internal` domain, resolved
by CoreDNS inside the cluster. If a pod cannot resolve names, first
check that the CoreDNS pods are healthy.

## Propagation

Changes to public records propagate according to the TTL. Before a
migration, lower the TTL to 300 seconds at least 24 hours before
the change.

## Tools

Use `dig +trace` to follow the resolution chain and `dig @8.8.8.8`
to compare with an external resolver.
