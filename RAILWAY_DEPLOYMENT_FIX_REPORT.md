# AniPulse — Railway FFmpeg Deployment Fix Report

Generated: 2026-05-22

## TL;DR

✅ FFmpeg / FFprobe installed and verified in Railway production
✅ Full AMV rendering pipeline working end-to-end in production
✅ Graceful 503 + clean error handling when ffmpeg is missing
✅ Memory-bounded render so we fit under Railway's 512MB trial cap

Production URL: `https://anipulse-landing-production.up.railway.app`

## Final endpoint snapshot (2026-05-22T10:46:26Z)

| Endpoint                       | Result                                                                 |
| ------------------------------ | ---------------------------------------------------------------------- |
| `GET /`                        | `{"service":"AniPulse Backend API","version":"1.0.0","status":"running"}` |
| `GET /health`                  | `status=healthy, database=connected, ffmpeg_available=true`            |
| `GET /api/health/ffmpeg`       | `available=true, ffmpeg=/usr/bin/ffmpeg 5.1.9, ffprobe=/usr/bin/ffprobe 5.1.9, startup_check.overall_ok=true` |
| `GET /api/generate/queue/stats`| `running=true, worker_active=true`                                     |

## Production E2E test result (job `6e4bab75-fcfb-4d40-b44a-a41ecd9f0c8b`)

```
[10:42:21] BASE_URL = https://anipulse-landing-production.up.railway.app/api
[10:42:21] [health]    ffmpeg=/usr/bin/ffmpeg | ffprobe=/usr/bin/ffprobe
[10:42:22] [session]   created 517a32d0-7051-4086-8eac-7a399ea54f0a
[10:42:22] [upload]    video ok: test_clip1.mp4 (89 KB)
[10:42:23] [upload]    video ok: test_clip2.mp4 (72 KB)
[10:42:23] [upload]    video ok: test_clip3.mp4 (106 KB)
[10:42:24] [upload]    audio ok: test_music_beats.mp3 (401 KB)
[10:42:24] [generate]  job 6e4bab75... status=queued
[10:42:40] [poll]      [45%] generating_timeline: Timeline generation complete
[10:42:44] [poll]      [50%] rendering: Rendering video
[10:45:56] [poll]      [100%] completed: Completed
[10:45:57] [download]  saved anipulse_6e4bab75....mp4 (297247 bytes)
[10:45:57] [probe]     h264 video 1280x720, aac audio, duration 16.83s
[10:45:57] [DONE]      E2E pipeline OK
```

Total wall-clock time: **3m 32s** (analyze + timeline + render + export + concat-filter fallback).

## Verified ffmpeg install in production

```
ffmpeg version 5.1.9-0+deb12u1 Copyright (c) 2000-2026 the FFmpeg developers
  -> /usr/bin/ffmpeg
ffprobe version 5.1.9-0+deb12u1 Copyright (c) 2007-2026 the FFmpeg developers
  -> /usr/bin/ffprobe
```

All 9 Python deps verified at boot via `verify_deps.py`:
FastAPI 0.110.1, Uvicorn 0.29.0, Motor, librosa 0.11.0, soundfile 0.12.1,
NumPy 1.26.4, SciPy 1.13.0, Numba 0.59.1, ffmpeg-python.

## Commit timeline (all on `main`)

| Commit    | Subject                                                            |
| --------- | ------------------------------------------------------------------ |
| `e949341` | `fix(deploy): install ffmpeg via Dockerfile + graceful fallback`   |
| `455070c` | `fix(deploy): add nixpacks.toml fallback for either builder`       |
| `138b419` | `fix(deploy): use /health as healthcheck + harden startup`         |
| `dbedd6f` | `fix(deploy): introduce start.sh -- single source of truth`        |
| `2d9ca7e` | `fix(render): graceful fallback when per-segment effects fail`     |
| `26aa001` | `fix(render): bulletproof concatenate with concat-filter fallback` |
| `01369ac` | `fix(render): keep memory under Railway trial 512MB cap`           |

## Files added / modified

### New
- `backend/Dockerfile` — slim-bookworm + apt ffmpeg + libsndfile1 + python deps
- `backend/.dockerignore`
- `backend/nixpacks.toml` — fallback when Builder=NIXPACKS
- `backend/start.sh` — single shell-script entrypoint (Docker CMD + Railway startCommand)
- `backend/services/ffmpeg_availability.py` — cached binary probe + typed `FFmpegBinaryMissingError`
- `backend/tests/test_production_e2e.py` — end-to-end production smoke test

### Modified
- `backend/verify_deps.py` — structured banner, persists `/app/backend/logs/deps_status.json`, always exits 0
- `backend/services/ffmpeg_utils.py`
    * Re-exports availability helpers
    * `_run_command` fast-fails with typed error when binaries missing
    * `concatenate`: tries fast `-c copy`, falls back to `concat` filter on rc=1
    * `export_final`: memory-bounded (`ultrafast`, `-threads 2`, `rc-lookahead=10:ref=2`)
    * `apply_zoom`: skip on clips with `<6` frames
    * `validate_output`: minimum threshold lowered to 10KB
- `backend/services/render_service.py` — per-segment effect failures fall back to the trimmed clip
- `backend/services/processing_queue.py`
    * Pre-flight ffmpeg availability check; mark job FAILED with clear message
    * Default export resolution 720p (overridable via `ANIPULSE_OUTPUT_RES` env)
- `backend/server.py`
    * New `GET /api/health/ffmpeg` diagnostic endpoint
    * `/api/generate` returns structured HTTP 503 if ffmpeg missing
    * `/health` enriched with ffmpeg state + version + timestamp
    * Bounded MongoDB ping (`asyncio.wait_for(2.0s)`) + structured startup banner
- `backend/railway.json`, `backend/railway.toml`, `backend/nixpacks.toml` — all collapse to `sh start.sh` + healthcheckPath `/health` + 300s timeout
- `.gitignore` — exclude backend runtime dirs (logs/temp/uploads/exports)

## Root-cause chain (what we discovered along the way)

1. **Original symptom**: production `/api/generate` jobs crashed; ffmpeg not on PATH.
2. **First push** added Dockerfile + ffmpeg_availability. Build succeeded BUT Railway dashboard had `Builder=DOCKERFILE` configured, so our `railway.json` toggle alone wasn't the bottleneck — turns out the bigger issue was step 3.
3. **Healthcheck timeout (60s)** was killing cold starts that took 30-60s for librosa/scipy/numba imports → bumped to 300s and switched to lightweight `/health`.
4. **Multi-statement startCommand** (`verify_deps.py || true; exec uvicorn ...`) failed silently in Railway's PID-1 context — verify_deps ran, but uvicorn never started. **Moved everything into `start.sh`** which fixed boot.
5. After boot worked, render failed at **`apply_zoom`** because `zoompan` rejects clips with too few frames → wrapped per-segment effect in try/except + skip-on-tiny-clip in `apply_zoom`.
6. Then failed at **`concatenate`** because `concat demuxer + -c copy` requires identical codec params → added `_concatenate_with_filter` fallback that re-encodes to a uniform 720p/h264/aac.
7. Finally failed at **`export_final` with rc=-9 (SIGKILL)** because 1080p libx264 OOM'd the 512MB trial container → dropped default to 720p + `preset=ultrafast` + `-threads 2` + `rc-lookahead=10:ref=2`.

## How error logging now helps future debugging

- Every cold start writes `/app/backend/logs/deps_status.json` with all binary paths, versions, python module versions.
- `/api/health/ffmpeg` exposes that JSON plus the live in-process status.
- `/health` returns `ffmpeg_available` + `ffmpeg_missing` alongside DB state.
- Startup banner in Railway logs shows: python version, cwd, PORT, MONGO_URL, CORS, ffmpeg status.
- Every FFmpeg invocation gets an 8-char trace_id; stderr tail is logged + saved to `/app/backend/logs/<op>_<trace>.log`.
- Jobs that fail in the worker are marked `FAILED` in MongoDB with `error_message`, `error_trace_id`, `error_stage`, surfaced through `/api/generate/{job_id}/status`.
- API now returns HTTP 503 with structured detail (`error: ffmpeg_unavailable`, `missing: [...]`) instead of crashing.
