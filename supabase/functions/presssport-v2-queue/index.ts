import { createClient } from "npm:@supabase/supabase-js@2.95.0";
const headers = {"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer","Access-Control-Allow-Origin":"null"};
const response=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});
Deno.serve(async req=>{
  if(req.method!=="GET")return response({error:"method_not_allowed"},405);
  const u=new URL(req.url);
  if(u.searchParams.get("mode")!=="queue")return response({message:"Press & Sport Cloud V2 — authorized read-only queue",read_only:true},200);
  const bearer=req.headers.get("Authorization")||"";
  if(!bearer.startsWith("Bearer ")||bearer.length>8200)return response({error:"unauthorized"},401);
  const token=bearer.slice(7);
  const url=Deno.env.get("SUPABASE_URL")||"";
  const anon=Deno.env.get("SUPABASE_ANON_KEY")||"";
  const service=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
  if(!url||!anon||!service)return response({error:"service_unavailable"},503);
  try{
    const client=createClient(url,anon,{auth:{persistSession:false,autoRefreshToken:false}});
    const {data:{user},error}=await client.auth.getUser(token);
    if(error||!user||!user.email_confirmed_at)return response({error:"unauthorized"},401);
    const admin=createClient(url,service,{auth:{persistSession:false,autoRefreshToken:false}});
    const {data,error:rpcError}=await admin.rpc("presssport_admin_v2_queue",{p_actor:user.id});
    if(rpcError)return response({error:"forbidden"},403);
    return response(data);
  }catch{return response({error:"service_unavailable"},503)}
});
