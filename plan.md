# plan.md

## 1. Objectives
- Deliver the **AniPulse** product experience in phases:
  - ✅ **Marketing landing page** (dark anime cyberpunk aesthetic; neon glow + glassmorphism)
  - ✅ **Upload workflow**: creators upload **1–20 video clips** + **1 audio track**, see **progress**, **previews**, can remove files, and proceed to processing.
  - ⏭️ **Phase 4 (current focus): AI-powered AMV Generator MVP**
    - ✅ Analyze uploaded music (BPM/beats/drops/energy) via `librosa`
    - 🔄 Build a **stable, modular FFmpeg utilities layer** (core rendering foundation)
    - ⏭️ Generate an edit timeline (beats→cuts, drops→transitions)
    - ⏭️ Render a beat-synced AMV with FFmpeg
    - ⏭️ Provide async processing with persisted status + progress
- Maintain a **clean, scalable architecture** with reusable UI components and backend services structured for future:
  - Cloud storage (S3 / Cloudflare R2)
  - GPU acceleration
  - AI scene detection, subtitles, multi-style editing modes
  - Queue scaling / distributed workers
- Enforce engineering requirements for Phase 4 foundation:
  - Stability-first development
  - Modular, reusable utilities
  - Thorough automated/integration testing before timeline generation
  - Detailed FFmpeg logging + actionable error reporting
  - Output integrity validation after every operation
  - Cleanup of intermediate artifacts
  - Performance/timing metrics for all rendering operations
  - Compatibility with async FastAPI architecture (no API blocking)

---

## 2. Implementation Steps

### Phase 1: Core POC (skip — not required)
- No external integrations required for the landing page.

---

## STATUS UPDATE — Phase 2 COMPLETED ✅ (Landing Page)

**Completion Date:** May 21, 2026

**Phase 2 Results:**
- ✅ 100% test success rate (0 bugs found)
- ✅ Fully responsive (mobile + desktop)
- ✅ Smooth animations and premium cyberpunk glass UI
- ✅ Zero console errors

**Delivered Components:**
- Sticky Navbar + mobile menu
- Hero (animated background + CTAs)
- Features (5 feature cards)
- How It Works (4 steps)
- Demo Preview (6 cards)
- CTA section
- Footer with social links

**Branding:**
- ✅ Renamed all branding from **CyberEdit → AniPulse**

**Deployment readiness:**
- ✅ GitHub repo connected
- ✅ Vercel-ready frontend config (`vercel.json`, `.vercelignore`, docs)

---

### Phase 2: V1 App Development (Landing Page) ✅ Completed

**User stories**
1. ✅ As a creator, I want to instantly understand what AniPulse does from the hero headline and visuals.
2. ✅ As a mobile user, I want the entire page to be readable and fast without horizontal scrolling.
3. ✅ As a user, I want smooth animations that feel premium but don’t distract from the CTA.
4. ✅ As a creator, I want to scan features quickly and know if it supports TikTok/Reels export.
5. ✅ As a user, I want to see believable demo previews that communicate “anime edit output”.

**Phase 2 test**
- ✅ One full E2E pass completed with testing agent.

---

## STATUS UPDATE — Phase 3 COMPLETED ✅ (Upload System)

**Completion Date:** May 21–22, 2026

**Phase 3 Results:**
- ✅ Upload workflow implemented end-to-end (frontend + backend)
- ✅ Drag-and-drop upload UI + browse fallback
- ✅ Per-file progress via XHR progress events
- ✅ File validation (type/size/count/total budget)
- ✅ Remove uploaded files (frontend + backend)
- ✅ Video thumbnail previews (client-side)
- ✅ “Process Now” / placeholder processing endpoint
- ✅ E2E test pass completed

**Backend deliverables:**
- ✅ UploadSession model persisted to MongoDB
- ✅ StorageProvider abstraction with LocalStorageProvider
- ✅ Endpoints:
  - `POST /api/upload/sessions`
  - `GET /api/upload/sessions/{session_id}`
  - `POST /api/upload/sessions/{session_id}/videos`
  - `POST /api/upload/sessions/{session_id}/audio`
  - `DELETE /api/upload/sessions/{session_id}/files/{file_id}`
  - `POST /api/upload/sessions/{session_id}/process` (placeholder)

**Frontend deliverables:**
- ✅ `/upload` route with cyberpunk UI
- ✅ Navbar + Hero CTAs route to `/upload`
- ✅ Upload summary + button enable/disable logic

---

## STATUS UPDATE — Deployment Track (Backend) IN PROGRESS 🔄

**Railway readiness improvements:**
- ✅ Production-ready FastAPI config (env vars, health endpoint, logs)
- ✅ Railway config added (`backend/railway.json`, `backend/Procfile`, `backend/runtime.txt`)
- ✅ CORS configured via `CORS_ORIGINS`
- ✅ Documentation added:
  - `backend/RAILWAY_DEPLOYMENT.md`
  - `FRONTEND_CONFIG.md`
  - `DEPLOYMENT_CHECKLIST.md`
- ✅ Fixed Railway build blocker:
  - Removed Emergent/internal dependency from `backend/requirements.txt`
  - Requirements now include only PyPI-installable packages

**Remaining:**
- 🔄 Deploy backend to Railway + set env vars
- 🔄 Update Vercel `REACT_APP_BACKEND_URL` to Railway URL

---

### Phase 3: Upload System Implementation ✅ Completed

#### 3.1 Scope
Build the **upload workflow** (no AI editing yet in Phase 3):
- Drag-and-drop upload UI
- Upload **multiple video clips** (min 1, max 20)
- Upload **single audio/music file** (exactly 1)
- Show per-file progress + overall summary
- Validate files (type, count, size, total size)
- Allow removing previously uploaded files
- Show preview thumbnails for uploaded videos
- After upload completes: show previews + enable **“Process Now”** button (placeholder)
- Preserve existing landing page design.

#### 3.2 Upload Constraints (Confirmed)
- **Video**: MP4, MOV, WebM
  - Max size per clip: **500MB**
  - Count: **1–20** clips
- **Audio**: MP3, WAV
  - Max size: **50MB**
  - Count: **1** file
- **Total upload budget per session**: **2GB**

#### 3.3 Backend (APIs + Storage)
**Goal:** local storage now, structured for future cloud storage.

**Storage layout (local):**
- `/backend/uploads/sessions/{sessionId}/videos/*`
- `/backend/uploads/sessions/{sessionId}/audio/*`
- `/backend/uploads/sessions/{sessionId}/thumbnails/*` (reserved)

**Modular architecture for future:**
- `services/storage_provider.py` (Local now, S3/R2 later)
- `services/file_validator.py`
- `services/upload_session_service.py`

---

# Phase 4: AI-Powered AMV Generator MVP (CURRENT — Foundation First)

## 4.1 Product Goal
Create the first working MVP that **automatically generates a beat-synced anime AMV** from:
- uploaded anime clips (1–20)
- one music file (MP3/WAV)

**Output:** MP4 (H.264 + AAC), default **1920×1080 @ 30 FPS**, optimized for TikTok/Reels/Shorts.
- Fallback to **720p** if 1080p render fails
- Hard cap output length: **≤ 3 minutes**
- Target output file size: **≤ 250MB**

## 4.2 Processing UX Requirements (Confirmed)
- Fully async processing; user can leave and return later
- Persist processing state + progress in MongoDB
- Provide live updates while user stays on the page
- Frontend polls every **3–5 seconds**

**State machine:**
`queued → analyzing → generating_timeline → rendering → completed` (or `failed`)

**Max total processing time:** 10 minutes

## 4.3 Backend Architecture (Scalable Structure)

### 4.3.1 Folder structure (target)
```
backend/
  api/
  services/
  processing/
  ffmpeg/
  models/
  uploads/
  exports/
  logs/
  tests/
```

### 4.3.2 Data model additions (MongoDB)
Extend UploadSession (or add a new ProcessingSession) to include:
- `status`: queued/analyzing/generating_timeline/rendering/completed/failed
- `progress_pct`: 0–100
- `current_stage`: string
- `audio_analysis`: { bpm, beats, drops, energy_curve }
- `edit_timeline`: structured JSON
- `export`: { storage_key, url/path, size_bytes, duration }
- `ffmpeg_logs`: path or tail snippets (store pointer, not huge logs)
- `error_message`, `error_trace_id`
- performance metrics:
  - `timings_ms`: { probe, trim, concat, transition, export, total }
- timestamps: stage started/completed

## 4.4 Core Engines to Implement

### 4.4.1 Audio Analysis Engine (librosa) ✅ Implemented
**File:** `backend/services/audio_analyzer.py`

**Outputs (example):**
```json
{
  "bpm": 145,
  "beats": [0.43, 0.84],
  "drops": [32.1, 64.2],
  "energy_curve": [{"time": 0.0, "energy": 0.12}]
}
```

### 4.4.2 Video Processing Engine (FFmpeg utilities) 🔄 IN PROGRESS (Stability Gate)
**File:** `backend/services/ffmpeg_utils.py`

**Current state:**
- ✅ Implemented core functions (probe, trim, concat, extract_audio, merge_audio)
- ✅ Implemented initial transitions/effects (transition, zoom, shake, speed ramp, export)
- 🔄 Needs stability hardening + comprehensive tests + integrity validation
- 🔄 Needs detailed FFmpeg logging + performance metrics
- 🔄 Needs async-compatible API test endpoints

**Design requirements (from latest user requirements):**
- Transition/effect functions must be modular and independently testable
- Each operation must validate output integrity (video stream present, duration > 0, playable container)
- All intermediate outputs must be cleaned up after tests
- Add timing/performance metrics per operation
- Add detailed execution logging, including:
  - fully logged FFmpeg commands (sanitized)
  - stderr capture (tail + full log file option)
  - structured error payloads

**Integrity validation checklist (per output):**
- file exists and size > minimum threshold
- `ffprobe` confirms expected streams (video, optional audio)
- duration is non-zero and within expected range tolerance
- container/codec is compatible (`h264/aac` for mp4 where relevant)

### 4.4.3 AI Edit Timeline Generator (Rules Engine) ⏭️ BLOCKED until FFmpeg utilities are verified
Generate edit timeline JSON:
- Beats → cuts
- Drops → transitions
- High energy → faster cuts + stronger effects
- Low energy → smoother transitions + longer shots

**Hard rule:** Timeline generation begins only after FFmpeg utilities + endpoints are tested and verified.

### 4.4.4 Render Pipeline (Async) ⏭️ After timeline generator
- Validate session readiness
- Audio analysis
- Generate timeline
- Render final output with FFmpeg
- Save output to `/backend/exports/sessions/{sessionId}/final.mp4`
- Update DB status + progress throughout
- Cleanup temp/intermediate files

## 4.5 Processing Queue System (Async, MVP) ⏭️ After FFmpeg layer verified
- In-process asyncio-based queue (single instance)
- Background worker started on FastAPI startup
- Job record persisted in MongoDB so state survives refresh

**Progress tracking (example):**
- queued: 0–5%
- analyzing: 5–25%
- generating_timeline: 25–40%
- rendering: 40–95%
- completed: 100%

## 4.6 API Endpoints (Phase 4)

### 4.6.1 FFmpeg Test Endpoints (NEW — must implement before timeline work)
Add endpoints for verifying FFmpeg utilities in isolation (async, non-blocking implementation):
- `POST /api/test/ffmpeg/trim`
- `POST /api/test/ffmpeg/concatenate`
- `POST /api/test/ffmpeg/transition`
- (optional) `POST /api/test/ffmpeg/effect/zoom`
- (optional) `POST /api/test/ffmpeg/effect/shake`
- (optional) `POST /api/test/ffmpeg/effect/speed_ramp`

Each endpoint must:
- accept uploaded/selected session media
- run the operation asynchronously (or in background task pattern)
- return:
  - output path/key
  - probe metadata of output
  - integrity validation results
  - timing metrics
  - log trace id / location

### 4.6.2 AMV Generation Endpoints (Later)
Add endpoints (keeping Phase 3 upload endpoints):
- `POST /api/amv/sessions/{session_id}/generate` → enqueue job
- `GET /api/amv/sessions/{session_id}/status` → status + progress + stage
- `GET /api/amv/sessions/{session_id}/timeline` → timeline JSON (optional)
- `GET /api/amv/sessions/{session_id}/audio-analysis` → analysis JSON (optional)
- `GET /api/amv/sessions/{session_id}/download` → download final MP4 (or signed URL later)

## 4.7 Storage (Phase 4)
Local storage for MVP:
- uploads: `/backend/uploads/sessions/{session_id}/...`
- exports: `/backend/exports/sessions/{session_id}/final.mp4`
- logs: `/backend/logs/sessions/{session_id}/ffmpeg.log`
- temp: `/backend/temp/*` (ensure cleanup)

Design storage keys to be cloud-ready (S3/R2 prefix-compatible).

## 4.8 Frontend Changes (Phase 4) ⏭️ After backend generation endpoints exist
Maintain existing look/feel.

### Pages/UI
- `/upload` enhancements:
  - Replace placeholder “Process Now” with **Generate AMV** (calls generate endpoint)
  - Show processing state machine + progress bar
  - Poll status every 3–5 seconds
  - When completed: show preview video player + download button

### Components (reusable)
- `ProcessingStatusCard` (stage + message)
- `ProcessingProgressBar` (overall + stage)
- `ExportPlayer` (HTML5 video)
- `DownloadButton`

## 4.9 Logging + Debugging (Expanded)
- Structured logs for:
  - uploads
  - librosa analysis
  - timeline generation
  - FFmpeg command lines + stderr capture
- Add per-operation FFmpeg log context:
  - `operation_id` / `trace_id`
  - command
  - return code
  - stderr tail
  - full stderr path (optional)
  - elapsed time
- Store a per-session log file path (don’t store massive logs in MongoDB)

## 4.10 Testing Plan (Phase 4) (Updated: Stability-first)

### 4.10.1 FFmpeg Utilities Test Harness (NEW — MUST COMPLETE FIRST)
Create deterministic tests using generated media (avoid relying on user uploads):
- Generate synthetic video clips via ffmpeg filters (color test sources)
- Generate synthetic audio via sine wave

**Required tests for `FFmpegUtils`:**
- probe:
  - returns duration/size/streams; handles missing audio
- trim:
  - output duration within tolerance; playable mp4
- concatenate:
  - output duration approx sum of inputs; playable mp4
- extract_audio:
  - output has audio stream; non-zero duration
- merge_audio:
  - output contains video + new audio; duration trimmed correctly
- apply_transition:
  - output playable; duration expected; transition types validated
- apply_zoom / apply_shake / apply_speed_ramp:
  - output playable; duration expected; independent testability
- export_final:
  - outputs correct resolution/fps; `+faststart`; size cap logic

**Test artifacts requirements:**
- Validate integrity after each operation via `ffprobe` checks
- Ensure cleanup of intermediates (even on failure)
- Record performance metrics per operation

### 4.10.2 Integration Tests (After FFmpeg utilities verified)
- Exercise `/api/test/ffmpeg/*` endpoints end-to-end
- Confirm async behavior (no blocking; timeouts; predictable failure errors)

### 4.10.3 Unit tests (Later)
- audio analyzer outputs BPM/beats/drops
- timeline generator mapping rules

### 4.10.4 E2E (Later)
- upload → generate → poll → preview → download

---

## 3. Next Actions (Updated)

### Stability Gate: FFmpeg Foundation (NOW)
1. 🔄 Review and harden `backend/services/ffmpeg_utils.py`
   - add structured logging + stderr capture
   - add output integrity validation helpers
   - add consistent exception payloads
   - add performance timing metrics wrappers
   - ensure all functions are reusable and side-effect controlled
2. 🔄 Create comprehensive local test harness:
   - `backend/tests/test_ffmpeg_core.py` (or similar)
   - synthetic media generation
   - automated cleanup
   - produce a test report artifact (JSON)
3. 🔄 Add FastAPI test endpoints for FFmpeg utilities:
   - trim, concatenate, transition (+ optional effects)
   - ensure async-compatible execution
4. 🔄 Verify endpoints via curl/python scripts and confirm outputs play.

### After Stability Gate Passes
5. Deploy backend to Railway + configure MongoDB + CORS.
6. Update Vercel `REACT_APP_BACKEND_URL` and redeploy frontend.
7. Implement timeline generator (rules engine).
8. Implement async queue worker + persisted status/progress.
9. Implement full render pipeline and AMV endpoints.
10. Update frontend `/upload` with progress + preview + download.
11. Run one full E2E test pass for “upload → generate → download”.

---

## 4. Success Criteria (Updated)
- ✅ Landing page remains unchanged in look/feel.
- ✅ Upload workflow supports:
  - 1–20 video clips, 1 audio file
  - format + size validation
  - progress UI + remove files
  - responsive layout

### Phase 4 Stability Gate (NEW — Must pass before timeline work)
- FFmpeg utilities are fully tested with deterministic inputs.
- All operations produce validated, playable outputs.
- Detailed logging exists for every FFmpeg execution (command + stderr tail + trace id).
- Performance metrics are captured per operation.
- Test endpoints exist and are verified working.
- Intermediate files are cleaned up reliably.
- Utilities are modular and reusable for the future render pipeline.
- Async FastAPI compatibility is maintained (no blocking request thread; timeouts handled).

### Phase 4 MVP (After Stability Gate)
- Users can click **Generate AMV** and job is queued.
- Status progresses: queued → analyzing → generating_timeline → rendering → completed/failed.
- Progress % updates persist in DB.
- Final MP4 is rendered with beat-synced cuts.
- Output meets constraints (1080p 30fps H.264 AAC; fallback to 720p; ≤3min; ≤250MB).
- Frontend shows preview player + download button.
- Errors are actionable, logged, and surfaced cleanly.
- Architecture is modular and ready for:
  - Cloud storage migration
  - FFmpeg feature expansion
  - Scene detection / subtitles / style modes
  - Queue scaling
