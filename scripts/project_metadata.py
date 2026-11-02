#!/usr/bin/env python3
"""Public project identity; hardware names remain Gemini/MSM8996."""
import argparse
import json
from pathlib import Path
import re

PROJECT = json.loads((Path(__file__).resolve().parents[1] / 'config/project.json').read_text())
assert re.fullmatch(r'[a-z0-9-]+', PROJECT['slug'])
assert re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.]+)?', PROJECT['version'])
PREFIX = PROJECT['slug'] + '_' + PROJECT['version']

def artifact_names():
    return {'fastboot': PREFIX + '_fastboot.zip', 'twrp': PREFIX + '_twrp.zip'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--field', choices=(*PROJECT, 'prefix', 'fastboot', 'twrp'), required=True)
    args = parser.parse_args()
    print({'prefix': PREFIX, **PROJECT, **artifact_names()}[args.field])
