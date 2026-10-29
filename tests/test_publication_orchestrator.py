import hashlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from scripts.presssport_publication_orchestrator import execute_once, PublicationUncertain

MANIFEST = Path("publishing/presssport-2026-10-28.json").read_bytes()
NOW = datetime(2026, 10, 28, 12, 10, tzinfo=timezone.utc)
AUTH = dict(instagram_account_id="17841425937268080",
            manifest_path="publishing/presssport-2026-10-28.json",
            publish_authorized=True, approved_by="Paolo Savio",
            manifest_sha256=hashlib.sha256(MANIFEST).hexdigest(),
            action="publish_now", authorized_at="2026-10-28T12:00:00+00:00")

class Cursor:
    def __init__(self, db): self.db=db; self.result=None
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self, sql, params):
        if sql.lstrip().startswith("INSERT"):
            key, account, digest, attempt = params
            if self.db.row is not None: raise RuntimeError("duplicate reservation")
            self.db.pending=dict(key=key, attempt=attempt, state="reserved")
            self.result=(key,)
        else:
            state, media, reconcile, key, attempt, old = params
            row=self.db.row
            if row is None or (row["key"],row["attempt"],row["state"]) != (key,attempt,old):
                self.result=None
            else:
                self.db.pending=dict(row,state=state,media=media,reconcile=reconcile)
                self.result=(key,)
    def fetchone(self): return self.result

class DB:
    def __init__(self): self.row=None; self.pending=None; self.events=[]
    def cursor(self): return Cursor(self)
    def commit(self):
        self.row=self.pending if self.pending is not None else self.row
        self.pending=None
        self.events.append("commit:"+self.row["state"])
    def rollback(self): self.pending=None; self.events.append("rollback")

class Meta:
    def __init__(self,db,fail=False): self.db=db; self.fail=fail; self.calls=0
    def post(self,req):
        assert self.db.row["state"]=="publishing"
        assert self.db.pending is None
        self.db.events.append("meta:"+req["path"])
        self.calls+=1
        if self.fail and self.calls==1: raise TimeoutError("ambiguous Meta result")
        return str(100000+self.calls)
    def status(self,cid): return {"id":cid,"status_code":"FINISHED"}

class OrchestratorTests(unittest.TestCase):
    def test_success_commits_before_meta_and_records_media(self):
        db=DB(); meta=Meta(db)
        result=execute_once(db,MANIFEST,AUTH,meta,identity_verified=True,now=NOW)
        self.assertEqual(result["state"],"published")
        self.assertEqual(db.row["state"],"published")
        self.assertEqual(meta.calls,9)
        self.assertEqual(db.events[:2],["commit:reserved","commit:publishing"])
        self.assertEqual(db.events[-1],"commit:published")
    def test_ambiguous_outcome_quarantined_without_retry(self):
        db=DB(); meta=Meta(db,fail=True)
        with self.assertRaises(PublicationUncertain):
            execute_once(db,MANIFEST,AUTH,meta,identity_verified=True,now=NOW)
        self.assertEqual(meta.calls,1)
        self.assertEqual(db.row["state"],"uncertain")
        self.assertTrue(db.row["reconcile"])
    def test_pending_containers_eventually_ready(self):
        db=DB()
        class PendingMeta(Meta):
            def __init__(self, db):
                super().__init__(db)
                self.polls={}
            def status(self, cid):
                count=self.polls.get(cid,0)+1
                self.polls[cid]=count
                return {"id":cid,"status_code":"IN_PROGRESS" if count==1 else "FINISHED"}
        meta=PendingMeta(db)
        result=execute_once(db,MANIFEST,AUTH,meta,identity_verified=True,now=NOW,
                            readiness_checks=2,readiness_interval=0,sleep=lambda _:None)
        self.assertEqual(result["state"],"published")
        self.assertEqual(len(meta.polls),8)
        self.assertTrue(all(v==2 for v in meta.polls.values()))
    def test_readiness_timeout_quarantines_without_publish_retry(self):
        db=DB()
        class PendingMeta(Meta):
            def status(self,cid): return {"id":cid,"status_code":"IN_PROGRESS"}
        meta=PendingMeta(db)
        with self.assertRaises(PublicationUncertain):
            execute_once(db,MANIFEST,AUTH,meta,identity_verified=True,now=NOW,
                         readiness_checks=2,readiness_interval=0,sleep=lambda _:None)
        self.assertEqual(meta.calls,7)
        self.assertEqual(db.row["state"],"uncertain")
        self.assertTrue(db.row["reconcile"])
    def test_first_commit_failure_never_contacts_meta(self):
        class FailingDB(DB):
            def commit(self):
                raise TimeoutError("commit outcome unknown")
        db=FailingDB(); meta=Meta(db)
        with self.assertRaises(PublicationUncertain):
            execute_once(db,MANIFEST,AUTH,meta,identity_verified=True,now=NOW)
        self.assertEqual(meta.calls,0)
        self.assertIn("rollback",db.events)
    def test_second_commit_failure_never_contacts_meta(self):
        class FailingDB(DB):
            def __init__(self):
                super().__init__()
                self.commit_count=0
            def commit(self):
                self.commit_count+=1
                if self.commit_count==2:
                    raise TimeoutError("publishing commit outcome unknown")
                return super().commit()
        db=FailingDB(); meta=Meta(db)
        with self.assertRaises(PublicationUncertain):
            execute_once(db,MANIFEST,AUTH,meta,identity_verified=True,now=NOW)
        self.assertEqual(meta.calls,0)
        self.assertEqual(db.row["state"],"reserved")
        self.assertIn("rollback",db.events)
    def test_disabled_authorization_blocks_before_db_or_meta(self):
        db=DB(); meta=Meta(db)
        with self.assertRaises(PermissionError):
            execute_once(db,MANIFEST,dict(AUTH,publish_authorized=False),
                         meta,identity_verified=True,now=NOW)
        self.assertIsNone(db.row)
        self.assertEqual(meta.calls,0)
    def test_future_schedule_never_publishes_immediately(self):
        db=DB(); meta=Meta(db)
        scheduled=dict(AUTH,action="schedule",scheduled_at="2026-10-29T12:00:00+00:00")
        with self.assertRaises(PermissionError):
            execute_once(db,MANIFEST,scheduled,meta,identity_verified=True,now=NOW)
        self.assertIsNone(db.row)
        self.assertEqual(meta.calls,0)
    def test_missing_action_never_publishes(self):
        db=DB(); meta=Meta(db)
        with self.assertRaises(PermissionError):
            execute_once(db,MANIFEST,dict(AUTH,action=None),meta,identity_verified=True,now=NOW)
        self.assertIsNone(db.row)
        self.assertEqual(meta.calls,0)
    def test_identity_required(self):
        db=DB(); meta=Meta(db)
        with self.assertRaises(PermissionError):
            execute_once(db,MANIFEST,AUTH,meta,identity_verified=False,now=NOW)
        self.assertEqual(meta.calls,0)
    def test_duplicate_reservation_blocks_second_publish(self):
        db=DB(); first=Meta(db)
        execute_once(db,MANIFEST,AUTH,first,identity_verified=True,now=NOW)
        second=Meta(db)
        with self.assertRaises(RuntimeError):
            execute_once(db,MANIFEST,AUTH,second,identity_verified=True,now=NOW)
        self.assertEqual(second.calls,0)

if __name__=="__main__": unittest.main()
