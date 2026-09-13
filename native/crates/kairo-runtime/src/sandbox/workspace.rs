use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use tracing::{debug, error, info, warn};
use uuid::Uuid;

const WORKSPACE_PREFIX: &str = "kairo_sbx_";

/// Isolated temporary workspace providing RAII cleanup.
/// On drop or explicit cleanup, the directory tree is deleted.
pub struct IsolatedWorkspace {
    path: PathBuf,
    execution_id: String,
    cleaned: bool,
}

impl IsolatedWorkspace {
    /// Create a new isolated workspace directory in the OS temp directory.
    pub fn create(execution_id: &str) -> io::Result<Self> {
        let unique_id = Uuid::new_v4().simple().to_string();
        let folder_name = format!("{}{}_{}", WORKSPACE_PREFIX, execution_id, &unique_id[..8]);
        let temp_base = std::env::temp_dir();
        let path = temp_base.join(folder_name);

        fs::create_dir_all(&path)?;
        debug!(
            "sandbox_workspace.created execution_id={} path={}",
            execution_id,
            path.display()
        );

        Ok(Self {
            path,
            execution_id: execution_id.to_string(),
            cleaned: false,
        })
    }

    /// Returns the workspace root path.
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Explicitly perform cleanup of the workspace.
    pub fn cleanup(&mut self) -> io::Result<()> {
        if self.cleaned {
            return Ok(());
        }
        if self.path.exists() {
            fs::remove_dir_all(&self.path)?;
            debug!(
                "sandbox_workspace.cleaned execution_id={} path={}",
                self.execution_id,
                self.path.display()
            );
        }
        self.cleaned = true;
        Ok(())
    }

    /// Check if the workspace directory currently exists on disk.
    pub fn exists(&self) -> bool {
        self.path.exists()
    }

    /// Recursively measure the total bytes and file count contained within this workspace.
    pub fn measure_usage(&self) -> io::Result<(u64, u32)> {
        if !self.path.exists() {
            return Ok((0, 0));
        }

        let mut total_bytes = 0u64;
        let mut file_count = 0u32;
        let mut stack = vec![self.path.clone()];

        while let Some(dir) = stack.pop() {
            let entries = match fs::read_dir(&dir) {
                Ok(e) => e,
                Err(_) => continue,
            };

            for entry in entries.flatten() {
                let p = entry.path();
                if p.is_dir() {
                    stack.push(p);
                } else if p.is_file() {
                    file_count += 1;
                    if let Ok(meta) = entry.metadata() {
                        total_bytes += meta.len();
                    }
                }
            }
        }

        Ok((total_bytes, file_count))
    }

    /// Validate workspace usage against disk and file count limits.
    pub fn check_limits(
        &self,
        max_bytes: Option<u64>,
        max_files: Option<u32>,
    ) -> Result<(u64, u32), kairo_protocol::RuntimeError> {
        let (bytes, files) = self.measure_usage().map_err(|e| {
            kairo_protocol::RuntimeError::internal(
                "WORKSPACE_MEASURE_FAILED",
                format!("Failed to measure workspace usage: {}", e),
            )
        })?;

        if let Some(limit_bytes) = max_bytes {
            if bytes > limit_bytes {
                return Err(kairo_protocol::RuntimeError::resource_limit(
                    "DISK_LIMIT_EXCEEDED",
                    format!(
                        "Workspace disk limit exceeded: {} bytes > {} bytes",
                        bytes, limit_bytes
                    ),
                ));
            }
        }

        if let Some(limit_files) = max_files {
            if files > limit_files {
                return Err(kairo_protocol::RuntimeError::resource_limit(
                    "FILE_COUNT_EXCEEDED",
                    format!(
                        "Workspace file count limit exceeded: {} files > {} files",
                        files, limit_files
                    ),
                ));
            }
        }

        Ok((bytes, files))
    }
}

impl Drop for IsolatedWorkspace {
    fn drop(&mut self) {
        if !self.cleaned && self.path.exists() {
            if let Err(err) = fs::remove_dir_all(&self.path) {
                warn!(
                    "sandbox_workspace.drop_cleanup_failed execution_id={} path={} error={}",
                    self.execution_id,
                    self.path.display(),
                    err
                );
            } else {
                debug!(
                    "sandbox_workspace.drop_cleaned execution_id={}",
                    self.execution_id
                );
            }
        }
    }
}

/// Prunes any stale `kairo_sbx_*` directories left in the OS temp directory from previous abnormal exits.
pub fn clean_stale_workspaces() -> usize {
    let temp_dir = std::env::temp_dir();
    let mut cleaned_count = 0;

    let entries = match fs::read_dir(&temp_dir) {
        Ok(e) => e,
        Err(err) => {
            warn!("sandbox_workspace.stale_scan_failed error={}", err);
            return 0;
        }
    };

    for entry in entries.flatten() {
        let file_name = entry.file_name().to_string_lossy().to_string();
        if file_name.starts_with(WORKSPACE_PREFIX) {
            let path = entry.path();
            if path.is_dir() {
                if let Err(err) = fs::remove_dir_all(&path) {
                    error!(
                        "sandbox_workspace.stale_cleanup_failed path={} error={}",
                        path.display(),
                        err
                    );
                } else {
                    cleaned_count += 1;
                    info!(
                        "sandbox_workspace.stale_workspace_pruned path={}",
                        path.display()
                    );
                }
            }
        }
    }

    cleaned_count
}
