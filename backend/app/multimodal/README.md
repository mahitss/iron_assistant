# Kairo Multimodal Intelligence Layer

Unified reasoning architecture across authorized **TEXT**, **IMAGE**, **AUDIO**, **VIDEO**, **SCREEN CONTEXT**, and **DOCUMENTS**.

## Architecture Pipeline

```
INPUT
  ↓
MODALITY DETECTION
  ↓
VALIDATION (Magic numbers, extensions, format integrity)
  ↓
SECURITY (Permissions, Device Binding, Emergency Stop, Anti-Injection)
  ↓
NORMALIZATION (Stable SHA-256 digests, dimensions, duration)
  ↓
MODEL ROUTING (Capability-matching: IMAGE, AUDIO, VIDEO, DOCUMENT)
  ↓
ANALYSIS (Image, Speech STT, Bounded Video Sampling, Grounded Documents, Ephemeral Screen)
  ↓
STRUCTURED RESULT (Citations, Evidence, Uncertainty Notes, Resource Usage)
  ↓
KNOWLEDGE / CONTEXT / USER
```

## Privileged Modalities & Device Governance
- **Zero Autonomous Hardware Access**: Screen, microphone, camera, and filesystem captures strictly require explicit user permissions and active device verification.
- **Vision vs. Computer Separation**: Visual analysis ("What is on the screen?") is strictly separated from Computer actions ("Click button"). Visual outputs never trigger actions without standard SecurityCenter approval.
- **Anti-Prompt Injection**: Derived OCR (`DERIVED_OCR_CONTENT`), transcripts (`DERIVED_TRANSCRIPT`), and document text are quarantined as untrusted user inputs that cannot mutate system policies or grant permissions.
- **Privacy by Design**: Inferring sensitive personal attributes (health, religion, politics, sexual orientation, personality) and persistent biometric profiling (face embeddings, voiceprints) are strictly prohibited.
