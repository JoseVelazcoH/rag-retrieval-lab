# Runbook: Payment gateway errors

The checkout service talks to the external payment gateway through
`payments-api`. This guide covers the failures the billing platform
team sees most often.

## ERR_4021: payment token rejected

Checkout fails and `payments-api` logs `ERR_4021` when the gateway
refuses the one-time payment token sent with a charge. The usual
causes are a token older than 10 minutes, a token already used in a
previous attempt, or a mismatch between the merchant key of the
environment and the one that created the token.

## Action

Ask the customer to retry so the browser requests a fresh token. If
the error keeps coming back for many customers, compare the
`GATEWAY_MERCHANT_KEY` value in the secrets manager with the one
registered in the gateway dashboard and open an incident with the
billing platform team.

## Timeouts

If the gateway does not answer within 20 seconds, `payments-api`
cancels the charge and shows a generic error to the customer. Never
retry a charge automatically: check the gateway dashboard first to
avoid billing the customer twice.
