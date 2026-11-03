-- Existing project queue: only metadata references to private Drive files.
ALTER TABLE presssport_internal.project_editorial_queue ADD COLUMN IF NOT EXISTS source_drive_file_id text;
ALTER TABLE presssport_internal.project_editorial_queue ADD COLUMN IF NOT EXISTS source_drive_filename text;
ALTER TABLE presssport_internal.project_editorial_queue DROP CONSTRAINT IF EXISTS project_queue_source_pair_ck;
ALTER TABLE presssport_internal.project_editorial_queue ADD CONSTRAINT project_queue_source_pair_ck CHECK (
  (source_drive_file_id IS NULL AND source_drive_filename IS NULL) OR
  (source_drive_file_id ~ '^[A-Za-z0-9_-]{15,100}$' AND char_length(btrim(coalesce(source_drive_filename,''))) BETWEEN 1 AND 220)
);
CREATE OR REPLACE FUNCTION public.presssport_admin_project_source_attach(p_actor uuid, p_slug text, p_key text, p_file_id text, p_filename text)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
BEGIN
 IF NOT EXISTS (
   SELECT 1 FROM auth.users u
   JOIN presssport_internal.admin_allowlist a ON lower(a.email)=lower(u.email)
   WHERE u.id=p_actor AND u.email_confirmed_at IS NOT NULL
 ) THEN RAISE EXCEPTION 'forbidden' USING errcode='42501'; END IF;
 IF p_slug='press-sport'
    OR p_file_id IS NULL OR p_file_id !~ '^[A-Za-z0-9_-]{15,100}$'
    OR char_length(btrim(coalesce(p_filename,''))) NOT BETWEEN 1 AND 220
 THEN RETURN false; END IF;
 UPDATE presssport_internal.project_editorial_queue q
 SET source_drive_file_id=p_file_id,
     source_drive_filename=btrim(p_filename),
     updated_at=now()
 FROM presssport_internal.content_projects p
 WHERE q.project_id=p.id AND p.slug=p_slug
   AND q.external_key=p_key
   AND q.state IN ('pending','failed','draft_for_review');
 RETURN found;
END $function$
;
REVOKE ALL ON FUNCTION public.presssport_admin_project_source_attach(uuid,text,text,text,text) FROM public,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.presssport_admin_project_source_attach(uuid,text,text,text,text) TO service_role;
CREATE OR REPLACE FUNCTION public.presssport_admin_project_queue(p_actor uuid, p_slug text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
BEGIN
 IF NOT EXISTS (
   SELECT 1 FROM auth.users u
   JOIN presssport_internal.admin_allowlist a ON lower(a.email)=lower(u.email)
   WHERE u.id=p_actor AND u.email_confirmed_at IS NOT NULL
 ) THEN RAISE EXCEPTION 'forbidden' USING errcode='42501'; END IF;
 IF NOT EXISTS (SELECT 1 FROM presssport_internal.content_projects WHERE slug=p_slug)
 THEN RAISE EXCEPTION 'unknown project'; END IF;
 RETURN coalesce((
  SELECT jsonb_agg(jsonb_build_object(
   'external_key',q.external_key,'state',q.state,'brief',q.brief,
   'channel',q.channel,'planned_date',q.planned_date,
   'source_drive_file_id',q.source_drive_file_id,'source_drive_filename',q.source_drive_filename,
   'draft_text',CASE WHEN q.state='draft_for_review' THEN q.draft_text ELSE NULL END,
   'created_at',q.created_at
  ) ORDER BY q.created_at DESC)
  FROM (
    SELECT q.* FROM presssport_internal.project_editorial_queue q
    JOIN presssport_internal.content_projects p ON p.id=q.project_id
    WHERE p.slug=p_slug ORDER BY q.created_at DESC LIMIT 50
  ) q
 ),'[]'::jsonb);
END $function$
;
REVOKE ALL ON FUNCTION public.presssport_admin_project_queue(uuid,text) FROM public,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.presssport_admin_project_queue(uuid,text) TO service_role;
