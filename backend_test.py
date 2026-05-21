import requests
import sys
import os
from pathlib import Path
import io

class UploadSystemTester:
    def __init__(self, base_url="https://cyber-edit.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, passed, message=""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED - {message}")
        self.test_results.append({
            "name": name,
            "passed": passed,
            "message": message
        })

    def test_create_session(self):
        """Test creating an upload session"""
        try:
            response = requests.post(f"{self.base_url}/upload/sessions")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "session" in data:
                    self.session_id = data["session"]["session_id"]
                    self.log_test("Create Upload Session", True)
                    return True
                else:
                    self.log_test("Create Upload Session", False, "Invalid response format")
            else:
                self.log_test("Create Upload Session", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Create Upload Session", False, str(e))
        return False

    def test_get_session(self):
        """Test getting session details"""
        if not self.session_id:
            self.log_test("Get Session Details", False, "No session ID")
            return False
        
        try:
            response = requests.get(f"{self.base_url}/upload/sessions/{self.session_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "session" in data:
                    session = data["session"]
                    if (session.get("session_id") == self.session_id and
                        session.get("status") == "draft" and
                        isinstance(session.get("videos"), list) and
                        session.get("audio") is None):
                        self.log_test("Get Session Details", True)
                        return True
                    else:
                        self.log_test("Get Session Details", False, "Invalid session data")
                else:
                    self.log_test("Get Session Details", False, "Invalid response format")
            else:
                self.log_test("Get Session Details", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Get Session Details", False, str(e))
        return False

    def test_upload_video(self):
        """Test uploading a video file"""
        if not self.session_id:
            self.log_test("Upload Video", False, "No session ID")
            return False
        
        try:
            # Create a small test video file (mock)
            # In real scenario, we'd use an actual video file
            test_file = io.BytesIO(b"fake video content for testing")
            test_file.name = "test_video.mp4"
            
            files = {'file': ('test_video.mp4', test_file, 'video/mp4')}
            response = requests.post(
                f"{self.base_url}/upload/sessions/{self.session_id}/videos",
                files=files
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "file" in data:
                    file_data = data["file"]
                    if (file_data.get("file_type") == "video" and
                        file_data.get("original_name") == "test_video.mp4"):
                        self.log_test("Upload Video", True)
                        return True
                    else:
                        self.log_test("Upload Video", False, "Invalid file data")
                else:
                    self.log_test("Upload Video", False, "Invalid response format")
            else:
                self.log_test("Upload Video", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Upload Video", False, str(e))
        return False

    def test_upload_audio(self):
        """Test uploading an audio file"""
        if not self.session_id:
            self.log_test("Upload Audio", False, "No session ID")
            return False
        
        try:
            # Create a small test audio file (mock)
            test_file = io.BytesIO(b"fake audio content for testing")
            test_file.name = "test_audio.mp3"
            
            files = {'file': ('test_audio.mp3', test_file, 'audio/mpeg')}
            response = requests.post(
                f"{self.base_url}/upload/sessions/{self.session_id}/audio",
                files=files
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "file" in data:
                    file_data = data["file"]
                    if (file_data.get("file_type") == "audio" and
                        file_data.get("original_name") == "test_audio.mp3"):
                        self.log_test("Upload Audio", True)
                        return True
                    else:
                        self.log_test("Upload Audio", False, "Invalid file data")
                else:
                    self.log_test("Upload Audio", False, "Invalid response format")
            else:
                self.log_test("Upload Audio", False, f"Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_test("Upload Audio", False, str(e))
        return False

    def test_file_validation_video_format(self):
        """Test video file format validation"""
        if not self.session_id:
            self.log_test("Video Format Validation", False, "No session ID")
            return False
        
        try:
            # Try uploading invalid format
            test_file = io.BytesIO(b"fake content")
            files = {'file': ('test.txt', test_file, 'text/plain')}
            response = requests.post(
                f"{self.base_url}/upload/sessions/{self.session_id}/videos",
                files=files
            )
            
            # Should return 400 for invalid format
            if response.status_code == 400:
                data = response.json()
                if not data.get("success") and "error" in data:
                    self.log_test("Video Format Validation", True)
                    return True
                else:
                    self.log_test("Video Format Validation", False, "Expected error message")
            else:
                self.log_test("Video Format Validation", False, f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.log_test("Video Format Validation", False, str(e))
        return False

    def test_file_validation_audio_format(self):
        """Test audio file format validation"""
        if not self.session_id:
            self.log_test("Audio Format Validation", False, "No session ID")
            return False
        
        try:
            # Try uploading invalid format
            test_file = io.BytesIO(b"fake content")
            files = {'file': ('test.txt', test_file, 'text/plain')}
            response = requests.post(
                f"{self.base_url}/upload/sessions/{self.session_id}/audio",
                files=files
            )
            
            # Should return 400 for invalid format
            if response.status_code == 400:
                data = response.json()
                if not data.get("success") and "error" in data:
                    self.log_test("Audio Format Validation", True)
                    return True
                else:
                    self.log_test("Audio Format Validation", False, "Expected error message")
            else:
                self.log_test("Audio Format Validation", False, f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.log_test("Audio Format Validation", False, str(e))
        return False

    def test_session_ready_status(self):
        """Test session ready to process status"""
        if not self.session_id:
            self.log_test("Session Ready Status", False, "No session ID")
            return False
        
        try:
            response = requests.get(f"{self.base_url}/upload/sessions/{self.session_id}")
            
            if response.status_code == 200:
                data = response.json()
                session = data.get("session", {})
                # After uploading 1 video and 1 audio, should be ready
                if session.get("is_ready"):
                    self.log_test("Session Ready Status", True)
                    return True
                else:
                    self.log_test("Session Ready Status", False, "Session not marked as ready")
            else:
                self.log_test("Session Ready Status", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Session Ready Status", False, str(e))
        return False

    def test_process_session(self):
        """Test processing a session (placeholder)"""
        if not self.session_id:
            self.log_test("Process Session", False, "No session ID")
            return False
        
        try:
            response = requests.post(f"{self.base_url}/upload/sessions/{self.session_id}/process")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "message" in data:
                    self.log_test("Process Session", True)
                    return True
                else:
                    self.log_test("Process Session", False, "Invalid response format")
            else:
                self.log_test("Process Session", False, f"Status code: {response.status_code}")
        except Exception as e:
            self.log_test("Process Session", False, str(e))
        return False

    def test_get_nonexistent_session(self):
        """Test getting a non-existent session"""
        try:
            response = requests.get(f"{self.base_url}/upload/sessions/nonexistent-id-12345")
            
            if response.status_code == 404:
                self.log_test("Get Non-existent Session", True)
                return True
            else:
                self.log_test("Get Non-existent Session", False, f"Expected 404, got {response.status_code}")
        except Exception as e:
            self.log_test("Get Non-existent Session", False, str(e))
        return False

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print(f"📊 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        print("="*60)
        
        if self.tests_passed < self.tests_run:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['name']}: {result['message']}")

def main():
    print("🚀 Starting AniPulse Upload System Backend Tests")
    print("="*60)
    
    tester = UploadSystemTester()
    
    # Run tests in sequence
    print("\n📝 Testing Upload Session Management...")
    tester.test_create_session()
    tester.test_get_session()
    
    print("\n📤 Testing File Uploads...")
    tester.test_upload_video()
    tester.test_upload_audio()
    
    print("\n🔍 Testing File Validation...")
    tester.test_file_validation_video_format()
    tester.test_file_validation_audio_format()
    
    print("\n✅ Testing Session Status...")
    tester.test_session_ready_status()
    
    print("\n⚙️ Testing Session Processing...")
    tester.test_process_session()
    
    print("\n🔒 Testing Error Handling...")
    tester.test_get_nonexistent_session()
    
    # Print summary
    tester.print_summary()
    
    # Return exit code
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
