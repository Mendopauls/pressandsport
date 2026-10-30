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
      const template = await Deno.readTextFile(new URL("./portal.html", import.meta.url));
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
