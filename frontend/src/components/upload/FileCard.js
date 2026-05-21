import React from 'react';
import { motion } from 'framer-motion';
import { X, Film, Music, Check } from 'lucide-react';
import { validation } from '../../services/uploadService';

const FileCard = ({ file, onRemove, progress, type }) => {
  const [thumbnail, setThumbnail] = React.useState(null);

  React.useEffect(() => {
    // Generate video thumbnail
    if (type === 'video' && file.file) {
      const video = document.createElement('video');
      video.preload = 'metadata';
      video.src = URL.createObjectURL(file.file);
      
      video.onloadedmetadata = () => {
        video.currentTime = 1; // Seek to 1 second
      };

      video.onseeked = () => {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        setThumbnail(canvas.toDataURL());
        URL.revokeObjectURL(video.src);
      };
    }
  }, [file.file, type]);

  const Icon = type === 'video' ? Film : Music;
  const isUploading = progress !== undefined && progress < 100;
  const isComplete = progress === 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="glass-effect rounded-xl p-4 border border-white/10 hover:border-cyber-purple/50 transition-all group relative overflow-hidden"
    >
      {/* Progress overlay */}
      {isUploading && (
        <div 
          className="absolute inset-0 bg-cyber-purple/20 transition-all"
          style={{ width: `${progress}%` }}
        />
      )}

      <div className="relative z-10 flex items-center gap-4">
        {/* Thumbnail or Icon */}
        <div className="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0 bg-gradient-to-br from-cyber-purple to-cyber-cyan flex items-center justify-center">
          {thumbnail ? (
            <img src={thumbnail} alt="Video thumbnail" className="w-full h-full object-cover" />
          ) : (
            <Icon className="w-8 h-8 text-white" />
          )}
        </div>

        {/* File info */}
        <div className="flex-1 min-w-0">
          <p className="text-white font-medium truncate">{file.name || file.original_name}</p>
          <p className="text-gray-400 text-sm">
            {validation.formatFileSize(file.size || file.size_bytes)}
          </p>
          
          {/* Progress bar */}
          {isUploading && (
            <div className="mt-2">
              <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  className="h-full bg-gradient-to-r from-cyber-purple to-cyber-cyan"
                />
              </div>
              <p className="text-xs text-cyber-cyan mt-1">{Math.round(progress)}% uploaded</p>
            </div>
          )}

          {isComplete && (
            <div className="flex items-center gap-1 mt-1 text-green-400 text-sm">
              <Check className="w-4 h-4" />
              <span>Uploaded</span>
            </div>
          )}
        </div>

        {/* Remove button */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => onRemove(file)}
          className="w-8 h-8 rounded-lg glass-effect border border-white/10 hover:border-red-500 hover:bg-red-500/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
          disabled={isUploading}
        >
          <X className="w-4 h-4 text-white" />
        </motion.button>
      </div>
    </motion.div>
  );
};

export default FileCard;
