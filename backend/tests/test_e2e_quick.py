"""
Quick End-to-End Generation Test with Real Beat Music

Simplified test focusing on core workflow validation.
"""

import requests
import time
import json
from pathlib import Path

BASE_URL = "http://localhost:8001/api"
TEST_MEDIA = Path("/app/backend/test_media")

def test_e2e_generation():
    """Test complete generation with real audio"""
    print("="*60)
    print("AniPulse E2E Generation Test")
    print("="*60)
    
    # Use existing test media
    videos = [
        TEST_MEDIA / "test_clip1.mp4",
        TEST_MEDIA / "test_clip2.mp4",
        TEST_MEDIA / "test_clip3.mp4"
    ]
    audio = TEST_MEDIA / "test_music_beats.mp3"
    
    # Verify files exist
    for v in videos:
        if not v.exists():
            print(f"✗ Video not found: {v}")
            return False
    if not audio.exists():
        print(f"✗ Audio not found: {audio}")
        return False
    
    print(f"✓ Test files ready: {len(videos)} videos + audio")
    
    # Create session
    print("\n1. Creating upload session...")
    response = requests.post(f"{BASE_URL}/upload/sessions")
    response.raise_for_status()
    session_id = response.json()['session']['session_id']
    print(f"✓ Session: {session_id}")
    
    # Upload videos
    print("\n2. Uploading videos...")
    for video in videos:
        with open(video, 'rb') as f:
            files = {'file': (video.name, f, 'video/mp4')}
            response = requests.post(f"{BASE_URL}/upload/sessions/{session_id}/videos", files=files)
            response.raise_for_status()
        print(f"✓ Uploaded: {video.name}")
    
    # Upload audio
    print("\n3. Uploading audio...")
    with open(audio, 'rb') as f:
        files = {'file': (audio.name, f, 'audio/mpeg')}
        response = requests.post(f"{BASE_URL}/upload/sessions/{session_id}/audio", files=files)
        response.raise_for_status()
    print(f"✓ Uploaded: {audio.name}")
    
    # Start generation
    print("\n4. Starting generation...")
    response = requests.post(
        f"{BASE_URL}/generate",
        json={"session_id": session_id, "style": "amv_default", "max_duration": 20.0}
    )
    response.raise_for_status()
    job_id = response.json()['job_id']
    print(f"✓ Job started: {job_id}")
    
    # Poll status
    print("\n5. Monitoring progress...")
    start_time = time.time()
    last_progress = -1
    
    while time.time() - start_time < 180:  # 3 min timeout
        response = requests.get(f"{BASE_URL}/generate/{job_id}/status")
        response.raise_for_status()
        data = response.json()
        
        status = data['status']
        progress = data['progress_pct']
        stage = data['current_stage']
        
        # Print progress updates
        if int(progress) != int(last_progress):
            print(f"  [{progress:.0f}%] {status}: {stage}")
            last_progress = progress
        
        if status == 'completed':
            elapsed = time.time() - start_time
            print(f"\n✓ Generation completed in {elapsed:.1f}s")
            
            # Download result
            print("\n6. Downloading result...")
            response = requests.get(f"{BASE_URL}/generate/{job_id}/download", stream=True)
            response.raise_for_status()
            
            output_path = TEST_MEDIA / f"generated_{job_id[:8]}.mp4"
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = output_path.stat().st_size / (1024*1024)
            print(f"✓ Downloaded: {output_path.name} ({file_size:.2f}MB)")
            
            # Validate with ffprobe
            import subprocess
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(output_path)]
            result = subprocess.run(cmd, capture_output=True, check=True)
            probe_data = json.loads(result.stdout)
            duration = float(probe_data['format']['duration'])
            
            print(f"✓ Output validated: {duration:.2f}s duration")
            print("\n" + "="*60)
            print("SUCCESS: Full E2E test passed!")
            print("="*60)
            return True
        
        elif status == 'failed':
            error = data.get('error_message', 'Unknown error')
            print(f"\n✗ Generation failed: {error}")
            return False
        
        time.sleep(2)
    
    print("\n✗ Timeout")
    return False

if __name__ == "__main__":
    try:
        success = test_e2e_generation()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
