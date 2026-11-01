// Static browser client. No privileged Supabase keys or publication endpoints.
// Public environment configuration must be injected by a trusted same-origin server.
const settings = Object.freeze(window.PRESSSPORT_PUBLIC_CONFIG || {});
const expectedOrigin = window.location.origin;
const message = document.getElementById("message");
const queue = document.getElementById("queue");
const panel = document.getElementById("queue-panel");
const logout = document.getElementById("logout");
let accessToken = null; // memory only; never localStorage or cookies
function notify(text, error=false) { message.textContent=text; message.className=error?"error":"ok"; }
function configured() {
  try {
    const auth = new URL(settings.supabaseUrl);
    return auth.protocol==="https:" && typeof settings.publishableKey==="string"
      && settings.publishableKey.length>0
      && typeof settings.apiPath==="string"
      && settings.apiPath==="/api/editorial/v2/queue";
  } catch { return false; }
}
async function requestJson(url,options={}) {
  const r=await fetch(url,{...options,cache:"no-store",credentials:"omit",referrerPolicy:"no-referrer"});
  const data=await r.json().catch(()=>({}));
  if(!r.ok) throw new Error("HTTP "+r.status);
  return data;
}
async function reload() {
  if(!accessToken) return;
  const data=await requestJson(settings.apiPath,{headers:{"Authorization":"Bearer "+accessToken}});
  queue.replaceChildren();
  for(const item of data.items||[]) {
    const tr=document.createElement("tr");
    for(const field of ["post_key","channel","kind","state","planned_at"]) {
      const td=document.createElement("td");td.textContent=String(item[field]??"—");tr.append(td);
    }
    queue.append(tr);
  }
  if(!queue.children.length) {const tr=document.createElement("tr"),td=document.createElement("td");
    td.colSpan=5;td.textContent="Nessun contenuto in coda";tr.append(td);queue.append(tr);}
  panel.hidden=false;logout.hidden=false;
}
document.getElementById("login").addEventListener("submit",async event=>{
  event.preventDefault();
  if(!configured()){notify("Configurazione server mancante: console non attiva.",true);return;}
  const button=document.getElementById("login-button");button.disabled=true;
  try{
    const data=await requestJson(settings.supabaseUrl.replace(/\/$/,"")+"/auth/v1/token?grant_type=password",{
      method:"POST",headers:{"apikey":settings.publishableKey,"Content-Type":"application/json"},
      body:JSON.stringify({email:document.getElementById("email").value,
                           password:document.getElementById("password").value})});
    accessToken=data.access_token;
    document.getElementById("password").value="";
    await reload();notify("Accesso verificato.");
  }catch{accessToken=null;panel.hidden=true;notify("Autenticazione o accesso non riuscito.",true);}
  finally{button.disabled=false;}
});
document.getElementById("refresh").addEventListener("click",()=>reload().catch(()=>notify("Aggiornamento non riuscito.",true)));
logout.addEventListener("click",()=>{accessToken=null;panel.hidden=true;logout.hidden=true;queue.replaceChildren();notify("Sessione locale chiusa.");});
if(!configured()) notify("Questa pagina richiede la configurazione e distribuzione del backend autenticato.",true);
