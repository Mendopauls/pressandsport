import {createClient} from "npm:@supabase/supabase-js@2.95.0";
// Staging: separate server-to-server ingest. No social publishing capability.
const response=(body:unknown,status=200)=>new Response(JSON.stringify(body),{
  status,headers:{"content-type":"application/json","cache-control":"no-store",
    "x-content-type-options":"nosniff"}
});
const idPattern=/^[A-Za-z0-9_-]{15,80}$/;
Deno.serve(async request=>{
  try {
    if(request.method!=="POST")return response({error:"method_not_allowed"},405);
    if(request.headers.has("Origin"))return response({error:"browser_not_allowed"},403);
    const url=Deno.env.get("SUPABASE_URL")||"";
    const serviceKey=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
    const secret=Deno.env.get("PRESSSPORT_DRIVE_INGEST_SECRET")||"";
    if(!url||!serviceKey||secret.length<32)return response({error:"not_configured"},503);
    const received=request.headers.get("X-Drive-Ingest-Secret")||"";
    const enc=new TextEncoder();
    const want=new Uint8Array(await crypto.subtle.digest("SHA-256",enc.encode(secret)));
    const got=new Uint8Array(await crypto.subtle.digest("SHA-256",enc.encode(received)));
    let delta=0;
    for(let i=0;i<want.length;i++)delta|=want[i]^got[i];
    if(delta!==0)return response({error:"unauthorized"},401);
    const raw=await request.text();
    if(raw.length>16000)return response({error:"too_large"},413);
    let body:Record<string,unknown>;
    try { body=JSON.parse(raw); } catch { return response({error:"bad_json"},400); }
    if(!body||Array.isArray(body)||typeof body!=="object")return response({error:"invalid_payload"},400);
    const fileId=body.source_file_id, jobKey=body.job_key, brief=body.brief;
    if(body.project_slug!=="press-sport"||typeof fileId!=="string"||!idPattern.test(fileId)||
       typeof jobKey!=="string"||jobKey!=="ps-drive-"+fileId||jobKey.length>100||
       typeof brief!=="string"||brief.length<20||brief.length>12000||
       !brief.includes("NON PUBBLICARE"))return response({error:"invalid_brief"},400);
    const admin=createClient(url,serviceKey,{auth:{persistSession:false,autoRefreshToken:false}});
    const {data:inserted,error}=await admin.rpc("presssport_worker_enqueue",{
      p_key:jobKey,p_brief:brief
    });
    if(error)return response({error:"enqueue_failed"},500);
    if(inserted!==true)return response({existing:true,publication:false},409);
    return response({accepted:true,state:"pending",publication:false},201);
  } catch {
    return response({error:"request_failed"},400);
  }
});
