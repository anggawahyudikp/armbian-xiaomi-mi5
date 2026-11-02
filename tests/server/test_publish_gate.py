"""Missing hardware evidence must never pass the publication gate."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PublishGateTest(unittest.TestCase):
    def test_missing_hardware_report_blocks_publication(self):
        project = json.loads((ROOT / 'config/project.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for suffix in ('fastboot.zip', 'twrp.zip'):
                (output / f"{project['slug']}_{project['version']}_{suffix}").touch()
            (output / 'SHA256SUMS').touch()
            (output / 'release-validation.json').write_text('{"passed":true}')
            (output / 'build-provenance.json').write_text('{"offline_validation_passed":true}')
            result = subprocess.run(['bash', str(ROOT / 'scripts/publish-release.sh'),
                                     '--publish', 'invalid-repo-format'],
                                    env={**os.environ, 'OUT': directory}, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Resolve the recorded device regression', result.stderr)
            self.assertIn('evidence is missing', (output / 'release-notes.md').read_text())
