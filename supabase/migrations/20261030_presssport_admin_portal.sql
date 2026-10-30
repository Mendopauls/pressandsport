-- Press & Sport Cloud: server-enforced editor identity and narrow queue API.
-- Does not alter any published post, Meta authorization, or reservation ledger.
CREATE TABLE IF NOT EXISTS presssport_internal.admin_allowlist (
  email text PRIMARY KEY CHECK (email = lower(email) AND email LIKE '%@%'),
  created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE presssport_internal.admin_allowlist ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON presssport_internal.admin_allowlist FROM PUBLIC, anon, authenticated;
INSERT INTO presssport_internal.admin_allowlist(email)
VALUES ('info@paolosavio.eu') ON CONFLICT (email) DO NOTHING;

-- Only the Supabase Edge Function's server-side service-role client may
-- invoke this RPC. It rechecks the confirmed Auth user against the allowlist.
CREATE OR REPLACE FUNCTION public.presssport_admin_queue(
  p_actor uuid,
  p_action text,
  p_post_key text DEFAULT NULL,
  p_payload jsonb DEFAULT '{}'::jsonb
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog
AS $function$
DECLARE
  v_email text;
  v_confirmed timestamptz;
  v_urls jsonb;
  v_caption text;
  v_digest text;
  v_state text;
  v_planned timestamptz;
  v_items jsonb;
  v_result jsonb;
  v_key text;
BEGIN
  SELECT lower(u.email), u.email_confirmed_at
    INTO v_email, v_confirmed
    FROM auth.users AS u WHERE u.id=p_actor;
  IF v_email IS NULL OR v_confirmed IS NULL
     OR NOT EXISTS (SELECT 1 FROM presssport_internal.admin_allowlist AS a
                    WHERE a.email=v_email) THEN
    RAISE EXCEPTION 'verified Press & Sport administrator required'
      USING ERRCODE='28000';
  END IF;

  IF p_action='list' THEN
    SELECT COALESCE(jsonb_agg(to_jsonb(t)), '[]'::jsonb) INTO v_items
      FROM (
        SELECT post_key, instagram_account_id, caption, image_urls,
               content_sha256, editorial_state, approved_by, approved_at,
               planned_at, created_at, updated_at
        FROM presssport_internal.editorial_queue
        ORDER BY created_at DESC, post_key DESC
        LIMIT 50
      ) t;
    RETURN jsonb_build_object('items',v_items,'admin_email',v_email,
                              'publication_authorized',false);

  ELSIF p_action='create' THEN
    v_key := p_payload->>'post_key';
    v_caption := btrim(p_payload->>'caption');
    v_urls := p_payload->'image_urls';
    IF v_key IS NULL OR v_key !~ '^[a-z0-9][a-z0-9-]{2,78}[a-z0-9]$'
       OR v_caption IS NULL OR char_length(v_caption) NOT BETWEEN 1 AND 2200
       OR p_payload->>'instagram_account_id' IS DISTINCT FROM '17841425937268080'
       OR v_urls IS NULL OR jsonb_typeof(v_urls) <> 'array'
       OR jsonb_array_length(v_urls) NOT BETWEEN 2 AND 10 THEN
      RAISE EXCEPTION 'invalid editorial draft';
    END IF;
    IF EXISTS (
      SELECT 1 FROM jsonb_array_elements(v_urls) e
      WHERE jsonb_typeof(e.value) <> 'string'
         OR e.value #>> '{}' !~ '^https://pressandsport[.]it/[^?#]+[.]jpe?g$'
         OR e.value #>> '{}' LIKE '%/../%'
    ) OR (
      SELECT count(*) <> count(DISTINCT e.value)
      FROM jsonb_array_elements_text(v_urls) e(value)
    ) THEN
      RAISE EXCEPTION 'invalid or duplicated public JPEG URLs';
    END IF;
    v_digest := pg_catalog.encode(pg_catalog.sha256(
      pg_catalog.convert_to(
        jsonb_build_object('instagram_account_id','17841425937268080',
                           'caption',v_caption,'image_urls',v_urls)::text,
        'UTF8')), 'hex');
    INSERT INTO presssport_internal.editorial_queue
      (post_key,instagram_account_id,caption,image_urls,content_sha256)
    VALUES (v_key,'17841425937268080',v_caption,v_urls,v_digest)
    RETURNING editorial_state INTO v_state;
    RETURN jsonb_build_object('post_key',v_key,'editorial_state',v_state,
                              'publication_authorized',false);

  ELSIF p_action='transition' THEN
    v_key := p_post_key;
    IF v_key IS NULL OR v_key !~ '^[a-z0-9][a-z0-9-]{2,78}[a-z0-9]$'
       OR p_payload->>'from_state' IS NULL
       OR p_payload->>'to_state' IS NULL THEN
      RAISE EXCEPTION 'invalid transition request';
    END IF;
    SELECT editorial_state INTO v_state
    FROM presssport_internal.editorial_queue
    WHERE post_key=v_key FOR UPDATE;
    IF NOT FOUND OR v_state IS DISTINCT FROM p_payload->>'from_state' THEN
      RAISE EXCEPTION 'editorial state changed; refresh before continuing';
    END IF;
    IF NOT (
        (v_state='draft' AND p_payload->>'to_state' IN ('ready_for_review','cancelled'))
     OR (v_state='ready_for_review' AND p_payload->>'to_state' IN ('draft','approved','cancelled'))
     OR (v_state='approved' AND p_payload->>'to_state' IN ('planned','cancelled'))
     OR (v_state='planned' AND p_payload->>'to_state' IN ('approved','cancelled'))
    ) THEN
      RAISE EXCEPTION 'transition not permitted';
    END IF;
    IF p_payload->>'to_state'='planned' THEN
      v_planned := (p_payload->>'planned_at')::timestamptz;
      IF v_planned IS NULL OR v_planned <= now() THEN
        RAISE EXCEPTION 'planned date must be future';
      END IF;
    END IF;
    UPDATE presssport_internal.editorial_queue
    SET editorial_state=p_payload->>'to_state',
        approved_by=CASE WHEN v_state='ready_for_review'
                          AND p_payload->>'to_state'='approved'
                         THEN 'Paolo Savio' ELSE approved_by END,
        approved_at=CASE WHEN v_state='ready_for_review'
                          AND p_payload->>'to_state'='approved'
                         THEN now() ELSE approved_at END,
        planned_at=CASE WHEN p_payload->>'to_state'='planned' THEN v_planned
                        WHEN p_payload->>'to_state'='approved' THEN NULL
                        ELSE planned_at END,
        updated_at=now()
    WHERE post_key=v_key AND editorial_state=v_state
    RETURNING jsonb_build_object(
      'post_key',post_key,'editorial_state',editorial_state,
      'planned_at',planned_at,'publication_authorized',false)
    INTO v_result;
    IF v_result IS NULL THEN
      RAISE EXCEPTION 'editorial update not committed';
    END IF;
    RETURN v_result;
  END IF;
  RAISE EXCEPTION 'unsupported editorial action';
END;
$function$;

REVOKE ALL ON FUNCTION public.presssport_admin_queue(uuid,text,text,jsonb)
FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.presssport_admin_queue(uuid,text,text,jsonb)
TO service_role;
