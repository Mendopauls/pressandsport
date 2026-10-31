-- Press & Sport multichannel v2: NEW, separate editorial queue.
-- Does not touch legacy editorial_queue or production publication reservations.
-- Applying this migration never publishes, schedules, or authorizes a post.
CREATE SCHEMA IF NOT EXISTS presssport_internal;

CREATE TABLE IF NOT EXISTS presssport_internal.multichannel_queue (
  post_key text PRIMARY KEY CHECK (post_key ~ '^[a-z0-9][a-z0-9-]{2,78}[a-z0-9]$'),
  channel text NOT NULL CHECK (channel IN ('instagram','linkedin')),
  content_kind text NOT NULL CHECK (content_kind IN
      ('instagram_image','instagram_carousel','instagram_story','linkedin_image')),
  account_id text NOT NULL,
  caption text NOT NULL CHECK (char_length(caption) <= 3000),
  image_urls jsonb NOT NULL CHECK (jsonb_typeof(image_urls)='array'),
  content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
  editorial_state text NOT NULL DEFAULT 'draft'
    CHECK (editorial_state IN ('draft','ready_for_review','approved','planned','cancelled')),
  approved_by text,
  approved_at timestamptz,
  planned_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT multichannel_kind_account CHECK (
    (channel='instagram' AND account_id='17841425937268080'
     AND content_kind IN ('instagram_image','instagram_carousel','instagram_story')
     AND char_length(caption)<=2200)
    OR (channel='linkedin' AND account_id='146625659'
        AND content_kind='linkedin_image')
  ),
  CONSTRAINT multichannel_image_count CHECK (
    (content_kind='instagram_carousel' AND jsonb_array_length(image_urls) BETWEEN 2 AND 10)
    OR (content_kind <> 'instagram_carousel' AND jsonb_array_length(image_urls)=1)
  ),
  CONSTRAINT multichannel_caption_required CHECK (
    content_kind='instagram_story' OR char_length(trim(caption))>0
  ),
  CONSTRAINT multichannel_approval CHECK (
    editorial_state NOT IN ('approved','planned')
    OR (approved_by='Paolo Savio' AND approved_at IS NOT NULL)
  ),
  CONSTRAINT multichannel_plan CHECK (
    editorial_state <> 'planned' OR planned_at IS NOT NULL
  )
);
CREATE INDEX IF NOT EXISTS multichannel_queue_due_idx
  ON presssport_internal.multichannel_queue(planned_at)
  WHERE editorial_state='planned';
ALTER TABLE presssport_internal.multichannel_queue ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON presssport_internal.multichannel_queue FROM PUBLIC, anon, authenticated;
-- Preserve existing schema grants used by the legacy production pipeline.

CREATE OR REPLACE FUNCTION presssport_internal.guard_multichannel_queue()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, presssport_internal
AS $$
BEGIN
  IF TG_OP='UPDATE' THEN
    IF OLD.post_key IS DISTINCT FROM NEW.post_key
      OR OLD.channel IS DISTINCT FROM NEW.channel
      OR OLD.content_kind IS DISTINCT FROM NEW.content_kind
      OR OLD.account_id IS DISTINCT FROM NEW.account_id THEN
      RAISE EXCEPTION 'editorial identity is immutable';
    END IF;
    IF (OLD.editorial_state <> 'draft' OR NEW.editorial_state <> 'draft')
      AND (OLD.caption IS DISTINCT FROM NEW.caption
       OR OLD.image_urls IS DISTINCT FROM NEW.image_urls
       OR OLD.content_sha256 IS DISTINCT FROM NEW.content_sha256) THEN
      RAISE EXCEPTION 'submitted content is immutable';
    END IF;
    IF OLD.editorial_state <> NEW.editorial_state AND NOT (
      (OLD.editorial_state='draft' AND NEW.editorial_state IN ('ready_for_review','cancelled'))
      OR (OLD.editorial_state='ready_for_review' AND NEW.editorial_state IN ('draft','approved','cancelled'))
      OR (OLD.editorial_state='approved' AND NEW.editorial_state IN ('planned','cancelled'))
      OR (OLD.editorial_state='planned' AND NEW.editorial_state IN ('approved','cancelled'))
    ) THEN RAISE EXCEPTION 'invalid editorial transition'; END IF;
    IF OLD.editorial_state IN ('approved','planned','cancelled')
      AND (OLD.approved_by IS DISTINCT FROM NEW.approved_by
      OR OLD.approved_at IS DISTINCT FROM NEW.approved_at) THEN
      RAISE EXCEPTION 'approval audit immutable';
    END IF;
  END IF;
  IF NEW.editorial_state IN ('approved','planned')
    AND (NEW.approved_by IS DISTINCT FROM 'Paolo Savio' OR NEW.approved_at IS NULL)
    THEN RAISE EXCEPTION 'named approval required'; END IF;
  IF NEW.editorial_state='planned'
    AND (NEW.planned_at IS NULL OR NEW.planned_at <= now())
    THEN RAISE EXCEPTION 'planned date must be future'; END IF;
  NEW.updated_at=now();
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS guard_multichannel_queue_trg
  ON presssport_internal.multichannel_queue;
CREATE TRIGGER guard_multichannel_queue_trg
BEFORE INSERT OR UPDATE ON presssport_internal.multichannel_queue
FOR EACH ROW EXECUTE FUNCTION presssport_internal.guard_multichannel_queue();
REVOKE ALL ON FUNCTION presssport_internal.guard_multichannel_queue()
  FROM PUBLIC, anon, authenticated;
