import unittest
from argparse import Namespace
from unittest.mock import patch
from scripts.presssport_editorial_console_cli import parser, run

class ConsoleTests(unittest.TestCase):
    def test_missing_args(self):
        with self.assertRaises(SystemExit):
            parser().parse_args(["draft"])

    def test_approval_disabled_without_verified_identity(self):
        args = Namespace(command="transition", post_key="x",
                         from_state="ready_for_review", to_state="approved",
                         operator="Paolo Savio", planned_at=None)
        with self.assertRaises(PermissionError):
            run(args, object())

    @patch("scripts.presssport_editorial_console_cli.list_queue")
    def test_readonly_list(self, list_queue):
        list_queue.return_value = []
        self.assertEqual(run(Namespace(command="list"), object()), [])
        list_queue.assert_called_once()

if __name__ == "__main__":
    unittest.main()
