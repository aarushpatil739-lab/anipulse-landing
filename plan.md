# plan.md

## 1. Objectives
- Deliver the **AniPulse** product experience in phases:
  - ✅ **Marketing landing page** (dark anime cyberpunk aesthetic; neon glow + glassmorphism)
  - ✅ **Upload workflow**: creators upload **1–20 video clips** + **1 audio track**, see **progress**, **previews**, can remove files, and proceed to processing.
  - 🔄 **Phase 4 (current focus): AI-powered AMV Generator MVP**
    - ✅ Analyze uploaded music (BPM/beats/drops/energy) via `librosa` (`audio_analyzer.py`)
    - ✅ Build and verify a **stable, modular FFmpeg utilities layer** (core rendering foundation)
    - 🔄 Build **AI Timeline Generator** (beats→cuts, drops→transitions, energy→pacing/effects)
    - 🔄 Build **async processing queue system** (queued → analyzing_audio → generating_timeline → rendering → completed/failed)
    - 🔄 Render a beat-synced AMV using the verified FFmpeg foundation
    - 🔄 Persist processing state + progress in MongoDB
- Maintain a **clean, scalable architecture** with reusable frontend components and backend services structured for future:
  - Cloud storage (S3 / Cloudflare R2)
  - GPU acceleration
  - AI scene detection, subtitles, multi-style editing modes
  - Queue scaling / distributed workers

### Engineering priorities (Phase 4)
- Stability-first development
- Modular and reusable services (timeline generation independent of FFmpeg)
- Thorough automated/integration testing before expanding effects
- Detailed logging + actionable error reporting
- Output integrity validation after every operation
- Cleanup of intermediate artifacts
- Performance/timing metrics for rendering operations
- Async FastAPI compatibility (no blocking API)

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

# Phase 4: AI-Powered AMV Generator MVP (CURRENT)

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

**State machine (updated):**
`queued → analyzing_audio → generating_timeline → rendering → completed` (or `failed`)

**Max total processing time:** 10 minutes

## 4.3 Backend Architecture (Scalable Structure)

### 4.3.1 Folder structure (target)
```
backend/
  api/
  services/
    audio_analyzer.py
    ffmpeg_utils.py
    timeline_generator.py
    clip_selector.py
    pacing_engine.py
    render_service.py
  processing/
    queue.py
    worker.py
  models/
    upload_session.py
    generation_job.py
  uploads/
  exports/
  logs/
  tests/
```

### 4.3.2 Data model additions (MongoDB)
Add a **GenerationJob** collection (preferred over mutating UploadSession heavily) OR extend UploadSession with job fields.

**GenerationJob fields (recommended):**
- `job_id`: string (UUID)
- `session_id`: string
- `status`: queued/analyzing_audio/generating_timeline/rendering/completed/failed
- `progress_pct`: 0–100
- `current_stage`: string
- `audio_analysis`: { bpm, beats, drops, energy_curve, sections }
- `edit_timeline`: structured JSON
- `export`: { path, size_bytes, duration }
- `timings_ms`: { analyzing_audio, generating_timeline, rendering, total }
- `ffmpeg_logs`: { last_trace_id, log_files[] } (pointers only)
- `error_message`, `error_trace_id`
- timestamps: `created_at`, `updated_at`, `started_at`, `completed_at`

## 4.4 Core Engines

### 4.4.1 Audio Analysis Engine (librosa) ✅ Implemented
**File:** `backend/services/audio_analyzer.py`

Outputs include:
- BPM
- beat timestamps
- drop/intensity timestamps
- energy curve + energy sections

### 4.4.2 Video Processing Engine (FFmpeg utilities) ✅ VERIFIED (Stability Gate PASSED)
**File:** `backend/services/ffmpeg_utils.py`

**Delivered:**
- ✅ detailed execution logging (trace IDs, full stderr logs to `/backend/logs`)
- ✅ performance metrics per operation
- ✅ output integrity validation helper (`validate_output`)
- ✅ modular transitions/effects
- ✅ async-compatible subprocess execution

**Test endpoints (verified):**
- ✅ `POST /api/test/ffmpeg/probe`
- ✅ `POST /api/test/ffmpeg/trim`
- ✅ `POST /api/test/ffmpeg/concatenate`
- ✅ `POST /api/test/ffmpeg/transition`
- ✅ `GET /api/test/ffmpeg/metrics`

**Report:** `/app/FFMPEG_STABILITY_GATE_REPORT.md`

### 4.4.3 AI Timeline Generator (Rules + Weighted Random) 🔄 NOW
**Goal:** Produce structured edit timeline JSON independent of FFmpeg implementation.

**Responsibilities:**
- map beat timestamps to cuts
- map drops/intensity spikes to transitions
- map energy levels to pacing
- assign effects dynamically
- generate structured edit timeline JSON

**Output example:**
```json
{
  "timeline": [
    {
      "clip": "clip_01.mp4",
      "start": 0.0,
      "end": 2.4,
      "transition": "flash",
      "effect": "zoom_shake",
      "energy": "high"
    }
  ]
}
```

**Safety checks (must pass before rendering):**
- no negative times; `start < end`
- no overlaps unless explicitly allowed
- total output duration ≤ audio duration and ≤ 180s cap
- referenced clips exist and have sufficient duration
- avoid empty timeline

### 4.4.4 Clip Selection Engine 🔄 NOW
**Rules:**
- avoid repetitive clips (cooldowns, last-used penalty)
- avoid reusing the same time ranges too frequently
- weighted/random selection tuned by energy section:
  - high energy: prefer motion-heavy clips (proxy via high FPS, higher bitrate, shorter shot lengths; future: optical flow)
  - low energy: prefer longer, smoother clips

### 4.4.5 Dynamic Pacing Engine 🔄 NOW
**Rules:**
- high BPM → faster cuts
- low energy → longer cinematic shots
- drops → stronger transitions/effects
- calm sections → smoother pacing
- anime-style AMV pacing:
  - fast aggressive cuts during drops
  - cinematic pauses during emotional sections
  - smooth pacing transitions between energy levels

### 4.4.6 Render Service (Modular, Async) ⏭️ AFTER Timeline Generator
**Responsibilities:**
- validate generated timeline
- execute a minimal, stable rendering pipeline using FFmpegUtils:
  - trim segments
  - apply transitions/effects (MVP subset)
  - concatenate
  - merge music
  - export final
- validate output integrity (non-empty, playable)
- cleanup intermediates

## 4.5 Async Processing Queue System (MVP) 🔄 NOW
**Design:**
- In-process asyncio Queue (single worker) for MVP
- Persistent job record in MongoDB
- Non-blocking API: `POST /api/generate` enqueues and returns `job_id`
- Worker loop runs on FastAPI startup

**Stages:**
- queued (0–5%)
- analyzing_audio (5–25%)
- generating_timeline (25–45%)
- rendering (45–95%)
- completed (100%)
- failed (error)

**Logging requirements:**
- queue execution logs
- stage start/end logs
- timeline generation logs
- clip selection logs
- pacing decision logs
- render stage logs + ffmpeg trace IDs

## 4.6 API Endpoints (Phase 4 Generation)

### 4.6.1 Generation endpoints (NEW)
- `POST /api/generate`
  - body: `{ "session_id": "...", "style": "amv_default" }` (style optional)
  - returns: `{ job_id }`
- `GET /api/generate/{job_id}/status`
  - returns: status, progress_pct, stage, error_message (if failed)
- `GET /api/generate/{job_id}/timeline`
  - returns: generated timeline JSON
- `GET /api/generate/{job_id}/download`
  - returns: final MP4 (FileResponse) or JSON with path

### 4.6.2 Test generation endpoint (NEW)
- `POST /api/generate/test`
  - Uses uploaded clips + uploaded audio (from session)
  - Runs: analyze → timeline → render
  - Intended for integration validation (not production)

## 4.7 Storage (Phase 4)
Local storage for MVP:
- uploads: `/backend/uploads/sessions/{session_id}/...`
- temp: `/backend/temp/jobs/{job_id}/...`
- exports: `/backend/exports/jobs/{job_id}/final.mp4`
- logs: `/backend/logs/*` (FFmpeg stderr per operation; optional per-job summary log)

All paths must be cloud-ready (prefix compatible for future S3/R2).

## 4.8 Frontend Changes (Phase 4) ⏭️ After generation endpoints exist
Maintain existing look/feel.

### Pages/UI
- `/upload` enhancements:
  - Replace placeholder “Process Now” with **Generate AMV** (calls `POST /api/generate`)
  - Show processing state machine + progress bar
  - Poll status every 3–5 seconds
  - When completed: preview player + download button

## 4.9 Logging + Debugging (Phase 4)
- Structured logs for:
  - audio analysis
  - timeline generation decisions
  - clip selection weights + outcomes
  - pacing rules applied
  - render stage and FFmpeg trace IDs
  - queue job lifecycle
- Store pointers in MongoDB rather than raw logs

## 4.10 Testing Plan (Phase 4)

### 4.10.1 Unit tests (NEW)
- timeline generator:
  - stable deterministic output given fixed random seed
  - no overlaps / invalid segments
  - respects duration caps
- clip selection:
  - enforces cooldown/anti-repetition
  - energy-based weighting changes distribution
- pacing engine:
  - high BPM produces shorter average cuts
  - drops produce stronger transitions/effects

### 4.10.2 Integration tests (NEW)
- `POST /api/generate/test` with a small session:
  - validates job transitions and progress updates
  - validates final output exists and passes integrity
  - validates cleanup of intermediates

### 4.10.3 E2E (Later)
- upload → generate → poll → preview → download

---

## 3. Next Actions (Updated)

### Completed Foundation
1. ✅ Audio analysis service implemented (`audio_analyzer.py`).
2. ✅ FFmpeg utilities stability gate passed:
   - hardened utilities + integrity validation + metrics
   - test scripts and verified test endpoints

### Phase 4: Timeline + Queue + MVP Render (NOW)
3. 🔄 Implement **GenerationJob** model + MongoDB persistence.
4. 🔄 Implement **async queue + background worker** (startup task).
5. 🔄 Implement **Timeline Generator** service:
   - pacing engine
   - clip selection engine
   - transition/effect assignment
   - timeline validation
6. 🔄 Implement **Render Service** that consumes timeline and uses FFmpegUtils.
7. 🔄 Add generation endpoints:
   - `POST /api/generate`
   - `GET /api/generate/{job_id}/status`
   - `GET /api/generate/{job_id}/timeline`
   - `GET /api/generate/{job_id}/download`
   - `POST /api/generate/test`
8. 🔄 Integration test pass:
   - create session with 2–3 clips + audio
   - run generate/test
   - validate final mp4 integrity

### After MVP Pipeline Works
9. Deploy backend to Railway + configure MongoDB + CORS.
10. Update Vercel `REACT_APP_BACKEND_URL` and redeploy frontend.
11. Update frontend `/upload` with progress + preview + download.
12. Run full E2E test pass for “upload → generate → download”.

---

## 4. Success Criteria (Updated)
- ✅ Landing page remains unchanged in look/feel.
- ✅ Upload workflow supports:
  - 1–20 video clips, 1 audio file
  - format + size validation
  - progress UI + remove files
  - responsive layout

### Phase 4 Foundation (Completed)
- ✅ FFmpeg utilities are fully tested with deterministic inputs.
- ✅ All operations produce validated, playable outputs.
- ✅ Detailed logging exists for every FFmpeg execution (command + stderr + trace id).
- ✅ Performance metrics captured per operation.
- ✅ Test endpoints exist and are verified working.
- ✅ Intermediate files cleaned up reliably.
- ✅ Async FastAPI compatibility maintained.

### Phase 4 MVP (Target)
- User can start generation with `POST /api/generate` and receives `job_id`.
- Job status progresses: queued → analyzing_audio → generating_timeline → rendering → completed/failed.
- Progress % updates persist in MongoDB.
- Timeline JSON is generated, validated, and downloadable.
- Final MP4 is rendered and downloadable, and passes integrity checks.
- Output meets constraints:
  - 1080p 30fps H.264 + AAC (fallback to 720p)
  - ≤ 3 minutes
  - ≤ 250MB
- Anime-style AMV pacing achieved:
  - aggressive cuts at drops
  - cinematic pauses in low energy sections
  - smooth transitions between energy levels
- Architecture remains modular and future-ready:
  - cloud storage migration
  - GPU acceleration
  - expanded effects
  - distributed job queue
