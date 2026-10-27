# Press & Sport — Meta publishing (without Windsor.ai)

The cloud workflow stages approved images from Google Drive using GitHub OIDC.
This independent publisher uses the official Meta Graph API, not Ollama or Windsor.ai.
Ollama/PS AI Control Center can prepare caption and drafts; cloud publishing works with the PC off.

## Publication safety
- This branch only contains a **draft** manifest, with an empty caption.
- Publishing requires a reviewed manifest with `status: approved`, seven public JPEG URLs, a non-empty caption, and explicit manual workflow confirmation.
- Configure a GitHub environment named `instagram-publishing` with required reviewers before enabling publication.
- Add environment secret `META_INSTAGRAM_ACCESS_TOKEN` containing a valid Meta access token with Instagram content publishing permissions.
- Do not commit tokens or enable automatic scheduling until a dry run and permission checks pass.
- Meta's publishing API may require image URLs to be directly accessible and properly encoded.

## Status
Publisher source and gated workflow are prepared. No Instagram publishing has occurred.
