import {createClient} from "npm:@supabase/supabase-js@2.95.0";
const HTML="<!doctype html><html lang=\"it\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><meta name=\"robots\" content=\"noindex,nofollow\"><meta name=\"referrer\" content=\"no-referrer\"><title>Press & Sport Cloud V2 - Coda</title><style>:root{color-scheme:dark;font:16px system-ui,sans-serif}body{background:#111;color:#f4f4f4;margin:0}main{max-width:1000px;margin:40px auto;padding:20px}h1{letter-spacing:.03em}section{border:1px solid #444;background:#1d1d1d;border-radius:12px;padding:18px}button{background:#d3a565;border:0;border-radius:6px;padding:10px 16px;cursor:pointer;font-weight:bold}table{width:100%;border-collapse:collapse}td,th{padding:12px 8px;border-bottom:1px solid #444;text-align:left}table{display:block;overflow-x:auto}p{color:#aaa}.error{color:#ffbaba}</style></head><body><main><h1>PRESS & SPORT CLOUD V2</h1><p>Coda editoriale multicanale · Sola lettura</p><section><button id=\"refresh\" type=\"button\">Carica coda</button> <button id=\"logout\" type=\"button\">Disconnetti</button><p id=\"status\" role=\"status\">Per accedere, utilizza prima il portale amministratore Press & Sport già esistente.</p><table><thead><tr><th>Contenuto</th><th>Canale</th><th>Formato</th><th>Stato</th><th>Pianificazione</th></tr></thead><tbody id=\"rows\"></tbody></table></section><p>Nessuna pubblicazione può essere avviata da questa pagina.</p></main><script type=\"module\" nonce=\"__NONCE__\">import{createClient}from \"https://esm.sh/@supabase/supabase-js@2.95.0\";const status=document.getElementById(\"status\"),rows=document.getElementById(\"rows\");const config=await fetch(\"?mode=config\",{cache:\"no-store\"}).then(r=>r.json());const client=createClient(config.supabase_url,config.publishable_key,{auth:{storageKey:\"presssport-admin-session\",detectSessionInUrl:true,persistSession:true,autoRefreshToken:true}});async function load(){rows.replaceChildren();const{data:{session}}=await client.auth.getSession();if(!session){status.textContent=\"Nessuna sessione. Accedi prima dal portale Press & Sport Cloud.\";return;}try{const resp=await fetch(\"?mode=queue\",{headers:{\"Authorization\":\"Bearer \"+session.access_token},cache:\"no-store\"});if(!resp.ok)throw Error(\"Accesso non autorizzato (\"+resp.status+\")\");const payload=await resp.json();for(const item of payload.items||[]){const tr=document.createElement(\"tr\");for(const k of [\"post_key\",\"channel\",\"kind\",\"state\",\"planned_at\"]){const td=document.createElement(\"td\");td.textContent=item[k]??\"—\";tr.append(td)}rows.append(tr)}status.textContent=\"Contenuti in coda: \"+(payload.items||[]).length+\" · Pubblicazione disabilitata.\"}catch(e){status.textContent=e.message;status.className=\"error\"}}document.getElementById(\"refresh\").addEventListener(\"click\",load);document.getElementById(\"logout\").addEventListener(\"click\",async()=>{await client.auth.signOut();rows.replaceChildren();status.textContent=\"Sessione chiusa.\"});await load();</script></body></html>";
function json(data:unknown,status=200){return new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}})}
Deno.serve(async req=>{
 const u=new URL(req.url);
 if(req.method!=="GET")return json({error:"method_not_allowed"},405);
 const url=Deno.env.get("SUPABASE_URL")||"", anon=Deno.env.get("SUPABASE_ANON_KEY")||"";
 if(!url||!anon)return json({error:"service_unavailable"},503);
 if(u.searchParams.get("mode")==="config")return json({supabase_url:url,publishable_key:anon});
 if(u.searchParams.get("mode")!=="queue"){
  const nonce=crypto.randomUUID().replaceAll("-","");
  return new Response(HTML.replaceAll("__NONCE__",nonce),{headers:{
   "Content-Type":"text/html; charset=utf-8","Cache-Control":"no-store","X-Frame-Options":"DENY",
   "Referrer-Policy":"no-referrer","X-Content-Type-Options":"nosniff",
   "Content-Security-Policy":"default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; style-src 'unsafe-inline'; script-src 'nonce-"+nonce+"' https://esm.sh; connect-src 'self' "+new URL(url).origin
  }});
 }
 const authorization=req.headers.get("Authorization")||"";
 if(!authorization.startsWith("Bearer ")||authorization.length>8200)return json({error:"unauthorized"},401);
 const token=authorization.slice(7),service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
 if(!service)return json({error:"service_unavailable"},503);
 try{
  const auth=createClient(url,anon,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data:{user},error}=await auth.auth.getUser(token);
  if(error||!user||!user.email_confirmed_at)return json({error:"unauthorized"},401);
  const admin=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data,error:dbError}=await admin.rpc("presssport_admin_v2_queue",{p_actor:user.id});
  if(dbError)return json({error:"forbidden"},403);
  return json(data);
 }catch{return json({error:"service_unavailable"},503)}
});
