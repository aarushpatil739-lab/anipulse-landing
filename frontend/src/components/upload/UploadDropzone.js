import React, { useCallback } from 'react';
import { motion } from 'framer-motion';
import { Upload, Film, Music } from 'lucide-react';

const UploadDropzone = ({ type, onDrop, disabled, multiple = false, accept }) => {
  const [isDragging, setIsDragging] = React.useState(false);

  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragging(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled) return;

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      onDrop(multiple ? files : files[0]);
    }
  }, [disabled, onDrop, multiple]);

  const handleFileSelect = useCallback((e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      onDrop(multiple ? files : files[0]);
    }
    e.target.value = ''; // Reset input
  }, [onDrop, multiple]);

  const Icon = type === 'video' ? Film : Music;
  const title = type === 'video' ? 'Upload Video Clips' : 'Upload Music Track';
  const subtitle = type === 'video' 
    ? 'MP4, MOV, or WebM • Max 500MB per file • Up to 20 clips'
    : 'MP3 or WAV • Max 50MB • One file required';

  return (
    <motion.div
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      className={`relative`}
    >
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          glass-effect rounded-2xl p-8 border-2 transition-all duration-300
          ${isDragging ? 'border-cyber-purple glow-purple bg-cyber-purple/10' : 'border-white/20'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-cyber-cyan'}
        `}
      >
        <input
          type="file"
          id={`upload-${type}`}
          accept={accept}
          multiple={multiple}
          onChange={handleFileSelect}
          disabled={disabled}
          className="hidden"
        />

        <label
          htmlFor={disabled ? undefined : `upload-${type}`}
          className={`flex flex-col items-center gap-4 ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <motion.div
            animate={isDragging ? { scale: 1.1 } : { scale: 1 }}
            className={`
              w-20 h-20 rounded-full flex items-center justify-center
              ${isDragging ? 'bg-cyber-purple' : 'bg-gradient-to-br from-cyber-purple to-cyber-cyan'}
            `}
          >
            <Icon className="w-10 h-10 text-white" />
          </motion.div>

          <div className="text-center">
            <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
            <p className="text-gray-400 text-sm mb-4">{subtitle}</p>
            <div className="flex items-center gap-2 justify-center text-cyber-cyan">
              <Upload className="w-4 h-4" />
              <span className="text-sm font-medium">
                {isDragging ? 'Drop files here' : 'Drag & drop or click to browse'}
              </span>
            </div>
          </div>
        </label>
      </div>
    </motion.div>
  );
};

export default UploadDropzone;
