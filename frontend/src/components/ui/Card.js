import React from 'react';
import { motion } from 'framer-motion';

export const Card = ({ children, className = '', hover = true, ...props }) => {
  const cardVariants = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    hover: hover ? { y: -8, transition: { duration: 0.3 } } : {},
  };
  
  return (
    <motion.div
      variants={cardVariants}
      initial="initial"
      whileInView="animate"
      whileHover="hover"
      viewport={{ once: true, margin: '-100px' }}
      className={`glass-effect rounded-2xl p-6 border border-white/10 ${className}`}
      {...props}
    >
      {children}
    </motion.div>
  );
};

export const GlassCard = ({ children, className = '', glow = 'purple', ...props }) => {
  const glowClass = glow === 'purple' ? 'hover:glow-purple' : glow === 'cyan' ? 'hover:glow-cyan' : 'hover:glow-pink';
  
  return (
    <Card 
      className={`${glowClass} transition-all duration-300 ${className}`}
      {...props}
    >
      {children}
    </Card>
  );
};
