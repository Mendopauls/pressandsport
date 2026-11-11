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

def repair_prompt(brief, draft):
    """Generate a constraint-focused prompt for a LOCAL model only."""
    obj = _parse(draft)
    errors = validate_draft(obj)
    if not errors:
        return None
    return ("BOZZA TECNICA - NON PUBBLICARE. Correggi senza inventare fatti, "
            "nomi, date, risultati, citazioni o dati. Se i dettagli mancano, "
            "richiedi verifica umana in fact_checks. Restituisci SOLO JSON "
            "con instagram_caption tra 450 e 750 caratteri, linkedin_caption "
            "tra 650 e 1000, visual_brief, fact_checks, suggested_alt_text. "
            "Conta i caratteri prima di rispondere. Problemi: "
            + ", ".join(errors) + "\nBRIEF:\n" + str(brief)[:12000]
            + "\nBOZZA:\n" + json.dumps(obj, ensure_ascii=False))

def validate_then_repair(brief, draft, generate_once):
    """At most one retry via supplied Ollama callback; always human review."""
    errors = validate_draft(draft)
    if not errors:
        return {"draft": draft, "issues": [], "retries": 0,
                "needs_human_review": True}
    try:
        instruction = repair_prompt(brief, draft)
        candidate = generate_once(instruction)
    except (ValueError, TypeError, RuntimeError):
        return {"draft": draft, "issues": errors, "retries": 0,
                "needs_human_review": True}
    return {"draft": candidate, "issues": validate_draft(candidate),
            "retries": 1, "needs_human_review": True}
