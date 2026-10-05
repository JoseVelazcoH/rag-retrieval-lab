# Runbook: Refund errors

Refunds go through `payments-api` to the same external gateway used at
checkout. These are the refund codes the billing platform team sees
most often.

## ERR_4012: refund window expired

The gateway rejects refunds requested more than 180 days after the
original charge. `payments-api` logs `ERR_4012` and the support agent
sees "refund not allowed". Issue store credit instead and tag the
ticket `refund-expired`.

## ERR_4201: partial refund exceeds balance

The requested amount is larger than what is left to refund on the
charge, usually because a previous partial refund already went
through. Check the refund history of the charge in the gateway
dashboard before trying again with the remaining amount.
