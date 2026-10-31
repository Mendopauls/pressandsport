import { createClient } from "npm:@supabase/supabase-js@2.95.0";
const SITE="https://pressandsport.it";
const base={"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Access-Control-Allow-Origin":SITE,"Vary":"Origin","Access-Control-Allow-Methods":"GET, OPTIONS","Access-Control-Allow-Headers":"authorization, apikey, content-type"};
const respond=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status,headers:base});
Deno.serve(async req=>{
  const origin=req.headers.get("Origin");
  if(origin && origin!==SITE)return respond({error:"origin_not_allowed"},403);
  if(req.method==="OPTIONS")return new Response(null,{status:204,headers:base});
  if(req.method!=="GET")return respond({error:"method_not_allowed"},405);
  const path=new URL(req.url);
  if(path.searchParams.get("mode")==="config"){
    const url=Deno.env.get("SUPABASE_URL")||"",key=Deno.env.get("SUPABASE_ANON_KEY")||"";
    if(!url||!key)return respond({error:"service_unavailable"},503);
    return respond({supabase_url:url,publishable_key:key});
  }
  if(path.searchParams.get("mode")!=="queue")return respond({service:"Press & Sport Cloud V2 API",read_only:true});
  const authorization=req.headers.get("Authorization")||"";
  if(!authorization.startsWith("Bearer ")||authorization.length>8200)return respond({error:"unauthorized"},401);
  const url=Deno.env.get("SUPABASE_URL")||"",anon=Deno.env.get("SUPABASE_ANON_KEY")||"",service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
  if(!url||!anon||!service)return respond({error:"service_unavailable"},503);
  try{
    const client=createClient(url,anon,{auth:{persistSession:false,autoRefreshToken:false}});
    const {data:{user},error}=await client.auth.getUser(authorization.slice(7));
    if(error||!user||!user.email_confirmed_at)return respond({error:"unauthorized"},401);
    const admin=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
    const {data,error:rpcError}=await admin.rpc("presssport_admin_v2_queue",{p_actor:user.id});
    if(rpcError)return respond({error:"forbidden"},403);
    return respond(data);
  }catch{return respond({error:"service_unavailable"},503)}
});
