#!/usr/bin/env python3
"""Fail-closed preproduction audit. Static and offline: no DB or Meta calls."""
import ast
import json
from pathlib import Path
from scripts.presssport_release_audit import audit

ROOT=Path(__file__).resolve().parents[1]
DRY_RUN=ROOT/"scripts/presssport_cloud_publisher.py"
ORCHESTRATOR=ROOT/"scripts/presssport_publication_orchestrator.py"
AUTH=ROOT/"publishing/presssport-2026-10-28-authorization.json"

def _functions(path):
    tree=ast.parse(path.read_text(encoding="utf-8"))
    return {node.name:node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}

def _calls(function):
    return {node.func.id for node in ast.walk(function)
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)}

def inspect_preproduction():
    release=audit()
    authorization=json.loads(AUTH.read_text(encoding="utf-8"))
    dry=_functions(DRY_RUN)
    orchestrator=_functions(ORCHESTRATOR)
    checks={
        "publication_disabled": authorization.get("publish_authorized") is False,
        "dry_run_entrypoint": "run_dry_run" in dry and "main" in dry,
        "dry_run_no_execute_once": all("execute_once" not in _calls(fn) for fn in dry.values()),
        "orchestrator_has_publish_now_gate": "execute_once" in orchestrator
            and any(isinstance(n,ast.Compare) and isinstance(n.left,ast.Call)
                    and isinstance(n.left.func,ast.Attribute) and n.left.func.attr=="get"
                    and any(isinstance(a,ast.Constant) and a.value=="action" for a in n.left.args)
                    for n in ast.walk(orchestrator["execute_once"])),
        "release_not_ready": release["release_ready"] is False,
        "runner_dry_run_only": release["runner_mode"]=="dry_run_only",
        "all_components_present": not release["missing_components"],
    }
    return {"checks":checks,"passed":all(checks.values()),
            "release_ready":False,"publication_performed":False}

def main():
    result=inspect_preproduction()
    print(json.dumps(result,indent=2,sort_keys=True))
    if not result["passed"]:
        raise SystemExit("BLOCKED: preproduction audit failed")
    print("PASS: preproduction safety audit; LIVE RELEASE NOT AUTHORIZED")

if __name__=="__main__":
    main()
