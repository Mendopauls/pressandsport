import {createClient} from "npm:@supabase/supabase-js@2.95.0";
const headers={"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};
const reply=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers});
const project=Deno.env.get("SUPABASE_URL")||"";
const anon=Deno.env.get("SUPABASE_ANON_KEY")||"";
const key=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
const client=()=>createClient(project,key,{auth:{persistSession:false,autoRefreshToken:false}});
Deno.serve(async req=>{
 try{
  if(req.method!=="POST")return reply({error:"method_not_allowed"},405);
  if(!project||!anon||!key)return reply({error:"service_unavailable"},503);
  const url=new URL(req.url),mode=url.searchParams.get("mode");
  if(!["enqueue","claim","complete"].includes(mode||""))return reply({error:"not_found"},404);
  const raw=await req.text();
  if(raw.length>40000)return reply({error:"payload_too_large"},413);
  const data=JSON.parse(raw);
  if(!data||typeof data!=="object")return reply({error:"invalid_payload"},400);
  const admin=client();
  if(mode==="enqueue"){
    const auth=req.headers.get("Authorization")||"";
    if(!auth.startsWith("Bearer "))return reply({error:"unauthorized"},401);
    const userClient=createClient(project,anon,{auth:{persistSession:false,autoRefreshToken:false}});
    const {data:{user},error}=await userClient.auth.getUser(auth.slice(7));
    if(error||!user?.email_confirmed_at)return reply({error:"unauthorized"},401);
    const {data:allow,error:checkError}=await admin.rpc("presssport_admin_v2_queue",{p_actor:user.id});
    if(checkError||!allow)return reply({error:"forbidden"},403);
    if(typeof data.job_key!=="string"||! /^[a-zA-Z0-9_-]{3,100}$/.test(data.job_key)||
       typeof data.brief!=="string"||!data.brief.trim()||data.brief.length>12000)
       return reply({error:"invalid_job"},400);
    const {error:insertError}=await admin.rpc("presssport_worker_enqueue",{p_key:data.job_key,p_brief:data.brief});
    if(insertError)return reply({error:"enqueue_failed"},500);
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