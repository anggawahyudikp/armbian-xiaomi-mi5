"""Capture all tracked changes and added files relative to kernel HEAD."""
from pathlib import Path
import subprocess


def source_patch(source: Path) -> bytes:
    source = source.resolve()
    options = ['--no-color', '--no-ext-diff', '--no-textconv', '--binary']
    patch = subprocess.check_output(['git', 'diff', *options, 'HEAD', '--'], cwd=source)
    added = subprocess.check_output(
        ['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=source)
    for name in sorted(filter(None, added.split(b'\0'))):
        relative = name.decode('utf-8', errors='surrogateescape')
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unexpected source path from git')
        result = subprocess.run(['git', 'diff', '--no-index', *options,
                                 '--', '/dev/null', relative], cwd=source, capture_output=True)
        if result.returncode != 1:
            raise RuntimeError('Cannot record added kernel file: ' + relative)
        patch += result.stdout
    return patch
