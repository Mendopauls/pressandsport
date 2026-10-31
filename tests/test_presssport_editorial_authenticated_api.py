import unittest
from unittest.mock import patch
from scripts.presssport_editorial_authenticated_api import handle_request, is_operator, verified_email

class Cursor:
    def __init__(self, allowed=True): self.allowed=allowed; self.executed=[]
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def execute(self,query,params): self.executed.append((query,params))
    def fetchone(self): return (self.allowed,)

class Connection:
    def __init__(self, allowed=True): self.cur=Cursor(allowed)
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def cursor(self): return self.cur

class AuthTests(unittest.TestCase):
    def check(self,method="GET",auth="Bearer test",allowed=True,email="operator@example.test"):
        conn=Connection(allowed)
        with patch("scripts.presssport_editorial_authenticated_api.list_queue",return_value=[]) as listing:
            code,payload=handle_request(method,"/api/editorial/v2/queue",auth,
                db_connect=lambda:conn,supabase_url="https://project.supabase.co",
                publishable_key="public",verifier=lambda *a: email)
        return code,payload,conn,listing

    def test_verifier_rejects_non_https(self):
        self.assertIsNone(verified_email("abc", "http://project.supabase.co",
                                         "public", opener=lambda *a, **k: None))

    def test_verifier_uses_auth_identity_only(self):
        import io
        class Reply(io.BytesIO):
            status = 200
            def __enter__(self): return self
            def __exit__(self,*a): return False
        def opener(request, timeout):
            self.assertEqual(timeout, 8)
            self.assertEqual(request.get_header("Authorization"), "Bearer token")
            return Reply(b'{"email":" ADMIN@Example.test ","user_metadata":{"role":"admin"}}')
        self.assertEqual(
            verified_email("token", "https://project.supabase.co", "public", opener),
            "admin@example.test")

    def test_anonymous_rejected(self):
        code,_,conn,_=self.check(auth=None)
        self.assertEqual(code,401)
        self.assertEqual(conn.cur.executed,[])

    def test_non_operator_rejected(self):
        code,_,_,listing=self.check(allowed=False)
        self.assertEqual(code,403)
        listing.assert_not_called()

    def test_operator_readonly(self):
        code,payload,conn,listing=self.check()
        self.assertEqual(code,200)
        self.assertTrue(payload["read_only"])
        self.assertFalse(payload["publication_authorized"])
        listing.assert_called_once()
        self.assertEqual(conn.cur.executed[0][1],("operator@example.test",))

    def test_write_method_rejected(self):
        code,_,conn,_=self.check(method="POST")
        self.assertEqual(code,405)
        self.assertEqual(conn.cur.executed,[])

    def test_path_rejected(self):
        code,_=handle_request("GET","/api/editorial/v2/publish","Bearer test",
            db_connect=lambda:None,supabase_url="https://project.supabase.co",
            publishable_key="public",verifier=lambda *a:"operator@example.test")
        self.assertEqual(code,404)

if __name__=="__main__":
    unittest.main()
