"""Offline caption validation and one bounded retry; never publishes."""
import json

REQUIRED = ("instagram_caption", "linkedin_caption", "visual_brief",
            "fact_checks", "suggested_alt_text")
LIMITS = {"instagram_caption": (450, 750), "linkedin_caption": (650, 1000)}

def _parse(value):
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        raise ValueError("Expected JSON text or dict")
    result = json.loads(value.strip())
    if not isinstance(result, dict):
        raise ValueError("JSON root must be an object")
    return result

def utf16_length(value):
    """Match the browser editor's JS length semantics."""
    return len(value.encode("utf-16-le")) // 2

def validate_draft(draft):
    """Return quality errors. Empty does NOT mean editorial approval."""
    try:
        obj = _parse(draft)
    except (ValueError, TypeError):
        return ["invalid_json"]
    errors = []
    for key in REQUIRED:
        if not isinstance(obj.get(key), str) or not obj[key].strip():
            errors.append("missing_" + key)
    for key, (minimum, maximum) in LIMITS.items():
        value = obj.get(key)
        if isinstance(value, str):
            size = utf16_length(value)
            if not minimum <= size <= maximum:
                errors.append(key + "_length_" + str(size))
    return errors


# Topic alignment is a conservative heuristic, not a factual verifier.
import re
import unicodedata

_COMMON_WORDS = set(("obiettivo tema argomento esempio educativo informativo " +
    "preparare preparazione buon buona della delle degli della della da per con " +
    "delle delle alla anche tutto tutti ogni una uno sulla sul nella un che " +
    "senza non pubblicare questa questo testi testo contenuto simulazione " +
    "post bozza editoriale scrivere creare progetto instagram linkedin " +
    "ollama drive richiesti caratteri revisione verifica descrizione").split())

def _fold_topic(value):
    s = "".join(ch for ch in unicodedata.normalize("NFKD", str(value))
                if not unicodedata.combining(ch)).lower()
    return re.sub(r"\s+", " ", s).strip()

def validate_grounding(brief, draft):
    """Flag obvious subject drift; a passing result is NOT fact checking."""
    try:
        obj = _parse(draft)
    except (ValueError, TypeError):
        return ["invalid_json"]
    source = str(brief)
    explicit = re.search(r"(?im)^\s*QA_TOPIC_TERMS\s*:\s*(.+)$", source)
    forbidden_line = re.search(r"(?im)^\s*QA_FORBIDDEN_TERMS\s*:\s*(.+)$", source)
    required = ([_fold_topic(x) for x in explicit.group(1).split("|") if x.strip()]
                if explicit else [])
    forbidden = ([_fold_topic(x) for x in forbidden_line.group(1).split("|") if x.strip()]
                 if forbidden_line else [])
    focus = re.search(r"(?im)^\s*(?:obiettivo|tema|argomento)\s*:\s*([^\r\n]{12,500})", source)
    anchor_words = []
    if focus and not required:
        words = re.findall(r"[a-z]{5,}", _fold_topic(focus.group(1)))
        anchor_words = list(dict.fromkeys(
            word[:6] for word in words if word not in _COMMON_WORDS
        ))
    errors = []
    for channel in LIMITS:
        content = obj.get(channel)
        if not isinstance(content, str) or not content.strip():
            continue
        lower = _fold_topic(content)
        if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", lower)
               for term in forbidden):
            errors.append("forbidden_topic_" + channel)
        if required and any(
            not re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", lower)
            for term in required
        ):
            errors.append("missing_topic_" + channel)
        elif not required and len(anchor_words) >= 3:
            present = {word[:6] for word in re.findall(r"[a-z]{5,}", lower)}
            if len(present.intersection(anchor_words)) < 2:
                errors.append("weak_topic_alignment_" + channel)
    return errors

# Conservative editorial tripwires. These flag claims for review; they do not
# prove whether an event happened. Never use them to auto-approve publication.
_DATE_PATTERN = re.compile(r"\b\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{4}\b")
_TIME_PATTERN = re.compile(r"\b(?:alle|ore)\s+\d{1,2}(?:[.:]\d{2})\b")
_SCORE_PATTERN = re.compile(r"\b\d+\s+(?:vittorie|sconfitte|gol|partite)\b")
_UNSUPPORTED_ASSERTION_PATTERN = re.compile(
    r"\b(?:tutto e stato verificato|la gara e stata confermata|"
    r"ha gia ottenuto le autorizzazioni|ha verificato tutte le informazioni|"
    r"la gara si terra|la squadra[^.!?]{0,90}ha vinto)\b")
_PROMPT_LEAK_PATTERN = re.compile(
    r"\b(?:sei un editor|non pubblicare|test di editorializzazione|"
    r"restituisci solo json|questo e un test editoriale|"
    r"collaudo interno|nessun evento reale|obiettivo\s*:|"
    r"press\s*&\s*sport\s*-\s*(?:test|collaudo)|"
    r"ricorda,?\s*non descrivere|non inventare nomi|"
    r"evita ripetizioni e?\s+esempi fittizi)\b")
_URL_PATTERN = re.compile(
    r"\b(?:https?://|www\.)[^\s<>()]+|"
    r"\b[a-z][a-z0-9-]{2,}\.(?:it|com|org|net|eu|es)\b")
_PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+39[-.\s]?)?(?:0\d{1,3}[-.\s])?"
    r"\d{2,4}[-.\s]\d{3,4}[-.\s]\d{3,5}(?!\w)")



def validate_editorial_red_flags(brief, draft):
    """Conservative review flags for prompt leaks and unsupported specifics.

    Does NOT establish factual truth. Missing a flag is not approval.
    """
    try:
        obj = _parse(draft)
    except (ValueError, TypeError):
        return ["invalid_json"]
    source = _fold_topic(brief)
    simulation = any(marker in source for marker in (
        "non inventare", "nessun evento reale", "simulazione", "nessun evento",
    ))
    issues = []
    for channel in LIMITS:
        value = obj.get(channel)
        if not isinstance(value, str) or not value.strip():
            continue
        value = _fold_topic(value)
        if _PROMPT_LEAK_PATTERN.search(value):
            issues.append("prompt_leak_" + channel)
        if simulation:
            if any(match.group() not in source for match in _DATE_PATTERN.finditer(value)):
                issues.append("unsupported_date_" + channel)
            if any(match.group() not in source for match in _TIME_PATTERN.finditer(value)):
                issues.append("unsupported_time_" + channel)
            if any(match.group() not in source for match in _SCORE_PATTERN.finditer(value)):
                issues.append("unsupported_result_" + channel)
            if _UNSUPPORTED_ASSERTION_PATTERN.search(value):
                issues.append("unsupported_assertion_" + channel)
            if any(match.group().rstrip(".,;:") not in source
                   for match in _URL_PATTERN.finditer(value)):
                issues.append("unsupported_url_" + channel)
            if any(match.group() not in source
                   for match in _PHONE_PATTERN.finditer(value)):
                issues.append("unsupported_phone_" + channel)
            if re.search(
                r"\b(?:tutte? le informazioni (?:sono state|e stata) verificate|"
                r"(?:le foto|le fotografie)[^.?!]{0,120}"
                r"(?:sono state|risultano) autorizzate)\b", value
            ):
                issues.append("unsupported_verification_" + channel)
    return issues

def evaluate_draft(brief, draft):
    errors = validate_draft(draft)
    if "invalid_json" not in errors:
        errors += validate_grounding(brief, draft)
        errors += validate_editorial_red_flags(brief, draft)
    return errors


def repair_prompt(brief, draft):
    """Generate a constraint-focused prompt for a LOCAL model only."""
    obj = _parse(draft)
    errors = evaluate_draft(brief, obj)
    if not errors:
        return None
    return ("BOZZA TECNICA - NON PUBBLICARE. Correggi senza inventare fatti, "
            "nomi, date, risultati, citazioni o dati. Se i dettagli mancano, "
            "richiedi verifica umana in fact_checks. Restituisci SOLO JSON "
            "con instagram_caption tra 450 e 750 caratteri, linkedin_caption "
            "tra 650 e 1000, visual_brief, fact_checks, suggested_alt_text. "
            "Conta i caratteri, rispetta il tema del brief e non confondere " 
            "Drive/Ollama con il tema editoriale. Problemi: "
            + ", ".join(errors) + "\nBRIEF:\n" + str(brief)[:12000]
            + "\nBOZZA:\n" + json.dumps(obj, ensure_ascii=False))

def validate_then_repair(brief, draft, generate_once):
    """At most one retry via supplied Ollama callback; always human review."""
    errors = evaluate_draft(brief, draft)
    if not errors:
        return {"draft": draft, "issues": [], "retries": 0,
                "needs_human_review": True}
    try:
        instruction = repair_prompt(brief, draft)
        candidate = generate_once(instruction)
    except (ValueError, TypeError, RuntimeError):
        return {"draft": draft, "issues": errors, "retries": 0,
                "needs_human_review": True}
    return {"draft": candidate, "issues": evaluate_draft(brief, candidate),
            "retries": 1, "needs_human_review": True}
