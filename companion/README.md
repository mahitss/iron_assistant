# Kairo Local Companion Runtime

The **Kairo Local Companion** is a sandboxed, trusted local daemon enabling Kairo to interact safely with the user's personal workstation without exposing unrestricted remote desktop control, shell execution, or arbitrary code execution to the cloud.

---

## Core Security Guarantees

1. **Zero Remote Shell**: Arbitrary shell execution (`shell.execute`, bash, PowerShell, cmd.exe) is strictly **FORBIDDEN**. Only allowlisted, structured actions can be called.
2. **Dual-Layer Authorization**: Every request must satisfy both Cloud SecurityCenter authorization and the independent `LocalPolicyEngine`.
3. **Safe Default OFF**: Computer control, microphone, and camera are **OFF** by default and automatically revert to OFF upon crash, restart, or prolonged inactivity (15m).
4. **Local Emergency Stop**: Instant hardware cutoff operates independently of network connectivity.
5. **Sandboxed Filesystem**: Strictly bounded to approved workspace paths with canonical realpath resolution and traversal (`../`) defense.

---

## Quickstart & CLI Usage

```bash
# 1. Check local companion status
python -m companion.src.main status

# 2. Pair device with Kairo Cloud
python -m companion.src.main register --cloud-url http://localhost:8000 --token $USER_JWT_TOKEN --name "My Workstation"

# 3. Explicitly arm a capability
python -m companion.src.main arm --capability computer_control

# 4. Trigger Local Emergency Stop
python -m companion.src.main stop

# 5. Clear Emergency Stop (returns to safe OFF state)
python -m companion.src.main reset-stop
```
