#!/usr/bin/env python3
"""
Startup verification script for Railway backend.
Verifies all dependencies are installed before starting the server.
"""

import sys
import subprocess

def check_dependency(module_name, display_name=None):
    """Check if a Python module can be imported"""
    if display_name is None:
        display_name = module_name
    
    try:
        __import__(module_name)
        print(f"✅ {display_name} imported successfully")
        return True
    except ImportError as e:
        print(f"❌ {display_name} import failed: {e}")
        return False

def check_system_command(cmd, name):
    """Check if a system command exists"""
    try:
        result = subprocess.run(
            [cmd, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ {name}: {version}")
            return True
        else:
            print(f"❌ {name} not found")
            return False
    except Exception as e:
        print(f"❌ {name} check failed: {e}")
        return False

def main():
    print("="*60)
    print("AniPulse Backend Startup Verification")
    print("="*60)
    print()
    
    all_ok = True
    
    # Check system dependencies
    print("System Dependencies:")
    print("-" * 60)
    ffmpeg_ok = check_system_command('ffmpeg', 'FFmpeg')
    ffprobe_ok = check_system_command('ffprobe', 'FFprobe')
    
    if not ffmpeg_ok:
        print("⚠️  FFmpeg not found - will be required for video processing")
    if not ffprobe_ok:
        print("⚠️  FFprobe not found - will be required for video analysis")
    print()
    
    # Check Python dependencies
    print("Python Dependencies:")
    print("-" * 60)
    all_ok &= check_dependency('fastapi', 'FastAPI')
    all_ok &= check_dependency('uvicorn', 'Uvicorn')
    all_ok &= check_dependency('motor', 'Motor (MongoDB)')
    all_ok &= check_dependency('librosa', 'librosa (Audio Analysis)')
    all_ok &= check_dependency('soundfile', 'soundfile (Audio I/O)')
    all_ok &= check_dependency('numpy', 'NumPy')
    all_ok &= check_dependency('scipy', 'SciPy')
    all_ok &= check_dependency('numba', 'Numba')
    all_ok &= check_dependency('ffmpeg', 'ffmpeg-python')
    print()
    
    # Check service imports
    print("Service Modules:")
    print("-" * 60)
    all_ok &= check_dependency('services.audio_analyzer', 'AudioAnalyzer')
    all_ok &= check_dependency('services.timeline_generator', 'TimelineGenerator')
    all_ok &= check_dependency('services.render_service', 'RenderService')
    all_ok &= check_dependency('services.processing_queue', 'ProcessingQueue')
    print()
    
    print("="*60)
    if all_ok:
        print("✅ All dependencies verified successfully!")
        print("="*60)
        sys.exit(0)
    else:
        print("❌ Some dependencies are missing!")
        print("="*60)
        sys.exit(1)

if __name__ == '__main__':
    main()
