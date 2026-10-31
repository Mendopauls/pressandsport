"""PressSport local Ollama worker: durable inbox, retry on Windows restart.

Does NOT access Meta, LinkedIn, Supabase credentials, or publish anything.
Jobs are JSON files in inbox, outputs remain drafts for human editorial review.
"""
import argparse
import json
import os
import sqlite3
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CREATE = """CREATE TABLE IF NOT EXISTS jobs (
 job_key TEXT PRIMARY KEY, source_file TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('pending','running','complete','failed')),
 attempts INTEGER NOT NULL DEFAULT 0,
 updated TEXT NOT NULL, result_file TEXT, error TEXT)"""

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def connect(root):
    root.mkdir(parents=True, exist_ok=True)
    db=sqlite3.connect(root / "jobs.sqlite3")
    db.execute(CREATE)
    db.execute("UPDATE jobs SET state='pending', updated=? WHERE state='running'",(utcnow(),))
    db.commit()
    return db

def discover(db, root):
    folder=root/"inbox"
    folder.mkdir(exist_ok=True)
    for item in sorted(folder.glob("*.json")):
        try:
            job=json.loads(item.read_text(encoding="utf-8-sig"))
            key=job.get("job_key")
            if not isinstance(key,str) or not key or len(key)>100 or not all(c.isalnum() or c in "-_" for c in key):
                print(f"IMPORT SKIPPED {item.name}: invalid job_key", flush=True)
                continue
            if not isinstance(job.get("brief"),str) or not 1<=len(job["brief"])<=12000:
                print(f"IMPORT SKIPPED {item.name}: invalid brief", flush=True)
                continue
            db.execute("INSERT OR IGNORE INTO jobs(job_key,source_file,state,updated) VALUES(?,?,'pending',?)",
                       (key,str(item.resolve()),utcnow()))
        except (OSError, ValueError, TypeError, sqlite3.Error) as exc:
            print(f"IMPORT ERROR {item.name}: {type(exc).__name__}: {exc}", flush=True)
            continue
    db.commit()

def generate(brief,endpoint,model,timeout=120):
    url=endpoint.rstrip("/")+"/api/generate"
    if not (url.startswith("http://127.0.0.1:") or url.startswith("http://localhost:")):
        raise ValueError("Ollama endpoint must be local")
    payload=json.dumps({"model":model,"prompt":"Scrivi una bozza editoriale Press & Sport in italiano, senza inventare fatti. Non pubblicare. Brief:\n"+brief,"stream":False}).encode()
    req=urllib.request.Request(url,data=payload,headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=timeout) as response:
        result=json.load(response)
    if not isinstance(result.get("response"),str) or not result["response"].strip():
        raise ValueError("Ollama returned empty draft")
    return result["response"]

def process_one(db,root,endpoint,model):
    row=db.execute("SELECT job_key,source_file,attempts FROM jobs WHERE state='pending' ORDER BY updated,job_key LIMIT 1").fetchone()
    if not row:return False
    key,path,attempts=row
    db.execute("UPDATE jobs SET state='running',attempts=attempts+1,updated=? WHERE job_key=?",(utcnow(),key));db.commit()
    try:
        job=json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if job.get("job_key")!=key:raise ValueError("Job identifier mismatch")
        text=generate(job["brief"],endpoint,model)
        output=root/"drafts";output.mkdir(exist_ok=True)
        destination=output/(key+".json")
        temp=output/(key+".tmp")
        temp.write_text(json.dumps({"job_key":key,"status":"draft_for_review","model":model,
                                    "text":text,"created_at":utcnow()},ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(temp,destination)
        db.execute("UPDATE jobs SET state='complete',result_file=?,error=NULL,updated=? WHERE job_key=?",
                   (str(destination),utcnow(),key))
    except (Exception) as exc:
        # Retry after next run, up to 3 attempts. Never discard input.
        state="failed" if attempts+1>=3 else "pending"
        db.execute("UPDATE jobs SET state=?,error=?,updated=? WHERE job_key=?",
                   (state,type(exc).__name__,utcnow(),key))
        db.commit()
        return False
    db.commit()
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=str(Path.home()/"PressSport-Ollama"))
    p.add_argument("--endpoint",default="http://127.0.0.1:11434")
    p.add_argument("--model",default="llama3.2")
    p.add_argument("--once",action="store_true")
    args=p.parse_args()
    root=Path(args.root).expanduser().resolve()
    db=connect(root)
    while True:
        discover(db,root)
        worked=process_one(db,root,args.endpoint,args.model)
        if args.once:break
        if not worked:time.sleep(30)

if __name__=="__main__":main()
