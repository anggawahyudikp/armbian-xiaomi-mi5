"""Prove that recorded patches reconstruct staged, unstaged and added sources."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from kernel_source_identity import source_patch


class SourceIdentityTests(unittest.TestCase):
    def test_patch_reconstructs_complete_changed_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, restored = root/'source', root/'restored'
            source.mkdir()
            def git(*args, cwd=source, **kwargs):
                return subprocess.run(['git', *args], cwd=cwd, check=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
            git('init', '-q')
            (source/'tracked').write_text('original\n')
            (source/'deleted').write_text('remove\n')
            git('add', '.')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                'commit', '-qm', 'base')
            git('clone', '-q', str(source), str(restored))
            (source/'tracked').write_text('staged\n')
            git('add', 'tracked')
            (source/'tracked').write_text('unstaged after staging\n')
            (source/'deleted').unlink()
            (source/'added driver.c').write_text('added driver\n')
            (source/'binary').write_bytes(b'\0\xff\x01\0')
            (source/'link').symlink_to('tracked')
            patch = source_patch(source)
            git('apply', '--check', '-', cwd=restored, input=patch)
            git('apply', '-', cwd=restored, input=patch)
            for name in ['tracked', 'added driver.c', 'binary']:
                self.assertEqual((source/name).read_bytes(), (restored/name).read_bytes())
            self.assertFalse((restored/'deleted').exists())
            self.assertTrue((restored/'link').is_symlink())
            self.assertEqual((restored/'link').readlink(), Path('tracked'))
            self.assertEqual(patch, source_patch(source))

    def test_clean_source_has_empty_patch(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            for args in [('init', '-q'), ('-c', 'user.name=Fixture', '-c',
                         'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'base')]:
                subprocess.run(['git', *args], cwd=source, check=True, capture_output=True)
            self.assertEqual(source_patch(source), b'')


if __name__ == '__main__':
    unittest.main()
