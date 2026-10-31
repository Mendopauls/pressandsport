"""Press & Sport Cloud Ollama bridge. Cloud claims are leased, not publication authorizations.
Requires PRESSSPORT_WORKER_SECRET in Windows user environment. Never logs the secret.
"""
import argparse
import json
import os
import time
import urllib.request
import urllib.error
from presssport_ollama_worker import generate

API="https://acruqsduyucbrkxlqiqi.supabase.co/functions/v1/presssport-ollama-sync"

def request(mode,secret,data=None):
    body=json.dumps(data or {}).encode("utf-8")
    req=urllib.request.Request(API+"?mode="+mode,data=body,method="POST",
        headers={"Content-Type":"application/json","X-Worker-Secret":secret})
    with urllib.request.urlopen(req,timeout=25) as response:
        return json.load(response)

def cycle(secret,model):
    result=request("claim",secret)
    job=result.get("job")
    if not job:return "idle"
    try:
        draft=generate(job["brief"],"http://127.0.0.1:11434",model,timeout=300)
        outcome=request("complete",secret,{"job_key":job["job_key"],
            "lease_token":job["lease_token"],"text":draft,"model":model})
        return "complete" if outcome.get("completed") else "lease_expired"
    except Exception as exc:
        print("Worker job error:",type(exc).__name__,flush=True)
        return "retry_after_lease"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",default="qwen2.5:3b")
    p.add_argument("--once",action="store_true")
    args=p.parse_args()
    secret=os.getenv("PRESSSPORT_WORKER_SECRET","")
    if len(secret)<32:raise SystemExit("Missing PRESSSPORT_WORKER_SECRET (minimum 32 characters)")
    while True:
        try:
            print("SYNC:",cycle(secret,args.model),flush=True)
        except (urllib.error.URLError,ValueError,KeyError) as exc:
            print("SYNC ERROR:",type(exc).__name__,flush=True)
        if args.once:break
        time.sleep(30)

if __name__=="__main__":main()
