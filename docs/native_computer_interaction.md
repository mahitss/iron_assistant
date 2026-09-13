# Kairo Native Computer Interaction Substrate (Task 84)

## 1. Architectural Overview

The **Kairo Native Computer Interaction Substrate** establishes a secure, typed, target-validated, and governed execution pipeline bridging high-level cognitive agent planning to host-level computer interaction primitives.

```
AI PLANNER / AGENT INTENT
        ↓
    TOOLREGISTRY   (Registers native_window_inspect, native_mouse_action, native_screen_capture, etc.)
        ↓
    TOOLEXECUTOR   (Orchestrates tool argument validation, policy checks, resource limits)
        ↓
   SECURITYCENTER  (Authoritative access control: ALLOWED for read-only inspect, APPROVAL_REQUIRED for mutations)
        ↓
     GOVERNANCE    (Policy engine, device authorization, step-up authentication, human review)
        ↓
  APPROVALREGISTRY (Single-use approval tokens binding target, parameters, and time)
        ↓
 RESOURCE ECONOMY  (Limits computer action frequency, capture intervals, and rate throttling)
        ↓
NATIVE RUNTIME CLIENT (Asynchronous framed JSON IPC channel over TCP/NamedPipe)
        ↓
    RUST RUNTIME   (kairo-runtime daemon, low-level OS boundary enforcement)
        ↓
 NATIVE SUBSTRATE  (Target window/process pre-action validation: ABORT_TARGET_CHANGED)
        ↓
 WIN32 CONTROL     (Win32 FFI: GetWindowRect, EnumWindows, SetCursorPos, SendInput, mouse_event)
        ↓
INPUT STATE TRACKER (Real-time tracking of held keys/buttons; emergency_reset_input release)
        ↓
 SCREEN OBSERVATION(Bounded frame capture: dimension limits, zero persistent raw pixel logging)
        ↓
   RETURN RESULT   (Structured ComputerOperationResult, timing, status, error categorization)
```

---

## 2. Core Architectural Principles

1. **Python / Rust Division of Responsibilities**:
   - **Python** owns high-level cognitive planning, goal decomposition, target identification, risk assessment, governance evaluation, security authorization, and human approval workflows.
   - **Rust** provides deterministic, low-level execution primitives: window enumeration, process inspection, display metrics, bounded screen capture, clipboard reading/writing, and synthetic input generation (mouse movements, clicks, keyboard events). Rust never autonomously decides UI actions.
2. **Target Context Binding (Zero Blind Coordinates)**:
   - Coordinate-only consequential clicking is strictly prohibited.
   - Actions provide `TargetContext` (expected window ID, window title substring, process name). Prior to injecting input, the native substrate verifies that the focused foreground window matches the intended target.
   - If the user switches windows or a popup interrupts focus, the action immediately aborts with `ABORT_TARGET_CHANGED`.
3. **EmergencyStop Always Wins**:
   - Operator kill-switch activation immediately blocks all computer interaction requests.
   - The native `InputStateTracker` releases all held mouse buttons and modifier keys (Ctrl, Shift, Alt) via OS input events to eliminate stuck-state hazards.
4. **Observation and Data Hygiene**:
   - Screen capture is strictly bounded in resolution and frequency. Raw pixel data is never persistently logged to disk or console.
   - Clipboard reading and writing are treated as sensitive data operations; contents are excluded from standard audit logs to protect credentials and personal data.
5. **Prompt Injection as Untrusted Data**:
   - Text retrieved from window titles, OCR/screen content, or clipboard buffers is categorized as untrusted external observation data. It is never elevated to instructions or policy modifiers.

---

## 3. Native Primitives Catalog

The native computer substrate exposes 8 distinct primitives:

| Capability ID | Tool Name | Mutating | Permission | Description |
| :--- | :--- | :--- | :--- | :--- |
| `native.window.inspect` | `native_window_inspect` | No | `READ` | Enumerate active host windows, titles, PIDs, geometry, visibility, and focus state. |
| `native.process.inspect` | `native_process_inspect` | No | `READ` | Discover host processes, names, parentage, and lifecycle state. |
| `native.display.inspect` | `native_display_inspect` | No | `READ` | Query monitor dimensions, DPI scale factors, and coordinate boundaries. |
| `native.screen.capture` | `native_screen_capture` | No | `READ` | Capture bounded point-in-time screen frame metadata with privacy screening. |
| `native.clipboard.read` | `native_clipboard_read` | No | `READ` | Read clipboard text content without persistent logging. |
| `native.clipboard.write` | `native_clipboard_write` | Yes | `WRITE` | Governed writing of text to the host clipboard. |
| `native.input.mouse` | `native_mouse_action` | Yes | `EXECUTE` | Target-validated cursor movements, single/double/right clicks with coordinate bounds checks. |
| `native.input.keyboard` | `native_keyboard_action` | Yes | `EXECUTE` | Target-validated text typing and key actions with stuck-key tracking and RAII release. |

---

## 4. Input State Tracking & Emergency Release

To protect against hung key modifiers or held mouse buttons (e.g. agent timeout while holding mouse drag or Shift key):
- The Rust runtime maintains an `InputStateTracker` wrapping `Arc<RwLock<HashSet<String>>>` for held keys and buttons.
- On any cancellation, deadline expiration, or `emergency_stop()` signal, `emergency_reset_input()` is called automatically.
- Win32 `mouse_event` sends `MOUSEEVENTF_LEFTUP`, `MOUSEEVENTF_RIGHTUP`, and `MOUSEEVENTF_MIDDLEUP`.
- Win32 `keybd_event` sends `KEYEVENTF_KEYUP` for all tracked virtual keys.

---

## 5. Safe Python Fallback (Degraded Mode)

When the native Rust runtime daemon is stopped or unreachable:
- Tool execution defaults to `ToolExecutionPreference.NATIVE_PREFERRED`.
- `ToolExecutor` catches connection failures, records circuit-breaker state, and seamlessly engages the safe Python fallback implementation (`_execute_python`).
- Fallback tools provide synthetic/mock observation data marked with `execution_class="PYTHON"`, allowing safe test suite execution and graceful degradation without service crashes.
