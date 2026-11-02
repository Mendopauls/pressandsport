-- Manual draft authoring for isolated multi-project queues; never publishes.
create or replace function public.presssport_admin_project_draft_save(p_actor uuid,p_slug text,p_key text,p_text text)
returns boolean language plpgsql security definer set search_path='' as $$
begin
 if not exists(select 1 from auth.users u join presssport_internal.admin_allowlist a on lower(a.email)=lower(u.email) where u.id=p_actor and u.email_confirmed_at is not null) then raise exception 'forbidden';end if;
 if p_text is null or char_length(btrim(p_text)) not between 1 and 30000 then return false;end if;
 update presssport_internal.project_editorial_queue q
 set draft_text=btrim(p_text),state='draft_for_review',updated_at=now()
 from presssport_internal.content_projects p
 where q.project_id=p.id and p.slug=p_slug and q.external_key=p_key
 and q.state in ('pending','failed','draft_for_review');
 return found;
end $$;
revoke all on function public.presssport_admin_project_draft_save(uuid,text,text,text) from public,anon,authenticated;
grant execute on function public.presssport_admin_project_draft_save(uuid,text,text,text) to service_role;
