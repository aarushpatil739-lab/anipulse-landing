import React from 'react';

export const Container = ({ children, className = '', size = 'default' }) => {
  const sizes = {
    default: 'max-w-7xl',
    sm: 'max-w-4xl',
    lg: 'max-w-[1400px]',
    full: 'max-w-full',
  };
  
  return (
    <div className={`mx-auto px-4 sm:px-6 lg:px-8 ${sizes[size]} ${className}`}>
      {children}
    </div>
  );
};
