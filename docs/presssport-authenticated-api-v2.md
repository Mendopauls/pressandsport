# Editorial API v2 — deployment contract

The implementation in `scripts/presssport_editorial_authenticated_api.py` is **read-only** and **not deployed**. It exposes only `GET /api/editorial/v2/queue`. Requests require a fresh Supabase Auth access token, verified through `/auth/v1/user`, and the verified email must be in `presssport_internal.admin_allowlist`.

## Secure server settings (never commit values)

- `PRESSSPORT_DATABASE_URL`: private Postgres connection string, stored only in server secrets
- `PRESSSPORT_SUPABASE_URL`: exact HTTPS project URL
- `PRESSSPORT_SUPABASE_PUBLISHABLE_KEY`: publishable/anon key, for Auth validation API

The client must **never** receive the database URL or role credentials. The authenticated API must run behind HTTPS, a trusted reverse proxy, server-side rate limits and appropriate operational logging (excluding bearer tokens). Before deployment, validate origin/cookie handling and session revocation policy.

The endpoint never accepts browser-provided identity, role, or target account; it reads verified email from Supabase Auth, checks the allowlist in private Postgres, and returns a filtered minimal editorial summary. 401 unauthenticated; 403 not allowlisted; 405 mutation method. No endpoint publishes.

## Deployment gates

1. Review dedicated V2 SQL migration and run isolated PostgreSQL CI.
2. Confirm service is deployed only in the correct Press & Sport project.
3. Complete integration tests with actual Supabase Auth test user, role revoked and expired token.
4. Build a frontend that obtains the authenticated user's access token without exposing service credentials.
5. Add audited mutation API with CSRF/origin defense appropriate to chosen auth mechanism and explicit editorial operator approval. Publishing approval stays separate.
6. Add a **separate** publisher with atomic reservations, reconciliation, target account pinning, Meta/LinkedIn API error handling and explicit per-manifest release authorization.
7. Never automatically requeue the 28 October published carousel.

CLI approval also remains disabled until the trusted identity route is integrated; local operator data alone is not a valid authorization assertion.
