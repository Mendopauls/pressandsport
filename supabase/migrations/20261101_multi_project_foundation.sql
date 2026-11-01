-- Multi-project foundation. Additive only: Press & Sport legacy queues remain unchanged.
create table if not exists presssport_internal.content_projects(
 id uuid primary key default gen_random_uuid(),
 slug text not null unique check(slug ~ '^[a-z0-9][a-z0-9-]{1,62}$'),
 name text not null check(char_length(name) between 2 and 120),
 status text not null default 'draft' check(status in ('draft','active','archived')),
 editorial_profile jsonb not null default '{}'::jsonb check(jsonb_typeof(editorial_profile)='object'),
 drive_folder_id text,
 publication_enabled boolean not null default false check(publication_enabled=false),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create table if not exists presssport_internal.content_project_members(
 project_id uuid not null references presssport_internal.content_projects(id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,
 access_role text not null check(access_role in ('owner','editor','viewer')),
 created_at timestamptz not null default now(),
 primary key(project_id,user_id)
);
create table if not exists presssport_internal.content_project_jobs(
 job_key text primary key references presssport_internal.ollama_jobs(job_key) on delete cascade,
 project_id uuid not null references presssport_internal.content_projects(id),
 created_at timestamptz not null default now()
);
alter table presssport_internal.content_projects enable row level security;
alter table presssport_internal.content_project_members enable row level security;
alter table presssport_internal.content_project_jobs enable row level security;
revoke all on presssport_internal.content_projects,presssport_internal.content_project_members,presssport_internal.content_project_jobs from public,anon,authenticated;
insert into presssport_internal.content_projects(slug,name,status,editorial_profile)
values
('press-sport','Press & Sport','active', '{"channels":["instagram","linkedin"],"voice":"informativo e professionale"}'::jsonb),
('ninaart','Ninaart','draft', '{"channels":[],"voice":"da definire"}'::jsonb),
('ussa','USSA','draft', '{"channels":[],"voice":"da definire"}'::jsonb),
('paolo-savio','Paolo Savio','draft', '{"channels":[],"voice":"da definire"}'::jsonb)
on conflict(slug) do nothing;
insert into presssport_internal.content_project_jobs(job_key,project_id)
select j.job_key,p.id
from presssport_internal.ollama_jobs j
cross join presssport_internal.content_projects p
where p.slug='press-sport'
on conflict(job_key) do nothing;
