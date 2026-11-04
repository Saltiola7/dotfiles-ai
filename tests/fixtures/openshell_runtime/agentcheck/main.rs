//! Fixed agent comparison; FD3 belongs only to trusted code.
use std::ffi::CString;
use std::io;
use std::os::unix::process::{CommandExt, ExitStatusExt};
use std::process::{Command, ExitCode, Stdio};

#[path = "upstream_child_seccomp.rs"]
mod upstream_child_seccomp;
#[path = "patched_child_seccomp.rs"]
mod patched_child_seccomp;

const WORK: &str = "/var/lib/dotfiles-ai-openshell-build/store/work";

enum Filter {
    None,
    Upstream(upstream_child_seccomp::ChildHardeningProgram),
    Patched(patched_child_seccomp::ChildHardeningProgram),
}

impl Filter {
    fn count(&self) -> usize {
        match self {
            Self::None => 0,
            Self::Upstream(value) => value.instruction_count(),
            Self::Patched(value) => value.instruction_count(),
        }
    }

    fn install(&mut self) -> io::Result<()> {
        match self {
            Self::None => upstream_child_seccomp::mark_inherited_descriptors_close_on_exec(),
            Self::Upstream(value) => value.install(),
            Self::Patched(value) => value.install(),
        }
    }
}

// Fixed 32-byte little-endian records. This function is also called after fork:
// only stack copies and the async-signal-safe write syscall are permitted here.
fn record(event: u8, mode: u8, values: [i32; 6]) -> io::Result<()> {
    let mut bytes = [0_u8; 32];
    bytes[..4].copy_from_slice(b"OAC1");
    bytes[4] = event;
    bytes[5] = mode;
    for (index, value) in values.iter().enumerate() {
        bytes[8 + index * 4..12 + index * 4].copy_from_slice(&value.to_le_bytes());
    }
    let mut offset = 0;
    while offset < bytes.len() {
        // SAFETY: FD3 is a verified pipe; bytes remains live for this write.
        let written = unsafe { libc::write(3, bytes[offset..].as_ptr().cast(), bytes.len() - offset) };
        if written < 0 {
            let error = io::Error::last_os_error();
            if error.raw_os_error() == Some(libc::EINTR) { continue; }
            return Err(error);
        }
        if written == 0 { return Err(io::Error::from_raw_os_error(libc::EIO)); }
        offset += written as usize;
    }
    Ok(())
}

fn socket_result(domain: i32) -> i32 {
    // SAFETY: scalar socket arguments; successful descriptors are closed here.
    let fd = unsafe { libc::socket(domain, libc::SOCK_STREAM | libc::SOCK_CLOEXEC, 0) };
    if fd < 0 { io::Error::last_os_error().raw_os_error().unwrap_or(libc::EIO) }
    else { unsafe { libc::close(fd); } 0 }
}

fn pair_result(socket: bool) -> i32 {
    let mut fds = [-1; 2];
    // SAFETY: fds contains space for both descriptors and stays live throughout.
    let result = unsafe {
        if socket { libc::socketpair(libc::AF_UNIX, libc::SOCK_STREAM | libc::SOCK_CLOEXEC, 0, fds.as_mut_ptr()) }
        else { libc::pipe2(fds.as_mut_ptr(), libc::O_CLOEXEC) }
    };
    if result < 0 { io::Error::last_os_error().raw_os_error().unwrap_or(libc::EIO) }
    else { unsafe { libc::close(fds[0]); libc::close(fds[1]); } 0 }
}

fn stdio_mask() -> i32 {
    let mut mask = 0;
    for fd in 0..3 {
        // SAFETY: stat consists of plain fields; fstat initializes it on success.
        let mut info: libc::stat = unsafe { std::mem::zeroed() };
        if unsafe { libc::fstat(fd, &mut info) } != 0 { continue; }
        let kind = info.st_mode & libc::S_IFMT;
        if kind == libc::S_IFIFO || (fd == 0 && kind == libc::S_IFCHR && info.st_rdev == libc::makedev(1, 3)) {
            mask |= 1 << fd;
        }
    }
    mask
}

fn run() -> io::Result<()> {
    // Drop the held launch executable before preparing or forking a child.
    if unsafe { libc::syscall(libc::SYS_close_range, 4_u32, u32::MAX, 0_u32) } != 0 {
        return Err(io::Error::last_os_error());
    }
    if unsafe { libc::prctl(libc::PR_SET_DUMPABLE, 0, 0, 0, 0) } != 0
        || unsafe { libc::prctl(libc::PR_GET_DUMPABLE, 0, 0, 0, 0) } != 0 {
        return Err(io::Error::from_raw_os_error(libc::EPERM));
    }
    let mut info: libc::stat = unsafe { std::mem::zeroed() };
    if unsafe { libc::fstat(3, &mut info) } != 0 || info.st_mode & libc::S_IFMT != libc::S_IFIFO
        || unsafe { libc::fcntl(3, libc::F_GETFL) } & libc::O_ACCMODE != libc::O_WRONLY {
        return Err(io::Error::from_raw_os_error(libc::EBADF));
    }
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 { return Err(io::Error::from_raw_os_error(libc::EINVAL)); }
    let probe = args[1].as_str();
    let mode = match args[2].as_str() {
        "unfiltered" => 0, "upstream" => 1, "patched" => 2,
        _ => return Err(io::Error::from_raw_os_error(libc::EINVAL)),
    };
    let (agent, argv): (&str, &[&str]) = match probe {
        "codex-version" => ("codex/bin/codex", &["--version"]),
        "codex-help" => ("codex/bin/codex", &["--help"]),
        "codex-empty-login" => ("codex/bin/codex", &["login", "status"]),
        "codex-stdio" => ("codex/bin/codex", &["app-server", "--stdio"]),
        "opencode-version" => ("opencode/opencode", &["--version"]),
        "opencode-help" => ("opencode/opencode", &["--help"]),
        "opencode-rg" => ("opencode/opencode", &["--pure", "debug", "rg", "files", "--limit", "1", "--glob", "sentinel.txt"]),
        _ => return Err(io::Error::from_raw_os_error(libc::EINVAL)),
    };
    let parent = std::process::id();
    let mut filter = match mode {
        0 => Filter::None,
        1 => Filter::Upstream(upstream_child_seccomp::prepare(parent)?),
        _ => Filter::Patched(patched_child_seccomp::prepare(parent)?),
    };
    let parent_pipe = CString::new(format!("/proc/{parent}/fd/3")).unwrap();
    let case = format!("{WORK}/agent-cases-1/{probe}-{}", args[2]);
    let mut command = Command::new(format!("{WORK}/agent-assets-1/{agent}"));
    command.args(argv).current_dir(format!("{case}/workspace")).env_clear()
        .env("PATH", format!("{WORK}/agent-assets-1/codex/codex-path:/usr/bin:/bin"))
        .env("LC_ALL", "C").env("LANG", "C").env("TERM", "dumb").env("NO_COLOR", "1")
        .stdin(Stdio::inherit()).stdout(Stdio::inherit()).stderr(Stdio::inherit());
    for (key, directory) in [
        ("HOME", "home"), ("CODEX_HOME", "codex"), ("XDG_CONFIG_HOME", "config"),
        ("XDG_DATA_HOME", "data"), ("XDG_STATE_HOME", "state"), ("XDG_CACHE_HOME", "cache"),
        ("TMPDIR", "tmp"), ("CARGO_HOME", "cargo"), ("RUSTUP_HOME", "rustup"), ("CARGO_TARGET_DIR", "target"),
    ] { command.env(key, format!("{case}/{directory}")); }
    for key in ["OPENCODE_PURE", "OPENCODE_DISABLE_DEFAULT_PLUGINS", "OPENCODE_DISABLE_PROJECT_CONFIG",
        "OPENCODE_DISABLE_AUTOUPDATE", "OPENCODE_DISABLE_MODELS_FETCH", "OPENCODE_DISABLE_EXTERNAL_SKILLS",
        "OPENCODE_DISABLE_CLAUDE_CODE", "OPENCODE_DISABLE_LSP_DOWNLOAD", "OPENCODE_DISABLE_FFF",
        "OPENCODE_DISABLE_TERMINAL_TITLE"] { command.env(key, "1"); }
    command.env("OPENCODE_EXPERIMENTAL_DISABLE_FILEWATCHER", "true")
        .env("OPENCODE_CONFIG_CONTENT", "{\"autoupdate\":false,\"plugin\":[]}");
    record(1, mode, [parent as i32, filter.count() as i32, 1, 0, unsafe { libc::getppid() }, 0])?;
    // SAFETY: every allocation and filter preparation precedes fork. The hook
    // uses only prepared memory, scalar syscalls, stack storage and pipe writes.
    unsafe {
        command.pre_exec(move || {
            let limits = libc::rlimit { rlim_cur: 0, rlim_max: 0 };
            if libc::setrlimit(libc::RLIMIT_CORE, &limits) != 0
                || libc::prctl(libc::PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0 {
                return Err(io::Error::last_os_error());
            }
            for signal in [libc::SIGPIPE, libc::SIGINT, libc::SIGTERM] {
                let mut action: libc::sigaction = std::mem::zeroed();
                action.sa_sigaction = libc::SIG_DFL;
                libc::sigemptyset(&mut action.sa_mask);
                if libc::sigaction(signal, &action, std::ptr::null_mut()) != 0 {
                    return Err(io::Error::last_os_error());
                }
            }
            let installed = filter.install();
            let error = installed.as_ref().err().and_then(io::Error::raw_os_error).unwrap_or(0);
            record(2, mode, [error, libc::getpid(), i32::from(mode != 0), 0, 0, 0])?;
            installed?;
            let access = libc::open(parent_pipe.as_ptr(), libc::O_WRONLY | libc::O_CLOEXEC);
            let denied = if access < 0 { io::Error::last_os_error().raw_os_error().unwrap_or(libc::EIO) }
                else { libc::close(access); 0 };
            let cloexec = i32::from(libc::fcntl(3, libc::F_GETFD) & libc::FD_CLOEXEC != 0);
            let stdio = stdio_mask();
            let nnp = libc::prctl(libc::PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0);
            let dumpable = libc::prctl(libc::PR_GET_DUMPABLE, 0, 0, 0, 0);
            record(6, mode, [denied, cloexec, stdio, nnp, dumpable, 0])?;
            if ![libc::EPERM, libc::EACCES].contains(&denied) || cloexec != 1 || stdio != 7 || nnp != 1 || dumpable != 0 {
                return Err(io::Error::from_raw_os_error(libc::EPROTO));
            }
            let unix = socket_result(libc::AF_UNIX);
            let pair = pair_result(true);
            let inet = socket_result(libc::AF_INET);
            let pipe = pair_result(false);
            record(3, mode, [unix, pair, inet, pipe, 0, 0])?;
            let expected = if mode == 2 { libc::EPERM } else { 0 };
            if unix != expected || pair != expected || inet != 0 || pipe != 0 {
                return Err(io::Error::from_raw_os_error(libc::EPROTO));
            }
            Ok(())
        });
    }
    match command.spawn() {
        Ok(mut child) => {
            record(4, mode, [0, child.id() as i32, 0, 0, 0, 0])?;
            let status = child.wait()?;
            record(5, mode, [status.code().unwrap_or(-1), status.signal().unwrap_or(0),
                            i32::from(status.core_dumped()), 0, 0, 0])?;
        }
        Err(error) => record(4, mode, [error.raw_os_error().unwrap_or(libc::EIO), 0, 0, 0, 0, 0])?,
    }
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => { eprintln!("agent fixture: {error}"); ExitCode::from(125) }
    }
}
