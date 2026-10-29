# Read-only cloud verification

The cloud dry-run workflow runs on relevant changes to main and may also be
started manually. It checks Meta identity and the Supabase ledger through
read-only operations. It never calls the publication orchestrator.

Editorial approval does not authorize publication. Live publishing requires
a separate explicit approval and a separately audited production runner.

Review the GitHub Actions run and its logs before treating cloud connectivity
as verified. A green offline unit-test run alone is insufficient.
