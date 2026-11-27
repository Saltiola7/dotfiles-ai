"""Model trusted system anchors in synthetic tests under rootless evidence."""
from contextlib import ExitStack, contextmanager
import os
from pathlib import Path
import runpy
import sys
from unittest.mock import patch


@contextmanager
def trusted_fixture_anchors():
    # Native CI must exercise actual ownership. In a single-user namespace
    # the kernel cannot represent host root, even for these system anchors.
    if not sys.platform.startswith('linux') or os.getuid() == 0:
        yield
        return
    uid_map = Path('/proc/self/uid_map').read_text().split()
    if len(uid_map) != 3 or int(uid_map[0]) != os.getuid() or uid_map[2] != '1':
        yield
        return
    overflow = int(Path('/proc/sys/kernel/overflowuid').read_text())
    anchors = {Path('/'), Path('/tmp'), Path('/proc/sys/kernel/random/boot_id')}
    lstat, fstat = Path.lstat, os.fstat
    unmapped = {path: (info.st_dev, info.st_ino) for path in anchors
                if (info := lstat(path)).st_uid == overflow}
    identities = set(unmapped.values())

    def root_owner(info):
        fields = list(info)
        fields[4] = 0  # st_uid; preserve mode, device, inode and link count
        return os.stat_result(fields)

    def fixture_lstat(path, *args, **kwargs):
        info = lstat(path, *args, **kwargs)
        if info.st_uid == overflow and unmapped.get(path) == (info.st_dev, info.st_ino):
            return root_owner(info)
        return info

    def fixture_fstat(fd):
        info = fstat(fd)
        if info.st_uid == overflow and (info.st_dev, info.st_ino) in identities:
            return root_owner(info)
        return info

    with ExitStack() as stack:
        if unmapped:
            stack.enter_context(patch.object(Path, 'lstat', fixture_lstat))
            stack.enter_context(patch.object(os, 'fstat', fixture_fstat))
        yield


if __name__ == '__main__':
    # Subprocess launcher test: execve still runs the reporting fake binary.
    sys.argv.pop(0)
    with trusted_fixture_anchors():
        sys.exit(runpy.run_path(sys.argv[0])['main']())
