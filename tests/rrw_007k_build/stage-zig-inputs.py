"""Stage the known Linux VT build inputs from exact pins; run from any cwd."""

import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile

os.umask(0o077)
ROOT = Path(sys.argv[1]).resolve()
VENDOR = ROOT / "source/vendor/libghostty-vt"
CACHE = ROOT / "zig-input-cache"
SYSTEM = ROOT / "zig-system"
PACKAGE = re.compile(r'\.url\s*=\s*"(https://[^"]+)",\s*\.hash\s*=\s*"([A-Za-z0-9_.-]+)"')
KNOWN = {
    "N-V-__8AAB0eQwD-0MdOEBmz7intriBReIsIDNlukNVoNu6o",
    "N-V-__8AADYiAAB_80AWnH1AxXC0tql9thT-R-DYO1gBqTLc",
    "N-V-__8AAEFmBABuDGOKxAI6VMg41b9euMZ-z7HS9EcUdaor",
    "N-V-__8AAGmZhABbsPJLfbqrh6JTHsXhY6qCaLAQyx25e0XE",
    "N-V-__8AAP5JWgCGP_AD0teWpa4krRvE9VPZzvviGdbmN4jI",
    "uucode-0.2.0-ZZjBPlK5VADj7fdoq7G8LIHzD5o6FSkcBXXrRWr4jnrA",
}
TRANSLATE = "translate_c-0.0.0-Q_BUWhVNBwDOEcIqub4VFPJPB6D9dgwzUMHTX5KWr8Xr"
ARO = "aro-0.0.0-JSD1Qk6lNgDdcDV4Vh7Sfy-34m2TluIVOdPzMmj_0BjX"


def stage(hash_value, manifests):
    urls = {
        url for manifest in manifests
        for url, digest in PACKAGE.findall(manifest.read_text())
        if digest == hash_value
    }
    if len(urls) != 1:
        raise RuntimeError(f"Expected exactly one manifest URL for {hash_value}: {urls}")
    url = urls.pop()
    archive = ROOT / "dl" / f"zig-{hash_value}.tar.gz"
    if not archive.exists():
        partial = archive.with_name(archive.name + ".part")
        subprocess.run([
            "curl", "-q", "-fsSL", "--proto", "=https", "--proto-redir", "=https",
            "--connect-timeout", "12", "--max-time", "90", "--output", partial, url,
        ], check=True, timeout=95)
        partial.rename(archive)
    actual = subprocess.check_output(
        [ROOT / "zig/zig", "fetch", "--global-cache-dir", CACHE, archive],
        cwd=VENDOR, env={"PATH": "/usr/bin:/bin", "HOME": str(ROOT / "fetch-home")},
        text=True, timeout=40,
    ).strip()
    if actual != hash_value:
        raise RuntimeError(f"Package hash mismatch: expected {hash_value}, got {actual}")
    with tarfile.open(CACHE / "p" / f"{hash_value}.tar.gz") as tar:
        members = tar.getmembers()
        if not members or not all(
            (entry.isdir() or entry.isfile())
            and PurePosixPath(entry.name).parts[:1] == (hash_value,)
            for entry in members
        ):
            raise RuntimeError(f"Unexpected archive layout: {hash_value}")
        tar.extractall(SYSTEM, members=members, filter="data")
    print(f"{hash_value}\t{url}", flush=True)


if __name__ == "__main__":
    SYSTEM.mkdir(exist_ok=True)
    vendored_manifests = sorted(VENDOR.rglob("build.zig.zon"))
    stage(TRANSLATE, vendored_manifests)
    stage(ARO, [SYSTEM / TRANSLATE / "build.zig.zon"])
    for digest in sorted(KNOWN):
        stage(digest, vendored_manifests)
