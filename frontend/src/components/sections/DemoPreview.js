import React from 'react';
import { motion } from 'framer-motion';
import { Container } from '../ui/Container';
import { SectionHeading } from '../ui/SectionHeading';
import { demoVideos } from '../../lib/content';

const DemoPreview = () => {
  return (
    <section id="demo" className="py-24 relative overflow-hidden" data-testid="demo-section">
      {/* Background effects */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyber-cyan/10 rounded-full blur-[150px]" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-cyber-pink/10 rounded-full blur-[150px]" />
      
      <Container>
        <SectionHeading
          badge="Creator Showcase"
          title="See What Others"
          titleHighlight="Are Creating"
          subtitle="Real edits from our creator community. Your next viral video is one click away."
        />
        
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {demoVideos.map((video, index) => (
            <motion.div
              key={video.id}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              whileHover={{ y: -10 }}
              className="group cursor-pointer"
              data-testid={`demo-card-${video.id}`}
            >
              {/* Video thumbnail */}
              <div className="relative aspect-[9/16] rounded-2xl overflow-hidden glass-effect border border-white/10 group-hover:border-cyber-purple/50 transition-all duration-300 group-hover:glow-purple">
                <img
                  src={video.thumbnail}
                  alt={video.title}
                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                />
                
                {/* Gradient overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-cyber-darker via-cyber-darker/50 to-transparent opacity-60 group-hover:opacity-40 transition-opacity duration-300" />
                
                {/* Play button */}
                <motion.div
                  whileHover={{ scale: 1.2 }}
                  className="absolute inset-0 flex items-center justify-center"
                >
                  <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm border border-white/30 flex items-center justify-center group-hover:bg-cyber-purple/80 transition-all duration-300 glow-purple">
                    <span className="text-white text-2xl">▶️</span>
                  </div>
                </motion.div>
                
                {/* Badges */}
                <div className="absolute top-4 left-4 flex flex-col gap-2">
                  {video.beatSync && (
                    <span className="glass-effect px-3 py-1 rounded-full text-xs font-semibold text-cyber-cyan border border-cyber-cyan/30">
                      🎵 Beat Synced
                    </span>
                  )}
                  <span className="glass-effect px-3 py-1 rounded-full text-xs font-semibold text-white border border-white/20">
                    {video.fps}
                  </span>
                </div>
                
                {/* Duration */}
                <div className="absolute top-4 right-4 glass-effect px-3 py-1 rounded-full text-xs font-semibold text-white border border-white/20">
                  {video.duration}
                </div>
                
                {/* Bottom info */}
                <div className="absolute bottom-4 left-4 right-4">
                  <h4 className="text-xl font-bold text-white mb-1 group-hover:text-gradient transition-all duration-300">
                    {video.title}
                  </h4>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-300">{video.style}</span>
                    <div className="flex items-center gap-1 text-gray-400 text-sm">
                      <span>❤️</span>
                      <span>{(Math.random() * 100).toFixed(1)}K</span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
        
        {/* View more button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5 }}
          className="text-center mt-12"
        >
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="glass-effect px-8 py-3 rounded-lg font-semibold text-white border border-cyber-purple/30 hover:border-cyber-purple hover:glow-purple transition-all duration-300"
          >
            View More Creations →
          </motion.button>
        </motion.div>
      </Container>
    </section>
  );
};

export default DemoPreview;
