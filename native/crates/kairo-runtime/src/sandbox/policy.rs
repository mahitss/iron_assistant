use kairo_protocol::{RuntimeError, SandboxPolicy};
use std::path::{Component, Path, PathBuf};

/// Validates that a requested path is safe and strictly contained within allowed boundaries.
/// Rejects path traversal (`..`), absolute root escapes, and invalid components.
pub fn validate_path_safety(
    requested: &Path,
    allowed_roots: &[PathBuf],
    workspace_dir: Option<&Path>,
) -> Result<PathBuf, RuntimeError> {
    // 1. Check for directory traversal components
    for comp in requested.components() {
        if comp == Component::ParentDir {
            return Err(RuntimeError::invalid_request(
                "PATH_TRAVERSAL_DETECTED",
                format!(
                    "Path traversal attempt ('..') rejected: '{}'",
                    requested.display()
                ),
            ));
        }
    }

    // 2. Resolve target path
    let target = if requested.is_absolute() {
        requested.to_path_buf()
    } else if let Some(ws) = workspace_dir {
        ws.join(requested)
    } else {
        return Err(RuntimeError::invalid_request(
            "RELATIVE_PATH_WITHOUT_WORKSPACE",
            format!(
                "Relative path '{}' cannot be resolved without an active workspace",
                requested.display()
            ),
        ));
    };

    // 3. Normalize path components
    let mut normalized = PathBuf::new();
    for comp in target.components() {
        match comp {
            Component::Prefix(p) => normalized.push(p.as_os_str()),
            Component::RootDir => normalized.push(Component::RootDir.as_os_str()),
            Component::CurDir => {}
            Component::ParentDir => {
                normalized.pop();
            }
            Component::Normal(n) => normalized.push(n),
        }
    }

    // 4. Verify boundary against allowed roots and workspace
    let mut all_allowed: Vec<PathBuf> = allowed_roots.to_vec();
    if let Some(ws) = workspace_dir {
        all_allowed.push(ws.to_path_buf());
    }

    if all_allowed.is_empty() {
        return Err(RuntimeError::invalid_request(
            "FILESYSTEM_ACCESS_DENIED",
            format!(
                "Filesystem access denied: no allowed roots for target '{}'",
                normalized.display()
            ),
        ));
    }

    let is_within_allowed = all_allowed.iter().any(|allowed| {
        let allowed_norm = normalize_path(allowed);
        normalized.starts_with(&allowed_norm)
    });

    if !is_within_allowed {
        return Err(RuntimeError::invalid_request(
            "PATH_ESCAPE_DETECTED",
            format!(
                "Target path '{}' escapes allowed sandbox boundaries: {:?}",
                normalized.display(),
                all_allowed
            ),
        ));
    }

    // 5. Symlink check: if file exists, verify canonical path
    if target.exists() {
        if let Ok(canonical) = target.canonicalize() {
            let canonical_allowed = all_allowed.iter().any(|allowed| {
                if let Ok(canon_allowed) = allowed.canonicalize() {
                    canonical.starts_with(&canon_allowed)
                } else {
                    let norm_allowed = normalize_path(allowed);
                    canonical.starts_with(&norm_allowed)
                }
            });

            if !canonical_allowed {
                return Err(RuntimeError::invalid_request(
                    "SYMLINK_ESCAPE_DETECTED",
                    format!(
                        "Symlink target '{}' resolves outside allowed sandbox boundaries: {:?}",
                        canonical.display(),
                        all_allowed
                    ),
                ));
            }
        }
    }

    Ok(normalized)
}

/// Helper to normalize a Path by resolving '.' and '..' textually.
pub fn normalize_path(path: &Path) -> PathBuf {
    let mut normalized = PathBuf::new();
    for comp in path.components() {
        match comp {
            Component::Prefix(p) => normalized.push(p.as_os_str()),
            Component::RootDir => normalized.push(Component::RootDir.as_os_str()),
            Component::CurDir => {}
            Component::ParentDir => {
                normalized.pop();
            }
            Component::Normal(n) => normalized.push(n),
        }
    }
    normalized
}

/// Calculate the effective sandbox policy combining capability contracts and request options.
pub fn calculate_effective_policy(
    capability_policy: &SandboxPolicy,
    requested_policy: &Option<SandboxPolicy>,
) -> SandboxPolicy {
    match requested_policy {
        Some(req) => capability_policy.intersect(req),
        None => capability_policy.clone(),
    }
}
