// Upload API service
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const uploadAPI = {
  // Create a new upload session
  createSession: async () => {
    const response = await fetch(`${API}/upload/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return response.json();
  },

  // Get session details
  getSession: async (sessionId) => {
    const response = await fetch(`${API}/upload/sessions/${sessionId}`);
    return response.json();
  },

  // Upload a video file
  uploadVideo: async (sessionId, file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Track upload progress
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          const progress = (e.loaded / e.total) * 100;
          onProgress(progress);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(JSON.parse(xhr.responseText));
        }
      });

      xhr.addEventListener('error', () => {
        reject({ success: false, error: 'Network error' });
      });

      xhr.open('POST', `${API}/upload/sessions/${sessionId}/videos`);
      xhr.send(formData);
    });
  },

  // Upload an audio file
  uploadAudio: async (sessionId, file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Track upload progress
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && onProgress) {
          const progress = (e.loaded / e.total) * 100;
          onProgress(progress);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(JSON.parse(xhr.responseText));
        }
      });

      xhr.addEventListener('error', () => {
        reject({ success: false, error: 'Network error' });
      });

      xhr.open('POST', `${API}/upload/sessions/${sessionId}/audio`);
      xhr.send(formData);
    });
  },

  // Remove a file
  removeFile: async (sessionId, fileId) => {
    const response = await fetch(`${API}/upload/sessions/${sessionId}/files/${fileId}`, {
      method: 'DELETE',
    });
    return response.json();
  },

  // Delete entire session
  deleteSession: async (sessionId) => {
    const response = await fetch(`${API}/upload/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    return response.json();
  },

  // Start processing
  processSession: async (sessionId) => {
    const response = await fetch(`${API}/upload/sessions/${sessionId}/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return response.json();
  },
};

// File validation helpers
export const validation = {
  // File size limits
  MAX_VIDEO_SIZE: 500 * 1024 * 1024, // 500MB
  MAX_AUDIO_SIZE: 50 * 1024 * 1024,  // 50MB
  MAX_TOTAL_SIZE: 2 * 1024 * 1024 * 1024, // 2GB
  MAX_VIDEOS: 20,
  MIN_VIDEOS: 1,

  // Allowed formats
  VIDEO_TYPES: ['video/mp4', 'video/quicktime', 'video/webm'],
  AUDIO_TYPES: ['audio/mpeg', 'audio/wav', 'audio/x-wav'],

  // Validate video file
  validateVideo: (file) => {
    if (!validation.VIDEO_TYPES.includes(file.type)) {
      return { valid: false, error: 'Invalid video format. Allowed: MP4, MOV, WebM' };
    }
    if (file.size > validation.MAX_VIDEO_SIZE) {
      return { valid: false, error: 'Video file exceeds 500MB limit' };
    }
    return { valid: true };
  },

  // Validate audio file
  validateAudio: (file) => {
    if (!validation.AUDIO_TYPES.includes(file.type)) {
      return { valid: false, error: 'Invalid audio format. Allowed: MP3, WAV' };
    }
    if (file.size > validation.MAX_AUDIO_SIZE) {
      return { valid: false, error: 'Audio file exceeds 50MB limit' };
    }
    return { valid: true };
  },

  // Format file size
  formatFileSize: (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  },
};
