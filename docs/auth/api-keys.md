# API keys and service tokens

## What they are

An API key identifies a system, not a person. Every service token
belongs to a team and has permissions limited to a set of routes.
Service tokens are created from the admin panel.

## Usage rules

Never include a token in source code or in a chat. Store each
token in the secrets manager. If a token shows up in a repository,
consider it compromised and generate another token.

## GitHub personal tokens

GitHub personal tokens must expire within 90 days at most and carry
the minimum permissions. A token with no expiration will be revoked
for security during the monthly audit.

## Rotation

Rotate every service token every 180 days. The previous token keeps
working for 48 hours to ease the migration.
