# Press & Sport Cloud — private admin portal

The first administrator is **info@paolosavio.eu** (and no other address).
This is an allowlist identity, **not** an already-created Auth account.

## Architecture
- Supabase Edge Function: `presssport-admin`. The public GET route serves a
  login page. The protected POST route verifies an **actual confirmed** Supabase
  Auth bearer token with `auth.getUser(token)` and checks the exact email.
- A narrow PostgreSQL RPC `public.presssport_admin_queue` is callable **only
  by service_role**, re-verifies the same user's ID against `auth.users` and
  the internal email allowlist, and modifies only the editorial queue.
- `SUPABASE_SERVICE_ROLE_KEY` stays in the Edge Function environment. No
  service-role key, database password, or Meta token is sent to the browser.
- The editorial queue and allowlist stay in `presssport_internal`, with RLS
  on and no direct browser privileges.

## First login
1. Deploy the Edge Function with `verify_jwt=false` because only the GET
   landing page is public; POST verifies JWT explicitly server-side.
2. Open the function URL at
   `https://acruqsduyucbrkxlqiqi.supabase.co/functions/v1/presssport-admin`.
3. In Supabase Dashboard → Authentication → URL Configuration, add that exact
   URL as an **Additional Redirect URL**. Keep existing redirect URLs.
4. Click `Invia link di accesso` in the portal.
5. Follow the magic link received at `info@paolosavio.eu`. The first
   successful email-based login can create the Supabase Auth user. A verified
   email is mandatory; all other addresses are denied by both the Edge
   Function and SQL.
6. Auth email delivery must be configured and working; Supabase email limits
   or redirect misconfiguration can block login. If login fails, inspect Auth
   settings and email provider configuration rather than bypassing checks.

## Editorial actions
- Create draft: code, caption, 2–10 public JPEG URLs on `pressandsport.it`.
- Submit draft for review, approve as Paolo Savio, or cancel.
- Optionally plan a **future editorial date**. This is not a scheduler.
- Publication is absent from the portal by design. Any Instagram publication
  still requires fresh and separate authorization and the existing one-shot
  reservation + Meta API boundary. The carousel already published on
  30 October 2026 must never be resubmitted.

## Deployment checks
- Offline GitHub CI tests the browser script's JavaScript syntax, the Edge
  TypeScript module, SQL privileges, no Meta calls, and the authorization gate.
- Verify unauthorized API calls return 401/403, GET config returns only
  public information, and the admin can list an empty editorial queue.
- The admin user must receive the login email and complete verification before
  editing content. Do not claim the login works without this end-to-end check.
