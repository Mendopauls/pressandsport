"""Small, testable prompt builder for Press & Sport local Ollama calls.

Isolated staging helper: does not call Ollama, read credentials or publish.
Only passes editorial subject matter, never raw processing instructions.
"""
import re

PLATFORMS = {
    "instagram_caption": ("Instagram", 450, 750, 600),
    "linkedin_caption": ("LinkedIn", 650, 1000, 825),
}
_CONTROL = re.compile(
    r"(?i)^(?:press\s*&\s*sport\s*[-—]|non pubblicare|nessun evento reale|"
    r"instagram\s*[:—]|linkedin\s*[:—]|produci|preparare anche|"
    r"prepara anche|revisione umana|nessuna approvazione|"
    r"nessuna pubblicazione|nessun uso|schema json|qa_|"
    r"non inventare|tutti i contenuti|la bozza|"
    r"i contenuti richiedono|il tono\s+e|il tono\s+è)"
)
_SECTION = re.compile(
    r"(?i)^(?:trattare|approfondire|contenuti da trattare|punti chiave)\s*:"
)
_HEADING = re.compile(r"(?i)^[a-z][a-z_ ]{2,35}\s*:")


def extract_editorial_context(brief):
    """Return editorial subject/points, excluding raw QA/publishing instructions.

    An empty extraction is preferable to a made-up subject.
    """
    if not isinstance(brief, str):
        raise TypeError("brief must be a string")
    lines = [re.sub(r"\s+", " ", x.strip()) for x in brief.splitlines()]
    goal = []
    points = []
    mode = None
    for line in lines:
        if not line:
            mode = None
            continue
        if _CONTROL.search(line):
            mode = None
            continue
        match = re.match(r"(?i)^(?:obiettivo|tema|argomento)\s*:\s*(.*)$", line)
        if match:
            goal = [match.group(1).strip()]
            mode = "goal"
            continue
        if _SECTION.match(line):
            mode = "points"
            continue
        if line.startswith(("- ", "• ", "* ")):
            if mode == "points":
                point = line[2:].strip()
                if point and not _CONTROL.search(point):
                    points.append(point)
            continue
        if _HEADING.match(line):
            mode = None
            continue
        if mode == "goal":
            goal.append(line)
        elif mode == "points":
            points.append(line)
    objective = " ".join(filter(None, goal)).strip(" .")
    if not objective:
        raise ValueError("No editorial objective in brief; manual review required")
    concise_points = []
    for point in points:
        if point and point not in concise_points:
            concise_points.append(point)
    context = objective + "."
    if concise_points:
        context += "\nPunti da sviluppare: " + "; ".join(concise_points[:8]) + "."
    return context[:1600]


def build_platform_request(brief, channel, model="qwen2.5:3b"):
    """Construct an Ollama /api/generate payload, without making a request."""
    if channel not in PLATFORMS:
        raise ValueError("Unsupported channel")
    label, minimum, maximum, target = PLATFORMS[channel]
    context = extract_editorial_context(brief)
    prompt = (
        "Scrivi una caption educativa in italiano per " + label + ". "
        "Tema e punti editoriali:\n" + context + "\n"
        "Offri consigli pratici; non descrivere eventi specifici come avvenuti. "
        "Non inventare nomi, date, risultati, orari, autorizzazioni o fonti verificate. "
        "Non riportare istruzioni di lavoro, etichette o intestazioni. "
        "Sviluppa il tema senza ripetizioni o esempi fittizi presentati come reali. "
        "Lunghezza tra " + str(minimum) + " e " + str(maximum) +
        " caratteri inclusi spazi; obiettivo " + str(target) + ". "
        "Rispondi con un solo oggetto JSON contenente la chiave " + channel + "."
    )
    return {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": {
            "type": "object",
            "properties": {channel: {"type": "string"}},
            "required": [channel],
            "additionalProperties": False,
        },
        "options": {"num_predict": 1100, "temperature": 0.2},
    }
