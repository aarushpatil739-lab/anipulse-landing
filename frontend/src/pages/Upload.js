import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Sparkles, AlertCircle, CheckCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Container } from '../components/ui/Container';
import { Button } from '../components/ui/Button';
import UploadDropzone from '../components/upload/UploadDropzone';
import FileCard from '../components/upload/FileCard';
import BeatTimeline from '../components/upload/BeatTimeline';
import RenderSettings from '../components/upload/RenderSettings';
import ClipIntensityStrip from '../components/upload/ClipIntensityStrip';
import { uploadAPI, validation } from '../services/uploadService';

const Upload = () => {
  const navigate = useNavigate();
  const backendUrl = process.env.REACT_APP_BACKEND_URL;
  const [sessionId, setSessionId] = useState(null);
  const [videos, setVideos] = useState([]);
  const [audio, setAudio] = useState(null);
  const [uploadProgress, setUploadProgress] = useState({});
  const [errors, setErrors] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [totalSize, setTotalSize] = useState(0);
  
  // Generation state
  const [jobId, setJobId] = useState(null);
  const [generationStatus, setGenerationStatus] = useState(null);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStage, setGenerationStage] = useState('');
  const [generationError, setGenerationError] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);

  // Render-format state
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [verticalMode, setVerticalMode] = useState('blurred');

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

  // Process uploads - Start AMV generation
  const handleProcess = async () => {
    setIsProcessing(true);
    setGenerationError(null);
    
    try {
      // Start generation
      const response = await fetch(`${backendUrl}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          style: 'amv_default',
          max_duration: 180.0,
          aspect_ratio: aspectRatio,
          vertical_mode: verticalMode,
        })
      });
      
      const data = await response.json();
      
      if (data.success && data.job_id) {
        setJobId(data.job_id);
        setGenerationStatus('queued');
        // Start polling for status
        pollGenerationStatus(data.job_id);
      } else {
        throw new Error(data.detail || 'Failed to start generation');
      }
    } catch (error) {
      console.error('Generation error:', error);
      setErrors(prev => [...prev, `Failed to start generation: ${error.message}`]);
      setIsProcessing(false);
      setGenerationError(error.message);
    }
  };
  
  // Poll generation status
  const pollGenerationStatus = async (jobId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${backendUrl}/api/generate/${jobId}/status`);
        const data = await response.json();
        
        if (data.success) {
          setGenerationStatus(data.status);
          setGenerationProgress(data.progress_pct);
          setGenerationStage(data.current_stage);
          
          // Stop polling if completed or failed
          if (data.status === 'completed') {
            clearInterval(pollInterval);
            setIsProcessing(false);
            setDownloadUrl(`${backendUrl}/api/generate/${jobId}/download`);
          } else if (data.status === 'failed') {
            clearInterval(pollInterval);
            setIsProcessing(false);
            setGenerationError(data.error_message || 'Generation failed');
            setErrors(prev => [...prev, `Generation failed: ${data.error_message || 'Unknown error'}`]);
          }
        }
      } catch (error) {
        console.error('Status poll error:', error);
        // Don't clear interval on network errors, keep trying
      }
    }, 2000); // Poll every 2 seconds
    
    // Cleanup on unmount
    return () => clearInterval(pollInterval);
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

        {/* AI insights: beat timeline + clip intensity (visible once
            audio/videos are uploaded; harmless before that). */}
        {audio && !audio.uploading && (
          <div className="mb-8">
            <BeatTimeline
              sessionId={sessionId}
              backendUrl={backendUrl}
            />
          </div>
        )}

        {uploadedVideos.length > 0 && (
          <div className="mb-8">
            <ClipIntensityStrip
              sessionId={sessionId}
              backendUrl={backendUrl}
            />
          </div>
        )}

        {/* Render-format selector (always visible once a session exists) */}
        {sessionId && (
          <div className="mb-8">
            <RenderSettings
              aspectRatio={aspectRatio}
              onAspectRatioChange={setAspectRatio}
              verticalMode={verticalMode}
              onVerticalModeChange={setVerticalMode}
              disabled={isProcessing}
            />
          </div>
        )}

        {/* Generation Progress UI */}
        {isProcessing && jobId && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-effect rounded-2xl p-8 border border-purple-500/30 mb-8 bg-gradient-to-br from-purple-500/5 to-blue-500/5"
          >
            <div className="text-center mb-6">
              <h3 className="text-2xl font-bold text-white mb-2">
                {generationStatus === 'completed' ? 'Generation Complete!' : 'Generating Your AMV...'}
              </h3>
              <p className="text-gray-300 text-sm">
                {generationStage || 'Initializing...'}
              </p>
            </div>
            
            {/* Progress bar */}
            <div className="relative w-full h-3 bg-gray-800 rounded-full overflow-hidden mb-4">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${generationProgress}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
                className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500"
                style={{
                  boxShadow: '0 0 20px rgba(168, 85, 247, 0.5)'
                }}
              />
            </div>
            
            {/* Progress percentage */}
            <p className="text-center text-white font-mono text-lg mb-4">
              {Math.round(generationProgress)}%
            </p>
            
            {/* Stage indicators */}
            <div className="grid grid-cols-4 gap-2 text-xs">
              {[
                { key: 'analyzing_audio', label: 'Analyzing' },
                { key: 'generating_timeline', label: 'Timeline' },
                { key: 'rendering', label: 'Rendering' },
                { key: 'completed', label: 'Complete' }
              ].map((stage, idx) => {
                const isActive = generationStatus === stage.key;
                const isComplete = ['analyzing_audio', 'generating_timeline', 'rendering', 'completed'].indexOf(generationStatus) > idx;
                
                return (
                  <div
                    key={stage.key}
                    className={`p-2 rounded text-center transition-all ${
                      isActive 
                        ? 'bg-purple-500/30 text-white border border-purple-500' 
                        : isComplete
                        ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                        : 'bg-gray-800/50 text-gray-500 border border-gray-700'
                    }`}
                  >
                    {stage.label}
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Success State with Download */}
        {generationStatus === 'completed' && downloadUrl && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-effect rounded-2xl p-8 border border-green-500/50 mb-8 bg-gradient-to-br from-green-500/10 to-blue-500/10 text-center"
            data-testid="generation-success"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            >
              <CheckCircle className="w-20 h-20 text-green-400 mx-auto mb-4" />
            </motion.div>
            <h3 className="text-3xl font-bold text-white mb-2">Your AMV is Ready!</h3>
            <p className="text-gray-300 mb-2">AI-generated beat-synced anime music video</p>
            <p className="text-sm text-gray-400 mb-6">
              {aspectRatio} {aspectRatio !== '16:9' ? `· ${verticalMode}` : ''} · 720p · H.264 · beat-synced
            </p>

            {/* Inline preview player so the creator can scrub before download */}
            <div
              className={`mx-auto rounded-xl overflow-hidden border border-white/10 bg-black mb-6 ${
                aspectRatio === '9:16'
                  ? 'w-[270px] h-[480px]'
                  : aspectRatio === '1:1'
                  ? 'w-[360px] h-[360px]'
                  : 'w-full max-w-[720px] aspect-video'
              }`}
              data-testid="result-preview"
            >
              <video
                src={downloadUrl}
                controls
                playsInline
                className="w-full h-full object-contain bg-black"
              />
            </div>

            <Button
              variant="primary"
              size="lg"
              onClick={() => {
                window.location.href = downloadUrl;
              }}
              className="text-xl px-12 py-4 mb-4"
              data-testid="download-amv-btn"
            >
              <span className="mr-2">⬇</span>
              Download AMV
            </Button>
          </motion.div>
        )}

        {/* Error State */}
        {generationStatus === 'failed' && generationError && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-effect rounded-2xl p-6 border border-red-500/50 mb-8 bg-red-500/10 text-center"
          >
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
            <h3 className="text-xl font-bold text-white mb-2">Generation Failed</h3>
            <p className="text-red-300 text-sm mb-4">{generationError}</p>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setGenerationStatus(null);
                setGenerationError(null);
                setJobId(null);
                setIsProcessing(false);
              }}
              className="text-sm"
            >
              Try Again
            </Button>
          </motion.div>
        )}

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
              <>
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-2"></div>
                Generating AMV...
              </>
            ) : (
              <>
                <Sparkles className="w-6 h-6 mr-2" />
                Generate AMV
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
