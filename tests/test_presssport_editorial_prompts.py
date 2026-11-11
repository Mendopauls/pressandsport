"""Offline regression coverage for source-only editorial prompting."""
import unittest

from scripts.presssport_editorial_prompts import (
    build_platform_request,
    extract_editorial_context,
)


V7_BRIEF = """
PRESS & SPORT - COLLAUDO INTERNO
NON PUBBLICARE. NESSUN EVENTO REALE.

Obiettivo: spiegare come una società sportiva
dilettantistica può preparare un comunicato stampa.

Trattare:
- titolo informativo
- chi, cosa, dove e quando
- verifica delle fonti
- contatti della società
- diritti delle fotografie

Instagram: 450-750 caratteri.
LinkedIn: 650-1000 caratteri.
Preparare anche visual_brief e fact_checks.
Non inventare gare, date, orari o autorizzazioni.
La bozza richiede revisione umana.
NON PUBBLICARE.
"""

DRIVE_BRIEF = """
PRESS & SPORT — TEST DI IMPORTAZIONE DRIVE → OLLAMA
NON PUBBLICARE — BOZZA DI COLLAUDO, NESSUN EVENTO REALE

Obiettivo: preparare un esempio educativo sulla struttura di un buon
comunicato stampa per una società sportiva dilettantistica. Non citare società,
atleti, sponsor, eventi, date, risultati o dichiarazioni reali né inventati.

Produci esclusivamente un JSON con cinque campi:
- instagram_caption: tra 450 e 750 caratteri.
- linkedin_caption: tra 650 e 1000 caratteri.
- fact_checks: indicare che questa è una simulazione.
NON PUBBLICARE.
"""


class EditorialPromptTests(unittest.TestCase):
    def test_v7_objective_and_editorial_bullets_only(self):
        content = extract_editorial_context(V7_BRIEF)
        self.assertIn("società sportiva dilettantistica", content)
        self.assertIn("comunicato stampa", content)
        self.assertIn("titolo informativo", content)
        self.assertIn("diritti delle fotografie", content)
        self.assertNotIn("PRESS & SPORT - COLLAUDO", content)
        self.assertNotIn("NON PUBBLICARE", content)
        self.assertNotIn("450-750", content)
        self.assertNotIn("fact_checks", content)

    def test_platform_format_is_single_field_json(self):
        for channel, lower, upper in (
            ("instagram_caption", 450, 750),
            ("linkedin_caption", 650, 1000),
        ):
            with self.subTest(channel=channel):
                body = build_platform_request(V7_BRIEF, channel)
                self.assertEqual(body["format"]["required"], [channel])
                self.assertEqual(
                    list(body["format"]["properties"].keys()), [channel]
                )
                self.assertEqual(body["model"], "qwen2.5:3b")
                self.assertFalse(body["stream"])
                self.assertIn(str(lower), body["prompt"])
                self.assertIn(str(upper), body["prompt"])
                self.assertNotIn("PRESS & SPORT - COLLAUDO", body["prompt"])
                self.assertNotIn("NON PUBBLICARE", body["prompt"])
                self.assertIn("Non inventare", body["prompt"])

    def test_real_drive_brief_excludes_processing_instructions(self):
        content = extract_editorial_context(DRIVE_BRIEF)
        self.assertIn("comunicato stampa", content)
        self.assertNotIn("instagram_caption:", content)
        self.assertNotIn("JSON con cinque campi", content)
        self.assertNotIn("NON PUBBLICARE", content)

    def test_missing_objective_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_editorial_context("NON PUBBLICARE - test tecnico")
        with self.assertRaises(ValueError):
            build_platform_request("TEST tecnico", "instagram_caption")
        with self.assertRaises(ValueError):
            build_platform_request(V7_BRIEF, "facebook_caption")


if __name__ == "__main__":
    unittest.main()
