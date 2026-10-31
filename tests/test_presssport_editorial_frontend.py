import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class ConsoleFrontendTests(unittest.TestCase):
    def test_readonly_ui_and_no_secrets(self):
        html = (ROOT / "admin/editorial-v2.html").read_text(encoding="utf-8")
        js = (ROOT / "admin/editorial-v2.js").read_text(encoding="utf-8")
        self.assertIn("Coda editoriale", html)
        self.assertIn("api/editorial/v2/queue", js)
        self.assertNotIn("service_role", html + js)
        self.assertNotIn("localStorage.", js)
        self.assertNotIn("/publish", js)

    def test_config_never_contains_private_credentials(self):
        config=(ROOT / "admin/editorial-v2-config.example.js").read_text(encoding="utf-8")
        self.assertNotIn("DATABASE_URL", config)
        self.assertNotIn("service_role", config)

if __name__=="__main__":
    unittest.main()
