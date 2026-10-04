# Signing key rotation

## Schedule

JWT signing keys are rotated every 90 days. The previous key
stays published on the JWKS endpoint for 24 more hours so that
tokens already issued keep validating.

## Procedure

Generate the new key pair in the HSM, publish it on JWKS and switch
the active key of `auth-api`. Verify with `jwt verify` that a new
token validates with the new key.

## Emergency

If a private key leaks, rotate immediately and revoke all active
sessions. Open a security incident.
