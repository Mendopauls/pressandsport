"""Offline smoke tests for the production editorial console, no credentials or live publication."""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class EditorialConsoleTests(unittest.TestCase):
    def test_review_page_has_authentication(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn("signInWithPassword",html)
        self.assertIn("presssport-v2-web-session",html)
        self.assertIn("callJobs(\"list\")",html)

    def test_revision_history_is_separate_from_original(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn('callJobs("revision"',html)
        self.assertIn("latest_editorial_content",html)
        self.assertIn("Revisioni conservate",html)

    def test_no_publication_actions_in_review_console(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertNotIn('callJobs("publish"',html)
        self.assertNotIn('callJobs("approve"',html)
        self.assertIn("Checklist pre-pubblicazione",html)

    def test_revision_editor_enforces_caption_lengths(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn("Lunghezza caption fuori dai limiti editoriali",html)
        self.assertIn("content.instagram_caption.length<450",html)
        self.assertIn("content.linkedin_caption.length<650",html)

    def test_revision_api_and_migration_enforce_limits(self):
        migration_path=ROOT/"supabase"/"migrations"/"20261101_editorial_revision_caption_validation.sql"
        self.assertTrue(migration_path.exists(), "Migration missing from checked-out branch")
        migration=migration_path.read_text(encoding="utf-8")
        self.assertIn("char_length(ig) not between 450 and 750",migration)
        self.assertIn("char_length(li) not between 650 and 1000",migration)
        self.assertIn("grant execute",migration)
        for name in ("visual_brief","fact_checks","suggested_alt_text"):
            self.assertIn(name,migration)

    def test_existing_photo_is_not_mistaken_for_verified(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn("Archivio fotografico: file già associato",html)
        self.assertIn("Per sostituirlo occorre una nuova verifica",html)

    def test_duplicate_photo_association_is_skipped(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn("Fotografia già associata: nessuna modifica necessaria.",html)
        self.assertIn("item.asset_file_id===assetId.value.trim()",html)

    def test_asset_reassignment_migration_preserves_verification(self):
        migration=(ROOT/"supabase"/"migrations"/"20261101_editorial_asset_idempotency.sql").read_text(encoding="utf-8")
        self.assertIn("drive_file_id=excluded.drive_file_id", migration)
        self.assertIn("then presssport_internal.editorial_assets.verification_state", migration)
        self.assertIn("else 'pending' end", migration)
        self.assertIn("then presssport_internal.editorial_assets.verified_at else null end", migration)

    def test_multi_project_directory_is_read_only(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        migration=(ROOT/"supabase"/"migrations"/"20261101_multi_project_foundation.sql").read_text(encoding="utf-8")
        self.assertIn('callJobs("projects")',html)
        self.assertIn('const projectsArea=',html)
        self.assertIn("publication_enabled=false",migration)
        self.assertNotIn('callJobs("switch-project"',html)

    def test_other_projects_hide_legacy_editor(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn('id="project-selector"',html)
        self.assertIn('draftPanel.hidden=!legacy',html)
        self.assertIn('jobsArea.hidden=!legacy',html)
        self.assertIn('Spazio in preparazione',html)

    def test_selected_project_is_sent_to_editorial_api(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn('project_slug:projectSelector.value',html)
        self.assertIn('mode==="projects"?payload',html)

    def test_project_editorial_queue_is_separate(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        migration=(ROOT/"supabase"/"migrations"/"20261102_project_queues.sql").read_text(encoding="utf-8")
        self.assertIn('callJobs("project-list"',html)
        self.assertIn('callJobs("project-enqueue"',html)
        self.assertIn("unique(project_id,external_key)",migration)
        self.assertIn("enable row level security",migration)
        self.assertIn("p_slug='press-sport'",migration)

    def test_asset_verification_is_explicit(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        self.assertIn('item.asset_state==="verified"',html)
        self.assertIn('callJobs("asset"',html)
        self.assertIn("Approvazione umana",html)

    def test_cloud_ai_feature_gate_and_isolated_claim(self):
        worker=(ROOT/"supabase"/"functions"/"presssport-project-ai"/"index.ts").read_text(encoding="utf-8")
        migration=(ROOT/"supabase"/"migrations"/"20261102_project_ai_claim_finish.sql").read_text(encoding="utf-8")
        self.assertIn("PRESSSPORT_CLOUD_AI_ENABLED",worker)
        self.assertIn("PRESSSPORT_CLOUD_AI_API_KEY",worker)
        self.assertIn("cloud_ai_not_configured",worker)
        self.assertIn("presssport_admin_project_ai_claim",migration)
        self.assertIn("presssport_admin_project_ai_finish",migration)

    def test_project_drafts_are_read_only_and_isolated(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        migration=(ROOT/"supabase"/"migrations"/"20261102_project_draft_read.sql").read_text(encoding="utf-8")
        self.assertIn("Visualizza bozza AI (non approvata)",html)
        self.assertIn("copy.textContent=item.draft_text",html)
        self.assertIn("q.state='draft_for_review'",migration)
        self.assertIn("p.slug=p_slug",migration)

    def test_manual_project_drafts_never_publish(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        sql=(ROOT/"supabase"/"migrations"/"20261102_project_manual_draft.sql").read_text(encoding="utf-8")
        self.assertIn('callJobs("project-draft-save"',html)
        self.assertIn('Salva bozza (non pubblicare)',html)
        self.assertIn("p.slug=p_slug",sql)
        self.assertIn("state='draft_for_review'",sql)

    def test_zero_extra_cost_mode(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        cloud=(ROOT/"supabase"/"functions"/"presssport-project-ai"/"index.ts").read_text(encoding="utf-8")
        self.assertIn("Prepara traccia gratuita",html)
        self.assertIn("non viene sovrascritta",html)
        self.assertIn("paid_ai_disabled_by_zero_cost_policy",cloud)
        self.assertIn("return respond({error:",cloud)

    def test_free_calendar_and_export(self):
        html=(ROOT/"admin"/"console-v2-review.html").read_text(encoding="utf-8")
        api=(ROOT/"supabase"/"functions"/"presssport-ollama-sync"/"index.ts").read_text(encoding="utf-8")
        migration=(ROOT/"supabase"/"migrations"/"20261103_project_calendar_free.sql").read_text(encoding="utf-8")
        self.assertIn("Esporta fino a 50 incarichi",html)
        self.assertIn("URL.createObjectURL",html)
        self.assertIn('callJobs("project-schedule"',html)
        self.assertIn('presssport_admin_project_schedule',api)
        self.assertIn("p.slug=p_slug",migration)
        self.assertIn("planned_date",migration)
        self.assertIn("publication",html.lower())

if __name__=="__main__":unittest.main()
