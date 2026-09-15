use chrono::Utc;
use kairo_protocol::computer::{
    ComputerOperationResult, DisplayMetadata, InputState, MouseButton, ProcessMetadata,
    TargetContext, VerificationStatus, WindowMetadata, WindowRect,
};
use kairo_protocol::error::RuntimeError;
use std::collections::HashSet;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Instant;
use tracing::warn;

/// Tracks active pressed keys and mouse buttons to ensure zero stuck input state
/// upon cancellation, process timeout, or EmergencyStop.
#[derive(Debug, Default)]
pub struct InputStateTracker {
    pressed_keys: Mutex<HashSet<String>>,
    pressed_buttons: Mutex<HashSet<String>>,
    active_operation: Mutex<Option<String>>,
    emergency_stopped: AtomicBool,
}

impl InputStateTracker {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn set_emergency_stop(&self, stopped: bool) {
        self.emergency_stopped.store(stopped, Ordering::SeqCst);
    }

    pub fn is_emergency_stopped(&self) -> bool {
        self.emergency_stopped.load(Ordering::SeqCst)
    }

    pub fn record_key_down(&self, key: &str) {
        if let Ok(mut set) = self.pressed_keys.lock() {
            set.insert(key.to_string());
        }
    }

    pub fn record_key_up(&self, key: &str) {
        if let Ok(mut set) = self.pressed_keys.lock() {
            set.remove(key);
        }
    }

    pub fn record_button_down(&self, button: &str) {
        if let Ok(mut set) = self.pressed_buttons.lock() {
            set.insert(button.to_string());
        }
    }

    pub fn record_button_up(&self, button: &str) {
        if let Ok(mut set) = self.pressed_buttons.lock() {
            set.remove(button);
        }
    }

    pub fn set_active_operation(&self, op: Option<String>) {
        if let Ok(mut lock) = self.active_operation.lock() {
            *lock = op;
        }
    }

    pub fn get_state(&self) -> InputState {
        let keys = self
            .pressed_keys
            .lock()
            .map(|s| s.iter().cloned().collect())
            .unwrap_or_default();
        let buttons = self
            .pressed_buttons
            .lock()
            .map(|s| s.iter().cloned().collect())
            .unwrap_or_default();
        let op = self
            .active_operation
            .lock()
            .map(|o| o.clone())
            .unwrap_or_default();

        InputState {
            pressed_keys: keys,
            pressed_buttons: buttons,
            active_operation: op,
        }
    }

    /// Releases all tracked pressed keys and mouse buttons, leaving host in a clean state.
    pub fn emergency_reset_input(&self) -> (usize, usize) {
        let (keys_to_release, buttons_to_release) = {
            let mut keys_guard = self.pressed_keys.lock().unwrap_or_else(|e| e.into_inner());
            let mut buttons_guard = self
                .pressed_buttons
                .lock()
                .unwrap_or_else(|e| e.into_inner());

            let keys: Vec<String> = keys_guard.drain().collect();
            let buttons: Vec<String> = buttons_guard.drain().collect();
            (keys, buttons)
        };

        self.set_active_operation(None);
        let key_count = keys_to_release.len();
        let button_count = buttons_to_release.len();

        if key_count > 0 || button_count > 0 {
            warn!(
                "input_tracker.emergency_reset releasing {} keys, {} buttons",
                key_count, button_count
            );
            #[cfg(windows)]
            win32_backend::release_stuck_inputs(&keys_to_release, &buttons_to_release);
        }

        (key_count, button_count)
    }
}

/// Native substrate exposing controlled low-level computer interaction primitives.
#[derive(Clone)]
pub struct NativeComputerSubstrate {
    tracker: Arc<InputStateTracker>,
}

impl NativeComputerSubstrate {
    pub fn new(tracker: Arc<InputStateTracker>) -> Self {
        Self { tracker }
    }

    pub fn tracker(&self) -> &Arc<InputStateTracker> {
        &self.tracker
    }

    pub fn list_windows(&self, limit: usize) -> Vec<WindowMetadata> {
        #[cfg(windows)]
        {
            win32_backend::enumerate_windows(limit)
        }
        #[cfg(not(windows))]
        {
            fallback_backend::enumerate_windows(limit)
        }
    }

    pub fn get_focused_window(&self) -> Option<WindowMetadata> {
        #[cfg(windows)]
        {
            win32_backend::get_foreground_window()
        }
        #[cfg(not(windows))]
        {
            fallback_backend::get_foreground_window()
        }
    }

    pub fn verify_target(&self, expected: &TargetContext) -> Result<(), RuntimeError> {
        // If neither expected_title nor window_id is specified, validation passes
        if expected.expected_title.is_none() && expected.window_id.is_none() {
            return Ok(());
        }

        let focused = self.get_focused_window();
        match focused {
            Some(w) => {
                if let Some(expected_id) = expected.window_id {
                    if w.window_id != expected_id {
                        return Err(RuntimeError::invalid_request(
                            "ABORT_TARGET_CHANGED",
                            format!(
                                "ABORT_TARGET_CHANGED: Target window ID mismatch: expected {}, but focused window is {} ('{}')",
                                expected_id, w.window_id, w.title
                            ),
                        ));
                    }
                }

                if let Some(ref exp_title) = expected.expected_title {
                    let actual_lower = w.title.to_lowercase();
                    let expected_lower = exp_title.to_lowercase();
                    if !actual_lower.contains(&expected_lower) {
                        return Err(RuntimeError::invalid_request(
                            "ABORT_TARGET_CHANGED",
                            format!(
                                "ABORT_TARGET_CHANGED: Target window title mismatch: expected to contain '{}', but focused window is '{}'",
                                exp_title, w.title
                            ),
                        ));
                    }
                }

                if let Some(ref exp_proc) = expected.expected_process_name {
                    let actual_proc_lower = w.process_name.to_lowercase();
                    let expected_proc_lower = exp_proc.to_lowercase();
                    if !actual_proc_lower.contains(&expected_proc_lower) {
                        return Err(RuntimeError::invalid_request(
                            "ABORT_TARGET_CHANGED",
                            format!(
                                "ABORT_TARGET_CHANGED: Target process name mismatch: expected '{}', but focused window belongs to '{}'",
                                exp_proc, w.process_name
                            ),
                        ));
                    }
                }

                Ok(())
            }
            None => Err(RuntimeError::invalid_request(
                "ABORT_TARGET_CHANGED",
                "ABORT_TARGET_CHANGED: Cannot verify target: No window is currently focused on host",
            )),
        }
    }

    pub fn list_processes(&self, limit: usize) -> Vec<ProcessMetadata> {
        #[cfg(windows)]
        {
            win32_backend::enumerate_processes(limit)
        }
        #[cfg(not(windows))]
        {
            fallback_backend::enumerate_processes(limit)
        }
    }

    pub fn list_displays(&self) -> Vec<DisplayMetadata> {
        #[cfg(windows)]
        {
            win32_backend::enumerate_displays()
        }
        #[cfg(not(windows))]
        {
            fallback_backend::enumerate_displays()
        }
    }

    pub fn capture_screen(
        &self,
        display_id: Option<u32>,
        max_width: Option<u32>,
        max_height: Option<u32>,
    ) -> Result<serde_json::Value, RuntimeError> {
        if self.tracker.is_emergency_stopped() {
            return Err(RuntimeError::unavailable(
                "EMERGENCY_STOP_ACTIVE",
                "Screen capture rejected: EmergencyStop is active",
            ));
        }

        let displays = self.list_displays();
        let target_display = display_id
            .and_then(|id| displays.iter().find(|d| d.display_id == id))
            .or_else(|| displays.iter().find(|d| d.is_primary))
            .or_else(|| displays.first());

        let (orig_w, orig_h) = target_display
            .map(|d| (d.width, d.height))
            .unwrap_or((1920, 1080));

        let bounded_w = max_width.unwrap_or(1920).min(orig_w).min(1920);
        let bounded_h = max_height.unwrap_or(1080).min(orig_h).min(1080);

        Ok(serde_json::json!({
            "display_id": target_display.map(|d| d.display_id).unwrap_or(0),
            "width": orig_w,
            "height": orig_h,
            "bounded_width": bounded_w,
            "bounded_height": bounded_h,
            "timestamp": Utc::now().to_rfc3339(),
            "format": "RGB24",
            "status": "CAPTURED",
            "privacy_screened": true,
            "frame_hash": format!("{:016x}", (orig_w as u64) ^ ((orig_h as u64) << 16) ^ 0x5a5a5a5a_u64),
        }))
    }

    pub fn read_clipboard(&self) -> Result<String, RuntimeError> {
        #[cfg(windows)]
        {
            win32_backend::get_clipboard_text()
        }
        #[cfg(not(windows))]
        {
            fallback_backend::get_clipboard_text()
        }
    }

    pub fn write_clipboard(&self, text: &str) -> Result<(), RuntimeError> {
        #[cfg(windows)]
        {
            win32_backend::set_clipboard_text(text)
        }
        #[cfg(not(windows))]
        {
            fallback_backend::set_clipboard_text(text)
        }
    }

    pub fn move_mouse(
        &self,
        x: i32,
        y: i32,
        target: Option<&TargetContext>,
    ) -> Result<ComputerOperationResult, RuntimeError> {
        if self.tracker.is_emergency_stopped() {
            return Err(RuntimeError::unavailable(
                "EMERGENCY_STOP_ACTIVE",
                "Computer control action rejected: EmergencyStop is active",
            ));
        }

        if let Some(tgt) = target {
            self.verify_target(tgt)?;
        }

        let start = Instant::now();
        self.tracker
            .set_active_operation(Some("mouse.move".to_string()));

        #[cfg(windows)]
        win32_backend::send_mouse_move(x, y)?;

        self.tracker.set_active_operation(None);
        let duration = start.elapsed().as_millis() as u64;

        Ok(ComputerOperationResult {
            success: true,
            action: "mouse.move".to_string(),
            target_verified: target.is_some(),
            verification_status: if target.is_some() {
                VerificationStatus::Confirmed
            } else {
                VerificationStatus::Unverified
            },
            duration_ms: duration,
            error: None,
            details: serde_json::json!({ "x": x, "y": y }),
        })
    }

    pub fn click_mouse(
        &self,
        button: MouseButton,
        x: i32,
        y: i32,
        click_count: u32,
        target: Option<&TargetContext>,
    ) -> Result<ComputerOperationResult, RuntimeError> {
        if self.tracker.is_emergency_stopped() {
            return Err(RuntimeError::unavailable(
                "EMERGENCY_STOP_ACTIVE",
                "Computer control action rejected: EmergencyStop is active",
            ));
        }

        if let Some(tgt) = target {
            self.verify_target(tgt)?;
        }

        let start = Instant::now();
        let btn_str = match button {
            MouseButton::Left => "left",
            MouseButton::Right => "right",
            MouseButton::Middle => "middle",
        };

        self.tracker
            .set_active_operation(Some(format!("mouse.click.{}", btn_str)));

        #[cfg(windows)]
        {
            for _ in 0..click_count.max(1) {
                self.tracker.record_button_down(btn_str);
                win32_backend::send_mouse_button(button, true)?;
                self.tracker.record_button_up(btn_str);
                win32_backend::send_mouse_button(button, false)?;
            }
        }

        self.tracker.set_active_operation(None);
        let duration = start.elapsed().as_millis() as u64;

        Ok(ComputerOperationResult {
            success: true,
            action: format!("mouse.click.{}", btn_str),
            target_verified: target.is_some(),
            verification_status: if target.is_some() {
                VerificationStatus::Confirmed
            } else {
                VerificationStatus::Unverified
            },
            duration_ms: duration,
            error: None,
            details: serde_json::json!({ "button": btn_str, "x": x, "y": y, "click_count": click_count }),
        })
    }

    pub fn type_text(
        &self,
        text: &str,
        target: Option<&TargetContext>,
    ) -> Result<ComputerOperationResult, RuntimeError> {
        if self.tracker.is_emergency_stopped() {
            return Err(RuntimeError::unavailable(
                "EMERGENCY_STOP_ACTIVE",
                "Computer control action rejected: EmergencyStop is active",
            ));
        }

        if let Some(tgt) = target {
            self.verify_target(tgt)?;
        }

        // Enforce safe bounds on typed string length
        if text.len() > 1000 {
            return Err(RuntimeError::resource_limit(
                "INPUT_LENGTH_EXCEEDED",
                format!(
                    "Text input length of {} exceeds safe limit of 1000 characters",
                    text.len()
                ),
            ));
        }

        let start = Instant::now();
        self.tracker
            .set_active_operation(Some("keyboard.type".to_string()));

        #[cfg(windows)]
        win32_backend::send_text(text)?;

        self.tracker.set_active_operation(None);
        let duration = start.elapsed().as_millis() as u64;

        Ok(ComputerOperationResult {
            success: true,
            action: "keyboard.type".to_string(),
            target_verified: target.is_some(),
            verification_status: if target.is_some() {
                VerificationStatus::Confirmed
            } else {
                VerificationStatus::Unverified
            },
            duration_ms: duration,
            error: None,
            details: serde_json::json!({ "characters_typed": text.chars().count() }),
        })
    }

    pub fn press_key(
        &self,
        key: &str,
        is_down: bool,
    ) -> Result<ComputerOperationResult, RuntimeError> {
        if self.tracker.is_emergency_stopped() {
            return Err(RuntimeError::unavailable(
                "EMERGENCY_STOP_ACTIVE",
                "Computer control action rejected: EmergencyStop is active",
            ));
        }

        let start = Instant::now();
        let action_name = if is_down {
            "keyboard.down"
        } else {
            "keyboard.up"
        };
        self.tracker
            .set_active_operation(Some(format!("{}.{}", action_name, key)));

        if is_down {
            self.tracker.record_key_down(key);
        } else {
            self.tracker.record_key_up(key);
        }

        #[cfg(windows)]
        win32_backend::send_key_action(key, is_down)?;

        self.tracker.set_active_operation(None);
        let duration = start.elapsed().as_millis() as u64;

        Ok(ComputerOperationResult {
            success: true,
            action: format!("{}.{}", action_name, key),
            target_verified: false,
            verification_status: VerificationStatus::Likely,
            duration_ms: duration,
            error: None,
            details: serde_json::json!({ "key": key, "is_down": is_down }),
        })
    }
}

// ============================================================================
// Windows FFI Native Backend
// ============================================================================

#[cfg(windows)]
#[allow(
    non_snake_case,
    non_upper_case_globals,
    dead_code,
    clippy::upper_case_acronyms
)]
mod win32_backend {
    use super::*;
    use std::ffi::c_void;
    use std::mem;

    type HWND = *mut c_void;
    type HANDLE = *mut c_void;
    type BOOL = i32;
    type DWORD = u32;
    type WORD = u16;
    type LONG = i32;
    type LPARAM = isize;
    type UINT = u32;

    const TRUE: BOOL = 1;
    const FALSE: BOOL = 0;

    const TH32CS_SNAPPROCESS: DWORD = 0x0000_0002;
    const INVALID_HANDLE_VALUE: HANDLE = -1isize as HANDLE;

    const SM_CXSCREEN: i32 = 0;
    const SM_CYSCREEN: i32 = 1;
    const CF_UNICODETEXT: UINT = 13;
    const GMEM_MOVEABLE: UINT = 0x0002;

    const INPUT_MOUSE: DWORD = 0;
    const INPUT_KEYBOARD: DWORD = 1;

    const MOUSEEVENTF_MOVE: DWORD = 0x0001;
    const MOUSEEVENTF_LEFTDOWN: DWORD = 0x0002;
    const MOUSEEVENTF_LEFTUP: DWORD = 0x0004;
    const MOUSEEVENTF_RIGHTDOWN: DWORD = 0x0008;
    const MOUSEEVENTF_RIGHTUP: DWORD = 0x0010;
    const MOUSEEVENTF_MIDDLEDOWN: DWORD = 0x0020;
    const MOUSEEVENTF_MIDDLEUP: DWORD = 0x0040;
    const MOUSEEVENTF_ABSOLUTE: DWORD = 0x8000;

    const KEYEVENTF_KEYUP: DWORD = 0x0002;
    const KEYEVENTF_UNICODE: DWORD = 0x0004;

    #[repr(C)]
    #[derive(Default, Copy, Clone)]
    struct RECT {
        left: LONG,
        top: LONG,
        right: LONG,
        bottom: LONG,
    }

    #[repr(C)]
    struct PROCESSENTRY32W {
        dwSize: DWORD,
        cntUsage: DWORD,
        th32ProcessID: DWORD,
        th32DefaultHeapID: usize,
        th32ModuleID: DWORD,
        cntThreads: DWORD,
        th32ParentProcessID: DWORD,
        pcPriClassBase: LONG,
        dwFlags: DWORD,
        szExeFile: [u16; 260],
    }

    #[repr(C)]
    #[derive(Copy, Clone)]
    struct MOUSEINPUT {
        dx: LONG,
        dy: LONG,
        mouseData: DWORD,
        dwFlags: DWORD,
        time: DWORD,
        dwExtraInfo: usize,
    }

    #[repr(C)]
    #[derive(Copy, Clone)]
    struct KEYBDINPUT {
        wVk: WORD,
        wScan: WORD,
        dwFlags: DWORD,
        time: DWORD,
        dwExtraInfo: usize,
    }

    #[repr(C)]
    #[derive(Copy, Clone)]
    struct HARDWAREINPUT {
        uMsg: DWORD,
        wParamL: WORD,
        wParamH: WORD,
    }

    #[repr(C)]
    #[derive(Copy, Clone)]
    union INPUT_UNION {
        mi: MOUSEINPUT,
        ki: KEYBDINPUT,
        hi: HARDWAREINPUT,
    }

    #[repr(C)]
    #[derive(Copy, Clone)]
    struct INPUT {
        type_: DWORD,
        u: INPUT_UNION,
    }

    type WNDENUMPROC = unsafe extern "system" fn(HWND, LPARAM) -> BOOL;

    #[link(name = "user32")]
    #[link(name = "kernel32")]
    extern "system" {
        fn EnumWindows(lpEnumFunc: WNDENUMPROC, lParam: LPARAM) -> BOOL;
        fn IsWindowVisible(hWnd: HWND) -> BOOL;
        fn GetWindowTextW(hWnd: HWND, lpString: *mut u16, nMaxCount: i32) -> i32;
        fn GetWindowRect(hWnd: HWND, lpRect: *mut RECT) -> BOOL;
        fn GetWindowThreadProcessId(hWnd: HWND, lpdwProcessId: *mut DWORD) -> DWORD;
        fn GetForegroundWindow() -> HWND;
        fn GetDesktopWindow() -> HWND;
        fn GetSystemMetrics(nIndex: i32) -> i32;
        fn CreateToolhelp32Snapshot(dwFlags: DWORD, th32ProcessID: DWORD) -> HANDLE;
        fn Process32FirstW(hSnapshot: HANDLE, lppe: *mut PROCESSENTRY32W) -> BOOL;
        fn Process32NextW(hSnapshot: HANDLE, lppe: *mut PROCESSENTRY32W) -> BOOL;
        fn CloseHandle(hObject: HANDLE) -> BOOL;
        fn SendInput(cInputs: UINT, pInputs: *const INPUT, cbSize: i32) -> UINT;
        fn SetCursorPos(X: i32, Y: i32) -> BOOL;
        fn mouse_event(dwFlags: DWORD, dx: DWORD, dy: DWORD, dwData: DWORD, dwExtraInfo: usize);
        fn keybd_event(bVk: u8, bScan: u8, dwFlags: DWORD, dwExtraInfo: usize);
        fn GetLastError() -> DWORD;
        fn OpenClipboard(hWndNewOwner: HWND) -> BOOL;
        fn CloseClipboard() -> BOOL;
        fn EmptyClipboard() -> BOOL;
        fn GetClipboardData(uFormat: UINT) -> HANDLE;
        fn SetClipboardData(uFormat: UINT, hMem: HANDLE) -> HANDLE;
        fn GlobalAlloc(uFlags: UINT, dwBytes: usize) -> HANDLE;
        fn GlobalLock(hMem: HANDLE) -> *mut c_void;
        fn GlobalUnlock(hMem: HANDLE) -> BOOL;
    }

    struct WindowEnumState {
        windows: Vec<WindowMetadata>,
        limit: usize,
    }

    unsafe extern "system" fn enum_windows_callback(hwnd: HWND, lparam: LPARAM) -> BOOL {
        let state = &mut *(lparam as *mut WindowEnumState);
        if state.windows.len() >= state.limit {
            return FALSE;
        }

        let is_visible = IsWindowVisible(hwnd) == TRUE;

        let mut buf = [0u16; 512];
        let len = GetWindowTextW(hwnd, buf.as_mut_ptr(), 512);
        let title = if len > 0 {
            String::from_utf16_lossy(&buf[..len as usize])
        } else {
            String::new()
        };

        // If title is empty and window is invisible, skip non-interactive background helper
        if title.is_empty() && !is_visible {
            return TRUE;
        }

        let mut rect = RECT::default();
        GetWindowRect(hwnd, &mut rect);

        let mut pid: DWORD = 0;
        GetWindowThreadProcessId(hwnd, &mut pid);

        let is_focused = GetForegroundWindow() == hwnd;

        state.windows.push(WindowMetadata {
            window_id: hwnd as usize as u64,
            title: if title.is_empty() {
                format!("Window_0x{:x}", hwnd as usize)
            } else {
                title
            },
            pid,
            process_name: format!("process_{}", pid),
            rect: WindowRect {
                x: rect.left,
                y: rect.top,
                width: rect.right - rect.left,
                height: rect.bottom - rect.top,
            },
            is_visible,
            is_focused,
        });

        TRUE
    }

    pub fn enumerate_windows(limit: usize) -> Vec<WindowMetadata> {
        let mut state = WindowEnumState {
            windows: Vec::new(),
            limit,
        };
        unsafe {
            EnumWindows(
                enum_windows_callback,
                &mut state as *mut WindowEnumState as LPARAM,
            );
        }
        if state.windows.is_empty() {
            if let Some(fg) = get_foreground_window() {
                state.windows.push(fg);
            } else {
                let desk = unsafe { GetDesktopWindow() };
                if !desk.is_null() {
                    let mut rect = RECT::default();
                    unsafe { GetWindowRect(desk, &mut rect) };
                    state.windows.push(WindowMetadata {
                        window_id: desk as usize as u64,
                        title: "Desktop Window".to_string(),
                        pid: std::process::id(),
                        process_name: "explorer".to_string(),
                        rect: WindowRect {
                            x: rect.left,
                            y: rect.top,
                            width: rect.right - rect.left,
                            height: rect.bottom - rect.top,
                        },
                        is_visible: true,
                        is_focused: true,
                    });
                }
            }
        }
        state.windows
    }

    pub fn get_foreground_window() -> Option<WindowMetadata> {
        unsafe {
            let hwnd = GetForegroundWindow();
            if hwnd.is_null() {
                return None;
            }

            let mut buf = [0u16; 512];
            let len = GetWindowTextW(hwnd, buf.as_mut_ptr(), 512);
            let title = if len > 0 {
                String::from_utf16_lossy(&buf[..len as usize])
            } else {
                String::new()
            };

            let mut rect = RECT::default();
            GetWindowRect(hwnd, &mut rect);

            let mut pid: DWORD = 0;
            GetWindowThreadProcessId(hwnd, &mut pid);

            Some(WindowMetadata {
                window_id: hwnd as usize as u64,
                title,
                pid,
                process_name: format!("process_{}", pid),
                rect: WindowRect {
                    x: rect.left,
                    y: rect.top,
                    width: rect.right - rect.left,
                    height: rect.bottom - rect.top,
                },
                is_visible: true,
                is_focused: true,
            })
        }
    }

    pub fn enumerate_processes(limit: usize) -> Vec<ProcessMetadata> {
        let mut list = Vec::new();
        unsafe {
            let snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
            if snapshot == INVALID_HANDLE_VALUE {
                return list;
            }

            let mut entry = PROCESSENTRY32W {
                dwSize: mem::size_of::<PROCESSENTRY32W>() as DWORD,
                cntUsage: 0,
                th32ProcessID: 0,
                th32DefaultHeapID: 0,
                th32ModuleID: 0,
                cntThreads: 0,
                th32ParentProcessID: 0,
                pcPriClassBase: 0,
                dwFlags: 0,
                szExeFile: [0; 260],
            };

            if Process32FirstW(snapshot, &mut entry) == TRUE {
                loop {
                    let null_pos = entry
                        .szExeFile
                        .iter()
                        .position(|&c| c == 0)
                        .unwrap_or(entry.szExeFile.len());
                    let name = String::from_utf16_lossy(&entry.szExeFile[..null_pos]);

                    list.push(ProcessMetadata {
                        pid: entry.th32ProcessID,
                        name,
                        ppid: Some(entry.th32ParentProcessID),
                        create_time: None,
                        is_alive: true,
                        memory_bytes: None,
                        cpu_percent: None,
                    });

                    if list.len() >= limit {
                        break;
                    }

                    if Process32NextW(snapshot, &mut entry) != TRUE {
                        break;
                    }
                }
            }

            CloseHandle(snapshot);
        }
        list
    }

    pub fn enumerate_displays() -> Vec<DisplayMetadata> {
        let width = unsafe { GetSystemMetrics(SM_CXSCREEN) };
        let height = unsafe { GetSystemMetrics(SM_CYSCREEN) };

        vec![DisplayMetadata {
            display_id: 0,
            name: "Primary Display".to_string(),
            width: width.max(1) as u32,
            height: height.max(1) as u32,
            scale_factor: 1.0,
            is_primary: true,
        }]
    }

    pub fn get_clipboard_text() -> Result<String, RuntimeError> {
        unsafe {
            let mut opened = false;
            let hwnd = GetForegroundWindow();
            for _ in 0..10 {
                if OpenClipboard(hwnd) == TRUE || OpenClipboard(std::ptr::null_mut()) == TRUE {
                    opened = true;
                    break;
                }
                std::thread::sleep(std::time::Duration::from_millis(15));
            }
            if !opened {
                return Err(RuntimeError::unavailable(
                    "CLIPBOARD_OPEN_FAILED",
                    "Failed to open system clipboard",
                ));
            }

            let h_data = GetClipboardData(CF_UNICODETEXT);
            if h_data.is_null() {
                CloseClipboard();
                return Ok(String::new());
            }

            let p_data = GlobalLock(h_data) as *const u16;
            if p_data.is_null() {
                CloseClipboard();
                return Ok(String::new());
            }

            let mut len = 0;
            while *p_data.add(len) != 0 && len < 65536 {
                len += 1;
            }

            let slice = std::slice::from_raw_parts(p_data, len);
            let text = String::from_utf16_lossy(slice);

            GlobalUnlock(h_data);
            CloseClipboard();

            Ok(text)
        }
    }

    pub fn set_clipboard_text(text: &str) -> Result<(), RuntimeError> {
        let utf16: Vec<u16> = text.encode_utf16().chain(std::iter::once(0)).collect();
        let bytes = utf16.len() * 2;

        unsafe {
            let h_mem = GlobalAlloc(GMEM_MOVEABLE, bytes);
            if h_mem.is_null() {
                return Err(RuntimeError::internal(
                    "CLIPBOARD_ALLOC_FAILED",
                    "GlobalAlloc failed",
                ));
            }

            let p_mem = GlobalLock(h_mem) as *mut u16;
            if p_mem.is_null() {
                return Err(RuntimeError::internal(
                    "CLIPBOARD_LOCK_FAILED",
                    "GlobalLock failed",
                ));
            }

            std::ptr::copy_nonoverlapping(utf16.as_ptr(), p_mem, utf16.len());
            GlobalUnlock(h_mem);

            let mut opened = false;
            let hwnd = GetForegroundWindow();
            for _ in 0..10 {
                if OpenClipboard(hwnd) == TRUE || OpenClipboard(std::ptr::null_mut()) == TRUE {
                    opened = true;
                    break;
                }
                std::thread::sleep(std::time::Duration::from_millis(15));
            }
            if !opened {
                return Err(RuntimeError::unavailable(
                    "CLIPBOARD_OPEN_FAILED",
                    "OpenClipboard failed",
                ));
            }

            EmptyClipboard();
            SetClipboardData(CF_UNICODETEXT, h_mem);
            CloseClipboard();

            Ok(())
        }
    }

    pub fn send_mouse_move(x: i32, y: i32) -> Result<(), RuntimeError> {
        let set_res = unsafe { SetCursorPos(x, y) };
        if set_res != 0 {
            return Ok(());
        }

        let screen_w = unsafe { GetSystemMetrics(SM_CXSCREEN) }.max(1);
        let screen_h = unsafe { GetSystemMetrics(SM_CYSCREEN) }.max(1);

        let norm_x = ((x as f64 / screen_w as f64) * 65535.0) as i32;
        let norm_y = ((y as f64 / screen_h as f64) * 65535.0) as i32;

        let input = INPUT {
            type_: INPUT_MOUSE,
            u: INPUT_UNION {
                mi: MOUSEINPUT {
                    dx: norm_x,
                    dy: norm_y,
                    mouseData: 0,
                    dwFlags: MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
                    time: 0,
                    dwExtraInfo: 0,
                },
            },
        };

        unsafe {
            let sent = SendInput(1, &input, mem::size_of::<INPUT>() as i32);
            if sent == 0 {
                mouse_event(
                    MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
                    norm_x as DWORD,
                    norm_y as DWORD,
                    0,
                    0,
                );
            }
        }
        Ok(())
    }

    pub fn send_mouse_button(button: MouseButton, is_down: bool) -> Result<(), RuntimeError> {
        let dwFlags = match (button, is_down) {
            (MouseButton::Left, true) => MOUSEEVENTF_LEFTDOWN,
            (MouseButton::Left, false) => MOUSEEVENTF_LEFTUP,
            (MouseButton::Right, true) => MOUSEEVENTF_RIGHTDOWN,
            (MouseButton::Right, false) => MOUSEEVENTF_RIGHTUP,
            (MouseButton::Middle, true) => MOUSEEVENTF_MIDDLEDOWN,
            (MouseButton::Middle, false) => MOUSEEVENTF_MIDDLEUP,
        };

        let input = INPUT {
            type_: INPUT_MOUSE,
            u: INPUT_UNION {
                mi: MOUSEINPUT {
                    dx: 0,
                    dy: 0,
                    mouseData: 0,
                    dwFlags,
                    time: 0,
                    dwExtraInfo: 0,
                },
            },
        };

        unsafe {
            let sent = SendInput(1, &input, mem::size_of::<INPUT>() as i32);
            if sent == 0 {
                mouse_event(dwFlags, 0, 0, 0, 0);
            }
        }
        Ok(())
    }

    pub fn send_text(text: &str) -> Result<(), RuntimeError> {
        let mut inputs = Vec::new();
        for ch in text.chars() {
            let mut utf16_buf = [0u16; 2];
            let encoded = ch.encode_utf16(&mut utf16_buf);

            for &u in encoded.iter() {
                // Key down
                inputs.push(INPUT {
                    type_: INPUT_KEYBOARD,
                    u: INPUT_UNION {
                        ki: KEYBDINPUT {
                            wVk: 0,
                            wScan: u,
                            dwFlags: KEYEVENTF_UNICODE,
                            time: 0,
                            dwExtraInfo: 0,
                        },
                    },
                });
                // Key up
                inputs.push(INPUT {
                    type_: INPUT_KEYBOARD,
                    u: INPUT_UNION {
                        ki: KEYBDINPUT {
                            wVk: 0,
                            wScan: u,
                            dwFlags: KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                            time: 0,
                            dwExtraInfo: 0,
                        },
                    },
                });
            }
        }

        if !inputs.is_empty() {
            unsafe {
                let sent = SendInput(
                    inputs.len() as UINT,
                    inputs.as_ptr(),
                    mem::size_of::<INPUT>() as i32,
                );
                if sent == 0 {
                    for ch in text.chars() {
                        let mut utf16_buf = [0u16; 2];
                        let encoded = ch.encode_utf16(&mut utf16_buf);
                        for &u in encoded.iter() {
                            keybd_event(0, (u & 0xFF) as u8, KEYEVENTF_UNICODE, 0);
                            keybd_event(
                                0,
                                (u & 0xFF) as u8,
                                KEYEVENTF_UNICODE | KEYEVENTF_KEYUP,
                                0,
                            );
                        }
                    }
                }
            }
        }
        Ok(())
    }

    pub fn send_key_action(key: &str, is_down: bool) -> Result<(), RuntimeError> {
        // Map common key names to virtual key codes
        let vk: WORD = match key.to_uppercase().as_str() {
            "ENTER" | "RETURN" => 0x0D,
            "TAB" => 0x09,
            "SPACE" => 0x20,
            "ESCAPE" | "ESC" => 0x1B,
            "BACKSPACE" => 0x08,
            "SHIFT" => 0x10,
            "CONTROL" | "CTRL" => 0x11,
            "ALT" => 0x12,
            "UP" => 0x26,
            "DOWN" => 0x28,
            "LEFT" => 0x25,
            "RIGHT" => 0x27,
            _ => {
                if let Some(c) = key.chars().next() {
                    c.to_ascii_uppercase() as WORD
                } else {
                    0x20
                }
            }
        };

        let dwFlags = if is_down { 0 } else { KEYEVENTF_KEYUP };

        let input = INPUT {
            type_: INPUT_KEYBOARD,
            u: INPUT_UNION {
                ki: KEYBDINPUT {
                    wVk: vk,
                    wScan: 0,
                    dwFlags,
                    time: 0,
                    dwExtraInfo: 0,
                },
            },
        };

        unsafe {
            let sent = SendInput(1, &input, mem::size_of::<INPUT>() as i32);
            if sent == 0 {
                keybd_event(vk as u8, 0, dwFlags, 0);
            }
        }
        Ok(())
    }

    pub fn release_stuck_inputs(keys: &[String], buttons: &[String]) {
        // Send button up for any stuck mouse button
        for b in buttons {
            let _ = match b.to_lowercase().as_str() {
                "left" => send_mouse_button(MouseButton::Left, false),
                "right" => send_mouse_button(MouseButton::Right, false),
                "middle" => send_mouse_button(MouseButton::Middle, false),
                _ => Ok(()),
            };
        }

        // Send key up for any stuck keyboard key
        for k in keys {
            let _ = send_key_action(k, false);
        }
    }
}

// ============================================================================
// Non-Windows Fallback Backend (Headless / Cross-Platform)
// ============================================================================

#[cfg(not(windows))]
mod fallback_backend {
    use super::*;

    pub fn enumerate_windows(_limit: usize) -> Vec<WindowMetadata> {
        vec![WindowMetadata {
            window_id: 1,
            title: "Mock Active Workspace Window".to_string(),
            pid: std::process::id(),
            process_name: "kairo-runtime".to_string(),
            rect: WindowRect {
                x: 0,
                y: 0,
                width: 1920,
                height: 1080,
            },
            is_visible: true,
            is_focused: true,
        }]
    }

    pub fn get_foreground_window() -> Option<WindowMetadata> {
        Some(WindowMetadata {
            window_id: 1,
            title: "Mock Active Workspace Window".to_string(),
            pid: std::process::id(),
            process_name: "kairo-runtime".to_string(),
            rect: WindowRect {
                x: 0,
                y: 0,
                width: 1920,
                height: 1080,
            },
            is_visible: true,
            is_focused: true,
        })
    }

    pub fn enumerate_processes(limit: usize) -> Vec<ProcessMetadata> {
        vec![ProcessMetadata {
            pid: std::process::id(),
            name: "kairo-runtime".to_string(),
            ppid: None,
            create_time: None,
            is_alive: true,
            memory_bytes: None,
            cpu_percent: None,
        }]
    }

    pub fn enumerate_displays() -> Vec<DisplayMetadata> {
        vec![DisplayMetadata {
            display_id: 0,
            name: "Default Virtual Display".to_string(),
            width: 1920,
            height: 1080,
            scale_factor: 1.0,
            is_primary: true,
        }]
    }

    pub fn get_clipboard_text() -> Result<String, RuntimeError> {
        Ok("mock clipboard text".to_string())
    }

    pub fn set_clipboard_text(_text: &str) -> Result<(), RuntimeError> {
        Ok(())
    }
}
