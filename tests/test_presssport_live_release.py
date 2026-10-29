import hashlib
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from scripts.presssport_live_release import run_release, main

NOW = datetime(2026, 10, 29, 16, 0, tzinfo=timezone.utc)
ACCOUNT = "17841425937268080"
URLS = ["https://pressandsport.it/media/one.jpg", "https://pressandsport.it/media/two.jpg"]
MANIFEST = json.dumps({"status":"approved", "instagram_account_id":ACCOUNT, "caption":"approved caption", "image_urls":URLS}).encode()
DIGEST = hashlib.sha256(MANIFEST).hexdigest()
VALID_AUTH = {"instagram_account_id":ACCOUNT, "manifest_path":"publishing/presssport-2026-10-28.json",
    "manifest_sha256":DIGEST, "publish_authorized":True, "approved_by":"Paolo Savio",
    "authorized_at":NOW.isoformat(), "action":"publish_now", "scheduled_at":None}

def forbidden(*args, **kwargs):
    raise AssertionError("blocked operation must not be reached")

def release(**kw):
    options = dict(publish_now=True, confirm_account=ACCOUNT,
        confirm_sha256=DIGEST, token="fake", database_url="postgresql://fake",
        db_connect=forbidden, now=NOW, media_check=forbidden,
        identity_check=forbidden, meta_factory=forbidden)
    options.update(kw)
    return run_release(MANIFEST, VALID_AUTH, **options)

class ReleaseTests(unittest.TestCase):
    def test_disabled_authorization_blocks_before_media_or_db(self):
        auth=dict(VALID_AUTH, publish_authorized=False)
        with self.assertRaises(PermissionError):
            run_release(MANIFEST, auth, publish_now=True, confirm_account=ACCOUNT,
                confirm_sha256=DIGEST, token="fake", database_url="postgresql://fake",
                db_connect=forbidden, media_check=forbidden, now=NOW)
    def test_no_explicit_action_blocks(self):
        with self.assertRaisesRegex(PermissionError,"explicit publish_now"):
            release(publish_now=False)
    def test_mismatched_hash_blocks(self):
        with self.assertRaisesRegex(PermissionError,"confirmation"):
            release(confirm_sha256="0"*64)
    def test_mismatched_account_blocks(self):
        with self.assertRaisesRegex(PermissionError,"confirmation"):
            release(confirm_account="999")
    def test_stale_approval_blocks(self):
        with self.assertRaises(PermissionError):
            run_release(MANIFEST, VALID_AUTH, publish_now=True, confirm_account=ACCOUNT,
                confirm_sha256=DIGEST, token="fake", database_url="postgresql://fake",
                db_connect=forbidden, media_check=forbidden,
                now=datetime(2026,10,29,18,0,tzinfo=timezone.utc))
    def test_unreachable_media_blocks_before_db(self):
        with self.assertRaisesRegex(RuntimeError,"public carousel images"):
            run_release(MANIFEST, VALID_AUTH, publish_now=True, confirm_account=ACCOUNT,
                confirm_sha256=DIGEST, token="fake", database_url="postgresql://fake",
                db_connect=forbidden, media_check=lambda b: {"all_reachable":False, "image_count":0}, now=NOW)
    def test_good_release_hands_verified_dependencies_to_executor(self):
        checked=[]
        def media_check(b):
            checked.append("media")
            return {"all_reachable":True, "image_count":2}
        def identity_check(b,t):
            checked.append("identity")
            self.assertEqual(t,"fake")
            return {"verified":True, "account_id":ACCOUNT}
        def db_connect(url, **params):
            checked.append("db")
            self.assertEqual(params["sslmode"],"require")
            self.assertEqual(params["connect_timeout"],10)
            return "fake-connection"
        def meta_factory(token):
            checked.append("meta")
            return "fake-transport"
        with patch("scripts.presssport_live_release.execute_authorized") as executor:
            executor.return_value={"state":"test-only"}
            result=run_release(MANIFEST,VALID_AUTH,publish_now=True,confirm_account=ACCOUNT,
                confirm_sha256=DIGEST,token="fake",database_url="postgresql://fake",
                db_connect=db_connect,media_check=media_check,
                identity_check=identity_check,meta_factory=meta_factory,now=NOW)
            self.assertEqual(result["state"],"test-only")
            self.assertEqual(checked,["media"])
            kwargs=executor.call_args.kwargs
            self.assertEqual(kwargs["verify"](MANIFEST)["account_id"],ACCOUNT)
            self.assertEqual(kwargs["connect"](),"fake-connection")
            self.assertEqual(kwargs["make_meta"](),"fake-transport")
            self.assertEqual(checked,["media","identity","db","meta"])
    def test_main_environment_kill_switch(self):
        with patch.dict("os.environ",{"PRESSSPORT_ENABLE_LIVE_PUBLISH":"NO"}):
            with self.assertRaisesRegex(PermissionError,"environment gate"):
                main(["--publish-now","--confirm-account",ACCOUNT,"--confirm-manifest-sha256",DIGEST])
    def test_manual_workflow_only_and_default_authorization_disabled(self):
        from pathlib import Path
        workflow = Path(".github/workflows/presssport-authorized-release.yml").read_text()
        self.assertIn("workflow_dispatch:",workflow)
        self.assertIn("default: false",workflow)
        self.assertIn("if: inputs.publish_now == true",workflow)
        self.assertIn("environment: instagram-production",workflow)
        self.assertIn("cancel-in-progress: false",workflow)
        self.assertNotIn("  push:",workflow)
        self.assertNotIn("  schedule:",workflow)
        authorization = json.loads(Path("publishing/presssport-2026-10-28-authorization.json").read_text())
        self.assertIs(authorization["publish_authorized"],False)
if __name__=="__main__": unittest.main()
