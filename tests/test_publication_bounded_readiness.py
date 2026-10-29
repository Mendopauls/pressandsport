import unittest
from scripts.meta_bounded_readiness import wait_until_ready, ContainerNotReady

class Meta:
    def __init__(self, statuses): self.statuses=list(statuses); self.calls=0
    def status(self,cid):
        self.calls+=1
        return {"id":cid,"status_code":self.statuses.pop(0)}

class BoundedReadinessTests(unittest.TestCase):
    def test_pending_then_ready(self):
        m=Meta(["IN_PROGRESS","IN_PROGRESS","FINISHED"]); delays=[]
        self.assertTrue(wait_until_ready(m,"123",max_checks=3,interval_seconds=1,sleep=delays.append))
        self.assertEqual(m.calls,3)
        self.assertEqual(delays,[1,1])
    def test_timeout_never_exceeds_limit(self):
        m=Meta(["IN_PROGRESS"]*3)
        with self.assertRaisesRegex(ContainerNotReady,"timeout"):
            wait_until_ready(m,"123",max_checks=3,interval_seconds=0,sleep=lambda _:None)
        self.assertEqual(m.calls,3)
    def test_failed_status_stops(self):
        m=Meta(["ERROR"])
        with self.assertRaises(ContainerNotReady):
            wait_until_ready(m,"123",sleep=lambda _:None)
        self.assertEqual(m.calls,1)
    def test_published_status_stops(self):
        m=Meta(["PUBLISHED"])
        with self.assertRaises(ContainerNotReady):
            wait_until_ready(m,"123",sleep=lambda _:None)
    def test_invalid_limit(self):
        with self.assertRaises(ValueError):
            wait_until_ready(Meta([]),"123",max_checks=0,sleep=lambda _:None)

if __name__=="__main__": unittest.main()
