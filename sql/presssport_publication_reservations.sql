-- Press & Sport publication reservation design (NOT deployed).
-- Apply only to a dedicated Press & Sport database after project selection.
-- No client roles receive access. Backend service role only.
create schema if not exists presssport_internal;
create table if not exists presssport_internal.publication_reservations (
  publication_key text primary key,
  instagram_account_id text not null,
  manifest_sha256 text not null check (manifest_sha256 ~ '^[0-9a-f]{64}$'),
  attempt_id uuid not null unique,
  state text not null default 'reserved'
    check (state in ('reserved','publishing','published','uncertain','failed','cancelled')),
  meta_media_id text,
  reconciliation_required boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (state <> 'published' or meta_media_id is not null),
  check (state <> 'uncertain' or reconciliation_required = true)
);
alter table presssport_internal.publication_reservations enable row level security;
revoke all on schema presssport_internal from public, anon, authenticated;
revoke all on all tables in schema presssport_internal from public, anon, authenticated;
-- No UPSERT or TTL-based lock expiry: ambiguous outcomes must not release the key.
-- An INSERT with the same primary key fails atomically, including across workers.
-- Reconciliation and state updates require separate, audited server-side operations.
