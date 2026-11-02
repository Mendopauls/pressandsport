-- Read tenant-scoped generated drafts only after they reach editorial review.
create or replace function public.presssport_admin_project_queue(p_actor uuid,p_slug text)
returns jsonb language plpgsql security definer set search_path=''
as $$
begin
 if not exists(select 1 from auth.users u join presssport_internal.admin_allowlist a on lower(a.email)=lower(u.email) where u.id=p_actor and u.email_confirmed_at is not null) then raise exception 'forbidden' using errcode='42501';end if;
 if not exists(select 1 from presssport_internal.content_projects where slug=p_slug) then raise exception 'unknown project';end if;
 return coalesce((select jsonb_agg(jsonb_build_object('external_key',q.external_key,'state',q.state,'brief',q.brief,'draft_text',case when q.state='draft_for_review' then q.draft_text else null end,'created_at',q.created_at) order by q.created_at desc) from (select q.* from presssport_internal.project_editorial_queue q join presssport_internal.content_projects p on p.id=q.project_id where p.slug=p_slug order by q.created_at desc limit 50) q),'[]'::jsonb);
end $$;
revoke all on function public.presssport_admin_project_queue(uuid,text) from public,anon,authenticated;
grant execute on function public.presssport_admin_project_queue(uuid,text) to service_role;
