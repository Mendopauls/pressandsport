import {createClient} from "npm:@supabase/supabase-js@2.95.0";
const headers={"Access-Control-Allow-Origin":"https://pressandsport.it","Access-Control-Allow-Methods":"POST, OPTIONS","Access-Control-Allow-Headers":"authorization, content-type","Vary":"Origin","Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};
const reply=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers});
const project=Deno.env.get("SUPABASE_URL")||"";
const anon=Deno.env.get("SUPABASE_ANON_KEY")||"";
const key=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
const client=()=>createClient(project,key,{auth:{persistSession:false,autoRefreshToken:false}});
Deno.serve(async req=>{
 try{
  if(req.headers.get("Origin") && req.headers.get("Origin")!=="https://pressandsport.it")return reply({error:"origin_not_allowed"},403);
  if(req.method==="OPTIONS")return new Response(null,{status:204,headers});
  if(req.method!=="POST")return reply({error:"method_not_allowed"},405);
  if(!project||!anon||!key)return reply({error:"service_unavailable"},503);
  const url=new URL(req.url),mode=url.searchParams.get("mode");
  if(!["enqueue","list","projects","project-list","project-enqueue","asset","revision","claim","complete"].includes(mode||""))return reply({error:"not_found"},404);
  const raw=await req.text();
  if(raw.length>40000)return reply({error:"payload_too_large"},413);
  const data=JSON.parse(raw);
  if(!data||typeof data!=="object")return reply({error:"invalid_payload"},400);
  const admin=client();
  if(mode==="enqueue"||mode==="list"||mode==="projects"||mode==="project-list"||mode==="project-enqueue"||mode==="asset"||mode==="revision"){
    const auth=req.headers.get("Authorization")||"";
    if(!auth.startsWith("Bearer "))return reply({error:"unauthorized"},401);
    const userClient=createClient(project,anon,{auth:{persistSession:false,autoRefreshToken:false}});
    const {data:{user},error}=await userClient.auth.getUser(auth.slice(7));
    if(error||!user?.email_confirmed_at)return reply({error:"unauthorized"},401);
    const {data:allow,error:checkError}=await admin.rpc("presssport_admin_v2_queue",{p_actor:user.id});
    if(checkError||!allow)return reply({error:"forbidden"},403);
    if(mode==="projects"){
      const {data:projects,error:projectsError}=await admin.rpc("presssport_admin_content_projects",{p_actor:user.id});
      if(projectsError)return reply({error:"projects_forbidden"},403);
      return reply({items:projects});
    }
    if(mode==="project-list"||mode==="project-enqueue"){
      if(typeof data.project_slug!=="string"||data.project_slug==="press-sport")return reply({error:"invalid_project"},400);
      if(mode==="project-list"){
        const {data:items,error:e}=await admin.rpc("presssport_admin_project_queue",{p_actor:user.id,p_slug:data.project_slug});
        if(e)return reply({error:"project_queue_unavailable"},400);
        return reply({items});
      }
      const {data:inserted,error:e}=await admin.rpc("presssport_admin_project_enqueue",{p_actor:user.id,p_slug:data.project_slug,p_key:data.job_key,p_brief:data.brief});
      if(e)return reply({error:"project_enqueue_failed"},400);
      if(!inserted)return reply({error:"invalid_or_duplicate_project_job"},409);
      return reply({accepted:true,project_slug:data.project_slug,state:"pending_cloud_ai"},201);
    }
    if(mode!=="projects"){
      const selected=data.project_slug??"press-sport";
      if(selected!=="press-sport")return reply({error:"project_not_enabled"},409);
    }
    if(mode==="revision"){
      if(typeof data.job_key!=="string"||typeof data.content!=="object"||!data.content)return reply({error:"invalid_revision"},400);
      const {data:version,error:revisionError}=await admin.rpc("presssport_editorial_save_revision",{p_actor:user.id,p_key:data.job_key,p_content:data.content});
      if(revisionError)return reply({error:"revision_rejected"},400);
      return reply({saved:true,revision:version});
    }
    if(mode==="asset"){
      const {data:ok,error:assetError}=await admin.rpc("presssport_editorial_asset_assign",{p_actor:user.id,p_key:data.job_key,p_file_id:data.file_id,p_name:data.name});
      if(assetError||!ok)return reply({error:"asset_rejected"},400);
      return reply({assigned:true,verification_state:"pending"});
    }
    if(mode==="list"){
      const {data:jobs,error:listError}=await admin.rpc("presssport_admin_ollama_jobs",{p_actor:user.id});
      if(listError)return reply({error:"list_forbidden"},403);
      return reply({items:jobs});
    }
    if(typeof data.job_key!=="string"||! /^[a-zA-Z0-9_-]{3,100}$/.test(data.job_key)||
       typeof data.brief!=="string"||!data.brief.trim()||data.brief.length>12000)
       return reply({error:"invalid_job"},400);
    const {data:inserted,error:insertError}=await admin.rpc("presssport_worker_enqueue",{p_key:data.job_key,p_brief:data.brief});
    if(insertError)return reply({error:"enqueue_failed"},500);
    if(inserted!==true)return reply({error:"job_exists"},409);
    return reply({accepted:true,job_key:data.job_key},201);
  }
  const secret=Deno.env.get("PRESSSPORT_WORKER_SECRET")||"";
  const received=req.headers.get("X-Worker-Secret")||"";
  if(!secret||secret.length<32)return reply({error:"worker_not_configured"},503);
  const enc=new TextEncoder();
  const keyDigest=await crypto.subtle.digest("SHA-256",enc.encode(secret));
  const gotDigest=await crypto.subtle.digest("SHA-256",enc.encode(received));
  const a=new Uint8Array(keyDigest),b=new Uint8Array(gotDigest);
  let mismatch=0;for(let i=0;i<a.length;i++)mismatch|=a[i]^b[i];
  if(mismatch)return reply({error:"unauthorized"},401);
  const rest=admin;
  if(mode==="claim"){
    const token=crypto.randomUUID()+crypto.randomUUID();
    const digest=await crypto.subtle.digest("SHA-256",enc.encode(token));
    const hash=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,"0")).join("");
    const {data:rows,error}=await rest.rpc("presssport_worker_claim",{p_lease_hash:hash});
    if(error)return reply({error:"claim_failed"},500);
    if(!rows?.length)return reply({job:null});
    return reply({job:{...rows[0],lease_token:token}});
  }
  if(typeof data.job_key!=="string"||typeof data.lease_token!=="string"||
     typeof data.text!=="string"||!data.text.trim()||data.text.length>30000||
     typeof data.model!=="string"||data.model.length>100)
     return reply({error:"invalid_completion"},400);
  const digest=await crypto.subtle.digest("SHA-256",enc.encode(data.lease_token));
  const hash=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,"0")).join("");
  const {data:done,error}=await rest.rpc("presssport_worker_finish",{p_key:data.job_key,p_hash:hash,p_text:data.text,p_model:data.model});
  if(error)return reply({error:"completion_failed"},500);
  return reply({completed:done},done?200:409);
 }catch{return reply({error:"bad_request"},400)}
});