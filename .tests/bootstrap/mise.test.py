import os
import unittest
import subprocess

try:
    import tomllib as toml
except Exception:
    toml = None


class MiseTests(unittest.TestCase):
    def test_mise_toml_exists(self):
        self.assertTrue(os.path.isfile('.mise.toml'), '.mise.toml must exist at repository root')

    def test_mise_toml_parseable(self):
        if toml is None:
            self.skipTest('Python tomllib not available to parse TOML; install a TOML parser or run under Python 3.11+')
        with open('.mise.toml', 'rb') as f:
            data = toml.load(f)
        self.assertIsInstance(data, dict)

    def test_pinned_versions_match_mcp(self):
        # Expectations come from the Context7 MCP lookup executed earlier in this session
        expected_node = '22.17.0'
        expected_python = '3.13.9'
        # Additional pins found via GitHub releases API during this session
        expected_devbox = '0.16.0'
        expected_rust = '1.91.1'
        expected_age = '1.2.1'
        expected_pulumi = '3.207.0'

        if toml is None:
            self.skipTest('TOML parsing unavailable; cannot validate pinned versions')

        with open('.mise.toml', 'rb') as f:
            data = toml.load(f)

        tools = data.get('tools', {})
        self.assertEqual(tools.get('node'), expected_node, f'node version in .mise.toml must be pinned to {expected_node}')
        self.assertEqual(tools.get('python'), expected_python, f'python version in .mise.toml must be pinned to {expected_python}')
        self.assertEqual(str(tools.get('devbox')), expected_devbox, f'devbox must be pinned to {expected_devbox}')
        self.assertEqual(str(tools.get('rust')), expected_rust, f'rust must be pinned to {expected_rust}')
        self.assertEqual(str(tools.get('age')), expected_age, f'age must be pinned to {expected_age}')
        self.assertEqual(str(tools.get('pulumi')), expected_pulumi, f'pulumi must be pinned to {expected_pulumi}')


if __name__ == '__main__':
    unittest.main()
