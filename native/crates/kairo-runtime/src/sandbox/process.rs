use kairo_protocol::sandbox::{EnvironmentMode, EnvironmentPolicy};
use std::collections::HashMap;
use std::io;
use std::path::Path;
use tokio::io::AsyncReadExt;
use tokio::process::{Child, Command};
use tracing::{debug, warn};

#[cfg(windows)]
#[allow(
    non_snake_case,
    non_upper_case_globals,
    dead_code,
    clippy::upper_case_acronyms
)]
mod win32 {
    use std::ffi::c_void;
    pub type HANDLE = *mut c_void;
    pub type BOOL = i32;

    pub const JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: u32 = 0x0000_2000;
    pub const JOB_OBJECT_LIMIT_PROCESS_MEMORY: u32 = 0x0000_0100;
    pub const JOB_OBJECT_LIMIT_JOB_MEMORY: u32 = 0x0000_0200;
    pub const JOB_OBJECT_LIMIT_ACTIVE_PROCESS: u32 = 0x0000_0008;

    pub const JobObjectBasicAccountingInformation: u32 = 1;
    pub const JobObjectExtendedLimitInformation: u32 = 9;

    #[repr(C)]
    #[derive(Default)]
    pub struct IO_COUNTERS {
        pub ReadOperationCount: u64,
        pub WriteOperationCount: u64,
        pub OtherOperationCount: u64,
        pub ReadTransferCount: u64,
        pub WriteTransferCount: u64,
        pub OtherTransferCount: u64,
    }

    #[repr(C)]
    #[derive(Default)]
    pub struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
        pub PerProcessUserTimeLimit: i64,
        pub PerJobUserTimeLimit: i64,
        pub LimitFlags: u32,
        pub MinimumWorkingSetSize: usize,
        pub MaximumWorkingSetSize: usize,
        pub ActiveProcessLimit: u32,
        pub Affinity: usize,
        pub PriorityClass: u32,
        pub SchedulingClass: u32,
    }

    #[repr(C)]
    #[derive(Default)]
    pub struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
        pub BasicLimitInformation: JOBOBJECT_BASIC_LIMIT_INFORMATION,
        pub IoInfo: IO_COUNTERS,
        pub ProcessMemoryLimit: usize,
        pub JobMemoryLimit: usize,
        pub PeakProcessMemoryUsed: usize,
        pub PeakJobMemoryUsed: usize,
    }

    #[repr(C)]
    #[derive(Default)]
    pub struct JOBOBJECT_BASIC_ACCOUNTING_INFORMATION {
        pub TotalUserTime: i64,
        pub TotalKernelTime: i64,
        pub ThisPeriodTotalUserTime: i64,
        pub ThisPeriodTotalKernelTime: i64,
        pub TotalPageFaultCount: u32,
        pub TotalProcesses: u32,
        pub ActiveProcesses: u32,
        pub TotalTerminatedProcesses: u32,
    }

    #[link(name = "kernel32")]
    extern "system" {
        pub fn CreateJobObjectW(lpJobAttributes: *mut c_void, lpName: *const u16) -> HANDLE;
        pub fn SetInformationJobObject(
            hJob: HANDLE,
            JobObjectInformationClass: u32,
            lpJobInformation: *const c_void,
            cbJobInformationLength: u32,
        ) -> BOOL;
        pub fn QueryInformationJobObject(
            hJob: HANDLE,
            JobObjectInformationClass: u32,
            lpJobInformation: *mut c_void,
            cbJobInformationLength: u32,
            lpReturnLength: *mut u32,
        ) -> BOOL;
        pub fn AssignProcessToJobObject(hJob: HANDLE, hProcess: HANDLE) -> BOOL;
        pub fn TerminateJobObject(hJob: HANDLE, uExitCode: u32) -> BOOL;
        pub fn CloseHandle(hObject: HANDLE) -> BOOL;
    }
}

/// Metrics sampled directly from the OS process job container.
#[derive(Debug, Clone, Default)]
pub struct JobMetrics {
    pub peak_memory_bytes: Option<u64>,
    pub current_memory_bytes: Option<u64>,
    pub total_cpu_time_ms: Option<u64>,
    pub user_cpu_time_ms: Option<u64>,
    pub kernel_cpu_time_ms: Option<u64>,
    pub total_processes: u32,
    pub active_processes: u32,
}

/// Platform-specific process tree container ensuring complete termination of all children.
pub struct ProcessJobContainer {
    #[cfg(windows)]
    job_handle: win32::HANDLE,
    #[cfg(unix)]
    pgid: Option<i32>,
}

// Safety: The raw HANDLE on Windows is Send and Sync across thread boundaries
// as it represents an OS kernel object with thread-safe Win32 operations.
unsafe impl Send for ProcessJobContainer {}
unsafe impl Sync for ProcessJobContainer {}

impl ProcessJobContainer {
    pub fn noop() -> Self {
        Self {
            #[cfg(windows)]
            job_handle: std::ptr::null_mut(),
            #[cfg(unix)]
            pgid: None,
        }
    }

    pub fn new() -> io::Result<Self> {
        Self::new_with_limits(&Default::default(), &Default::default())
    }

    /// Construct a process container configured with hard OS kernel memory and process count limits.
    pub fn new_with_limits(
        budget: &kairo_protocol::ResourceBudget,
        process_tree: &kairo_protocol::ProcessTreePolicy,
    ) -> io::Result<Self> {
        #[cfg(windows)]
        {
            let handle = unsafe { win32::CreateJobObjectW(std::ptr::null_mut(), std::ptr::null()) };
            if handle.is_null() {
                return Err(io::Error::last_os_error());
            }

            let mut info = win32::JOBOBJECT_EXTENDED_LIMIT_INFORMATION::default();
            info.BasicLimitInformation.LimitFlags = win32::JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;

            // Enforce memory limits if configured
            if let Some(max_mem) = budget.max_memory_bytes {
                let limit_bytes = max_mem as usize;
                info.ProcessMemoryLimit = limit_bytes;
                info.JobMemoryLimit = limit_bytes;
                info.BasicLimitInformation.LimitFlags |=
                    win32::JOB_OBJECT_LIMIT_JOB_MEMORY | win32::JOB_OBJECT_LIMIT_PROCESS_MEMORY;
            }

            // Enforce child process creation limits
            if !process_tree.allow_child_processes {
                info.BasicLimitInformation.ActiveProcessLimit = 1;
                info.BasicLimitInformation.LimitFlags |= win32::JOB_OBJECT_LIMIT_ACTIVE_PROCESS;
            } else if process_tree.max_children > 0 {
                info.BasicLimitInformation.ActiveProcessLimit = process_tree.max_children + 1;
                info.BasicLimitInformation.LimitFlags |= win32::JOB_OBJECT_LIMIT_ACTIVE_PROCESS;
            }

            let res = unsafe {
                win32::SetInformationJobObject(
                    handle,
                    win32::JobObjectExtendedLimitInformation,
                    &info as *const _ as *const _,
                    std::mem::size_of::<win32::JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
                )
            };

            if res == 0 {
                unsafe { win32::CloseHandle(handle) };
                return Err(io::Error::last_os_error());
            }

            Ok(Self { job_handle: handle })
        }
        #[cfg(unix)]
        {
            let _ = (budget, process_tree);
            Ok(Self { pgid: None })
        }
    }

    /// Query low-level process metrics directly from the kernel Job Object.
    pub fn query_metrics(&self) -> JobMetrics {
        #[cfg(windows)]
        {
            if self.job_handle.is_null() {
                return JobMetrics::default();
            }

            let mut metrics = JobMetrics::default();

            // 1. Query extended limits to obtain PeakJobMemoryUsed
            let mut ext_info = win32::JOBOBJECT_EXTENDED_LIMIT_INFORMATION::default();
            let res_ext = unsafe {
                win32::QueryInformationJobObject(
                    self.job_handle,
                    win32::JobObjectExtendedLimitInformation,
                    &mut ext_info as *mut _ as *mut _,
                    std::mem::size_of::<win32::JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
                    std::ptr::null_mut(),
                )
            };
            if res_ext != 0 {
                let peak = ext_info
                    .PeakJobMemoryUsed
                    .max(ext_info.PeakProcessMemoryUsed) as u64;
                metrics.peak_memory_bytes = if peak > 0 { Some(peak) } else { None };
            }

            // 2. Query basic accounting to obtain CPU times and process counts
            let mut acct_info = win32::JOBOBJECT_BASIC_ACCOUNTING_INFORMATION::default();
            let res_acct = unsafe {
                win32::QueryInformationJobObject(
                    self.job_handle,
                    win32::JobObjectBasicAccountingInformation,
                    &mut acct_info as *mut _ as *mut _,
                    std::mem::size_of::<win32::JOBOBJECT_BASIC_ACCOUNTING_INFORMATION>() as u32,
                    std::ptr::null_mut(),
                )
            };
            if res_acct != 0 {
                // 100-ns intervals to milliseconds: divide by 10,000
                let user_ms = (acct_info.TotalUserTime / 10_000).max(0) as u64;
                let kernel_ms = (acct_info.TotalKernelTime / 10_000).max(0) as u64;
                metrics.user_cpu_time_ms = Some(user_ms);
                metrics.kernel_cpu_time_ms = Some(kernel_ms);
                metrics.total_cpu_time_ms = Some(user_ms + kernel_ms);
                metrics.total_processes = acct_info.TotalProcesses;
                metrics.active_processes = acct_info.ActiveProcesses;
            }

            metrics
        }
        #[cfg(unix)]
        {
            JobMetrics::default()
        }
    }

    /// Assign a newly spawned child process into the job container.
    pub fn assign_child(&mut self, child: &Child) -> io::Result<()> {
        #[cfg(windows)]
        {
            if let Some(handle) = child.raw_handle() {
                let res = unsafe { win32::AssignProcessToJobObject(self.job_handle, handle as _) };
                if res == 0 {
                    warn!(
                        "sandbox_process.assign_job_failed error={}",
                        io::Error::last_os_error()
                    );
                    return Err(io::Error::last_os_error());
                }
                debug!("sandbox_process.assigned_to_job_object");
            }
            Ok(())
        }
        #[cfg(unix)]
        {
            if let Some(id) = child.id() {
                self.pgid = Some(id as i32);
            }
            Ok(())
        }
    }

    /// Terminate the entire process tree contained within this job.
    pub fn terminate(&self) -> io::Result<()> {
        #[cfg(windows)]
        {
            let res = unsafe { win32::TerminateJobObject(self.job_handle, 1) };
            if res == 0 {
                // If the job has already finished/closed, this is not an error
                debug!(
                    "sandbox_process.terminate_job_status={}",
                    io::Error::last_os_error()
                );
            }
            Ok(())
        }
        #[cfg(unix)]
        {
            if let Some(pgid) = self.pgid {
                unsafe {
                    libc::kill(-pgid, libc::SIGKILL);
                }
            }
            Ok(())
        }
    }
}

impl Drop for ProcessJobContainer {
    fn drop(&mut self) {
        #[cfg(windows)]
        {
            if !self.job_handle.is_null() {
                unsafe {
                    win32::CloseHandle(self.job_handle);
                }
            }
        }
        #[cfg(unix)]
        {
            let _ = self.terminate();
        }
    }
}

/// Blacklisted substrings in environment variable keys to prevent accidental secret leakage.
const SENSITIVE_KEY_PATTERNS: &[&str] = &[
    "KEY",
    "SECRET",
    "TOKEN",
    "AUTH",
    "PASS",
    "PASSWORD",
    "CREDENTIAL",
    "PRIVATE",
    "KAIRO",
];

/// Builds a sanitized environment map adhering strictly to EnvironmentPolicy.
pub fn build_sanitized_environment(policy: &EnvironmentPolicy) -> HashMap<String, String> {
    let mut env = HashMap::new();

    match policy.mode {
        EnvironmentMode::Empty => {
            // Completely empty environment
        }
        EnvironmentMode::Explicit => {
            // Only explicitly provided variables
            for (k, v) in &policy.explicit_variables {
                if !is_sensitive_key(k) {
                    env.insert(k.clone(), v.clone());
                }
            }
        }
        EnvironmentMode::Allowlist | EnvironmentMode::InheritSafe => {
            // Collect allowed host variables, strictly filtering out sensitive patterns
            for key in &policy.allowed_variables {
                if is_sensitive_key(key) {
                    continue;
                }
                if let Ok(val) = std::env::var(key) {
                    env.insert(key.clone(), val);
                }
            }
            // Add explicit overrides
            for (k, v) in &policy.explicit_variables {
                if !is_sensitive_key(k) {
                    env.insert(k.clone(), v.clone());
                }
            }
        }
    }

    env
}

fn is_sensitive_key(key: &str) -> bool {
    let upper = key.to_uppercase();
    SENSITIVE_KEY_PATTERNS.iter().any(|pat| upper.contains(pat))
}

/// Spawns a process in the sandbox environment, wiring stdin to null and stdout/stderr to pipes.
pub fn configure_sandboxed_command(
    program: &Path,
    args: &[String],
    workspace_dir: &Path,
    env_vars: &HashMap<String, String>,
) -> Command {
    let mut cmd = Command::new(program);
    cmd.args(args);
    cmd.current_dir(workspace_dir);
    cmd.stdin(std::process::Stdio::null());
    cmd.stdout(std::process::Stdio::piped());
    cmd.stderr(std::process::Stdio::piped());

    // Clear all inherited environment and apply sanitized map
    cmd.env_clear();
    for (k, v) in env_vars {
        cmd.env(k, v);
    }

    cmd
}

/// Captures bounded output from an async reader up to max_bytes.
pub async fn read_bounded_stream<R: tokio::io::AsyncRead + Unpin>(
    mut reader: R,
    max_bytes: u64,
) -> (String, u64, bool) {
    let mut buffer = Vec::new();
    let mut temp = [0u8; 8192];
    let mut total_bytes = 0u64;
    let mut truncated = false;

    loop {
        match reader.read(&mut temp).await {
            Ok(0) => break,
            Ok(n) => {
                total_bytes += n as u64;
                if buffer.len() < max_bytes as usize {
                    let remaining = (max_bytes as usize) - buffer.len();
                    let to_take = n.min(remaining);
                    buffer.extend_from_slice(&temp[..to_take]);
                }
                if total_bytes > max_bytes {
                    truncated = true;
                }
            }
            Err(_) => break,
        }
    }

    let text = String::from_utf8_lossy(&buffer).to_string();
    (text, total_bytes, truncated)
}
