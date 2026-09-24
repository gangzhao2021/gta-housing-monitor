"""The short-password exception is opt-in for local demonstrations only."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import setup_owner_password
from housing.owner_auth import verify


class PasswordSetupTests(unittest.TestCase):
    def test_six_character_password_requires_explicit_local_demo_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".streamlit").mkdir()
            fake_password = "123456"
            with patch.object(setup_owner_password, "ROOT", root), \
                 patch("getpass.getpass", side_effect=[fake_password, fake_password]), \
                 patch("sys.argv", ["setup_owner_password.py"]):
                with self.assertRaises(SystemExit):
                    setup_owner_password.main()
            self.assertFalse((root / ".streamlit/owner_auth.env").exists())

            with patch.object(setup_owner_password, "ROOT", root), \
                 patch("getpass.getpass", side_effect=[fake_password, fake_password]), \
                 patch("sys.argv", ["setup_owner_password.py", "--local-demo"]):
                setup_owner_password.main()
            saved = (root / ".streamlit/owner_auth.env").read_text()
            self.assertNotIn(fake_password, saved)
            self.assertTrue(verify(fake_password, saved.split("'", 2)[1]))
