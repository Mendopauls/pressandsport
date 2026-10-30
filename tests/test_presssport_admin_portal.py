import re
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SQL=(ROOT/"supabase/migrations/20261030_presssport_admin_portal.sql").read_text()
EDGE=(ROOT/"supabase/functions/presssport-admin/index.ts").read_text()
HTML=(ROOT/"supabase/functions/presssport-admin/portal.html").read_text()

class AdminPortalContract(unittest.TestCase):
    def test_server_side_email_allowlist(self):
        self.assertIn("info@paolosavio.eu",SQL)
        self.assertIn("info@paolosavio.eu",EDGE)
        self.assertIn("email_confirmed_at",SQL)
        self.assertIn("email_confirmed_at",EDGE)
        self.assertIn("auth.getUser(bearer)",EDGE)
        self.assertIn("admin_allowlist",SQL)
        self.assertIn("auth.users",SQL)

    def test_admin_rpc_never_public(self):
        self.assertIn("SECURITY DEFINER",SQL)
        self.assertIn("SET search_path = pg_catalog",SQL)
        self.assertIn("REVOKE ALL ON FUNCTION public.presssport_admin_queue",SQL)
        self.assertIn("FROM PUBLIC, anon, authenticated",SQL)
        self.assertIn("TO service_role",SQL)
        self.assertIn("ENABLE ROW LEVEL SECURITY",SQL)
        self.assertIn("REVOKE ALL ON presssport_internal.admin_allowlist",SQL)

    def test_service_role_secret_only_on_server(self):
        self.assertIn('Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")',EDGE)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY",HTML)
        self.assertIn("SUPABASE_ANON_KEY",EDGE)
        self.assertIn("adminClient.rpc",EDGE)
        self.assertNotIn("meta_media_id",EDGE)
        self.assertNotIn("media_publish",EDGE)
        self.assertNotIn("meta_media_id",SQL)
        self.assertNotIn("publication_reservations",SQL)

    def test_login_and_editorial_only(self):
        self.assertIn("signInWithOtp",HTML)
        self.assertIn("detectSessionInUrl:true",HTML)
        self.assertIn("auth.signOut()",HTML)
        self.assertIn("publication_authorized',false",SQL)
        self.assertNotIn("publish_now",HTML)
        self.assertNotIn("media_publish",HTML)
        self.assertNotIn("POST /media",HTML)

    def test_origin_and_request_limits(self):
        self.assertIn('origin !== allowedOrigin',EDGE)
        self.assertIn("MAX_BODY_BYTES",EDGE)
        self.assertIn('url.searchParams.get("mode") !== "api"',EDGE)
        self.assertIn("script-src 'nonce-",EDGE)
        self.assertIn('new TextEncoder().encode(raw).byteLength',EDGE)

    def test_frontend_javascript_parses(self):
        match=re.search(r'<script[^>]*type="module"[^>]*>(.*?)</script>',HTML,re.S)
        self.assertIsNotNone(match)
        result=subprocess.run(["node","--input-type=module","--check"],
            input=match.group(1),text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__ == "__main__":
    unittest.main()
