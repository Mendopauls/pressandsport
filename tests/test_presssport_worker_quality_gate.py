"""Regressions for real V6 Ollama false-positive draft from 2026-11-11."""
import json
import unittest

from scripts.presssport_worker_quality_gate import apply_quality_gate


BRIEF = (
    "PRESS & SPORT - TEST EDITORIALE. NESSUN EVENTO REALE. "
    "Obiettivo: spiegare come una società sportiva dilettantistica "
    "possa preparare un buon comunicato stampa. "
    "Non inventare fatti, eventi, risultati, date o fonti verificate. NON PUBBLICARE."
)

# These are the actual captions that passed V6 length/keyword QA but invented events.
REAL_V6_IG = (
    "Sei curioso di sapere come una piccola società sportiva dilettantistica "
    "possa produrre un comunicato stampa efficace e professionale? "
    "Ci sono alcuni passaggi chiave da seguire per preparare un buon comunicato stampa. "
    "🏀 #sport #comunicatastampa #societaysportive\n\n"
    "1️⃣ **Titolo chiaro e informativo**: Comincia con un titolo che spiega chiaramente "
    "cosa si tratta. Ad esempio: 'Risultati eccellenti per la squadra locale di calcio'. "
    "📜 #titolo\n\n"
    "2️⃣ **Informazioni chi, cosa, dove e quando**: Specifica chi ha partecipato, cosa "
    "è successo, dove e quando. Ad esempio: 'La squadra locale di calcio ha vinto "
    "il torneo regionale, concludendo il campionato con 10 vittorie in 12 partite, "
    "il 15 maggio 2023'."
)
REAL_V6_LI = (
    "Sei un editor di Press & Sport. NON PUBBLICARE. "
    "Questo è un test di editorializzazione per LinkedIn. "
    "L'obiettivo è spiegare come una società sportiva dilettantistica possa "
    "preparare un buon comunicato stampa. Questo testaletto illustra il processo "
    "di preparazione di un comunicato stampa, da inizio alla fine. "
    "**Contesto**\nLa società sportiva dilettantistica ha deciso di organizzare "
    "una gara di calcio interno. Il team ha già selezionato i giocatori e ha "
    "iniziato l'allenamento. La gara si terrà domenica prossima alle 15.00 "
    "presso la sala da tennis. **Pianificazione**\n"
    "Il team ha già pianificato i dettagli della gara. La società ha già "
    "ottenuto le autorizzazioni necessarie per la gara. La società ha anche "
    "iniziato a contattare i media per la promozione della gara. **Verifiche**\n"
    "Il team ha verificato tutte le informazioni fornite. Tutto è stato "
    "verificato con fonti affidabili. La gara è stata confermata e "
    "l'allenamento è stato verificato con i giocatori."
)


def sample(ig=None, li=None):
    return {
        "instagram_caption": ig if ig is not None else
        "Il comunicato stampa per la società sportiva richiede dati verificati. " * 8,
        "linkedin_caption": li if li is not None else
        "Un comunicato stampa per la società sportiva deve distinguere "
        "le informazioni verificate dai dettagli ancora da controllare. " * 7,
        "visual_brief": "Schema astratto senza fotografie",
        "fact_checks": "Verificare ogni dato prima dell'uso",
        "suggested_alt_text": "Schema di un comunicato stampa",
    }


class GateTests(unittest.TestCase):
    def test_real_v6_output_is_blocked_despite_structural_pass(self):
        from scripts.presssport_caption_quality import validate_draft
        raw = sample(REAL_V6_IG, REAL_V6_LI)
        self.assertEqual(validate_draft(raw), [])
        gated = apply_quality_gate(BRIEF, raw)
        issues = gated["issues"]
        self.assertIn("unsupported_date_instagram_caption", issues)
        self.assertIn("unsupported_result_instagram_caption", issues)
        self.assertIn("prompt_leak_linkedin_caption", issues)
        self.assertIn("unsupported_time_linkedin_caption", issues)
        self.assertIn("unsupported_assertion_linkedin_caption", issues)
        parsed = json.loads(gated["draft"])
        self.assertEqual(parsed["instagram_caption"], "")
        self.assertEqual(parsed["linkedin_caption"], "")
        self.assertIn("QA NON SUPERATA", parsed["fact_checks"])
        self.assertTrue(gated["needs_human_review"])
        self.assertFalse(gated["publish_allowed"])

    def test_nonflagged_draft_still_requires_manual_review(self):
        gated = apply_quality_gate(BRIEF, sample())
        self.assertEqual(gated["issues"], [])
        self.assertTrue(json.loads(gated["draft"])["instagram_caption"])
        self.assertTrue(gated["needs_human_review"])
        self.assertFalse(gated["publish_allowed"])

    def test_invalid_json_fails_closed(self):
        gated = apply_quality_gate(BRIEF, "{broken json")
        parsed = json.loads(gated["draft"])
        self.assertIn("invalid_json", gated["issues"])
        self.assertEqual(parsed["instagram_caption"], "")
        self.assertEqual(parsed["linkedin_caption"], "")
        self.assertIn("QA NON SUPERATA", parsed["fact_checks"])

    def test_short_instagram_is_zeroed_without_dropping_linkedin(self):
        gated = apply_quality_gate(BRIEF, sample(ig="breve"))
        parsed = json.loads(gated["draft"])
        self.assertEqual(parsed["instagram_caption"], "")
        self.assertTrue(parsed["linkedin_caption"])
        self.assertFalse(gated["publish_allowed"])

    def test_v7_regression_upstream_block_remains_blocked(self):
        raw = sample(ig="", li="")
        raw["fact_checks"] = (
            "REVISIONE UMANA OBBLIGATORIA. QA NON SUPERATA: "
            "invalid_instagram_caption_after_retry_length_chars_1119. "
            "NON PUBBLICARE."
        )
        gated = apply_quality_gate(BRIEF, raw)
        parsed = json.loads(gated["draft"])
        self.assertIn("upstream_qa_block", gated["issues"])
        self.assertEqual(parsed["instagram_caption"], "")
        self.assertEqual(parsed["linkedin_caption"], "")
        self.assertIn("GATE AGGIUNTIVO", parsed["fact_checks"])
        self.assertEqual(parsed["fact_checks"].count("REVISIONE UMANA OBBLIGATORIA"), 1)
        self.assertFalse(gated["publish_allowed"])

    def test_v7_prompt_echo_not_considered_valid_caption(self):
        raw = sample(
            ig=("Un comunicato stampa deve spiegare titolo, chi e quando. " * 10),
            li=("PRESS & SPORT - COLLAUDO INTERNO. NON PUBBLICARE. "
                "NESSUN EVENTO REALE. Obiettivo: "
                "spiegare come preparare un comunicato stampa. " * 9),
        )
        gated = apply_quality_gate(BRIEF, raw)
        self.assertIn("prompt_leak_linkedin_caption", gated["issues"])
        parsed = json.loads(gated["draft"])
        self.assertEqual(parsed["linkedin_caption"], "")
        self.assertFalse(gated["publish_allowed"])

    def test_real_editorial_prompt_1745_char_failure_is_not_publishable(self):
        from scripts.presssport_caption_quality import evaluate_draft
        raw = sample()
        # Representative fragments from the actual 1745-character Ollama result:
        # a fabricated date, a fake phone/URL, unverifiable permissions and
        # processing instructions echoed into the caption.
        raw["instagram_caption"] = (
            "Il comunicato stampa include titolo, persone, tempi e luogo. "
            "Il Comitato Sportivo Dilettantistico ha annunciato una nuova "
            "stagione a Roma il 15 giugno 2023. "
            "Tutte le informazioni sono state verificate da fonti ufficiali. "
            "Per ulteriori informazioni contatta il 06-1234-5678 "
            "o visita www.comitodilettantistico.it. "
            "Le foto utilizzate sono state autorizzate. "
            "Ricorda, non descrivere gare specifiche come avvenute, "
            "non inventare nomi, date o risultati. "
            + "Il comunicato stampa deve essere chiaro e completo. " * 12
        )
        brief = BRIEF + " Non inventare recapiti, siti web o autorizzazioni."
        issues = evaluate_draft(brief, raw)
        self.assertTrue(any(x.startswith("instagram_caption_length_") for x in issues))
        self.assertIn("unsupported_date_instagram_caption", issues)
        self.assertIn("unsupported_phone_instagram_caption", issues)
        self.assertIn("unsupported_url_instagram_caption", issues)
        self.assertIn("unsupported_verification_instagram_caption", issues)
        self.assertIn("prompt_leak_instagram_caption", issues)

        gated = apply_quality_gate(brief, raw)
        data = json.loads(gated["draft"])
        self.assertEqual(data["instagram_caption"], "")
        self.assertTrue(data["linkedin_caption"])
        self.assertFalse(gated["publish_allowed"])
        self.assertIn("QA NON SUPERATA", data["fact_checks"])

    def test_phone_or_url_provided_in_brief_not_automatically_invented(self):
        from scripts.presssport_caption_quality import validate_editorial_red_flags
        brief = BRIEF + " Contatti confermati: 06-1234-5678 e www.sportclub.it."
        raw = sample(ig=(
            "Il comunicato stampa della societa sportiva riporta solo "
            "i dati forniti nel brief: 06-1234-5678 e www.sportclub.it. "
        ) * 6)
        issues = validate_editorial_red_flags(brief, raw)
        self.assertNotIn("unsupported_phone_instagram_caption", issues)
        self.assertNotIn("unsupported_url_instagram_caption", issues)

    def test_missing_metadata_never_marks_publishable(self):
        raw = sample()
        raw["visual_brief"] = ""
        gated = apply_quality_gate(BRIEF, raw)
        self.assertIn("missing_visual_brief", gated["issues"])
        self.assertIn("QA NON SUPERATA", json.loads(gated["draft"])["fact_checks"])
        self.assertFalse(gated["publish_allowed"])


if __name__ == "__main__":
    unittest.main()
