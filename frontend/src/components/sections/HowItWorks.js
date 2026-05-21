import React from 'react';
import { motion } from 'framer-motion';
import { Container } from '../ui/Container';
import { SectionHeading } from '../ui/SectionHeading';
import { steps } from '../../lib/content';

const HowItWorks = () => {
  return (
    <section id="how-it-works" className="py-24 relative" data-testid="how-it-works-section">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cyber-purple/5 to-transparent" />
      
      <Container>
        <SectionHeading
          badge="Simple Process"
          title="From Clips To Viral"
          titleHighlight="In 4 Steps"
          subtitle="No editing experience needed. Just upload, click, and watch the magic happen."
        />
        
        <div className="mt-16 relative">
          {/* Connection line */}
          <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-cyber-purple via-cyber-cyan to-cyber-pink opacity-30" />
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 relative">
            {steps.map((step, index) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                className="relative"
                data-testid={`step-${step.id}`}
              >
                {/* Step card */}
                <div className="glass-effect rounded-2xl p-6 border border-white/10 hover:border-cyber-purple/50 transition-all duration-300 hover:glow-purple group">
                  {/* Step number with glow */}
                  <motion.div
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    className="relative inline-block mb-4"
                  >
                    <div className="absolute inset-0 bg-gradient-to-br from-cyber-purple to-cyber-cyan blur-xl opacity-50 group-hover:opacity-100 transition-opacity" />
                    <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-cyber-purple to-cyber-cyan flex items-center justify-center">
                      <span className="text-2xl font-bold text-white">{step.number}</span>
                    </div>
                  </motion.div>
                  
                  {/* Icon */}
                  <div className="text-5xl mb-4 group-hover:scale-110 transition-transform duration-300">
                    {step.icon}
                  </div>
                  
                  {/* Title */}
                  <h3 className="text-xl font-bold text-white mb-3 group-hover:text-gradient transition-all duration-300">
                    {step.title}
                  </h3>
                  
                  {/* Description */}
                  <p className="text-gray-400 leading-relaxed">
                    {step.description}
                  </p>
                </div>
                
                {/* Arrow connector (hidden on mobile) */}
                {index < steps.length - 1 && (
                  <div className="hidden lg:block absolute top-1/2 -right-4 transform -translate-y-1/2 z-10">
                    <motion.div
                      animate={{ x: [0, 5, 0] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="text-cyber-cyan text-2xl"
                    >
                      →
                    </motion.div>
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
        
        {/* Bottom stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.5 }}
          className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-8"
        >
          {[
            { value: '< 60s', label: 'Average Edit Time' },
            { value: '10M+', label: 'Views Generated' },
            { value: '50K+', label: 'Creators' },
            { value: '4.9/5', label: 'User Rating' },
          ].map((stat, index) => (
            <motion.div
              key={index}
              whileHover={{ scale: 1.05 }}
              className="text-center"
            >
              <div className="text-4xl md:text-5xl font-bold text-gradient mb-2">
                {stat.value}
              </div>
              <div className="text-gray-400">{stat.label}</div>
            </motion.div>
          ))}
        </motion.div>
      </Container>
    </section>
  );
};

export default HowItWorks;
