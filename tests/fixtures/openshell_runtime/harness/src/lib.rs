//! Preliminary Linux kernel tests for the exact reviewed OpenShell child filter.
//! Preparation supplies the hash-verified module; this is not the runtime crate.

#[cfg(not(target_os = "linux"))]
compile_error!("OpenShell child filter harness requires Linux");

#[cfg(target_os = "linux")]
pub mod linux {
    pub mod child_seccomp;
}
