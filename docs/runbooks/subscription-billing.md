# Runbook: Subscription billing errors

Recurring charges are created by the `billing-scheduler` job every
night at 02:00 UTC.

## ERR_4210: card on file declined

The customer's saved card was declined during the nightly renewal.
The scheduler retries on days 1, 3 and 7, then pauses the
subscription and emails the customer a link to update the card. Do
not retry by hand: it counts against the gateway decline limit.

## ERR_4102: plan price not found

The subscription points to a plan price that was archived in the
gateway. Renewals fail for every customer on that plan until product
operations restores the price or migrates them to an active one.
