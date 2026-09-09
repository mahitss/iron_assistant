# Kairo Multimodal Intelligence Layer Specification (Task 30)

## 1. Overview
The Kairo Multimodal Intelligence Layer unifies reasoning across authorized **TEXT**, **IMAGE**, **AUDIO**, **VIDEO**, **SCREEN CONTEXT**, and **DOCUMENTS** under a single consistent request and context pipeline.

## 2. Invariants & Security Principles
- **No Autonomous Peripheral/Hardware Access**: Microphone, camera, screen, and filesystem captures strictly require explicit user permissions and active device verification.
- **Vision vs. Computer Action Separation**: Visual analysis ("What is on the screen?") is strictly separated from Computer Action ("Do something on the screen"). Visual outputs can never autonomously dispatch mouse or keyboard actions without the normal `Skill -> Plan -> SecurityCenter -> Human Approval -> Local Companion` pipeline.
- **Anti-Prompt Injection**: Derived OCR (`DERIVED_OCR_CONTENT`), speech transcripts (`DERIVED_TRANSCRIPT`), document chunks, and screen observations are quarantined as untrusted user content. They cannot modify system prompts or grant permissions.
- **Strict Privacy & Anti-Profiling**: No automatic inference of sensitive personal attributes (health, religion, political beliefs, sexual orientation, personality profiles). No persistent biometric profiling (face embeddings, voiceprints).

## 3. Supported Modalities & Limits

| Modality | Formats / Signatures | Size Limit | Duration Limit | Frame/Chunk Bound |
|---|---|---|---|---|
| **TEXT** | UTF-8 | 50,000 chars | N/A | N/A |
| **IMAGE** | PNG, JPEG, WebP, GIF | 15 MB | N/A | Max 4096px dimension |
| **AUDIO** | WAV, MP3, OGG, M4A | 25 MB | 300 seconds | Timestamps / Segments |
| **VIDEO** | MP4, WebM, MOV | 50 MB | 180 seconds | Bounded 30 frames (5s step) |
| **DOCUMENT** | PDF, DOCX, TXT, MD, CSV, JSON | 20 MB | N/A | Max 10 chunks / Page citations |
| **SCREEN** | Ephemeral Companion Capture | N/A | N/A | Ephemeral only (no disk persistence) |

## 4. API Endpoints
- `POST /api/v1/multimodal/analyze`: Analyze multimodal requests (text + image/screen/document).
- `POST /api/v1/multimodal/transcribe`: Audio transcription with timestamps and speaker-independent segments.
- `POST /api/v1/multimodal/process`: General multimodal pipeline entrypoint.
- `GET /api/v1/multimodal/{request_id}`: Status and cached result retrieval.

## 5. Event Bus Topics
- `multimodal.requested`
- `multimodal.processing`
- `multimodal.completed`
- `multimodal.failed`
- `image.processed`
- `audio.transcribed`
- `video.processed`
- `document.processed`
- `screen.captured` (Audit logged)
