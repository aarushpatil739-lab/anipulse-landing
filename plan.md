# plan.md

## 1. Objectives
- Deliver the **AniPulse** product experience in phases:
  - ✅ **Marketing landing page** (cyberpunk anime aesthetic, neon glow + glassmorphism)
  - ⏭️ **Upload workflow (current focus)**: creators can upload **1–20 video clips** + **1 audio track**, see **progress**, **previews**, and proceed to a **“Process Now”** step (no AI editing implemented yet).
- Maintain a **clean, scalable architecture** with reusable UI components and a backend structured for future **FFmpeg** + **AI processing** integrations.
- Ensure **responsive design**, accessibility basics, and performance-friendly UI.

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
- ✅ GitHub repo connected (manual push supported)
- ✅ Vercel-ready config (`vercel.json`, `.vercelignore`, updated docs)

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

### Phase 3: Upload System Implementation (Current Focus)

#### 3.1 Scope
Build the **upload workflow only** (no AI editing yet):
- Drag-and-drop upload UI
- Upload **multiple video clips** (min 1, max 20)
- Upload **single audio/music file** (exactly 1)
- Show per-file progress + overall progress
- Validate files (type, count, size, total size)
- Allow removing previously uploaded files
- Show preview thumbnails for uploaded videos
- After upload completes: show previews + enable **“Process Now”** button (placeholder)
- Preserve existing landing page design and routes; add upload flow without altering the marketing look.

#### 3.2 Upload Constraints (Confirmed)
- **Video**: MP4, MOV, WebM
  - Max size per clip: **500MB**
  - Count: **1–20** clips
- **Audio**: MP3, WAV
  - Max size: **50MB**
  - Count: **1** file
- **Total upload budget per session**: **2GB**

#### 3.3 Backend (APIs + Storage)
**Goal:** local temporary storage now, structured for future cloud storage.

**Endpoints (proposed):**
- `POST /api/uploads/sessions` → create an upload session
- `POST /api/uploads/sessions/:sessionId/videos` → upload one or multiple video clips (multipart)
- `POST /api/uploads/sessions/:sessionId/audio` → upload the audio track (multipart)
- `GET /api/uploads/sessions/:sessionId` → session metadata + uploaded files
- `DELETE /api/uploads/sessions/:sessionId/files/:fileId` → delete an uploaded file
- `POST /api/uploads/sessions/:sessionId/process` → placeholder “Process Now” trigger (returns 202 + message; no AI)

**Storage layout (local):**
- `/backend/uploads/sessions/{sessionId}/videos/*`
- `/backend/uploads/sessions/{sessionId}/audio/*`
- `/backend/uploads/sessions/{sessionId}/thumbnails/*` (reserved for future FFmpeg thumbnail generation)

**Modular architecture for future:**
- `storage/StorageProvider` interface
  - `LocalStorageProvider` (MVP)
  - `S3StorageProvider` / `R2StorageProvider` (future)
- `services/uploadSessionService` (create session, limits enforcement, metadata)
- `services/fileValidationService` (mime/type/size validation)
- `services/processService` stub (future AI pipeline trigger)
- Centralized error handling + consistent JSON error format.

**Data model (MongoDB):**
- UploadSession
  - id, createdAt, status (`draft|uploaded|processing|failed`)
  - videos: [{fileId, originalName, mimeType, sizeBytes, storageKey, createdAt}]
  - audio: {fileId, originalName, mimeType, sizeBytes, storageKey, createdAt} | null
  - totals: totalBytes

#### 3.4 Frontend (Upload UI)
**Add new route/page** (without changing existing landing page):
- `/upload` (or `/create`) for upload workflow

**Components (reusable):**
- `UploadDropzone` (drag & drop + click to browse)
- `UploadFileCard` (file info, remove, status)
- `UploadProgressBar` (per-file + overall)
- `VideoThumbnail` (client-side preview via `URL.createObjectURL`)
- `UploadErrors` (validation + server errors)

**UX:**
- Separate zones:
  - “Upload video clips” (multi)
  - “Upload music” (single)
- Show:
  - file list with sizes and progress
  - thumbnails grid for videos
  - audio file chip/card
- Disable “Process Now” until:
  - ≥1 uploaded video
  - exactly 1 uploaded audio
  - all uploads complete with success

#### 3.5 Testing Plan (Phase 3)
- Frontend:
  - Drag/drop & browse upload
  - Validation cases (wrong type, too large, >20 videos, missing audio)
  - Remove file interactions
  - Progress bar UI behavior
  - Responsive checks (mobile/desktop)
- Backend:
  - Multipart upload success/failure
  - Limit enforcement (500MB/50MB/2GB)
  - Session read/delete
  - Error format consistency

#### 3.6 Deliverables
- Working upload flow end-to-end (frontend + backend)
- Local file storage and session metadata persisted
- “Process Now” button triggers placeholder endpoint and returns a clear response
- Code structured for future FFmpeg thumbnail generation and AI processing pipeline.

---

### Phase 4: Optional Enhancements (only if requested)
**User stories**
1. Pricing section
2. Comparison table vs competitors
3. Waitlist/email capture
4. FAQ
5. Ready path to add AI/FFmpeg pipeline

**Add-ons**
- Pricing + FAQ sections
- Waitlist modal (frontend-only placeholder)
- Add FFmpeg thumbnail generation on upload completion
- Cloud storage adapter (S3/R2)

---

## 3. Next Actions
1. Implement Phase 3 backend session + upload endpoints with local storage provider.
2. Add frontend `/upload` page with cyberpunk drag-and-drop UI and progress tracking.
3. Wire up delete/remove for uploaded assets.
4. Add placeholder “Process Now” endpoint + UI state.
5. Run one full E2E test pass (upload + remove + responsive).

---

## 4. Success Criteria
- ✅ Landing page remains unchanged in look/feel.
- Upload workflow supports:
  - 1–20 video clips, 1 audio file
  - correct format + size validation
  - progress UI + ability to remove files
  - responsive layout
- Backend provides robust upload APIs with consistent errors.
- Upload storage is local but modular for future S3/R2.
- Architecture clearly prepares for future FFmpeg thumbnail generation and AI editing pipeline (not implemented in this phase).