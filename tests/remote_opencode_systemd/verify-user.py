#!/usr/bin/env python3
"""Credential-free F01 fixture only; never print native output or registration."""
import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import signal
import stat
import subprocess
import sys
import time
from urllib.parse import urlsplit


HOME = Path('/home/fixture')
SOURCE = HOME / '.local/share/chezmoi-dotfiles-ai'
CONFIG = HOME / '.config/dotfiles-ai/chezmoi.toml'
NATIVE = HOME / '.opencode/bin/opencode'
WRAPPER = HOME / '.local/bin/opencode'
UNIT = 'opencode-shared.service'


class QualificationFailure(RuntimeError):
    def __init__(self, status):
        self.status = status if 0 < status < 256 else 1


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(*args, timeout=10, env=None):
    # Captured output is intentionally never included in exceptions/diagnostics.
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                            env=env, cwd=HOME)
    if result.returncode:
        raise QualificationFailure(result.returncode if result.returncode > 0
                                   else 128 - result.returncode)
    return result.stdout.strip()


def systemctl(*args):
    return run('systemctl', '--user', *args)


def apply():
    run(str(HOME / '.local/bin/chezmoi'), '-c', str(CONFIG), '-S', str(SOURCE),
        'apply', timeout=180)
    require(not run('git', '-C', str(SOURCE), 'status', '--porcelain'),
            'fixture source generation changed')


def prepare():
    require(not (SOURCE / '.git').exists(), 'fixture already initialized')
    # Only the allowlisted public source is committed, once, in this disposable HOME.
    run('git', '-C', str(SOURCE), 'init', '--initial-branch=fixture')
    run('git', '-C', str(SOURCE), 'add', '.')
    run('git', '-C', str(SOURCE), '-c', 'user.name=F01 fixture',
        '-c', 'user.email=f01@example.invalid', '-c', 'commit.gpgsign=false',
        'commit', '-m', 'Public disposable F01 source')
    run('git', '-C', str(SOURCE), 'remote', 'add', 'origin',
        'https://github.com/Saltiola7/dotfiles-ai.git')
    run('git', '-C', str(SOURCE), 'checkout', '--detach')
    CONFIG.parent.mkdir(parents=True, mode=0o700)
    # Public bootstrap helper only downloads and verifies chezmoi. No stubs.
    spec = importlib.util.spec_from_file_location('bootstrap', '/opt/f01/bootstrap.py')
    if spec is None or spec.loader is None:
        raise RuntimeError('bootstrap loader unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.prepare_config()
    module.install_chezmoi()
    # Empty real config prevents unrelated plugins/MCP/provider integrations.
    # This fixture qualifies unit/wrapper/native behavior, NOT the full profile.
    config_dir = HOME / '.config/opencode'
    config_dir.mkdir(mode=0o700)
    (config_dir / 'opencode.json').write_text('{}\n')
    apply()  # The managed hook alone may start the initial service.
    ready()
    require(systemctl('is-enabled', UNIT) == 'enabled', 'unit not enabled')
    require((HOME / '.config/systemd/user/default.target.wants' / UNIT).is_symlink(),
            'unit not enabled under default.target')
    # A fresh /run is the restart witness; written by root-side prepare.


def owner(pid):
    proc = Path(f'/proc/{pid}')
    require(pid > 1 and proc.stat().st_uid == os.getuid(), 'service PID not fixture-owned')
    require((proc / 'exe').resolve() == NATIVE, 'service PID is not managed native binary')
    require(UNIT in (proc / 'cgroup').read_text(), 'service PID outside systemd unit')


def listening(pid, port):
    sockets = set()
    for fd in Path(f'/proc/{pid}/fd').iterdir():
        try:
            target = os.readlink(fd)
        except FileNotFoundError:
            continue
        if target.startswith('socket:['):
            sockets.add(target[8:-1])
    found = False
    for table in ('tcp', 'tcp6'):
        for row in Path(f'/proc/net/{table}').read_text().splitlines()[1:]:
            fields = row.split()
            if fields[3] != '0A' or fields[9] not in sockets:
                continue
            address, raw_port = fields[1].split(':')
            require(address in {'0100007F', '00000000000000000000000001000000'},
                    'service has a non-loopback TCP listener')
            found |= int(raw_port, 16) == port
    require(found, 'registered service port not owned/listening')


def connected(pid, port):
    sockets = set()
    for fd in Path(f'/proc/{pid}/fd').iterdir():
        try:
            target = os.readlink(fd)
        except FileNotFoundError:
            continue
        if target.startswith('socket:['):
            sockets.add(target[8:-1])
    for table in ('tcp', 'tcp6'):
        for row in Path(f'/proc/net/{table}').read_text().splitlines()[1:]:
            fields = row.split()
            if fields[3] == '01' and fields[9] in sockets:
                address, raw_port = fields[2].split(':')
                if (address in {'0100007F', '00000000000000000000000001000000'}
                        and int(raw_port, 16) == port):
                    return True
    return False


def inspect():
    require(systemctl('is-active', UNIT) == 'active', 'service not active')
    pid = int(systemctl('show', UNIT, '-p', 'MainPID', '--value'))
    owner(pid)
    server = run(str(WRAPPER), 'service', 'status', timeout=5)
    endpoint = urlsplit(server)
    require(endpoint.scheme == 'http' and endpoint.hostname == '127.0.0.1'
            and endpoint.port and not endpoint.username and not endpoint.password,
            'invalid service endpoint')
    registration = HOME / '.local/state/opencode/service.json'
    with os.fdopen(os.open(registration, os.O_RDONLY | os.O_NOFOLLOW)) as stream:
        metadata = os.fstat(stream.fileno())
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == os.getuid()
                and not metadata.st_mode & 0o077 and metadata.st_size <= 65536,
                'unsafe service registration')
        service = json.load(stream)
    require(service.get('pid') == pid and service.get('url') == server
            and isinstance(service.get('password'), str) and service['password'],
            'service registration mismatch')
    environment = dict(os.environ, OPENCODE_PASSWORD=service['password'])
    info = json.loads(run(str(NATIVE), 'api', '--server', server, 'get', '/api/info',
                          env=environment, timeout=5))
    version = run(str(NATIVE), '--version').removeprefix('opencode v')
    require(info.get('version') == version and info.get('pid') == pid,
            'explicit authenticated API identity mismatch')
    listening(pid, endpoint.port)
    return pid, server


def ready(previous=None):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            pid, server = inspect()
            if pid != previous:
                return pid, server
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            pass
        time.sleep(1)
    raise RuntimeError('bounded native service readiness failed')


def attach(pid, server):
    master, slave = pty.openpty()
    process = None
    try:
        process = subprocess.Popen([str(WRAPPER)], stdin=slave, stdout=slave,
                                   stderr=slave, cwd=HOME, start_new_session=True)
        os.close(slave)
        slave = None
        deadline = time.monotonic() + 12
        attached = False
        connection = False
        output = False
        while time.monotonic() < deadline:
            require(process.poll() is None, 'wrapper TUI exited before idle proof')
            proc = Path(f'/proc/{process.pid}')
            argv = (proc / 'cmdline').read_bytes().split(b'\0')
            if b'--server' in argv:
                index = argv.index(b'--server')
                attached |= (argv[index + 1] == server.encode()
                              and (proc / 'exe').resolve() == NATIVE)
                connection |= connected(process.pid, urlsplit(server).port)
            if select.select([master], [], [], 0.2)[0]:
                output |= bool(os.read(master, 65536))  # Discard all TUI output.
        require(attached and connection and output, 'managed wrapper did not connect a live TUI')
        require(inspect()[0] == pid, 'TUI replaced the boot-owned service')
        # No prompt/model selection or provider request: just idle, then exit.
        process.send_signal(signal.SIGINT)
        try:
            result = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.send_signal(signal.SIGINT)
            result = process.wait(timeout=5)
        require(result in (0, 130, -signal.SIGINT), 'TUI exit failed')
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        os.close(master)
        if slave is not None:
            os.close(slave)


def verify():
    require(systemctl('is-enabled', UNIT) == 'enabled', 'unit not boot enabled')
    require(systemctl('show', UNIT, '-p', 'Restart', '--value') == 'on-failure',
            'unit restart policy mismatch')
    pid, server = ready()  # No apply/start before boot readiness proof.
    attach(pid, server)
    apply()
    require(inspect()[0] == pid, 'reapply replaced healthy service')
    before = int(systemctl('show', UNIT, '-p', 'NRestarts', '--value'))
    require(int(systemctl('show', UNIT, '-p', 'MainPID', '--value')) == pid,
            'service PID changed before crash injection')
    owner(pid)
    # pidfd makes the single owned MainPID the target, never a reused process ID.
    descriptor = os.pidfd_open(pid)
    try:
        owner(pid)
        signal.pidfd_send_signal(descriptor, signal.SIGKILL)
    finally:
        os.close(descriptor)
    new_pid, _ = ready(previous=pid)
    require(new_pid != pid and int(systemctl('show', UNIT, '-p', 'NRestarts', '--value')) > before,
            'systemd did not recover the failed MainPID')
    print('F01: boot, API identity, loopback, TUI attach, reapply, crash recovery verified')


if __name__ == '__main__':
    try:
        require(os.getuid() == 1000 and Path.home() == HOME, 'wrong fixture identity')
        require(len(sys.argv) == 2 and sys.argv[1] in {'prepare', 'verify'}, 'invalid stage')
        {'prepare': prepare, 'verify': verify}[sys.argv[1]]()
    except Exception as error:
        # Neither subprocess output nor exception values can leak registration auth.
        print('F01: qualification failed (native output suppressed)', file=sys.stderr)
        sys.exit(error.status if isinstance(error, QualificationFailure)
                 else 124 if isinstance(error, subprocess.TimeoutExpired) else 1)
