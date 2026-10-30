-- Press & Sport Cloud: editorial queue foundation.
-- This table is NOT a publisher: editorial approval/planning never authorizes Meta POST.
-- Existing publication_reservations and already published media are untouched.
CREATE TABLE IF NOT EXISTS presssport_internal.editorial_queue (
  post_key text PRIMARY KEY CHECK (post_key ~ '^[a-z0-9][a-z0-9-]{2,78}[a-z0-9]$'),
  instagram_account_id text NOT NULL
    CHECK (instagram_account_id = '17841425937268080'),
  caption text NOT NULL CHECK (char_length(trim(caption)) BETWEEN 1 AND 2200),
  image_urls jsonb NOT NULL CHECK (
    jsonb_typeof(image_urls) = 'array'
    AND jsonb_array_length(image_urls) BETWEEN 2 AND 10
  ),
  content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
  editorial_state text NOT NULL DEFAULT 'draft'
    CHECK (editorial_state IN ('draft','ready_for_review','approved','planned','cancelled')),
  approved_by text,
  approved_at timestamptz,
  planned_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT approval_data_required CHECK (
    editorial_state NOT IN ('approved','planned')
    OR (approved_by = 'Paolo Savio' AND approved_at IS NOT NULL)
  ),
  CONSTRAINT planned_date_required CHECK (
    editorial_state <> 'planned' OR planned_at IS NOT NULL
  )
);
CREATE INDEX IF NOT EXISTS editorial_queue_planned_due_idx
ON presssport_internal.editorial_queue (planned_at)
WHERE editorial_state='planned';

ALTER TABLE presssport_internal.editorial_queue ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON presssport_internal.editorial_queue FROM PUBLIC, anon, authenticated;

-- Invoker-rights trigger: reject invalid editorial transitions and retroactive
-- modification of content after submission. Publication is never triggered.
CREATE OR REPLACE FUNCTION presssport_internal.guard_editorial_queue()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = presssport_internal, pg_temp
AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    IF OLD.post_key IS DISTINCT FROM NEW.post_key
      OR OLD.instagram_account_id IS DISTINCT FROM NEW.instagram_account_id THEN
      RAISE EXCEPTION 'editorial post identity cannot change';
    END IF;
    IF (OLD.editorial_state <> 'draft' OR NEW.editorial_state <> 'draft')
      AND (OLD.caption IS DISTINCT FROM NEW.caption
       OR OLD.image_urls IS DISTINCT FROM NEW.image_urls
       OR OLD.content_sha256 IS DISTINCT FROM NEW.content_sha256) THEN
      RAISE EXCEPTION 'submitted editorial content is immutable; return to draft first';
    END IF;
    IF OLD.editorial_state <> NEW.editorial_state AND NOT (
      (OLD.editorial_state = 'draft' AND NEW.editorial_state IN ('ready_for_review','cancelled'))
      OR (OLD.editorial_state = 'ready_for_review' AND NEW.editorial_state IN ('draft','approved','cancelled'))
      OR (OLD.editorial_state = 'approved' AND NEW.editorial_state IN ('planned','cancelled'))
      OR (OLD.editorial_state = 'planned' AND NEW.editorial_state IN ('approved','cancelled'))
    ) THEN
      RAISE EXCEPTION 'invalid editorial state transition';
    END IF;
    IF OLD.editorial_state IN ('approved','planned','cancelled')
      AND (OLD.approved_by IS DISTINCT FROM NEW.approved_by
        OR OLD.approved_at IS DISTINCT FROM NEW.approved_at) THEN
      RAISE EXCEPTION 'editorial approval audit cannot be changed';
    END IF;
  END IF;
  IF NEW.editorial_state = 'planned'
     AND (NEW.planned_at IS NULL OR NEW.planned_at <= now()) THEN
    RAISE EXCEPTION 'planned date must be in the future';
  END IF;
  IF NEW.editorial_state IN ('approved','planned')
     AND (NEW.approved_by <> 'Paolo Savio' OR NEW.approved_at IS NULL) THEN
    RAISE EXCEPTION 'named editorial approval required';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS guard_editorial_queue_trg ON presssport_internal.editorial_queue;
CREATE TRIGGER guard_editorial_queue_trg
BEFORE INSERT OR UPDATE ON presssport_internal.editorial_queue
FOR EACH ROW EXECUTE FUNCTION presssport_internal.guard_editorial_queue();

REVOKE ALL ON FUNCTION presssport_internal.guard_editorial_queue() FROM PUBLIC, anon, authenticated;
