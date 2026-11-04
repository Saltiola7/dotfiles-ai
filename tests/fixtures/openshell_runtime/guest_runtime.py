"""Fixed signed Fedora 44 musl runtime prerequisite, appended to the root controller.

This source defines no entrypoint. The caller must hold mounted_store's exclusive
ownership and deadline. RPM archives remain root-owned inside its 8 GiB volume;
the fixed installed files and RPM database use the separately measured guest
reserve. No package resolver, key import, scripts, triggers, or compiler install.

Provenance: Fedora release primary metadata SHA256
1f1fdf58f26864c869884f854e92bc502d6fdf1769be2b2804783c243edf36a0,
under https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Everything/aarch64/os/repodata/.
File/dependency records came from the same signed RPM headers. The fingerprint is
published at https://fedoraproject.org/security/. Header inspection is not signature
verification: the guest's existing trusted key must verify each complete archive.
Offline tests qualify source behavior only, not native installation or execution.
"""

import hashlib as runtime_hashlib
import urllib.request as runtime_request
import urllib.error as runtime_error

runtime_fingerprint = "36F612DCF27F7D1A48A835E4DBFCF71C6D9F90A6"
runtime_reserve = 4 * 1024**3
runtime_install_margin = 64 * 1024**2
runtime_engine_requires = (
    ("rpmlib(CompressedFileNames)", 16777226, "3.0.4-1"),
    ("rpmlib(FileDigests)", 16777226, "4.6.0-1"),
    ("rpmlib(PayloadFilesHavePrefix)", 16777226, "4.0-1"),
    ("rpmlib(PayloadIsZstd)", 16777226, "5.4.18-1"),
)
runtime_packages = (
    {"name": "musl-filesystem", "bytes": 8360, "installed_bytes": 0,
     "sha256": "018341852575149323787e8ea4ef3f24abfb89940b57ae8c197cb0f5325a7bef",
     "url": "https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Everything/aarch64/os/Packages/m/musl-filesystem-1.2.5-6.fc44.aarch64.rpm",
     "requires": runtime_engine_requires,
     "files": (
         ("/usr/aarch64-linux-musl", 0, "40755", "root", "root", "", ""),
         ("/usr/aarch64-linux-musl/include", 0, "40755", "root", "root", "", ""),
         ("/usr/aarch64-linux-musl/lib64", 0, "40755", "root", "root", "", ""),
     )},
    {"name": "musl-libc", "bytes": 472552, "installed_bytes": 945234,
     "sha256": "01aeca38d800cf311eba92d7ef95941e21ac2bf938917f25d2aad82e7a82fedf",
     "url": "https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Everything/aarch64/os/Packages/m/musl-libc-1.2.5-6.fc44.aarch64.rpm",
     "requires": (("config(musl-libc)", 268435464, "1.2.5-6.fc44"),
                  ("musl-filesystem(aarch-64)", 8, "1.2.5-6.fc44")) + runtime_engine_requires,
     "files": (
         ("/etc/ld-musl-aarch64.path", 30, "100644", "root", "root", "2ac97444143efc95727428829446aa7cb051034a8e64594b3f84b15f23bc3730", ""),
         ("/lib/ld-musl-aarch64.so.1", 938904, "100755", "root", "root", "a8aa556a0aee6e265a11cfc224c8fff2b5e965606315e71996be6d65237ab6a6", ""),
         ("/lib64/ld-musl-aarch64.so.1", 27, "120777", "root", "root", "", "../lib/ld-musl-aarch64.so.1"),
         ("/usr/aarch64-linux-musl/lib64/ld-musl-aarch64.so.1", 33, "120777", "root", "root", "", "../../../lib/ld-musl-aarch64.so.1"),
         ("/usr/lib/.build-id", 0, "40755", "root", "root", "", ""),
         ("/usr/lib/.build-id/01", 0, "40755", "root", "root", "", ""),
         ("/usr/lib/.build-id/01/029fcb1ff604f7733802eef1b0ea2b76bf9f15", 36, "120777", "root", "root", "", "../../../../lib/ld-musl-aarch64.so.1"),
         ("/usr/share/licenses/musl-libc", 0, "40755", "root", "root", "", ""),
         ("/usr/share/licenses/musl-libc/COPYRIGHT", 6204, "100644", "root", "root", "f9bc4423732350eb0b3f7ed7e91d530298476f8fec0c6c427a1c04ade22655af", ""),
     )},
)
runtime_identity_format = "%{NAME}\t%{EPOCHNUM}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\t%{SIZE}\n"
runtime_file_format = "[%{FILENAMES}\t%{FILESIZES}\t%{FILEMODES:octal}\t%{FILEUSERNAME}\t%{FILEGROUPNAME}\t%{FILEDIGESTS}\t%{FILELINKTOS}\n]"


def runtime_command(argv, *, check=True):
    return _command(argv, _work_end, maximum=60, check=check)


def runtime_stdout(argv):
    result = runtime_command(argv)
    if result["stderr"]:
        raise Refusal("runtime_command_diagnostic", stdout=result["stdout"], stderr=result["stderr"])
    return result["stdout"]


def runtime_identity(raw, package):
    expected = f"{package['name']}\t0\t1.2.5\t6.fc44\taarch64\t{package['installed_bytes']}\n".encode()
    if raw != expected:
        raise Refusal("runtime_package_identity")


def runtime_dependencies(raw, package):
    expected = [f"{name}\t{flags}\t{version}".encode() for name, flags, version in package["requires"]]
    if sorted(raw.splitlines()) != sorted(expected):
        raise Refusal("runtime_dependencies")


def runtime_files(raw, package):
    expected = ["\t".join(map(str, row)).encode() for row in package["files"]]
    if sorted(raw.splitlines()) != sorted(expected):
        raise Refusal("runtime_files")


def runtime_system():
    if sys.platform != "linux" or os.geteuid() != 0 or os.uname().machine != "aarch64":
        raise Refusal("runtime_platform")
    release = Path("/etc/os-release")
    if release.is_symlink():
        info = release.lstat()
        if info.st_uid or info.st_gid or release.resolve(strict=True) != Path("/usr/lib/os-release"):
            raise Refusal("runtime_platform")
        release = Path("/usr/lib/os-release")
    info = release.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid or info.st_gid or info.st_mode & 0o022:
        raise Refusal("runtime_platform")
    fields = dict(line.split("=", 1) for line in _read(release, 16384).decode().splitlines()
                  if "=" in line and not line.startswith("#"))
    if fields.get("ID", "").strip('"') != "fedora" or fields.get("VERSION_ID", "").strip('"') != "44":
        raise Refusal("runtime_platform")
    for executable in ("/usr/bin/rpm", "/usr/bin/rpmkeys"):
        info = Path(executable).lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid or info.st_gid or info.st_mode & 0o022:
            raise Refusal("runtime_tools")
    if not runtime_stdout(["/usr/bin/rpm", "--version"]).startswith(b"RPM version 6."):
        raise Refusal("runtime_tools")
    if runtime_stdout(["/usr/bin/rpm", "--eval", "%{_dbpath}"]) != b"/usr/lib/sysimage/rpm\n":
        raise Refusal("runtime_database")
    directory = Path("/usr/lib/sysimage/rpm")
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid or info.st_gid or info.st_mode & 0o022 or directory.resolve() != directory:
        raise Refusal("runtime_database")
    total = 0
    with os.scandir(directory) as entries:
        for count, entry in enumerate(entries, 1):
            if count > 4 or entry.name not in {"rpmdb.sqlite", "rpmdb.sqlite-shm", "rpmdb.sqlite-wal", ".rpm.lock"}:
                raise Refusal("runtime_database")
            item = entry.stat(follow_symlinks=False)
            if not stat.S_ISREG(item.st_mode) or item.st_uid or item.st_gid or item.st_nlink != 1 or item.st_mode & 0o022:
                raise Refusal("runtime_database")
            total += item.st_blocks * 512
    if total > 128 * 1024**2:
        raise Refusal("runtime_database")


def runtime_key():
    raw = runtime_stdout(["/usr/bin/rpmkeys", "--list", runtime_fingerprint])
    if raw.upper().split().count(runtime_fingerprint.encode()) != 1:
        raise Refusal("runtime_signing_key")


def runtime_signature(path):
    result = runtime_command(["/usr/bin/rpmkeys", "--checksig", str(path)])
    if result["stderr"] or result["stdout"] != f"{path}: digests signatures OK\n".encode():
        raise Refusal("runtime_signature", stdout=result["stdout"], stderr=result["stderr"])


def runtime_cache():
    directory = _active.mount / "runtime-rpms"
    if not directory.exists() and not directory.is_symlink():
        directory.mkdir(mode=0o700)
    _private(directory, directory=True)
    if directory.stat().st_dev != _active.mount.stat().st_dev:
        raise Refusal("runtime_cache_identity")
    allowed = {package["url"].rsplit("/", 1)[1] for package in runtime_packages}
    with os.scandir(directory) as entries:
        for count, entry in enumerate(entries, 1):
            if count > len(allowed) or entry.name not in allowed:
                raise Refusal("runtime_retained_download")
    return directory


class runtime_NoRedirect(runtime_request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise Refusal("runtime_download")


def runtime_open(url, timeout):
    # No ambient proxy or redirect may select a different transport endpoint.
    opener = runtime_request.build_opener(runtime_request.ProxyHandler({}), runtime_NoRedirect())
    return opener.open(runtime_request.Request(url, headers={"Accept-Encoding": "identity"}), timeout=timeout)


def runtime_download_expired(signum, frame):
    raise Refusal("runtime_download_deadline")


def runtime_download(package, path):
    # A total wall-clock alarm also bounds slow trickle reads. Socket timeouts
    # alone are inactivity limits and do not bound a complete response.
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise Refusal("runtime_download_timer_busy")
    partial = path.with_name(path.name + ".partial")
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    count = 0
    digest = runtime_hashlib.sha256()
    previous_handler = signal.signal(signal.SIGALRM, runtime_download_expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, _remaining(_work_end, 60))
        with runtime_open(package["url"], _remaining(_work_end, 20)) as response:
            if (response.status != 200 or response.geturl() != package["url"]
                    or response.headers.get("Content-Length") != str(package["bytes"])
                    or response.headers.get("Content-Encoding", "identity") != "identity"):
                raise Refusal("runtime_download")
            while True:
                _remaining(_work_end)
                chunk = response.read(min(65536, package["bytes"] + 1 - count))
                if not chunk:
                    break
                count += len(chunk)
                if count > package["bytes"]:
                    raise Refusal("runtime_download")
                digest.update(chunk)
                view = memoryview(chunk)
                while view:
                    view = view[os.write(fd, view):]
            if count != package["bytes"] or digest.hexdigest() != package["sha256"]:
                raise Refusal("runtime_download")
            os.fsync(fd)
    except (OSError, runtime_error.URLError, ValueError):
        raise Refusal("runtime_download") from None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        os.close(fd)
    # A no-overwrite link retains partial evidence on an unexpected collision.
    os.link(partial, path, follow_symlinks=False)
    partial.unlink()


def runtime_package(package, directory):
    path = directory / package["url"].rsplit("/", 1)[1]
    if not path.exists() and not path.is_symlink():
        runtime_download(package, path)
    identity = _private(path, size=package["bytes"])
    if path.stat().st_dev != directory.stat().st_dev:
        raise Refusal("runtime_cache_identity")
    if runtime_hashlib.sha256(_read(path, package["bytes"])).hexdigest() != package["sha256"]:
        raise Refusal("runtime_archive_digest")
    runtime_signature(path)
    runtime_identity(runtime_stdout(["/usr/bin/rpm", "-qp", "--queryformat", runtime_identity_format, str(path)]), package)
    runtime_dependencies(runtime_stdout(["/usr/bin/rpm", "-qp", "--queryformat",
                                        "[%{REQUIRENAME}\t%{REQUIREFLAGS}\t%{REQUIREVERSION}\n]", str(path)]), package)
    runtime_files(runtime_stdout(["/usr/bin/rpm", "-qp", "--queryformat", runtime_file_format, str(path)]), package)
    for option in ("--scripts", "--triggers", "--filetriggers"):
        if runtime_stdout(["/usr/bin/rpm", "-qp", option, str(path)]):
            raise Refusal("runtime_package_scripts")
    if _private(path, size=package["bytes"]) != identity:
        raise Refusal("runtime_cache_identity")
    return path


def runtime_installed():
    states = []
    for package in runtime_packages:
        result = runtime_command(["/usr/bin/rpm", "-q", "--queryformat", runtime_identity_format, package["name"]], check=False)
        if result["returncode"] == 0 and not result["stderr"]:
            runtime_identity(result["stdout"], package)
            states.append(True)
        elif (result["returncode"] == 1 and not result["stderr"]
              and result["stdout"] == f"package {package['name']} is not installed\n".encode()):
            states.append(False)
        else:
            raise Refusal("runtime_package_query", stdout=result["stdout"], stderr=result["stderr"])
    if len(set(states)) != 1:
        raise Refusal("runtime_partial_install")
    return states[0]


def runtime_verify_installed():
    if not runtime_installed():
        raise Refusal("runtime_install_incomplete")
    for package in runtime_packages:
        runtime_files(runtime_stdout(["/usr/bin/rpm", "-q", "--queryformat", runtime_file_format, package["name"]]), package)
        if runtime_stdout(["/usr/bin/rpm", "--verify", "--noscripts", package["name"]]):
            raise Refusal("runtime_installed_drift")
    runtime_system()


def runtime_preexisting():
    """Do not silently replace files left by an unowned or partial installation."""
    for package in runtime_packages:
        for filename, size, mode, user, group, digest, link in package["files"]:
            path = Path(filename)
            if not path.exists() and not path.is_symlink():
                continue
            info = path.lstat()
            if (mode != "40755" or not stat.S_ISDIR(info.st_mode)
                    or info.st_uid or info.st_gid or info.st_mode & 0o022):
                raise Refusal("runtime_preexisting_files")


def runtime_free():
    info = os.statvfs("/")
    return info.f_bavail * info.f_frsize


def install_runtime():
    """Install or verify only the reviewed two RPMs, under the active work deadline."""
    if _active is None or _work_end is None:
        raise Refusal("store_not_mounted")
    _remaining(_work_end)
    _verify(_active, _work_end)
    runtime_system()
    runtime_key()
    resumed = runtime_installed()
    before = runtime_free()
    if before < runtime_reserve + runtime_install_margin:
        raise Refusal("runtime_root_reserve")
    directory = runtime_cache()
    paths = [runtime_package(package, directory) for package in runtime_packages]
    _verify(_active, _work_end)
    if not resumed:
        runtime_preexisting()
        transaction = ["/usr/bin/rpm", "--install", "--noscripts", "--notriggers",
                       "--define", f"_tmppath {directory}"]
        runtime_command(transaction + ["--test"] + list(map(str, paths)))
        _verify(_active, _work_end)
        runtime_command(transaction + list(map(str, paths)))
    runtime_verify_installed()
    after = runtime_free()
    if after < runtime_reserve or before - after > runtime_install_margin:
        raise Refusal("runtime_root_reserve")
    _verify(_active, _work_end)
    return {"status": "runtime_ready", "resumed": resumed, "installed_bytes": 945234,
            "root_free_before": before, "root_free_after": after,
            "root_allocated_delta": max(0, before - after),
            "root_delta_scope": "filesystem available-space change, including concurrent system allocation",
            "packages": [{"name": package["name"], "version": "1.2.5-6.fc44.aarch64",
                          "sha256": package["sha256"], "bytes": package["bytes"]} for package in runtime_packages]}
