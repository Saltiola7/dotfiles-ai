"""Held-descriptor admission for the two closed Cargo binary outputs."""
import contextlib
import re
import sys


def full_cargo_identity(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,info.st_nlink,
            info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def full_cargo_runtime_fail(reason,path,info=None,matches=()):
    if info is None:
        try:info=Path(path).lstat()
        except OSError:pass
    fields=('device','inode','mode','uid','gid','links','size','mtime_ns','ctime_ns')
    report={'reason':reason,'path':str(path)[:512],
            'observed':dict(zip(fields,full_cargo_identity(info))) if info is not None else None,
            'companions':[name[:128] for name in matches[:2]]}
    raise RuntimeError('full_cargo_runtime:'+json.dumps(report,sort_keys=True,separators=(',',':')))


def full_cargo_artifact_name(selection):
    if type(selection) is not str or selection not in ('runtime','agent-probe'):
        raise RuntimeError('full_cargo_artifact_selection')
    return 'openshell-sandbox' if selection=='runtime' else 'openshell-agent-filter-probe'


@contextlib.contextmanager
def full_cargo_runtime_artifact(selection='runtime'):
    """Hold one closed artifact and its independently accounted Cargo alias."""
    name=full_cargo_artifact_name(selection)
    binary=WORK/'full-target-1/release'/name;deps=binary.parent/'deps'
    owned=[];directories=[];active=WORK;companion_fd=None
    def directory_identity(info):return (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid)
    try:
        remaining();root=WORK.lstat();device=root.st_dev
        if WORK.resolve()!=WORK:full_cargo_runtime_fail('root_alias',WORK,root)
        parent=None
        for part in (None,'full-target-1','release','deps'):
            active=WORK if part is None else active/part
            fd=os.open(active if part is None else part,
                os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,
                **({} if parent is None else {'dir_fd':parent}))
            owned.append(fd);info=os.fstat(fd)
            if (not stat.S_ISDIR(info.st_mode) or info.st_dev!=device or info.st_uid!=os.getuid()
                    or info.st_gid!=os.getgid() or info.st_mode&0o022
                    or directory_identity(info)!=directory_identity(active.lstat())):
                full_cargo_runtime_fail('ancestor',active,info)
            directories.append((active,fd,directory_identity(info)));parent=fd
        release_fd=directories[-2][1];deps_fd=directories[-1][1]
        active=binary
        fd=os.open(binary.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=release_fd)
        owned.append(fd);info=os.fstat(fd);identity=full_cargo_identity(info)
        if (not stat.S_ISREG(info.st_mode) or info.st_dev!=device or info.st_uid!=os.getuid()
                or info.st_gid!=os.getgid() or info.st_mode&0o022 or not info.st_mode&stat.S_IXUSR
                or info.st_nlink not in (1,2) or not 0<info.st_size<=256*1024**2):
            full_cargo_runtime_fail('metadata',binary,info)
        def aliases():
            matches=[]
            with os.scandir(deps_fd) as entries:
                for count,entry in enumerate(entries):
                    remaining()
                    if count>=8192:full_cargo_runtime_fail('entry_budget',deps,os.fstat(deps_fd),matches)
                    observed=entry.stat(follow_symlinks=False)
                    if (observed.st_dev,observed.st_ino)!=identity[:2]:continue
                    if (re.fullmatch(name.replace('-','_')+r'-[0-9a-f]{16}',entry.name) is None
                            or full_cargo_identity(observed)!=identity):
                        full_cargo_runtime_fail('companion',deps/entry.name,observed,matches)
                    matches.append(entry.name)
                    if len(matches)>1:full_cargo_runtime_fail('aliases',binary,os.fstat(fd),matches)
            if len(matches)!=identity[5]-1:full_cargo_runtime_fail('aliases',binary,os.fstat(fd),matches)
            return matches
        matches=aliases();companion=matches[0] if matches else None
        if companion:
            active=deps/companion
            companion_fd=os.open(companion,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=deps_fd)
            owned.append(companion_fd)
        def check_paths():
            remaining()
            for path,directory_fd,expected in directories:
                observed=os.fstat(directory_fd)
                if directory_identity(observed)!=expected or directory_identity(path.lstat())!=expected:
                    full_cargo_runtime_fail('ancestor_changed',path,observed)
            for path,file_fd in ((binary,fd),*(([(deps/companion,companion_fd)]) if companion else [])):
                observed=os.fstat(file_fd)
                if full_cargo_identity(observed)!=identity or full_cargo_identity(path.lstat())!=identity:
                    full_cargo_runtime_fail('file_changed',path,observed,matches)
        check_paths()
        yield fd,{'link_count':identity[5],'companion':companion}
        check_paths()
        if aliases()!=matches:full_cargo_runtime_fail('aliases_changed',binary,os.fstat(fd),matches)
        check_paths()
    except OSError:
        full_cargo_runtime_fail('io',active)
    finally:
        failed=False;primary=sys.exc_info()[1]
        for fd in reversed(owned):
            try:os.close(fd)
            except OSError:failed=True
        if failed:
            if primary is None:full_cargo_runtime_fail('descriptor_close',active)
            elif isinstance(primary,RuntimeError):primary.args=(str(primary)+'; runtime_descriptor_close_failed',)


def full_cargo_runtime_digest(fd,selection='runtime'):
    binary=WORK/'full-target-1/release'/full_cargo_artifact_name(selection)
    before=full_cargo_identity(os.fstat(fd));value=hashlib.sha256();offset=0
    if not 0<before[6]<=256*1024**2:full_cargo_runtime_fail('size',binary,os.fstat(fd))
    while offset<before[6]:
        remaining();block=os.pread(fd,min(1024*1024,before[6]-offset),offset)
        if not block:full_cargo_runtime_fail('short_read',binary,os.fstat(fd))
        value.update(block);offset+=len(block)
    remaining()
    if full_cargo_identity(os.fstat(fd))!=before:
        full_cargo_runtime_fail('hash_changed',binary,os.fstat(fd))
    return value.hexdigest()
