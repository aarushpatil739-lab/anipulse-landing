"""
End-to-End Generation Pipeline Test

Tests the complete AMV generation flow:
1. Create upload session
2. Upload test video clips
3. Upload test audio
4. Start generation
5. Poll status until complete
6. Validate output
"""

import asyncio
import requests
import time
import json
import subprocess
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8001/api"
TEST_MEDIA_DIR = Path("/app/backend/test_media")
TEST_MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def generate_test_video(name: str, duration: float = 5.0, color: str = "blue"):
    """Generate a test video"""
    output_path = TEST_MEDIA_DIR / f"{name}.mp4"
    
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', f'color=c={color}:s=1280x720:d={duration}:r=30',
        '-f', 'lavfi',
        '-i', f'sine=frequency=440:duration={duration}',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-y',
        str(output_path)
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"✓ Generated: {name}.mp4 ({duration}s, {color})")
    return str(output_path)


def generate_test_audio(name: str, duration: float = 15.0):
    """Generate test audio"""
    output_path = TEST_MEDIA_DIR / f"{name}.mp3"
    
    cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', f'sine=frequency=440:duration={duration}',
        '-c:a', 'libmp3lame',
        '-b:a', '192k',
        '-y',
        str(output_path)
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"✓ Generated: {name}.mp3 ({duration}s)")
    return str(output_path)


def test_generation_pipeline():
    """Test complete generation pipeline"""
    print("=" * 60)
    print("AniPulse Generation Pipeline Test")
    print("=" * 60)
    print()
    
    # Step 1: Generate test media
    print("Step 1: Generating test media...")
    print("-" * 60)
    
    video1 = generate_test_video("test_clip1", duration=5.0, color="red")
    video2 = generate_test_video("test_clip2", duration=4.0, color="blue")
    video3 = generate_test_video("test_clip3", duration=6.0, color="green")
    audio = generate_test_audio("test_music", duration=15.0)
    
    print()
    
    # Step 2: Create upload session
    print("Step 2: Creating upload session...")
    print("-" * 60)
    
    response = requests.post(f"{BASE_URL}/upload/sessions")
    response.raise_for_status()
    session_data = response.json()
    session_id = session_data['session']['session_id']
    
    print(f"✓ Session created: {session_id}")
    print()
    
    # Step 3: Upload videos
    print("Step 3: Uploading videos...")
    print("-" * 60)
    
    for video_path in [video1, video2, video3]:
        with open(video_path, 'rb') as f:
            files = {'file': (Path(video_path).name, f, 'video/mp4')}
            response = requests.post(
                f"{BASE_URL}/upload/sessions/{session_id}/videos",
                files=files
            )
            response.raise_for_status()
            print(f"✓ Uploaded: {Path(video_path).name}")
    
    print()
    
    # Step 4: Upload audio
    print("Step 4: Uploading audio...")
    print("-" * 60)
    
    with open(audio, 'rb') as f:
        files = {'file': (Path(audio).name, f, 'audio/mpeg')}
        response = requests.post(
            f"{BASE_URL}/upload/sessions/{session_id}/audio",
            files=files
        )
        response.raise_for_status()
        print(f"✓ Uploaded: {Path(audio).name}")
    
    print()
    
    # Step 5: Start generation
    print("Step 5: Starting generation...")
    print("-" * 60)
    
    response = requests.post(
        f"{BASE_URL}/generate",
        json={
            "session_id": session_id,
            "style": "amv_default",
            "max_duration": 15.0
        }
    )
    response.raise_for_status()
    gen_data = response.json()
    job_id = gen_data['job_id']
    
    print(f"✓ Generation started: {job_id}")
    print()
    
    # Step 6: Poll status until complete
    print("Step 6: Monitoring progress...")
    print("-" * 60)
    
    max_wait = 300  # 5 minutes
    start_time = time.time()
    last_status = None
    
    while True:
        if time.time() - start_time > max_wait:
            print(f"✗ Timeout after {max_wait}s")
            return False
        
        response = requests.get(f"{BASE_URL}/generate/{job_id}/status")
        response.raise_for_status()
        status_data = response.json()
        
        status = status_data['status']
        progress = status_data['progress_pct']
        stage = status_data['current_stage']
        
        # Print status updates
        if status != last_status:
            print(f"[{progress:.1f}%] {status}: {stage}")
            last_status = status
        
        # Check completion
        if status == 'completed':
            print(f"✓ Generation completed in {time.time() - start_time:.1f}s")
            break
        
        if status == 'failed':
            error_msg = status_data.get('error_message', 'Unknown error')
            print(f"✗ Generation failed: {error_msg}")
            return False
        
        time.sleep(2)  # Poll every 2 seconds
    
    print()
    
    # Step 7: Get timeline
    print("Step 7: Retrieving timeline...")
    print("-" * 60)
    
    response = requests.get(f"{BASE_URL}/generate/{job_id}/timeline")
    response.raise_for_status()
    timeline_data = response.json()
    
    segments = len(timeline_data['timeline']['segments'])
    duration = timeline_data['timeline']['total_duration']
    transitions = timeline_data['timeline']['transition_count']
    effects = timeline_data['timeline']['effect_count']
    
    print(f"✓ Timeline retrieved:")
    print(f"  - Segments: {segments}")
    print(f"  - Duration: {duration:.2f}s")
    print(f"  - Transitions: {transitions}")
    print(f"  - Effects: {effects}")
    print()
    
    # Step 8: Check final video
    print("Step 8: Validating output...")
    print("-" * 60)
    
    response = requests.get(f"{BASE_URL}/generate/{job_id}/status")
    response.raise_for_status()
    status_data = response.json()
    
    if 'has_export' in status_data and status_data['has_export']:
        print("✓ Export file available")
        
        # Test download endpoint
        response = requests.get(f"{BASE_URL}/generate/{job_id}/download", stream=True)
        response.raise_for_status()
        
        # Save to test location
        output_path = TEST_MEDIA_DIR / f"generated_{job_id}.mp4"
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = output_path.stat().st_size
        print(f"✓ Downloaded: {output_path.name} ({file_size / (1024*1024):.2f}MB)")
        
        # Validate with ffprobe
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, check=True)
        probe_data = json.loads(result.stdout)
        output_duration = float(probe_data['format']['duration'])
        
        print(f"✓ Output validated: {output_duration:.2f}s duration")
    else:
        print("✗ Export not available")
        return False
    
    print()
    print("=" * 60)
    print("SUCCESS: Full pipeline test passed!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_generation_pipeline()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
