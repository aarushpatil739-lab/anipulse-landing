"""
Comprehensive FFmpeg Utilities Test Suite

Tests all core FFmpeg operations with synthetic media to ensure:
- All functions produce valid, playable outputs
- Output integrity is validated
- Performance metrics are collected
- Cleanup works correctly
- Async compatibility is maintained
"""

import asyncio
import json
import sys
import os
from pathlib import Path
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ffmpeg_utils import FFmpegUtils, FFmpegError, IntegrityCheckResult


class TestMediaGenerator:
    """Generate synthetic test media using FFmpeg"""
    
    def __init__(self, output_dir: str = "/app/backend/test_media"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def generate_test_video(self, name: str, duration: float = 3.0, 
                                 color: str = "blue", size: str = "1280x720",
                                 fps: int = 30, with_audio: bool = True) -> str:
        """
        Generate a test video with colored background and optional tone audio
        
        Args:
            name: Output filename (without extension)
            duration: Duration in seconds
            color: Background color
            size: Video resolution (WxH)
            fps: Frame rate
            with_audio: Include audio tone
            
        Returns:
            Path to generated video file
        """
        output_path = str(self.output_dir / f"{name}.mp4")
        
        # Build FFmpeg command for test pattern
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'color=c={color}:s={size}:d={duration}:r={fps}',
        ]
        
        # Add audio if requested
        if with_audio:
            cmd.extend([
                '-f', 'lavfi',
                '-i', f'sine=frequency=440:duration={duration}'
            ])
        
        # Output settings
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p'
        ])
        
        if with_audio:
            cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
        
        cmd.extend(['-y', output_path])
        
        # Run command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Failed to generate test video: {name}")
        
        print(f"✓ Generated test video: {name}.mp4 ({duration}s, {color})")
        return output_path
    
    async def generate_test_audio(self, name: str, duration: float = 5.0,
                                 frequency: int = 440) -> str:
        """
        Generate test audio file (sine wave tone)
        
        Args:
            name: Output filename (without extension)
            duration: Duration in seconds
            frequency: Tone frequency in Hz
            
        Returns:
            Path to generated audio file
        """
        output_path = str(self.output_dir / f"{name}.mp3")
        
        cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', f'sine=frequency={frequency}:duration={duration}',
            '-c:a', 'libmp3lame',
            '-b:a', '192k',
            '-y',
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Failed to generate test audio: {name}")
        
        print(f"✓ Generated test audio: {name}.mp3 ({duration}s, {frequency}Hz)")
        return output_path
    
    def cleanup(self):
        """Remove all generated test media"""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
            print(f"✓ Cleaned up test media directory: {self.output_dir}")


class FFmpegTestSuite:
    """Comprehensive test suite for FFmpeg utilities"""
    
    def __init__(self):
        self.ffmpeg = FFmpegUtils()
        self.media_gen = TestMediaGenerator()
        self.test_results = []
        self.cleanup_paths = []
        
    def record_result(self, test_name: str, passed: bool, message: str = "", 
                     metrics: dict = None, integrity: IntegrityCheckResult = None):
        """Record test result"""
        result = {
            "test": test_name,
            "passed": passed,
            "message": message,
            "metrics": metrics,
            "integrity": integrity.__dict__ if integrity else None
        }
        self.test_results.append(result)
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"  → {message}")
        if metrics:
            print(f"  → Took {metrics.get('elapsed_ms', 0):.0f}ms")
    
    async def test_probe(self, video_path: str):
        """Test: Probe video metadata"""
        try:
            metadata = await self.ffmpeg.probe(video_path)
            
            # Validate metadata structure
            required_keys = ['duration', 'width', 'height', 'fps', 'has_video']
            missing = [k for k in required_keys if k not in metadata]
            
            if missing:
                self.record_result("probe", False, f"Missing keys: {missing}")
                return
            
            # Validate values are sensible
            if metadata['duration'] <= 0:
                self.record_result("probe", False, f"Invalid duration: {metadata['duration']}")
                return
            
            if not metadata['has_video']:
                self.record_result("probe", False, "Video stream not detected")
                return
            
            metrics = self.ffmpeg.get_last_metric()
            self.record_result(
                "probe",
                True,
                f"{metadata['width']}x{metadata['height']} @ {metadata['fps']:.1f}fps, {metadata['duration']:.2f}s",
                metrics
            )
            
        except Exception as e:
            self.record_result("probe", False, f"Exception: {str(e)}")
    
    async def test_trim(self, video_path: str):
        """Test: Trim video clip"""
        try:
            # Probe first to get duration
            metadata = await self.ffmpeg.probe(video_path)
            duration = metadata['duration']
            
            # Trim middle second
            start = duration / 3
            end = (duration / 3) * 2
            
            output = await self.ffmpeg.trim(video_path, start, end)
            self.cleanup_paths.append(output)
            
            # Validate output
            integrity = await self.ffmpeg.validate_output(
                output,
                require_video=True,
                min_duration=0.5
            )
            
            if not integrity.valid:
                self.record_result("trim", False, f"Integrity failed: {integrity.errors}")
                return
            
            # Check duration is approximately correct (within 10% tolerance)
            expected_duration = end - start
            actual_duration = integrity.duration
            tolerance = expected_duration * 0.1
            
            if abs(actual_duration - expected_duration) > tolerance:
                self.record_result(
                    "trim",
                    False,
                    f"Duration mismatch: expected {expected_duration:.2f}s, got {actual_duration:.2f}s"
                )
                return
            
            metrics = self.ffmpeg.get_last_metric()
            self.record_result(
                "trim",
                True,
                f"Trimmed {start:.2f}s to {end:.2f}s → {actual_duration:.2f}s output",
                metrics,
                integrity
            )
            
        except Exception as e:
            self.record_result("trim", False, f"Exception: {str(e)}")
    
    async def test_concatenate(self, video_paths: list):
        """Test: Concatenate multiple video clips"""
        try:
            if len(video_paths) < 2:
                self.record_result("concatenate", False, "Need at least 2 videos")
                return
            
            # Get durations
            durations = []
            for vp in video_paths:
                meta = await self.ffmpeg.probe(vp)
                durations.append(meta['duration'])
            
            expected_duration = sum(durations)
            
            output = await self.ffmpeg.concatenate(video_paths)
            self.cleanup_paths.append(output)
            
            # Validate output
            integrity = await self.ffmpeg.validate_output(
                output,
                require_video=True,
                min_duration=expected_duration * 0.8
            )
            
            if not integrity.valid:
                self.record_result("concatenate", False, f"Integrity failed: {integrity.errors}")
                return
            
            # Check duration is approximately correct (within 10% tolerance)
            actual_duration = integrity.duration
            tolerance = expected_duration * 0.1
            
            if abs(actual_duration - expected_duration) > tolerance:
                self.record_result(
                    "concatenate",
                    False,
                    f"Duration mismatch: expected {expected_duration:.2f}s, got {actual_duration:.2f}s"
                )
                return
            
            metrics = self.ffmpeg.get_last_metric()
            self.record_result(
                "concatenate",
                True,
                f"Concatenated {len(video_paths)} clips → {actual_duration:.2f}s output",
                metrics,
                integrity
            )
            
        except Exception as e:
            self.record_result("concatenate", False, f"Exception: {str(e)}")
    
    async def test_extract_audio(self, video_path: str):
        """Test: Extract audio from video"""
        try:
            # Check if video has audio
            metadata = await self.ffmpeg.probe(video_path)
            if not metadata['has_audio']:
                self.record_result("extract_audio", False, "Test video has no audio")
                return
            
            output = await self.ffmpeg.extract_audio(video_path)
            self.cleanup_paths.append(output)
            
            # Validate output (audio files don't have video stream)
            # Just check file exists and has reasonable size
            output_file = Path(output)
            if not output_file.exists():
                self.record_result("extract_audio", False, "Output file not created")
                return
            
            file_size = output_file.stat().st_size
            if file_size < 10_000:  # Min 10KB for valid audio
                self.record_result("extract_audio", False, f"Output too small: {file_size} bytes")
                return
            
            metrics = self.ffmpeg.get_last_metric()
            self.record_result(
                "extract_audio",
                True,
                f"Extracted audio: {file_size / 1024:.1f}KB",
                metrics
            )
            
        except Exception as e:
            self.record_result("extract_audio", False, f"Exception: {str(e)}")
    
    async def test_merge_audio(self, video_path: str, audio_path: str):
        """Test: Merge audio with video"""
        try:
            output = await self.ffmpeg.merge_audio(video_path, audio_path)
            self.cleanup_paths.append(output)
            
            # Validate output
            integrity = await self.ffmpeg.validate_output(
                output,
                require_video=True,
                require_audio=True,
                min_duration=1.0
            )
            
            if not integrity.valid:
                self.record_result("merge_audio", False, f"Integrity failed: {integrity.errors}")
                return
            
            metrics = self.ffmpeg.get_last_metric()
            self.record_result(
                "merge_audio",
                True,
                f"Merged video + audio → {integrity.duration:.2f}s",
                metrics,
                integrity
            )
            
        except Exception as e:
            self.record_result("merge_audio", False, f"Exception: {str(e)}")
    
    async def test_transition(self, clip1_path: str, clip2_path: str, transition_type: str):
        """Test: Apply transition between clips"""
        try:
            output = await self.ffmpeg.apply_transition(
                clip1_path,
                clip2_path,
                transition_type,
                duration=0.5
            )
            self.cleanup_paths.append(output)
            
            # Validate output
            integrity = await self.ffmpeg.validate_output(
                output,
                require_video=True,
                min_duration=2.0
            )
            
            if not integrity.valid:
                self.record_result(f"transition_{transition_type}", False, f"Integrity failed: {integrity.errors}")
                return
            
            metrics = self.ffmpeg.get_last_metric()
            self.record_result(
                f"transition_{transition_type}",
                True,
                f"Applied {transition_type} transition → {integrity.duration:.2f}s",
                metrics,
                integrity
            )
            
        except Exception as e:
            self.record_result(f"transition_{transition_type}", False, f"Exception: {str(e)}")
    
    async def test_effect_zoom(self, video_path: str):
        """Test: Apply zoom effect"""
        try:
            output = await self.ffmpeg.apply_zoom(video_path, zoom_factor=1.3)
            self.cleanup_paths.append(output)
            
            # Validate output
            integrity = await self.ffmpeg.validate_output(
                output,
                require_video=True,
                min_duration=1.0
            )
            
            if not integrity.valid:
                self.record_result("effect_zoom", False, f"Integrity failed: {integrity.errors}")
                return
            
            metrics = self.ffmpeg.get_last_metric()
            self.record_result(
                "effect_zoom",
                True,
                f"Applied zoom effect → {integrity.duration:.2f}s",
                metrics,
                integrity
            )
            
        except Exception as e:
            self.record_result("effect_zoom", False, f"Exception: {str(e)}")
    
    async def test_effect_shake(self, video_path: str):
        """Test: Apply shake effect"""
        try:
            output = await self.ffmpeg.apply_shake(video_path, intensity=15.0)
            self.cleanup_paths.append(output)
            
            # Validate output
            integrity = await self.ffmpeg.validate_output(
                output,
                require_video=True,
                min_duration=1.0
            )
            
            if not integrity.valid:
                self.record_result("effect_shake", False, f"Integrity failed: {integrity.errors}")
                return
            
            metrics = self.ffmpeg.get_last_metric()
            self.record_result(
                "effect_shake",
                True,
                f"Applied shake effect → {integrity.duration:.2f}s",
                metrics,
                integrity
            )
            
        except Exception as e:
            self.record_result("effect_shake", False, f"Exception: {str(e)}")
    
    async def test_effect_speed_ramp(self, video_path: str):
        """Test: Apply speed ramp effect"""
        try:
            output = await self.ffmpeg.apply_speed_ramp(video_path, speed_factor=2.0)
            self.cleanup_paths.append(output)
            
            # Validate output
            integrity = await self.ffmpeg.validate_output(
                output,
                require_video=True,
                min_duration=0.5
            )
            
            if not integrity.valid:
                self.record_result("effect_speed_ramp", False, f"Integrity failed: {integrity.errors}")
                return
            
            metrics = self.ffmpeg.get_last_metric()
            self.record_result(
                "effect_speed_ramp",
                True,
                f"Applied speed ramp (2x) → {integrity.duration:.2f}s",
                metrics,
                integrity
            )
            
        except Exception as e:
            self.record_result("effect_speed_ramp", False, f"Exception: {str(e)}")
    
    async def test_export_final(self, video_path: str):
        """Test: Export final video with optimization"""
        try:
            output = str(Path("/app/backend/temp") / "export_test_final.mp4")
            result = await self.ffmpeg.export_final(
                video_path,
                output,
                resolution="1080p",
                fps=30,
                quality="balanced"
            )
            self.cleanup_paths.append(result)
            
            # Validate output
            integrity = await self.ffmpeg.validate_output(
                result,
                require_video=True,
                require_audio=True,
                min_duration=1.0
            )
            
            if not integrity.valid:
                self.record_result("export_final", False, f"Integrity failed: {integrity.errors}")
                return
            
            # Check output is optimized (has faststart)
            # This is done by ffprobe but not validated here
            
            metrics = self.ffmpeg.get_last_metric()
            self.record_result(
                "export_final",
                True,
                f"Exported 1080p @ 30fps → {integrity.file_size_bytes / (1024*1024):.2f}MB",
                metrics,
                integrity
            )
            
        except Exception as e:
            self.record_result("export_final", False, f"Exception: {str(e)}")
    
    def cleanup_test_outputs(self):
        """Clean up all test output files"""
        cleaned = 0
        for path in self.cleanup_paths:
            try:
                Path(path).unlink(missing_ok=True)
                cleaned += 1
            except Exception as e:
                print(f"Warning: Failed to cleanup {path}: {e}")
        
        print(f"✓ Cleaned up {cleaned}/{len(self.cleanup_paths)} test output files")
    
    def print_summary(self):
        """Print test summary"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['passed'])
        failed = total - passed
        
        print("\n" + "="*60)
        print("FFmpeg Utilities Test Summary")
        print("="*60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ({(passed/total*100) if total > 0 else 0:.1f}%)")
        print(f"Failed: {failed}")
        print("="*60)
        
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  ✗ {result['test']}: {result['message']}")
        
        return passed == total
    
    def save_report(self, filename: str = "/app/backend/tests/test_report.json"):
        """Save detailed test report to JSON"""
        report = {
            "total_tests": len(self.test_results),
            "passed": sum(1 for r in self.test_results if r['passed']),
            "failed": sum(1 for r in self.test_results if not r['passed']),
            "tests": self.test_results
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"✓ Test report saved to: {filename}")
        return report


async def run_full_test_suite():
    """Run the complete FFmpeg test suite"""
    print("="*60)
    print("FFmpeg Utilities Comprehensive Test Suite")
    print("="*60)
    print()
    
    suite = FFmpegTestSuite()
    
    # Step 1: Generate test media
    print("Step 1: Generating synthetic test media...")
    print("-" * 60)
    
    video1 = await suite.media_gen.generate_test_video("test_video_blue", duration=3.0, color="blue")
    video2 = await suite.media_gen.generate_test_video("test_video_red", duration=2.5, color="red")
    video3 = await suite.media_gen.generate_test_video("test_video_green", duration=2.0, color="green")
    audio1 = await suite.media_gen.generate_test_audio("test_audio_440", duration=5.0, frequency=440)
    
    print()
    
    # Step 2: Run tests
    print("Step 2: Running FFmpeg operations tests...")
    print("-" * 60)
    
    await suite.test_probe(video1)
    await suite.test_trim(video1)
    await suite.test_concatenate([video1, video2, video3])
    await suite.test_extract_audio(video1)
    await suite.test_merge_audio(video2, audio1)
    await suite.test_transition(video1, video2, "fade")
    await suite.test_transition(video1, video2, "flash")
    await suite.test_effect_zoom(video1)
    await suite.test_effect_shake(video2)
    await suite.test_effect_speed_ramp(video3)
    await suite.test_export_final(video1)
    
    print()
    
    # Step 3: Cleanup
    print("Step 3: Cleanup...")
    print("-" * 60)
    suite.cleanup_test_outputs()
    suite.media_gen.cleanup()
    
    print()
    
    # Step 4: Summary and report
    success = suite.print_summary()
    suite.save_report()
    
    return success


if __name__ == "__main__":
    success = asyncio.run(run_full_test_suite())
    sys.exit(0 if success else 1)
