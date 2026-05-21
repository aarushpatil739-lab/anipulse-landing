import React from 'react';
import { motion } from 'framer-motion';
import { Container } from '../ui/Container';
import { SectionHeading } from '../ui/SectionHeading';
import { GlassCard } from '../ui/Card';
import { features } from '../../lib/content';

const Features = () => {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };
  
  return (
    <section id="features" className="py-24 relative" data-testid="features-section">
      <Container>
        <SectionHeading
          badge="Powerful Features"
          title="Everything You Need To"
          titleHighlight="Dominate The Feed"
          subtitle="Professional-grade AI tools designed for creators who want to stand out"
        />
        
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-16"
        >
          {features.map((feature, index) => (
            <GlassCard
              key={feature.id}
              glow={index % 3 === 0 ? 'purple' : index % 3 === 1 ? 'cyan' : 'pink'}
              className="group cursor-pointer"
              data-testid={`feature-card-${feature.id}`}
            >
              {/* Icon with gradient background */}
              <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center text-3xl mb-4 group-hover:scale-110 transition-transform duration-300`}>
                {feature.icon}
              </div>
              
              <h3 className="text-2xl font-bold text-white mb-3 group-hover:text-gradient transition-all duration-300">
                {feature.title}
              </h3>
              
              <p className="text-gray-400 leading-relaxed">
                {feature.description}
              </p>
              
              {/* Hover arrow */}
              <motion.div
                initial={{ x: -10, opacity: 0 }}
                whileHover={{ x: 0, opacity: 1 }}
                className="mt-4 text-cyber-cyan flex items-center gap-2 font-medium"
              >
                Learn more →
              </motion.div>
            </GlassCard>
          ))}
        </motion.div>
        
        {/* Bottom CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5 }}
          className="text-center mt-16"
        >
          <p className="text-gray-400 mb-4">And many more features coming soon...</p>
          <div className="flex gap-2 justify-center flex-wrap">
            {['Voice Sync', '3D Effects', 'Color Grading', 'Smart Transitions'].map((tag) => (
              <span key={tag} className="glass-effect px-4 py-2 rounded-full text-sm text-gray-300 border border-white/10">
                {tag}
              </span>
            ))}
          </div>
        </motion.div>
      </Container>
    </section>
  );
};

export default Features;
