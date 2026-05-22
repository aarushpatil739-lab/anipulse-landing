# plan.md

## 1. Objectives
- Deliver the **AniPulse** product experience in phases:
  - ✅ **Marketing landing page** (cyberpunk anime aesthetic, neon glow + glassmorphism)
  - ✅ **Upload workflow**: creators upload **1–20 video clips** + **1 audio track**, see **progress**, **previews**, can remove files, and proceed to **“Process Now / Generate AMV”**.
  - ⏭️ **Phase 4 (current focus): AI-powered AMV Generator MVP**
    - Analyze uploaded music (BPM/beats/drops/energy)
    - Generate an edit timeline (beats→cuts, drops→transitions)
    - Render a beat-synced AMV with FFmpeg
    - Provide async processing with persisted status + progress
- Maintain a **clean, scalable architecture** with reusable UI components and backend services structured for future:
  - GPU acceleration
  - Cloud storage (S3 / Cloudflare R2)
  - AI scene detection, subtitles, multi-style editing modes
  - Queue scaling / distributed workers
- Ensure **responsive design**, accessibility basics, performance-friendly UI, and production-ready deployments.

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

# Phase 4: AI-Powered AMV Generator MVP (NEW — Current Focus)

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
- timestamps: stage started/completed

## 4.4 Core Engines to Implement

### 4.4.1 Audio Analysis Engine (librosa)
**Input:** uploaded music file

**Outputs:**
```json
{
  "bpm": 145,
  "beats": [0.43, 0.84, ...],
  "drops": [32.1, 64.2, ...],
  "energy_curve": [0.12, 0.18, ...]
}
```

**Features:**
- Detect BPM
- Beat timestamps
- Drops/intensity spikes
- Waveform energy / RMS
- Beat timeline JSON

### 4.4.2 Video Processing Engine (FFmpeg utilities)
Reusable functions:
- Probe metadata (duration, fps, resolution)
- Trim clips
- Concat/merge clips
- Auto-cut clips to beat timestamps
- Apply transitions and effects

**Transitions to support (MVP subset, extensible):**
- flash, fade, zoom, directional slide, blur

**Effects to support (MVP subset):**
- zoom in/out, camera shake, speed ramp, glow flashes, RGB split, motion blur

### 4.4.3 AI Edit Timeline Generator (Rules Engine)
Generate edit timeline JSON:
- Beats → cuts
- Drops → transitions
- High energy → faster cuts + stronger effects
- Low energy → smoother transitions + longer shots

**Weighted clip selection rules (MVP):**
- Avoid repeating same clip segment too frequently
- Favor motion-heavy clips during peaks
- Favor slower/emotional clips during lows
- Allow reuse of good clips around spikes

Output example:
```json
{
  "timeline": [
    {"clip": "clip1.mp4", "start": 0, "end": 2.4, "effect": "flash_transition"}
  ]
}
```

### 4.4.4 Render Pipeline (Async)
- Validate session readiness
- Audio analysis
- Generate timeline
- Render final output with FFmpeg
- Save output to `/backend/exports/sessions/{sessionId}/final.mp4`
- Update DB status + progress throughout
- Cleanup temp/intermediate files

## 4.5 Processing Queue System (Async, MVP)
- In-process asyncio-based queue (single instance)
- A background worker started on FastAPI startup
- Job record persisted in MongoDB so state survives refresh

**Progress tracking (example):**
- queued: 0–5%
- analyzing: 5–25%
- generating_timeline: 25–40%
- rendering: 40–95%
- completed: 100%

## 4.6 API Endpoints (Phase 4)
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

Design storage keys to be cloud-ready (S3/R2 prefix-compatible).

## 4.8 Frontend Changes (Phase 4)
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

## 4.9 Logging + Debugging
- Structured logs for:
  - uploads
  - librosa analysis
  - timeline generation
  - ffmpeg command lines + stderr capture
- Store a per-session log file path (don’t store massive logs in MongoDB)

## 4.10 Testing Plan (Phase 4)
- Unit tests:
  - audio analyzer outputs BPM/beats/drops
  - timeline generator mapping rules
- Integration tests:
  - enqueue job → status progression → completed
  - render pipeline produces valid mp4
- E2E:
  - upload → generate → poll → preview → download

---

## 3. Next Actions (Updated)
1. ✅ (Done) Implement upload workflow (Phase 3).
2. ✅ (Done) Prepare Railway backend deployment and fix requirements.
3. Deploy backend to Railway + configure MongoDB + CORS.
4. Update Vercel `REACT_APP_BACKEND_URL` and redeploy frontend.
5. Implement Phase 4:
   - Audio analysis engine (librosa)
   - Timeline generator
   - Async queue worker + status/progress
   - FFmpeg render pipeline
6. Update frontend `/upload` to show progress, preview, download.
7. Run one full E2E test pass for “upload → generate → download”.

---

## 4. Success Criteria (Updated)
- ✅ Landing page remains unchanged in look/feel.
- ✅ Upload workflow supports:
  - 1–20 video clips, 1 audio file
  - format + size validation
  - progress UI + remove files
  - responsive layout
- Phase 4 MVP:
  - Users can click **Generate AMV** and job is queued
  - Status progresses: queued → analyzing → generating_timeline → rendering → completed/failed
  - Progress % updates persist in DB
  - Final MP4 is rendered with beat-synced cuts
  - Output meets constraints (1080p 30fps H.264 AAC; fallback to 720p; ≤3min; ≤250MB)
  - Frontend shows preview player + download button
  - Errors are actionable, logged, and surfaced cleanly
- Architecture is modular and ready for:
  - Cloud storage migration
  - FFmpeg feature expansion
  - Scene detection / subtitles / style modes
  - Queue scaling
