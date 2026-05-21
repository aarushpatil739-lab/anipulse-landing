import React from 'react';
import { motion } from 'framer-motion';

export const SectionHeading = ({ 
  badge, 
  title, 
  titleHighlight, 
  subtitle, 
  centered = true,
  className = '' 
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6 }}
      className={`${centered ? 'text-center' : ''} ${className}`}
    >
      {badge && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="inline-block mb-4"
        >
          <span className="glass-effect px-4 py-2 rounded-full text-sm font-medium text-cyber-cyan border border-cyber-cyan/30">
            {badge}
          </span>
        </motion.div>
      )}
      
      <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-4 text-white">
        {title}{' '}
        {titleHighlight && (
          <span className="text-gradient">{titleHighlight}</span>
        )}
      </h2>
      
      {subtitle && (
        <p className="text-lg md:text-xl text-gray-300 max-w-3xl mx-auto">
          {subtitle}
        </p>
      )}
    </motion.div>
  );
};
