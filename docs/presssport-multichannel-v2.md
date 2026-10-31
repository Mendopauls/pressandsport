# Press & Sport Cloud — multichannel preparation v2

This branch adds an **offline manifest validator** for these planned types:

- `instagram_image`: one image (feed)
- `instagram_carousel`: two to ten images
- `instagram_story`: one image
- `linkedin_image`: one image

It accepts only public, stable HTTPS JPEG URLs on `pressandsport.it`, the configured Instagram account (`17841425937268080`) or LinkedIn organization (`146625659`), and hashes the complete manifest.

## What is not yet implemented

- No database schema migration for multichannel posts.
- No authenticated operator-facing web console.
- No LinkedIn or Instagram posting executor.
- No media publishing or hosting step for private Google Drive assets.
- No automatic scheduler or recurring GitHub Action.
- No transfer of editorial approval into publication permission.

Production release must require **new explicit authorization** for a specific digest and account, and a durable, atomic one-shot reservation ledger. Never requeue the 28 October carousel. Never use Google Drive preview links as public Meta image URLs.

## Next implementation sequence

1. Review tests and confirm validation against the existing reservation ledger.
2. Add a protected Supabase multichannel queue migration and backend access controls.
3. Implement a web console showing drafts, review, schedule and manual release, without auto-publish.
4. Implement account-specific executors with idempotency and accurate delivery status.
5. Test with new staging-only assets and explicit release authorization; deploy the scheduler separately.

Run: `python -m unittest tests.test_presssport_multichannel_manifest -v`.
