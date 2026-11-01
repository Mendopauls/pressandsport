-- Isolated smoke test. Every insert is rolled back.
BEGIN;
DO $$
DECLARE
  missing_approval boolean := false;
  invalid_transition boolean := false;
  immutable_content boolean := false;
  row_count integer;
BEGIN
  INSERT INTO presssport_internal.multichannel_queue
    (post_key,channel,content_kind,account_id,caption,image_urls,content_sha256)
  VALUES
    ('sample-queue-001','instagram','instagram_image','17841425937268080',
     'Test caption','["https://pressandsport.it/test.jpg"]'::jsonb,repeat('a',64));

  UPDATE presssport_internal.multichannel_queue
    SET editorial_state='ready_for_review'
    WHERE post_key='sample-queue-001';

  BEGIN
    UPDATE presssport_internal.multichannel_queue
      SET editorial_state='approved'
      WHERE post_key='sample-queue-001';
  EXCEPTION WHEN OTHERS THEN missing_approval := true; END;
  IF NOT missing_approval THEN
    RAISE EXCEPTION 'PASS expected approval guard failure';
  END IF;

  BEGIN
    UPDATE presssport_internal.multichannel_queue
      SET editorial_state='planned'
      WHERE post_key='sample-queue-001';
  EXCEPTION WHEN OTHERS THEN invalid_transition := true; END;
  IF NOT invalid_transition THEN
    RAISE EXCEPTION 'PASS expected transition guard failure';
  END IF;

  BEGIN
    UPDATE presssport_internal.multichannel_queue
      SET caption='Changed' WHERE post_key='sample-queue-001';
  EXCEPTION WHEN OTHERS THEN immutable_content := true; END;
  IF NOT immutable_content THEN
    RAISE EXCEPTION 'PASS expected immutable content guard failure';
  END IF;

  SELECT count(*) INTO row_count FROM presssport_internal.multichannel_queue
   WHERE post_key='sample-queue-001' AND editorial_state='ready_for_review';
  IF row_count<>1 THEN RAISE EXCEPTION 'Queue record state incorrect'; END IF;

  IF has_table_privilege('anon','presssport_internal.multichannel_queue','SELECT')
     OR has_table_privilege('authenticated','presssport_internal.multichannel_queue','INSERT') THEN
    RAISE EXCEPTION 'RLS/table privileges insufficient';
  END IF;
  RAISE NOTICE 'PASS: editorial transitions, immutability and RLS privileges';
END;
$$;
ROLLBACK;
