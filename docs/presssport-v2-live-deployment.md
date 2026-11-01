# Press & Sport Cloud V2 — Supabase deployment (31 October 2026)

The verified project is `acruqsduyucbrkxlqiqi` (Press & Sport), not any of the other Supabase projects.

## Deployed components

- `presssport_internal.multichannel_queue` — applied as `presssport_multichannel_queue_v2`, starts empty; legacy `editorial_queue` and `publication_reservations` untouched.
- `public.presssport_admin_v2_queue(uuid)` — applied as `presssport_admin_v2_queue_read_only`. EXECUTE revoked from PUBLIC, anon, authenticated; granted only to service_role. Function checks verified Auth user + `presssport_internal.admin_allowlist`.
- `presssport-v2-queue` Edge Function version 2 (active), source `supabase/functions/presssport-v2-queue/index.ts`; `verify_jwt=false` intentionally supports public read-only HTML and public config, while the `?mode=queue` data endpoint **manually verifies the bearer token with auth.getUser** and then enforces the SQL allowlist.
- Existing `presssport-admin` Edge Function is unchanged. The new page reuses its Supabase Auth browser session key `presssport-admin-session`.

## URLs

1. Existing login: `https://acruqsduyucbrkxlqiqi.supabase.co/functions/v1/presssport-admin`
2. V2 read-only queue: `https://acruqsduyucbrkxlqiqi.supabase.co/functions/v1/presssport-v2-queue`

Log in first via the existing admin page, then open V2 on the same browser and domain. A valid, confirmed, allowlisted session is required to read data.

## Verification

- Supabase reports Edge Function `ACTIVE` version 2.
- SQL verified: 1 allowlisted administrator, 0 V2 items, 1 historic published reservation; `authenticated` has no EXECUTE permission on the privileged RPC.
- Real-browser authenticated end-to-end check still required. Deployment success is not proof the browser session succeeds.
- No publisher, cron, Meta, LinkedIn or SMS/email automation has been enabled.
