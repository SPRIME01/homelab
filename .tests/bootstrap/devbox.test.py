import os
import json
import unittest


class DevboxTests(unittest.TestCase):
    def test_devbox_json_exists(self):
        self.assertTrue(os.path.isfile('devbox.json'), 'devbox.json must exist at repository root')

    def test_devbox_json_valid_json(self):
        with open('devbox.json', 'rb') as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_devbox_packages_present(self):
        with open('devbox.json', 'rb') as f:
            data = json.load(f)
        self.assertIn('packages', data, 'devbox.json must contain a top-level "packages" array')
        pkgs = data.get('packages') or []
        required = {'git', 'curl', 'jq', 'postgresql'}
        self.assertTrue(required.issubset(set(pkgs)), f'devbox.json packages must include {required}')


if __name__ == '__main__':
    unittest.main()
