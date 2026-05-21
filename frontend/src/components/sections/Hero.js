import React from 'react';
import { motion } from 'framer-motion';
import { Button } from '../ui/Button';
import { Container } from '../ui/Container';
import { GlowBackground, GridPattern } from '../ui/GlowBackground';
import { heroContent } from '../../lib/content';

const Hero = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20" data-testid="hero-section">
      {/* Animated Background */}
      <GlowBackground />
      <GridPattern />
      
      {/* Floating particles effect */}
      <div className="absolute inset-0">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-cyber-purple rounded-full"
            initial={{
              x: Math.random() * window.innerWidth,
              y: Math.random() * window.innerHeight,
              opacity: 0,
            }}
            animate={{
              y: [null, Math.random() * -500],
              opacity: [0, 1, 0],
            }}
            transition={{
              duration: Math.random() * 10 + 10,
              repeat: Infinity,
              delay: Math.random() * 5,
            }}
          />
        ))}
      </div>
      
      <Container className="relative z-10">
        <div className="text-center space-y-8">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <span className="glass-effect px-6 py-3 rounded-full text-sm font-medium text-cyber-cyan border border-cyber-cyan/30 inline-block">
              ✨ {heroContent.badge}
            </span>
          </motion.div>
          
          {/* Main Headline */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold text-white leading-tight">
              {heroContent.title}
              <br />
              <span className="text-gradient inline-block mt-2">
                {heroContent.titleHighlight}
              </span>
            </h1>
          </motion.div>
          
          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="text-xl md:text-2xl text-gray-300 max-w-4xl mx-auto leading-relaxed"
          >
            {heroContent.subtitle}
          </motion.p>
          
          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="flex flex-col sm:flex-row gap-4 justify-center items-center"
          >
            <Button variant="primary" size="lg" data-testid="cta-generate">
              {heroContent.primaryCTA} →
            </Button>
            <Button variant="secondary" size="lg" data-testid="cta-demo">
              {heroContent.secondaryCTA}
            </Button>
          </motion.div>
          
          {/* Hero Image/Visual Element */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, delay: 0.8 }}
            className="mt-16 relative"
          >
            <div className="relative w-full max-w-5xl mx-auto">
              <div className="aspect-video rounded-2xl overflow-hidden glass-effect border-2 border-cyber-purple/30 glow-purple">
                <img 
                  src="https://images.unsplash.com/photo-1762341154386-fa765c9f2aa5?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2ODh8MHwxfHNlYXJjaHwzfHxhbmltZSUyMGN5YmVycHVuayUyMG5lb24lMjBjaXR5JTIwZnV0dXJpc3RpY3xlbnwwfHx8fDE3NzkzNTk1MTR8MA&ixlib=rb-4.1.0&q=85"
                  alt="Cyberpunk anime cityscape"
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-cyber-darker via-transparent to-transparent" />
              </div>
              
              {/* Floating badges */}
              <motion.div
                animate={{ y: [-10, 10, -10] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -top-4 -right-4 glass-effect px-4 py-2 rounded-lg border border-cyber-cyan/30 text-cyber-cyan font-semibold"
              >
                ⚡ 60 FPS
              </motion.div>
              
              <motion.div
                animate={{ y: [10, -10, 10] }}
                transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -bottom-4 -left-4 glass-effect px-4 py-2 rounded-lg border border-cyber-pink/30 text-cyber-pink font-semibold"
              >
                🎵 Beat Synced
              </motion.div>
            </div>
          </motion.div>
        </div>
      </Container>
      
      {/* Scroll indicator */}
      <motion.div
        animate={{ y: [0, 10, 0] }}
        transition={{ duration: 2, repeat: Infinity }}
        className="absolute bottom-8 left-1/2 transform -translate-x-1/2"
      >
        <div className="w-6 h-10 border-2 border-white/30 rounded-full flex items-start justify-center p-2">
          <motion.div
            animate={{ y: [0, 12, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-1 h-2 bg-white rounded-full"
          />
        </div>
      </motion.div>
    </section>
  );
};

export default Hero;
