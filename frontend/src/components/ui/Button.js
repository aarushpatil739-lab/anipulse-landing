import React from 'react';
import { motion } from 'framer-motion';

export const Button = ({ 
  children, 
  variant = 'primary', 
  size = 'default',
  className = '',
  onClick,
  ...props 
}) => {
  const baseStyles = 'font-semibold rounded-lg transition-all duration-300 inline-flex items-center justify-center';
  
  const variants = {
    primary: 'bg-gradient-to-r from-cyber-purple to-cyber-cyan text-white glow-purple hover:scale-105 hover:glow-cyan',
    secondary: 'glass-effect text-white hover:border-cyber-purple hover:glow-purple',
    ghost: 'text-white hover:bg-white/10',
  };
  
  const sizes = {
    default: 'px-8 py-3 text-base',
    lg: 'px-12 py-4 text-lg',
    sm: 'px-6 py-2 text-sm',
  };
  
  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      onClick={onClick}
      {...props}
    >
      {children}
    </motion.button>
  );
};
