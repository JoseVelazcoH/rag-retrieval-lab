# Rollback

## When to do it

Roll back if the error rate rises by more than 2 points or if a
critical flow such as payments stops working. Do not try to fix
forward under pressure: stabilize first.

## How

From the deploy tool choose the previous version and press
"Revert". The process lasts about 3 minutes. Database migrations
are not reverted automatically: they must be backward compatible.

## Afterwards

Open a postmortem and mark the original pull request as reverted so
nobody deploys it again without fixing it.
