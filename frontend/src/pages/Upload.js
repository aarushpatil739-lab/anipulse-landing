import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Sparkles, AlertCircle, CheckCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Container } from '../components/ui/Container';
import { Button } from '../components/ui/Button';
import UploadDropzone from '../components/upload/UploadDropzone';
import FileCard from '../components/upload/FileCard';
import { uploadAPI, validation } from '../services/uploadService';

const Upload = () => {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState(null);
  const [videos, setVideos] = useState([]);
  const [audio, setAudio] = useState(null);
  const [uploadProgress, setUploadProgress] = useState({});
  const [errors, setErrors] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [totalSize, setTotalSize] = useState(0);

  // Create upload session on mount
  useEffect(() => {
    const createSession = async () => {
      try {
        const response = await uploadAPI.createSession();
        if (response.success) {
          setSessionId(response.session.session_id);
        }
      } catch (error) {
        setErrors(['Failed to create upload session. Please refresh the page.']);
      }
    };
    createSession();
  }, []);

  // Handle video drop/select
  const handleVideosDrop = async (files) => {
    const fileArray = Array.isArray(files) ? files : [files];
    
    // Validate each file
    for (const file of fileArray) {
      const validationResult = validation.validateVideo(file);
      if (!validationResult.valid) {
        setErrors(prev => [...prev, `${file.name}: ${validationResult.error}`]);
        continue;
      }

      // Check video count
      if (videos.length >= validation.MAX_VIDEOS) {
        setErrors(prev => [...prev, `Maximum ${validation.MAX_VIDEOS} videos allowed`]);
        break;
      }

      // Check total size
      if (totalSize + file.size > validation.MAX_TOTAL_SIZE) {
        setErrors(prev => [...prev, 'Total upload size exceeds 2GB limit']);
        break;
      }

      // Add to videos list with uploading state
      const tempId = `temp-${Date.now()}-${Math.random()}`;
      const videoEntry = {
        tempId,
        file,
        name: file.name,
        size: file.size,
        uploading: true,
      };
      
      setVideos(prev => [...prev, videoEntry]);
      setTotalSize(prev => prev + file.size);
      setUploadProgress(prev => ({ ...prev, [tempId]: 0 }));

      // Upload the file
      try {
        const response = await uploadAPI.uploadVideo(
          sessionId,
          file,
          (progress) => {
            setUploadProgress(prev => ({ ...prev, [tempId]: progress }));
          }
        );

        if (response.success) {
          // Update with server file data
          setVideos(prev => prev.map(v => 
            v.tempId === tempId 
              ? { ...v, ...response.file, uploading: false }
              : v
          ));
        } else {
          throw new Error(response.error);
        }
      } catch (error) {
        setErrors(prev => [...prev, `Failed to upload ${file.name}: ${error.message || 'Unknown error'}`]);
        setVideos(prev => prev.filter(v => v.tempId !== tempId));
        setTotalSize(prev => prev - file.size);
      }
    }
  };

  // Handle audio drop/select
  const handleAudioDrop = async (file) => {
    const validationResult = validation.validateAudio(file);
    if (!validationResult.valid) {
      setErrors(prev => [...prev, validationResult.error]);
      return;
    }

    // Check total size
    const audioSizeToRemove = audio ? audio.size : 0;
    if (totalSize - audioSizeToRemove + file.size > validation.MAX_TOTAL_SIZE) {
      setErrors(prev => [...prev, 'Total upload size exceeds 2GB limit']);
      return;
    }

    const tempId = `audio-${Date.now()}`;
    const audioEntry = {
      tempId,
      file,
      name: file.name,
      size: file.size,
      uploading: true,
    };

    setAudio(audioEntry);
    setTotalSize(prev => prev - audioSizeToRemove + file.size);
    setUploadProgress(prev => ({ ...prev, [tempId]: 0 }));

    // Upload the file
    try {
      const response = await uploadAPI.uploadAudio(
        sessionId,
        file,
        (progress) => {
          setUploadProgress(prev => ({ ...prev, [tempId]: progress }));
        }
      );

      if (response.success) {
        setAudio({ ...audioEntry, ...response.file, uploading: false });
      } else {
        throw new Error(response.error);
      }
    } catch (error) {
      setErrors(prev => [...prev, `Failed to upload audio: ${error.message || 'Unknown error'}`]);
      setAudio(null);
      setTotalSize(prev => prev - file.size);
    }
  };

  // Remove video
  const handleRemoveVideo = async (file) => {
    if (file.file_id) {
      try {
        await uploadAPI.removeFile(sessionId, file.file_id);
      } catch (error) {
        console.error('Failed to remove file from server:', error);
      }
    }
    setVideos(prev => prev.filter(v => v.tempId !== file.tempId && v.file_id !== file.file_id));
    setTotalSize(prev => prev - (file.size || file.size_bytes));
  };

  // Remove audio
  const handleRemoveAudio = async () => {
    if (audio && audio.file_id) {
      try {
        await uploadAPI.removeFile(sessionId, audio.file_id);
      } catch (error) {
        console.error('Failed to remove file from server:', error);
      }
    }
    setTotalSize(prev => prev - (audio?.size || audio?.size_bytes || 0));
    setAudio(null);
  };

  // Process uploads
  const handleProcess = async () => {
    setIsProcessing(true);
    try {
      const response = await uploadAPI.processSession(sessionId);
      if (response.success) {
        // Show success message (placeholder for now)
        alert(response.message || 'Processing started! AI editing coming soon.');
      } else {
        setErrors(prev => [...prev, response.error || 'Failed to start processing']);
      }
    } catch (error) {
      setErrors(prev => [...prev, 'Failed to start processing']);
    } finally {
      setIsProcessing(false);
    }
  };

  // Clear error after 5 seconds
  useEffect(() => {
    if (errors.length > 0) {
      const timer = setTimeout(() => {
        setErrors([]);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [errors]);

  const isReadyToProcess = videos.length >= 1 && audio && !videos.some(v => v.uploading) && !audio.uploading;
  const uploadedVideos = videos.filter(v => !v.uploading);

  return (
    <div className="min-h-screen bg-cyber-darker py-24">
      <Container>
        {/* Back button */}
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-8"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Home</span>
        </motion.button>

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-4">
            Upload Your <span className="text-gradient">Content</span>
          </h1>
          <p className="text-xl text-gray-300 max-w-2xl mx-auto">
            Upload your anime clips and music track to create an AI-powered AMV
          </p>
        </motion.div>

        {/* Error messages */}
        <AnimatePresence>
          {errors.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mb-8"
            >
              {errors.map((error, index) => (
                <div key={index} className="glass-effect rounded-lg p-4 border border-red-500/50 bg-red-500/10 mb-2 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <p className="text-red-300 text-sm">{error}</p>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
          {/* Video upload */}
          <div>
            <UploadDropzone
              type="video"
              onDrop={handleVideosDrop}
              disabled={!sessionId || videos.length >= validation.MAX_VIDEOS}
              multiple={true}
              accept="video/mp4,video/quicktime,video/webm"
            />

            {/* Video list */}
            {videos.length > 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-6 space-y-3"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white">
                    Video Clips ({videos.length}/{validation.MAX_VIDEOS})
                  </h3>
                </div>
                <AnimatePresence>
                  {videos.map((video) => (
                    <FileCard
                      key={video.tempId || video.file_id}
                      file={video}
                      onRemove={handleRemoveVideo}
                      progress={uploadProgress[video.tempId]}
                      type="video"
                    />
                  ))}
                </AnimatePresence>
              </motion.div>
            )}
          </div>

          {/* Audio upload */}
          <div>
            <UploadDropzone
              type="audio"
              onDrop={handleAudioDrop}
              disabled={!sessionId}
              multiple={false}
              accept="audio/mpeg,audio/wav,audio/x-wav"
            />

            {/* Audio file */}
            {audio && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-6"
              >
                <h3 className="text-lg font-semibold text-white mb-4">Music Track</h3>
                <FileCard
                  file={audio}
                  onRemove={handleRemoveAudio}
                  progress={uploadProgress[audio.tempId]}
                  type="audio"
                />
              </motion.div>
            )}
          </div>
        </div>

        {/* Upload summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-effect rounded-2xl p-6 border border-white/10 mb-8"
        >
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 text-center">
            <div>
              <p className="text-gray-400 text-sm mb-1">Videos Uploaded</p>
              <p className="text-3xl font-bold text-gradient">{uploadedVideos.length}</p>
            </div>
            <div>
              <p className="text-gray-400 text-sm mb-1">Audio Track</p>
              <p className="text-3xl font-bold text-gradient">{audio ? '1' : '0'}</p>
            </div>
            <div>
              <p className="text-gray-400 text-sm mb-1">Total Size</p>
              <p className="text-3xl font-bold text-gradient">{validation.formatFileSize(totalSize)}</p>
            </div>
            <div>
              <p className="text-gray-400 text-sm mb-1">Status</p>
              <div className="flex items-center justify-center gap-2">
                {isReadyToProcess ? (
                  <>
                    <CheckCircle className="w-6 h-6 text-green-400" />
                    <p className="text-xl font-bold text-green-400">Ready</p>
                  </>
                ) : (
                  <p className="text-xl font-bold text-gray-400">Uploading...</p>
                )}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Process button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <Button
            variant="primary"
            size="lg"
            onClick={handleProcess}
            disabled={!isReadyToProcess || isProcessing}
            className="text-xl px-16 py-6"
          >
            {isProcessing ? (
              'Processing...'
            ) : (
              <>
                <Sparkles className="w-6 h-6 mr-2" />
                Process Now
              </>
            )}
          </Button>
          {!isReadyToProcess && (
            <p className="text-gray-400 text-sm mt-4">
              {videos.length < 1 && 'Upload at least 1 video clip'}
              {videos.length >= 1 && !audio && ' and 1 audio track'}
              {videos.some(v => v.uploading) || (audio && audio.uploading) ? ' (uploading...)' : ''}
            </p>
          )}
        </motion.div>
      </Container>
    </div>
  );
};

export default Upload;
