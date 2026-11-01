-- Press & Sport editorial revisions: enforce caption limits on the trusted database boundary.
-- Reapply with Supabase SQL editor or migrations; does not enable publication.
create or replace function public.presssport_editorial_save_revision(p_actor uuid,p_key text,p_content jsonb)
returns integer language plpgsql security definer set search_path=''
as $fn$
declare n integer; ig text; li text;
begin
 if not exists (select 1 from auth.users u join presssport_internal.admin_allowlist a
   on lower(a.email)=lower(u.email)
   where u.id=p_actor and u.email_confirmed_at is not null)
 then raise exception 'forbidden' using errcode='42501'; end if;
 if jsonb_typeof(p_content)<>'object' or length(p_content::text)>30000
 then raise exception 'invalid content'; end if;
 if jsonb_typeof(p_content->'instagram_caption')<>'string'
    or jsonb_typeof(p_content->'linkedin_caption')<>'string'
 then raise exception 'invalid captions'; end if;
 ig:=p_content->>'instagram_caption';
 li:=p_content->>'linkedin_caption';
 if char_length(ig) not between 450 and 750 or char_length(li) not between 650 and 1000
 then raise exception 'caption lengths invalid'; end if;
 if not exists (select 1 from presssport_internal.ollama_jobs
    where job_key=p_key and state='draft_for_review')
 then raise exception 'draft unavailable'; end if;
 perform pg_advisory_xact_lock(hashtext(p_key));
 select coalesce(max(revision),0)+1 into n
 from presssport_internal.editorial_revisions where job_key=p_key;
 insert into presssport_internal.editorial_revisions(job_key,revision,content,origin)
 values (p_key,n,p_content,'editorial_revision');
 return n;
end $fn$;
revoke all on function public.presssport_editorial_save_revision(uuid,text,jsonb)
from public,anon,authenticated;
grant execute on function public.presssport_editorial_save_revision(uuid,text,jsonb) to service_role;
