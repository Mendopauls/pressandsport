-- Verified existing Google Drive project roots. No folder creation or sharing changes.
update presssport_internal.content_projects
set drive_folder_id=case slug
 when 'press-sport' then '1qDyBLKBunlQDL7iJGb6u33UfKkafFhdB'
 when 'ussa' then '1l4h8KT1iCvUemV6Zop9mWFqaEUM2vgwq'
 else drive_folder_id end,updated_at=now()
where (slug='press-sport' and drive_folder_id is null)
   or (slug='ussa' and drive_folder_id is null);
create or replace function public.presssport_admin_content_projects(p_actor uuid)
returns jsonb language plpgsql security definer set search_path=''
as $$
begin
 if not exists(select 1 from auth.users u join presssport_internal.admin_allowlist a on lower(a.email)=lower(u.email) where u.id=p_actor and u.email_confirmed_at is not null) then raise exception 'forbidden' using errcode='42501';end if;
 return coalesce((select jsonb_agg(jsonb_build_object('slug',p.slug,'name',p.name,'status',p.status,'publication_enabled',p.publication_enabled,'drive_folder_id',p.drive_folder_id,'assigned_jobs',(select count(*) from presssport_internal.content_project_jobs j where j.project_id=p.id)) order by p.name) from presssport_internal.content_projects p),'[]'::jsonb);
end $$;
revoke all on function public.presssport_admin_content_projects(uuid) from public,anon,authenticated;
grant execute on function public.presssport_admin_content_projects(uuid) to service_role;
