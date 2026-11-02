-- Secure project AI draft processing, no publication capabilities.
alter table presssport_internal.project_editorial_queue drop constraint if exists project_editorial_queue_state_check;
alter table presssport_internal.project_editorial_queue add constraint project_editorial_queue_state_check check(state in ('pending','processing','draft_for_review','failed','cancelled'));
CREATE OR REPLACE FUNCTION public.presssport_admin_project_ai_claim(p_actor uuid, p_slug text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare r jsonb;
begin
 if not exists(select 1 from auth.users u join presssport_internal.admin_allowlist a on lower(a.email)=lower(u.email) where u.id=p_actor and u.email_confirmed_at is not null) then raise exception 'forbidden';end if;
 with chosen as (select q.id from presssport_internal.project_editorial_queue q join presssport_internal.content_projects p on p.id=q.project_id where p.slug=p_slug and q.state='pending' order by q.created_at limit 1 for update of q skip locked),
 changed as (update presssport_internal.project_editorial_queue q set state='processing',updated_at=now() from chosen c where q.id=c.id returning q.id,q.brief,q.external_key,q.project_id)
 select jsonb_build_object('id',c.id,'brief',c.brief,'key',c.external_key,'project_name',p.name,'editorial_profile',p.editorial_profile) into r from changed c join presssport_internal.content_projects p on p.id=c.project_id;
 return r;
end $function$

CREATE OR REPLACE FUNCTION public.presssport_admin_project_ai_finish(p_actor uuid, p_id uuid, p_text text, p_success boolean)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
begin
 if not exists(select 1 from auth.users u join presssport_internal.admin_allowlist a on lower(a.email)=lower(u.email) where u.id=p_actor and u.email_confirmed_at is not null) then raise exception 'forbidden';end if;
 if p_text is null or char_length(p_text)>30000 then return false;end if;
 update presssport_internal.project_editorial_queue set state=case when p_success then 'draft_for_review' else 'failed' end,draft_text=case when p_success then p_text else null end,updated_at=now() where id=p_id and state='processing';
 return found;
end $function$

revoke all on function public.presssport_admin_project_ai_claim(uuid,text),public.presssport_admin_project_ai_finish(uuid,uuid,text,boolean) from public,anon,authenticated;
grant execute on function public.presssport_admin_project_ai_claim(uuid,text),public.presssport_admin_project_ai_finish(uuid,uuid,text,boolean) to service_role;
