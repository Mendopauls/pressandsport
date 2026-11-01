"""Generate a standalone, read-only editorial dashboard from queue rows.

No HTTP server, client-side API calls, secrets or publishing controls.
"""
from html import escape
from pathlib import Path

STATES = {"draft": "Bozza", "ready_for_review": "In revisione",
          "approved": "Approvato", "planned": "Pianificato",
          "cancelled": "Annullato"}

def render_dashboard(rows):
    cells = []
    for row in rows:
        key = escape(str(row.get("post_key", "")), quote=True)
        kind = escape(str(row.get("kind", "")), quote=True)
        channel = escape(str(row.get("channel", "")), quote=True)
        state = escape(STATES.get(row.get("state"), str(row.get("state", ""))), quote=True)
        planned = escape(str(row.get("planned_at") or "—"), quote=True)
        cells.append(f"<tr><td>{key}</td><td>{channel}</td><td>{kind}</td><td>{state}</td><td>{planned}</td></tr>")
    body = "\n".join(cells) if cells else '<tr><td colspan="5">Nessun contenuto nella coda</td></tr>'
    return f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Press &amp; Sport — Coda editoriale</title>
<style>
:root{{font-family:system-ui,Arial,sans-serif;color-scheme:dark}}
body{{margin:0;background:#141414;color:#f4f4f4}}
main{{max-width:1080px;margin:auto;padding:32px 18px}}
h1{{font-size:clamp(24px,4vw,38px);margin-bottom:6px}}
p{{color:#b5b5b5}}.notice{{border-left:4px solid #d53b3b;padding:12px;background:#252525;margin:20px 0}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{padding:13px 10px;border-bottom:1px solid #404040;text-align:left;overflow-wrap:anywhere}}
th{{color:#ccc}}.scroll{{overflow-x:auto}}small{{color:#999}}
</style></head><body><main><h1>PRESS &amp; SPORT</h1>
<p>Coda editoriale multicanale · Panoramica locale</p>
<div class="notice">Solo consultazione: approvazione editoriale e pubblicazione sono operazioni separate. Nessuna pubblicazione viene avviata da questa pagina.</div>
<div class="scroll"><table><thead><tr><th>Identificativo</th><th>Canale</th><th>Formato</th><th>Stato</th><th>Data pianificata</th></tr></thead>
<tbody>{body}</tbody></table></div>
<p><small>Report locale statico. Nessun collegamento diretto al database dal browser.</small></p>
</main></body></html>"""

def write_dashboard(rows, output):
    target = Path(output)
    target.write_text(render_dashboard(rows), encoding="utf-8")
    return target
