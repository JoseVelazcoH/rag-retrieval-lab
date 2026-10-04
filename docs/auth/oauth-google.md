# Sign in with Google

## Scope

Employees access internal tools with their corporate Google
Workspace account through OAuth 2.0.

## Configuration

The OAuth client is registered in the Google Cloud console of the
`andescloud-sso` project. The allowed redirect URIs are managed
with Terraform. Adding a new URI requires a pull request.

## Known problems

The `redirect_uri_mismatch` error means the application URI does
not match any registered one. Check capitalization and the trailing slash.
