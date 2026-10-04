# JWT authentication

## Structure

The `auth-api` service issues JWT tokens signed with RS256. Each
token includes the user identifier, their roles and the expiration
date in the `exp` field.

## Token expiration

When a user is locked out with their token, it has almost always
expired. The access token lasts 15 minutes: when it expires, the API
responds with 401 Unauthorized and the message `token expired`, and the
user has no access until the token is renewed with the refresh token,
which lasts 7 days. A skewed device clock also causes the rejection.
To confirm it, decode the token in the internal debugger and compare
the `exp` field with the current server time.

## Renewal

The client must call `POST /auth/refresh` before the access token
expires. If the refresh token has also expired, the user has to sign in
again with username and password.

## Revocation

To invalidate a user's session, add their identifier to the
revocation list in Redis. The list is checked on every request.
