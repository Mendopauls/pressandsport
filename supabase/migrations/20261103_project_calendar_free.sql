-- Editorial calendar only: channel and planned date have no social publishing side effects.
alter table presssport_internal.project_editorial_queue
 add column if not exists channel text not null default 'unspecified'
 check(channel in ('unspecified','instagram','facebook','linkedin','website','other'));
alter table presssport_internal.project_editorial_queue
 add column if not exists planned_date date;
create or replace function public.presssport_admin_project_schedule(p_actor uuid,p_slug text,p_key text,p_channel text,p_day date)
returns boolean language plpgsql security definer set search_path=''
as $$
begin
 if not exists(select 1 from auth.users u join presssport_internal.admin_allowlist a on lower(a.email)=lower(u.email) where u.id=p_actor and u.email_confirmed_at is not null) then raise exception 'forbidden' using errcode='42501';end if;
 if p_channel is null or p_channel not in ('unspecified','instagram','facebook','linkedin','website','other') then return false;end if;
 update presssport_internal.project_editorial_queue q
 set channel=p_channel,planned_date=p_day,updated_at=now()
 from presssport_internal.content_projects p
 where q.project_id=p.id and p.slug=p_slug and q.external_key=p_key
 and q.state in ('pending','failed','draft_for_review');
 return found;
end $$;
revoke all on function public.presssport_admin_project_schedule(uuid,text,text,text,date) from public,anon,authenticated;
grant execute on function public.presssport_admin_project_schedule(uuid,text,text,text,date) to service_role;
create or replace function public.presssport_admin_project_queue(p_actor uuid,p_slug text)
returns jsonb language plpgsql security definer set search_path=''
as $$
begin
 if not exists(select 1 from auth.users u join presssport_internal.admin_allowlist a on lower(a.email)=lower(u.email) where u.id=p_actor and u.email_confirmed_at is not null) then raise exception 'forbidden' using errcode='42501';end if;
 if not exists(select 1 from presssport_internal.content_projects where slug=p_slug) then raise exception 'unknown project';end if;
 return coalesce((select jsonb_agg(jsonb_build_object('external_key',q.external_key,'state',q.state,'brief',q.brief,'channel',q.channel,'planned_date',q.planned_date,'draft_text',case when q.state='draft_for_review' then q.draft_text else null end,'created_at',q.created_at) order by q.created_at desc) from (select q.* from presssport_internal.project_editorial_queue q join presssport_internal.content_projects p on p.id=q.project_id where p.slug=p_slug order by q.created_at desc limit 50) q),'[]'::jsonb);
end $$;
revoke all on function public.presssport_admin_project_queue(uuid,text) from public,anon,authenticated;
grant execute on function public.presssport_admin_project_queue(uuid,text) to service_role;
