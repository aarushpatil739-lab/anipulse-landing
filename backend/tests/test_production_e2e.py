"""
Production E2E test for AniPulse render pipeline.

Runs the complete flow against the live Railway backend:
  1. Create upload session
  2. Upload 3 test video clips
  3. Upload a test audio track
  4. POST /api/generate
  5. Poll /api/generate/{job_id}/status until completed/failed
  6. GET /api/generate/{job_id}/download and save the MP4
  7. ffprobe the downloaded MP4 to confirm it's a valid video
"""

import json
import sys
import time
import subprocess
from pathlib import Path

import requests

BASE_URL = "https://anipulse-landing-production.up.railway.app/api"
TEST_MEDIA = Path("/app/backend/test_media")
DOWNLOAD_DIR = Path("/tmp/anipulse_prod_test")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def log(stage: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{stage}] {msg}", flush=True)


def fail(msg: str) -> None:
    log("FAIL", msg)
    sys.exit(1)


def main() -> int:
    log("setup", f"BASE_URL = {BASE_URL}")

    # 0. Health check ------------------------------------------------------
    r = requests.get(f"{BASE_URL}/health/ffmpeg", timeout=30)
    if r.status_code != 200:
        fail(f"/api/health/ffmpeg -> HTTP {r.status_code}")
    h = r.json()
    if not h.get("available"):
        fail(f"ffmpeg not available in production: {h}")
    log("health", f"ffmpeg={h['ffmpeg']['path']} | ffprobe={h['ffprobe']['path']}")

    # 1. Session -----------------------------------------------------------
    r = requests.post(f"{BASE_URL}/upload/sessions", timeout=30)
    if r.status_code != 200:
        fail(f"create session: HTTP {r.status_code} {r.text[:200]}")
    sid = r.json()["session"]["session_id"]
    log("session", f"created {sid}")

    # 2. Upload videos -----------------------------------------------------
    videos = [TEST_MEDIA / f"test_clip{i}.mp4" for i in (1, 2, 3)]
    for v in videos:
        if not v.exists():
            fail(f"missing test media: {v}")
        with v.open("rb") as fh:
            r = requests.post(
                f"{BASE_URL}/upload/sessions/{sid}/videos",
                files={"file": (v.name, fh, "video/mp4")},
                timeout=120,
            )
        if r.status_code != 200:
            fail(f"upload {v.name}: HTTP {r.status_code} {r.text[:200]}")
        log("upload", f"video ok: {v.name} ({v.stat().st_size} bytes)")

    # 3. Upload audio ------------------------------------------------------
    audio = TEST_MEDIA / "test_music_beats.mp3"
    if not audio.exists():
        fail(f"missing audio: {audio}")
    with audio.open("rb") as fh:
        r = requests.post(
            f"{BASE_URL}/upload/sessions/{sid}/audio",
            files={"file": (audio.name, fh, "audio/mpeg")},
            timeout=120,
        )
    if r.status_code != 200:
        fail(f"upload audio: HTTP {r.status_code} {r.text[:200]}")
    log("upload", f"audio ok: {audio.name} ({audio.stat().st_size} bytes)")

    # 4. Start generation --------------------------------------------------
    r = requests.post(
        f"{BASE_URL}/generate",
        json={"session_id": sid, "style": "amv_default", "max_duration": 60.0},
        timeout=30,
    )
    if r.status_code != 200:
        fail(f"start generation: HTTP {r.status_code} {r.text[:400]}")
    job = r.json()
    job_id = job["job_id"]
    log("generate", f"job {job_id} status={job.get('status')}")

    # 5. Poll status -------------------------------------------------------
    deadline = time.time() + 360  # 6 min cap
    last_stage = None
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/generate/{job_id}/status", timeout=30)
        if r.status_code != 200:
            log("poll", f"status HTTP {r.status_code} {r.text[:200]}")
            time.sleep(3)
            continue
        st = r.json()
        cs = st.get("current_stage")
        if cs != last_stage:
            log("poll", f"[{st['progress_pct']:.0f}%] {st['status']}: {cs}")
            last_stage = cs
        if st["status"] == "completed":
            log("poll", "job COMPLETED")
            break
        if st["status"] == "failed":
            fail(f"job FAILED: {st.get('error_message')}")
        time.sleep(3)
    else:
        fail("timed out waiting for completion")

    # 6. Download MP4 ------------------------------------------------------
    r = requests.get(f"{BASE_URL}/generate/{job_id}/download", timeout=120, stream=True)
    if r.status_code != 200:
        fail(f"download HTTP {r.status_code}")
    out = DOWNLOAD_DIR / f"anipulse_{job_id}.mp4"
    total = 0
    with out.open("wb") as fh:
        for chunk in r.iter_content(chunk_size=65536):
            fh.write(chunk)
            total += len(chunk)
    log("download", f"saved {out} ({total} bytes)")

    # 7. Probe MP4 ---------------------------------------------------------
    ff = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size,bit_rate:stream=codec_type,codec_name,width,height",
            "-of",
            "json",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if ff.returncode != 0:
        fail(f"ffprobe failed: {ff.stderr[:400]}")
    info = json.loads(ff.stdout)
    log("probe", json.dumps(info, indent=2))

    has_video = any(s.get("codec_type") == "video" for s in info.get("streams", []))
    has_audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    if not (has_video and has_audio):
        fail(f"downloaded MP4 missing streams (video={has_video}, audio={has_audio})")

    log("DONE", f"E2E pipeline OK -- {out} contains valid video+audio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
