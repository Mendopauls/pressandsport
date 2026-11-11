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

def evaluate_draft(brief, draft):
    errors = validate_draft(draft)
    if "invalid_json" not in errors:
        errors += validate_grounding(brief, draft)
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
