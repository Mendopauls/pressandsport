import {createClient} from "npm:@supabase/supabase-js@2.95.0";
const cors={"Access-Control-Allow-Origin":"https://pressandsport.it","Access-Control-Allow-Methods":"POST,OPTIONS","Access-Control-Allow-Headers":"authorization,content-type","Content-Type":"application/json","Cache-Control":"no-store"};
const respond=(v:unknown,s=200)=>new Response(JSON.stringify(v),{status:s,headers:cors});
Deno.serve(async(req)=>{
 try{
  if(req.headers.get("Origin")&&req.headers.get("Origin")!=="https://pressandsport.it")return respond({error:"origin_denied"},403);
  if(req.method==="OPTIONS")return new Response(null,{status:204,headers:cors});
  if(req.method!=="POST")return respond({error:"method_not_allowed"},405);
  // Zero-extra-cost policy: paid AI providers must never be called by this endpoint.
  return respond({error:"paid_ai_disabled_by_zero_cost_policy",enabled:false,publication:false},503);
  const key=Deno.env.get("PRESSSPORT_CLOUD_AI_API_KEY");
  if(Deno.env.get("PRESSSPORT_CLOUD_AI_ENABLED")!=="true"||!key)return respond({error:"cloud_ai_not_configured",enabled:false},503);
  const url=Deno.env.get("SUPABASE_URL")||"",service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"",anon=Deno.env.get("SUPABASE_ANON_KEY")||"";
  if(!url||!service||!anon)return respond({error:"service_not_configured"},503);
  const auth=req.headers.get("Authorization")||"";
  if(!auth.startsWith("Bearer "))return respond({error:"unauthorized"},401);
  const body=await req.json();
  const slug=body?.project_slug;
  if(typeof slug!=="string"||!["ninaart","ussa","paolo-savio"].includes(slug))return respond({error:"project_not_enabled"},409);
  const userClient=createClient(url,anon,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data:{user},error:authError}=await userClient.auth.getUser(auth.slice(7));
  if(authError||!user?.email_confirmed_at)return respond({error:"unauthorized"},401);
  const admin=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data:claimed,error:claimError}=await admin.rpc("presssport_admin_project_ai_claim",{p_actor:user.id,p_slug:slug});
  if(claimError)return respond({error:"claim_denied"},403);
  if(!claimed)return respond({job:null});
  let draft="";
  let success=false;
  try{
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),45000);
    try{
      const response=await fetch("https://api.openai.com/v1/chat/completions",{
        method:"POST",headers:{"Authorization":"Bearer "+key,"Content-Type":"application/json"},
        body:JSON.stringify({model:Deno.env.get("PRESSSPORT_CLOUD_AI_MODEL")||"gpt-4.1-mini",temperature:0.5,max_tokens:900,
        messages:[{role:"system",content:"Sei un assistente editoriale. Scrivi solo una bozza da revisionare. Non inventare dati, citazioni, eventi, autorizzazioni, pubblicazioni o fonti. Rispondi in italiano. Se non ci sono dati sufficienti, indica le verifiche necessarie. Non creare né autorizzare pubblicazioni."},
        {role:"user",content:JSON.stringify({project:claimed.project_name,profile:claimed.editorial_profile,brief:claimed.brief})}]}),signal:controller.signal});
      if(!response.ok)throw Error("ai_provider_rejected");
      const result=await response.json();
      draft=String(result.choices?.[0]?.message?.content||"").trim();
      success=draft.length>0&&draft.length<=30000;
    }finally{clearTimeout(timeout)}
  }catch{draft="Generazione cloud non riuscita. Ripristino manuale necessario."}
  const {data:finished,error:finishError}=await admin.rpc("presssport_admin_project_ai_finish",{p_actor:user.id,p_id:claimed.id,p_text:draft,p_success:success});
  if(finishError||!finished)return respond({error:"draft_save_failed"},500);
  return respond({job_key:claimed.key,project_slug:slug,state:success?"draft_for_review":"failed",publication:false});
 }catch{return respond({error:"invalid_request"},400)}
});