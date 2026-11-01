import unittest
from scripts.presssport_editorial_dashboard import render_dashboard

class DashboardTests(unittest.TestCase):
    def test_empty_queue(self):
        self.assertIn("Nessun contenuto", render_dashboard([]))

    def test_html_is_escaped(self):
        html = render_dashboard([{"post_key": "<script>alert(1)</script>",
            "channel": "instagram", "kind": "instagram_image",
            "state": "draft", "planned_at": None}])
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_cannot_publish(self):
        html = render_dashboard([])
        self.assertNotIn("fetch(", html)
        self.assertNotIn("<form", html)
        self.assertNotIn("type=\"submit\"", html)

if __name__ == "__main__":
    unittest.main()
