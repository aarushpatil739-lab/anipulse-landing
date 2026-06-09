"""
Stability validation matrix - mirrors the user-specified critical cases.

CASE 1: 1 short clip + long audio + cinematic preset
CASE 2: 1 short clip + velocity preset
CASE 3: multiple clips + vertical export

Expected for ALL cases:
  * status -> completed (never SIGKILL / rc=-9)
  * downloadable MP4 exists
  * no infinite hang
  * footage_limited + safe_mode flags surface correctly when applicable
"""

import json
import sys
import time
from pathlib import Path

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001/api"
MEDIA = Path("/app/backend/test_media")
OUT = Path("/tmp/anipulse_stability")
OUT.mkdir(parents=True, exist_ok=True)


def log(*a):
    print("[%s]" % time.strftime("%H:%M:%S"), *a, flush=True)


def make_session(videos, audio_name):
    sid = requests.post(f"{BASE}/upload/sessions", timeout=30).json()["session"]["session_id"]
    for n in videos:
        with (MEDIA / n).open("rb") as f:
            r = requests.post(
                f"{BASE}/upload/sessions/{sid}/videos",
                files={"file": (n, f, "video/mp4")},
                timeout=120,
            )
        assert r.status_code == 200, f"upload {n}: {r.status_code} {r.text[:200]}"
    with (MEDIA / audio_name).open("rb") as f:
        r = requests.post(
            f"{BASE}/upload/sessions/{sid}/audio",
            files={"file": (audio_name, f, "audio/mpeg")},
            timeout=120,
        )
    assert r.status_code == 200, f"upload audio: {r.status_code}"
    return sid


def run_case(name, videos, audio, preset, aspect, vertical_mode):
    log(f"=== {name} ===")
    sid = make_session(videos, audio)
    log("session:", sid, "preset:", preset, "aspect:", aspect, "vm:", vertical_mode)

    payload = {
        "session_id": sid,
        "style": preset,
        "aspect_ratio": aspect,
        "vertical_mode": vertical_mode,
    }
    r = requests.post(f"{BASE}/generate", json=payload, timeout=30)
    assert r.status_code == 200, f"generate failed: {r.status_code} {r.text[:300]}"
    jid = r.json()["job_id"]
    log("job_id:", jid)

    last_stage = None
    flags_logged = False
    deadline = time.time() + 360
    while time.time() < deadline:
        s = requests.get(f"{BASE}/generate/{jid}/status", timeout=30).json()
        cs = s.get("current_stage")
        if cs != last_stage:
            log(f"  [{s.get('progress_pct',0):.0f}%] {s['status']}: {cs}")
            last_stage = cs
        if not flags_logged and "safe_mode" in s:
            log(
                f"  flags: safe_mode={s.get('safe_mode')} "
                f"reason={s.get('safe_mode_reason')!r}  "
                f"footage_limited={s.get('footage_limited')}  "
                f"warning={s.get('footage_warning')!r}"
            )
            flags_logged = True
        if s["status"] == "completed":
            r = requests.get(f"{BASE}/generate/{jid}/download", timeout=180)
            out = OUT / f"{name.replace(' ', '_').lower()}.mp4"
            out.write_bytes(r.content)
            log(f"  RESULT OK: {out.name} {len(r.content)} bytes "
                f"timeline_dur={s.get('timeline_duration')} segs={s.get('segment_count')}")
            return True, s
        if s["status"] == "failed":
            log("  RESULT FAIL:", s.get("error_message"))
            log("    raw_error:", s.get("raw_error"))
            return False, s
        time.sleep(3)
    log("  TIMEOUT")
    return False, s


cases = [
    # CASE 1: 1 short clip + long-ish music + cinematic
    ("CASE1 cinematic 1clip long-audio",
     ["test_clip1.mp4"], "test_music_beats.mp3", "cinematic", "16:9", "blurred"),
    # CASE 2: 1 short clip + velocity preset
    ("CASE2 velocity 1clip",
     ["test_clip1.mp4"], "test_music_beats.mp3", "velocity", "16:9", "blurred"),
    # CASE 3: multiple clips + 9:16 vertical
    ("CASE3 multi-clip vertical",
     ["test_clip1.mp4", "test_clip2.mp4", "test_clip3.mp4"],
     "test_music_beats.mp3", "cinematic", "9:16", "blurred"),
]

print("=" * 70)
print(" AniPulse Stability Matrix")
print("=" * 70)

results = []
for name, vids, aud, preset, aspect, vm in cases:
    try:
        ok, st = run_case(name, vids, aud, preset, aspect, vm)
    except Exception as exc:  # noqa: BLE001
        log("EXC:", exc)
        ok, st = False, {"error_message": str(exc)}
    results.append((name, ok, st))
    print()

print("=" * 70)
for name, ok, _ in results:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
print("=" * 70)

sys.exit(0 if all(r[1] for r in results) else 1)
