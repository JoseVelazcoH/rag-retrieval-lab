# Runbook: TLS certificates

## Automatic renewal

We use Let's Encrypt with `certbot`. The systemd timer tries to
renew twice a day and only acts when fewer than 30 days remain.

## Manual emergency renewal

If a certificate expires and automatic renewal failed, run
`certbot renew --force-renewal` and reload the proxy. Verify the
result with `openssl s_client -connect domain:443`.

## Alerts

A warning is sent 14 days before expiry to the `#infra-alerts` channel.
A browser that shows an insecure connection warning almost always
means an expired certificate or an incomplete chain.
