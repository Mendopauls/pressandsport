-- Idempotent Drive asset assignment: preserve verification on same file.
-- Changing the Drive file ID resets verification to pending.
create or replace function public.presssport_editorial_asset_assign(p_actor uuid,p_key text,p_file_id text,p_name text)
returns boolean language plpgsql security definer set search_path=''
as $$
begin
 if not exists(select 1 from auth.users u join presssport_internal.admin_allowlist a on lower(a.email)=lower(u.email) where u.id=p_actor and u.email_confirmed_at is not null) then raise exception 'forbidden';end if;
 if p_file_id is null or p_file_id !~ '^[A-Za-z0-9_-]{15,100}$' or p_name is null or char_length(btrim(p_name)) not between 1 and 220 then return false;end if;
 insert into presssport_internal.editorial_assets(job_key,drive_file_id,drive_filename,verification_state,verified_at)
 values(p_key,p_file_id,btrim(p_name),'pending',null)
 on conflict(job_key) do update set
 drive_file_id=excluded.drive_file_id,
 drive_filename=excluded.drive_filename,
 verification_state=case when presssport_internal.editorial_assets.drive_file_id=excluded.drive_file_id then presssport_internal.editorial_assets.verification_state else 'pending' end,
 verified_at=case when presssport_internal.editorial_assets.drive_file_id=excluded.drive_file_id then presssport_internal.editorial_assets.verified_at else null end;
 return true;
end $$;
revoke all on function public.presssport_editorial_asset_assign(uuid,text,text,text) from public,anon,authenticated;
grant execute on function public.presssport_editorial_asset_assign(uuid,text,text,text) to service_role;
