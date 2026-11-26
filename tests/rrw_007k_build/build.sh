#!/usr/bin/env bash
set -euo pipefail
umask 077

recipe=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
work=$(realpath -- "${1:?new private build directory required}")
[[ $(uname -sm) == 'Linux x86_64' && ! -e "$work" ]]
mkdir -p "$work"/{dl,source,zig,fetch-home,out}
target=x86_64-unknown-linux-musl
version=0.9.5+rrw.007k.1
pin=e8d7d9705a7a2c89cef4dd42079379f05685af87
image=docker.io/library/rust@sha256:d99f7b31f49909348dc59b51f3c95d1efded1701ffb222f095aaab7de3c4abd8
fetch() {
    curl -q -fsSL --proto '=https' --proto-redir '=https' --retry 2 \
        --connect-timeout 15 --max-time 180 "$1" -o "$2"
    printf '%s  %s\n' "$3" "$2" | sha256sum -c
}

fetch "https://codeload.github.com/herdrdev/herdr/tar.gz/$pin" "$work/dl/source.tar.gz" \
    364730fe096f2f79749c3e7d7204951406437ecb8161b8d93b6fc42ccde9100d
timeout -k 5s 540s bash "$recipe/fetch-zig.sh" "$work/dl/zig.tar.xz"
fetch "https://static.rust-lang.org/dist/2026-06-30/rust-std-1.96.1-$target.tar.xz" "$work/dl/std.tar.xz" \
    94192fe7e10f11e8595f2a29ebda182da0f786797fe908f44fbf80213cd845ac
printf '%s  %s\n' ebd2b8f59f9712bf39841e2073d784d95612b3d86eab857b03c29f18432a95e6 \
    "$recipe/native-proof.patch" | sha256sum -c
tar -xzf "$work/dl/source.tar.gz" --strip-components=1 -C "$work/source"
tar -xJf "$work/dl/zig.tar.xz" --strip-components=1 -C "$work/zig"
git -C "$work/source" apply --check "$recipe/native-proof.patch"
git -C "$work/source" apply "$recipe/native-proof.patch"
python3 - "$work/source" "$version" <<'PY'
from pathlib import Path
import re
import sys

source, version = Path(sys.argv[1]), sys.argv[2]
for filename in ("Cargo.toml", "Cargo.lock"):
    path = source / filename
    pattern = r'(?m)^(name = "herdr"\nversion = ")0\.9\.5(")$'
    text, count = re.subn(pattern, lambda m: m[1] + version + m[2], path.read_text())
    if count != 1:
        raise SystemExit(f"Unexpected Herdr package version in {filename}")
    path.write_text(text)
PY
python3 "$recipe/stage-zig-inputs.py" "$work" > "$work/out/zig-pins.tsv"
docker pull --platform linux/amd64 "$image"
[[ $(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$image") == linux/amd64 ]]
container=(docker run --rm --pull=never --cap-drop=all --security-opt=no-new-privileges
    --user "$(id -u):$(id -g)" --volume "$work:/work" --workdir /work/source
    --env HOME=/work/fetch-home --env CARGO_HOME=/work/cargo \
    --env RUSTUP_HOME=/usr/local/rustup --env RUSTUP_TOOLCHAIN=1.96.1)
"${container[@]}" "$image" cargo fetch --locked --target "$target"

"${container[@]}" --network=none \
    --env PATH=/work/zig:/usr/local/cargo/bin:/usr/bin:/bin \
    --env CARGO_TARGET_DIR=/work/target --env ZIG_GLOBAL_CACHE_DIR=/work/zig-cache \
    --env LIBGHOSTTY_VT_ZIG_SYSTEM_DIR=/work/zig-system \
    --env LIBGHOSTTY_VT_OPTIMIZE=ReleaseFast --env LIBGHOSTTY_VT_SIMD=true \
    --env CARGO_INCREMENTAL=0 --env LC_ALL=C --env TZ=UTC \
    "$image" bash -euc '
        [[ $(rustc --version) == "rustc 1.96.1 "* && $(zig version) == 0.16.0 ]]
        mkdir -p /work/std
        tar -xJf /work/dl/std.tar.xz --strip-components=1 -C /work/std
        mkdir /work/rust-sysroot
        sysroot=$(rustc --print sysroot)
        cp -as "$sysroot/." /work/rust-sysroot/
        bash /work/std/install.sh --prefix=/work/musl-stdlib --disable-ldconfig
        ln -s "/work/musl-stdlib/lib/rustlib/$1" "/work/rust-sysroot/lib/rustlib/$1"
        export CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_RUSTFLAGS="--remap-path-prefix=/work=/ --sysroot=/work/rust-sysroot -C linker=$sysroot/lib/rustlib/x86_64-unknown-linux-gnu/bin/rust-lld -C linker-flavor=gnu-lld"
        cargo build --release --locked --offline -j 4 --target "$1" --bin herdr
        install -m 0755 "/work/target/$1/release/herdr" /work/out/herdr
        [[ $(/work/out/herdr --version) == "herdr $2" ]]
        readelf -h /work/out/herdr | grep -F "Advanced Micro Devices X86-64"
        readelf -l /work/out/herdr > /work/out/elf-segments.txt
        ! grep -q INTERP /work/out/elf-segments.txt
        install -m 0644 LICENSE /work/out/HERDR-LICENSE
    ' bash "$target" "$version"
printf 'source=%s\nbuilder=%s\ntarget=%s\nversion=%s\n' "$pin" "$image" "$target" "$version" > "$work/out/build.txt"
(cd "$work" && sha256sum dl/{source,zig,std}.tar.* source/Cargo.lock > out/input-sha256.txt)
printf '%s  native-proof.patch\n' ebd2b8f59f9712bf39841e2073d784d95612b3d86eab857b03c29f18432a95e6 >> "$work/out/input-sha256.txt"
python3 - "$work" <<'PY'
from pathlib import Path
import re
import sys
import tarfile

work = Path(sys.argv[1])
names = re.compile(r"(?:licen[cs]e|notice|copying|copyright|unlicense)(?:[._-].*)?", re.I)
with tarfile.open(work / "out/notices.tar.gz", "w:gz") as archive:
    for root in ("source/vendor", "zig-system", "cargo/registry/src"):
        for path in sorted((work / root).rglob("*")):
            if path.is_file() and not path.is_symlink() and names.fullmatch(path.name):
                archive.add(path, arcname=str(path.relative_to(work)), recursive=False)
PY
(cd "$work/out" && sha256sum herdr > herdr.sha256)
