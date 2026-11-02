-- Separate project editorial queues. Never posts to social channels.
create table if not exists presssport_internal.project_editorial_queue(
 id uuid primary key default gen_random_uuid(),
 project_id uuid not null references presssport_internal.content_projects(id),
 external_key text not null check(external_key ~ '^[A-Za-z0-9_-]{3,100}$'),
 brief text not null check(char_length(brief) between 1 and 12000),
 state text not null default 'pending' check(state in ('pending','draft_for_review','cancelled')),
 draft_text text,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique(project_id,external_key)
);
create index if not exists project_editorial_queue_project_created on presssport_internal.project_editorial_queue(project_id,created_at desc);
alter table presssport_internal.project_editorial_queue enable row level security;
revoke all on presssport_internal.project_editorial_queue from public,anon,authenticated;
create or replace function public.presssport_admin_project_queue(p_actor uuid,p_slug text)
returns jsonb language plpgsql security definer set search_path=''
as $$
begin
 if not exists(select 1 from auth.users u join presssport_internal.admin_allowlist a on lower(a.email)=lower(u.email) where u.id=p_actor and u.email_confirmed_at is not null) then raise exception 'forbidden' using errcode='42501';end if;
 if not exists(select 1 from presssport_internal.content_projects where slug=p_slug) then raise exception 'unknown project';end if;
 return coalesce((select jsonb_agg(jsonb_build_object('external_key',q.external_key,'state',q.state,'brief',q.brief,'created_at',q.created_at) order by q.created_at desc) from (select q.* from presssport_internal.project_editorial_queue q join presssport_internal.content_projects p on p.id=q.project_id where p.slug=p_slug order by q.created_at desc limit 50) q),'[]'::jsonb);
end $$;
create or replace function public.presssport_admin_project_enqueue(p_actor uuid,p_slug text,p_key text,p_brief text)
returns boolean language plpgsql security definer set search_path=''
as $$
declare project_uuid uuid;
begin
 if not exists(select 1 from auth.users u join presssport_internal.admin_allowlist a on lower(a.email)=lower(u.email) where u.id=p_actor and u.email_confirmed_at is not null) then raise exception 'forbidden' using errcode='42501';end if;
 select id into project_uuid from presssport_internal.content_projects where slug=p_slug;
 if project_uuid is null or p_slug='press-sport' then return false;end if;
 if p_key is null or p_key !~ '^[A-Za-z0-9_-]{3,100}$' or p_brief is null or char_length(btrim(p_brief)) not between 1 and 12000 then return false;end if;
 insert into presssport_internal.project_editorial_queue(project_id,external_key,brief) values(project_uuid,p_key,btrim(p_brief)) on conflict(project_id,external_key) do nothing;
 return found;
end $$;
revoke all on function public.presssport_admin_project_queue(uuid,text),public.presssport_admin_project_enqueue(uuid,text,text,text) from public,anon,authenticated;
grant execute on function public.presssport_admin_project_queue(uuid,text),public.presssport_admin_project_enqueue(uuid,text,text,text) to service_role;
