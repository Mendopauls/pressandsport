/**
 * Press & Sport Cloud — authenticated editorial administration.
 *
 * GET serves the portal, GET ?mode=config serves a public publishable key.
 * POST ?mode=api ALWAYS verifies a real Supabase Auth user and the exact
 * confirmed admin email, then invokes a service-role-only guarded SQL RPC.
 * NO Meta credentials, publication triggers or publication endpoints exist.
 *
 * verify_jwt=false is intentional because the login page must be public;
 * the POST route verifies the bearer token using auth.getUser(token).
 */
import { createClient } from "npm:@supabase/supabase-js@2.95.0";

const ADMIN_EMAIL = "info@paolosavio.eu";
const MAX_BODY_BYTES = 32000;
const PORTAL_HTML = "<!doctype html>\n<html lang=\"it\">\n<head>\n<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n<meta name=\"robots\" content=\"noindex,nofollow\"><title>Press & Sport Cloud — Redazione</title>\n<style>\n:root{color-scheme:dark;font-family:Inter,system-ui,Arial,sans-serif;background:#0c1321;color:#e9eff7}\n*{box-sizing:border-box}body{margin:0}main{max-width:1060px;margin:auto;padding:28px 18px 70px}\nh1{font-size:clamp(1.65rem,4vw,2.6rem);margin:8px 0}h2{margin:0 0 14px;font-size:1.18rem}\np{line-height:1.6;color:#aebbd0}.top{display:flex;align-items:center;justify-content:space-between;gap:12px}\n.brand{font-weight:800;letter-spacing:.18em;color:#e7b778;font-size:.77rem}\n.card{border:1px solid #304059;background:#172338;border-radius:18px;padding:24px;margin-top:20px;box-shadow:0 12px 30px #0002}\nlabel{display:block;font-weight:600;font-size:.85rem;color:#cdd8e7;margin:15px 0 6px}\ninput,textarea{width:100%;background:#0f1b2d;color:#fff;border:1px solid #41516a;border-radius:10px;padding:13px;font:inherit;outline-offset:3px}\ntextarea{min-height:126px;resize:vertical}button{background:#d8a96a;border:0;border-radius:10px;color:#101723;padding:11px 17px;font:inherit;font-weight:700;cursor:pointer;margin:12px 8px 0 0}\nbutton.secondary{background:#2b3a51;color:#e8f0ff}button:disabled{opacity:.5;cursor:not-allowed}\nsmall{color:#9caac0}#notice{min-height:22px;margin-top:15px;color:#e7b778;white-space:pre-wrap}\n.toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}\n.item{padding:16px 0;border-top:1px solid #314158}.item h3{margin:0 0 6px;font-size:1rem;overflow-wrap:anywhere}\n.meta{font-size:.82rem;color:#afbed1;overflow-wrap:anywhere}.pill{display:inline-block;background:#32445e;border-radius:18px;padding:4px 10px;font-size:.75rem;font-weight:700}\n.two{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:720px){.two{grid-template-columns:1fr}}\n.hide{display:none!important}.warning{border-left:3px solid #d8a96a;padding-left:12px}.actions{display:flex;flex-wrap:wrap}\n</style>\n</head>\n<body><main>\n<div class=\"top\"><div class=\"brand\">PRESS & SPORT · CLOUD</div><button id=\"logout\" class=\"secondary hide\" type=\"button\">Esci</button></div>\n<h1>Redazione e programmazione</h1>\n<p>Gestione riservata dei contenuti Instagram. La pianificazione editoriale <strong>non pubblica automaticamente</strong>: ogni pubblicazione richiede un'autorizzazione separata.</p>\n<section id=\"login\" class=\"card\">\n<h2>Accesso amministratore</h2>\n<p>Riceverai un link di accesso all'indirizzo autorizzato. Non servono password condivise.</p>\n<label for=\"email\">Indirizzo amministratore</label>\n<input id=\"email\" type=\"email\" value=\"info@paolosavio.eu\" readonly autocomplete=\"username\">\n<button id=\"sendlink\" type=\"button\">Invia link di accesso</button>\n<p><small>Il link deve reindirizzare a questa pagina; il dominio va autorizzato nelle impostazioni Supabase Auth.</small></p>\n</section>\n<section id=\"console\" class=\"hide\">\n<div class=\"card toolbar\"><div><h2>Area riservata</h2><small id=\"identity\"></small></div>\n<button id=\"refresh\" class=\"secondary\">Aggiorna</button></div>\n<div class=\"two\">\n<section class=\"card\"><h2>Nuova bozza</h2>\n<label for=\"postKey\">Codice contenuto (slug univoco)</label>\n<input id=\"postKey\" placeholder=\"presssport-post-2026-11-03\" maxlength=\"80\">\n<label for=\"caption\">Caption Instagram</label><textarea id=\"caption\" maxlength=\"2200\" placeholder=\"Scrivi la caption...\"></textarea>\n<label for=\"urls\">URL pubblici delle immagini JPEG (da 2 a 10; uno per riga)</label>\n<textarea id=\"urls\" placeholder=\"https://pressandsport.it/.../slide-01.jpg\"></textarea>\n<button id=\"create\" type=\"button\">Salva bozza</button>\n</section>\n<section class=\"card\"><h2>Contenuti in lavorazione</h2><div id=\"items\"><p>Nessuna bozza caricata.</p></div></section>\n</div>\n<section class=\"card warning\"><h2>Pubblicazione protetta</h2><p>Le bozze e le date pianificate sono soltanto editoriali. Il pulsante di pubblicazione non è disponibile in questa versione; il carosello già pubblicato non viene riproposto.</p></section>\n</section>\n<div id=\"notice\" role=\"status\" aria-live=\"polite\"></div>\n</main>\n<script nonce=\"__CSP_NONCE__\" type=\"module\">\nimport { createClient } from \"https://esm.sh/@supabase/supabase-js@2.95.0\";\nconst $=id=>document.getElementById(id), notice=$(\"notice\");\nconst endpoint=location.pathname;\nconst show=(msg,bad=false)=>{notice.textContent=msg;notice.style.color=bad?\"#ffb4af\":\"#e7b778\"};\nlet client=null, session=null, busy=false;\nconst config=await fetch(endpoint+\"?mode=config\",{cache:\"no-store\"}).then(r=>{if(!r.ok)throw Error(\"Configurazione non disponibile\");return r.json()});\nclient=createClient(config.supabase_url,config.publishable_key,{auth:{storageKey:\"presssport-admin-session\",detectSessionInUrl:true,persistSession:true,autoRefreshToken:true}});\nfunction toggle(yes){$(\"login\").classList.toggle(\"hide\",yes);$(\"console\").classList.toggle(\"hide\",!yes);$(\"logout\").classList.toggle(\"hide\",!yes)}\nasync function api(action,payload={},post_key=null){\n  const {data:{session:s}}=await client.auth.getSession();\n  if(!s?.access_token)throw Error(\"Sessione scaduta: accedi di nuovo\");\n  const result=await fetch(endpoint+\"?mode=api\",{method:\"POST\",\n    headers:{\"Content-Type\":\"application/json\",\"Authorization\":\"Bearer \"+s.access_token},\n    body:JSON.stringify({action,payload,post_key}),cache:\"no-store\"});\n  const data=await result.json();\n  if(!result.ok)throw Error(data.error||\"Errore del servizio\");\n  return data;\n}\nconst states={draft:\"Bozza\",ready_for_review:\"Da approvare\",approved:\"Approvato\",planned:\"Pianificato\",cancelled:\"Annullato\"};\nfunction btn(label,callback){const e=document.createElement(\"button\");e.className=\"secondary\";e.textContent=label;e.addEventListener(\"click\",async()=>{if(busy)return;busy=true;e.disabled=true;try{await callback();await load()}catch(err){show(err.message,true)}finally{busy=false;e.disabled=false}});return e}\nfunction render(items){\n  const root=$(\"items\");root.replaceChildren();\n  if(!items?.length){const e=document.createElement(\"p\");e.textContent=\"Nessuna bozza in coda.\";root.append(e);return}\n  for(const p of items){\n    const wrap=document.createElement(\"div\");wrap.className=\"item\";\n    const title=document.createElement(\"h3\");title.textContent=p.post_key;wrap.append(title);\n    const badge=document.createElement(\"span\");badge.className=\"pill\";badge.textContent=states[p.editorial_state]||p.editorial_state;wrap.append(badge);\n    const desc=document.createElement(\"p\");desc.textContent=p.caption;wrap.append(desc);\n    const meta=document.createElement(\"div\");meta.className=\"meta\";meta.textContent=p.image_urls.length+\" immagini · \"+(p.planned_at?new Date(p.planned_at).toLocaleString(\"it-IT\"):\"nessuna data\");wrap.append(meta);\n    const actions=document.createElement(\"div\");actions.className=\"actions\";\n    const trans=async to_state=>api(\"transition\",{from_state:p.editorial_state,to_state},p.post_key);\n    if(p.editorial_state===\"draft\")actions.append(btn(\"Invia in revisione\",()=>trans(\"ready_for_review\")));\n    if(p.editorial_state===\"ready_for_review\"){\n      actions.append(btn(\"Approva contenuto\",()=>trans(\"approved\")));\n      actions.append(btn(\"Ritorna a bozza\",()=>trans(\"draft\")));\n    }\n    if(p.editorial_state===\"approved\")actions.append(btn(\"Pianifica\",async()=>{\n      const value=prompt(\"Data e ora italiana (formato AAAA-MM-GG HH:MM). È solo una pianificazione editoriale.\");\n      if(value===null)return;\n      const match=/^(\\d{4})-(\\d{2})-(\\d{2}) (\\d{2}):(\\d{2})$/.exec(value);\n      if(!match)throw Error(\"Formato data non valido\");\n      const dt=new Date(match[1]+\"-\"+match[2]+\"-\"+match[3]+\"T\"+match[4]+\":\"+match[5]+\":00\");\n      if(!Number.isFinite(dt.getTime()))throw Error(\"Data non valida\");\n      return api(\"transition\",{from_state:\"approved\",to_state:\"planned\",planned_at:dt.toISOString()},p.post_key);\n    }));\n    if(p.editorial_state===\"planned\")actions.append(btn(\"Rimuovi data\",()=>trans(\"approved\")));\n    if(![\"cancelled\"].includes(p.editorial_state))actions.append(btn(\"Annulla contenuto\",()=>{\n      if(!confirm(\"Annullare questa bozza?\"))return;\n      return trans(\"cancelled\");\n    }));\n    wrap.append(actions);root.append(wrap);\n  }\n}\nasync function load(){\n  const d=await api(\"list\");$(\"identity\").textContent=d.admin_email;\n  render(d.items);toggle(true);show(\"Area editoriale aggiornata. La pubblicazione è disattivata.\");\n}\nasync function check(){\n  const {data:{session:s}}=await client.auth.getSession();session=s;\n  if(!s){toggle(false);return}\n  try{await load()}catch(e){toggle(false);show(e.message,true)}\n}\n$(\"sendlink\").addEventListener(\"click\",async()=>{\n  $(\"sendlink\").disabled=true;try{\n    const {error}=await client.auth.signInWithOtp({\n      email:config.admin_email,\n      options:{emailRedirectTo:location.origin+location.pathname,shouldCreateUser:true}\n    });\n    if(error)throw error;\n    show(\"Link richiesto. Controlla la casella \"+config.admin_email+\".\");\n  }catch(e){show(e.message,true)}finally{$(\"sendlink\").disabled=false}\n});\n$(\"logout\").addEventListener(\"click\",async()=>{await client.auth.signOut();session=null;toggle(false);show(\"Accesso terminato.\")});\n$(\"refresh\").addEventListener(\"click\",()=>load().catch(e=>show(e.message,true)));\n$(\"create\").addEventListener(\"click\",async()=>{\n  $(\"create\").disabled=true;try{\n    const post_key=$(\"postKey\").value.trim(),caption=$(\"caption\").value.trim(),\n          image_urls=$(\"urls\").value.split(/\\r?\\n/).map(x=>x.trim()).filter(Boolean);\n    await api(\"create\",{post_key,caption,image_urls,instagram_account_id:\"17841425937268080\"});\n    $(\"postKey\").value=\"\";$(\"caption\").value=\"\";$(\"urls\").value=\"\";\n    await load();show(\"Bozza salvata. Pubblicazione NON autorizzata.\");\n  }catch(e){show(e.message,true)}finally{$(\"create\").disabled=false}\n});\nclient.auth.onAuthStateChange((event)=>{if(event===\"SIGNED_OUT\")toggle(false)});\nawait check();\n</script></body></html>\n";

const jsonHeaders = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "X-Frame-Options": "DENY",
};

function respond(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: jsonHeaders });
}

Deno.serve(async (req: Request): Promise<Response> => {
  try {
    const url = new URL(req.url);
    const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
    const anonKey = Deno.env.get("SUPABASE_ANON_KEY") || "";
    if (!supabaseUrl || !anonKey) {
      return respond({ error: "Configurazione di autenticazione non disponibile" }, 503);
    }
    if (req.method === "GET" && url.searchParams.get("mode") === "config") {
      // SUPABASE_ANON_KEY is intentionally a public, browser-safe key.
      return respond({ supabase_url: supabaseUrl, publishable_key: anonKey,
                       admin_email: ADMIN_EMAIL });
    }
    if (req.method === "GET") {
      const nonce = crypto.randomUUID().replaceAll("-", "");
      const template = PORTAL_HTML;
      return new Response(template.replaceAll("__CSP_NONCE__", nonce), {
        status: 200,
        headers: {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "no-store",
          "Referrer-Policy": "no-referrer",
          "X-Content-Type-Options": "nosniff",
          "X-Frame-Options": "DENY",
          "Content-Security-Policy":
            "default-src 'none'; base-uri 'none'; form-action 'none'; " +
            "frame-ancestors 'none'; object-src 'none'; img-src 'self' data:; " +
            "style-src 'unsafe-inline'; " +
            "script-src 'nonce-" + nonce + "' https://esm.sh; " +
            "connect-src 'self' " + supabaseUrl,
        },
      });
    }
    if (req.method !== "POST" || url.searchParams.get("mode") !== "api") {
      return respond({ error: "Operazione non consentita" }, 405);
    }
    const allowedOrigin = new URL(supabaseUrl).origin;
    const origin = req.headers.get("Origin");
    if (origin && origin !== allowedOrigin) {
      return respond({ error: "Origine non consentita" }, 403);
    }
    const authorization = req.headers.get("Authorization") || "";
    if (!authorization.startsWith("Bearer ")) {
      return respond({ error: "Sessione autenticata necessaria" }, 401);
    }
    const bearer = authorization.substring(7);
    if (bearer.length < 16 || bearer.length > 8192) {
      return respond({ error: "Token non valido" }, 401);
    }
    const anonClient = createClient(supabaseUrl, anonKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const { data: userData, error: userError } =
      await anonClient.auth.getUser(bearer);
    const user = userData?.user;
    if (userError || !user || user.email?.toLowerCase() !== ADMIN_EMAIL ||
        !user.email_confirmed_at) {
      return respond({ error: "Amministratore verificato richiesto" }, 403);
    }
    const contentLength = req.headers.get("content-length");
    if (contentLength && Number(contentLength) > MAX_BODY_BYTES) {
      return respond({ error: "Richiesta troppo grande" }, 413);
    }
    const raw = await req.text();
    if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) {
      return respond({ error: "Richiesta troppo grande" }, 413);
    }
    let body: { action?: unknown; payload?: unknown; post_key?: unknown };
    try { body = JSON.parse(raw); }
    catch { return respond({ error: "JSON non valido" }, 400); }
    if (!body || typeof body !== "object" ||
        !["list", "create", "transition"].includes(String(body.action))) {
      return respond({ error: "Azione editoriale non valida" }, 400);
    }
    const action = String(body.action);
    const payload = body.payload && typeof body.payload === "object" &&
        !Array.isArray(body.payload) ? body.payload : {};
    const postKey = typeof body.post_key === "string" ? body.post_key : null;
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
    if (!serviceKey) return respond({ error: "Servizio amministrativo non configurato" }, 503);
    const adminClient = createClient(supabaseUrl, serviceKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const { data, error } = await adminClient.rpc("presssport_admin_queue", {
      p_actor: user.id,
      p_action: action,
      p_post_key: postKey,
      p_payload: payload,
    });
    if (error) {
      // Errors from this narrow RPC contain no personal data or credentials.
      return respond({ error: error.message || "Operazione non consentita" }, 422);
    }
    return respond(data);
  } catch {
    return respond({ error: "Errore del servizio; nessuna pubblicazione eseguita" }, 500);
  }
});
