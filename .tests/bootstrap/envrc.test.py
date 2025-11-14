import os
import unittest
import subprocess


class EnvrcTests(unittest.TestCase):
    def test_envrc_exists(self):
        self.assertTrue(os.path.isfile('.envrc'), '.envrc must exist at repository root')

    def test_direnv_reports_allowed(self):
        # Use `direnv status` to determine whether the RC is allowed and loaded
        try:
            out = subprocess.check_output(['direnv', 'status'], stderr=subprocess.STDOUT, text=True)
        except FileNotFoundError:
            self.skipTest('direnv not installed; cannot runtime-validate .envrc')
        except subprocess.CalledProcessError as e:
            out = e.output

        self.assertIn('Found RC allowed true', out, 'direnv must report `.envrc` as allowed and loaded')


if __name__ == '__main__':
    unittest.main()
