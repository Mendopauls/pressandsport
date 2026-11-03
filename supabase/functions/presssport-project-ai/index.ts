// Zero-extra-cost policy: deliberately no AI provider integration, paid API keys or outbound requests.
// Human-authored drafts and free templates are handled by presssport-ollama-sync.
const cors={
 "Access-Control-Allow-Origin":"https://pressandsport.it",
 "Access-Control-Allow-Methods":"POST,OPTIONS",
 "Access-Control-Allow-Headers":"authorization,content-type",
 "Content-Type":"application/json",
 "Cache-Control":"no-store"
};
Deno.serve((req)=>{
 const origin=req.headers.get("Origin");
 if(origin&&origin!=="https://pressandsport.it")
  return new Response(JSON.stringify({error:"origin_denied"}),{status:403,headers:cors});
 if(req.method==="OPTIONS")return new Response(null,{status:204,headers:cors});
 if(req.method!=="POST")return new Response(JSON.stringify({error:"method_not_allowed"}),{status:405,headers:cors});
 return new Response(JSON.stringify({error:"paid_ai_disabled_by_zero_cost_policy",enabled:false,publication:false}),{status:503,headers:cors});
});
