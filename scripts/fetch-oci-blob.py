#!/usr/bin/env python3
"""Resume a public GHCR artifact in bounded ranges and verify its OCI digest."""
import argparse
import hashlib
import http.client
import json
import pathlib
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("repository", help="Public GHCR repository, e.g. armbian/os/armbian-firmware-full")
parser.add_argument("manifest", type=pathlib.Path, help="Manifest already fetched from the registry")
parser.add_argument("output", type=pathlib.Path)
parser.add_argument("--seed-partial", type=pathlib.Path)
args = parser.parse_args()
if not re.fullmatch(r"[a-z0-9][a-z0-9_./-]+", args.repository):
    raise SystemExit("Invalid repository name")
layers = json.loads(args.manifest.read_text())["layers"]
if len(layers) != 1:
    raise SystemExit("Expected a single-file OCI artifact")
digest, total = layers[0]["digest"], layers[0]["size"]
if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) or total <= 0:
    raise SystemExit("Invalid OCI layer metadata")
args.output.parent.mkdir(parents=True, exist_ok=True)
partial = args.output.with_suffix(args.output.suffix + ".resumable")
if not partial.exists() and args.seed_partial and args.seed_partial.is_file():
    shutil.copyfile(args.seed_partial, partial)
partial.touch(exist_ok=True)
if partial.stat().st_size > total:
    raise SystemExit("Partial file is larger than the registry artifact")


class RegistryRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, *parameters, **keywords):
        redirected = super().redirect_request(request, *parameters, **keywords)
        if redirected and urllib.parse.urlsplit(redirected.full_url).hostname != urllib.parse.urlsplit(request.full_url).hostname:
            redirected.remove_header("Authorization")
        return redirected


opener = urllib.request.build_opener(RegistryRedirect())


def token():
    query = urllib.parse.urlencode({"service": "ghcr.io", "scope": f"repository:{args.repository}:pull"})
    with opener.open("https://ghcr.io/token?" + query, timeout=30) as response:
        return json.load(response)["token"]


authorization = token()
failures = 0
while partial.stat().st_size < total:
    offset = partial.stat().st_size
    end = min(total - 1, offset + 16 * 1024 * 1024 - 1)
    request = urllib.request.Request("https://ghcr.io/v2/" + args.repository + "/blobs/" + digest,
                                     headers={"Authorization": "Bearer " + authorization,
                                              "Range": f"bytes={offset}-{end}"})
    try:
        with opener.open(request, timeout=60) as response:
            content_range = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
            if response.status != 206 or not content_range:
                raise SystemExit("Registry did not honor a byte-range request; refusing unsafe append")
            first, last, length = map(int, content_range.groups())
            if first != offset or last > end or length != total:
                raise SystemExit("Unexpected Content-Range from registry")
            remaining = last - first + 1
            with partial.open("ab") as output:
                while remaining:
                    data = response.read(min(1024 * 1024, remaining))
                    if not data:
                        raise EOFError("Interrupted range response")
                    output.write(data)
                    remaining -= len(data)
        failures = 0
        current = partial.stat().st_size
        print(f"Downloaded {current:,}/{total:,} bytes ({100 * current / total:.1f}%)", flush=True)
    except (OSError, http.client.HTTPException, EOFError) as exc:
        failures = 0 if partial.stat().st_size > offset else failures + 1
        if failures >= 8:
            raise SystemExit("Download made no progress after eight attempts") from exc
        if isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403):
            authorization = token()
        print(f"{type(exc).__name__}; resuming at byte {partial.stat().st_size:,}", flush=True)
        time.sleep(2)
with partial.open("rb") as stream:
    actual = hashlib.file_digest(stream, "sha256").hexdigest()
if actual != digest.removeprefix("sha256:"):
    raise SystemExit("OCI digest mismatch; partial file retained, final artifact NOT replaced")
partial.replace(args.output)
print("Verified OCI digest:", digest, flush=True)
