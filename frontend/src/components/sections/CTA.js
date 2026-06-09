import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/Button';
import { Container } from '../ui/Container';
import { ctaContent } from '../../lib/content';

const CTA = () => {
  const navigate = useNavigate();
  return (
    <section className="py-24 relative overflow-hidden" data-testid="cta-section">
      {/* Dramatic background */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-b from-cyber-darker via-cyber-purple/10 to-cyber-darker" />
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{ duration: 8, repeat: Infinity }}
          className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-r from-cyber-purple to-cyber-cyan rounded-full blur-[200px]"
        />
      </div>
      
      <Container className="relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center space-y-8"
        >
          {/* Main CTA text */}
          <div>
            <h2 className="text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-4">
              {ctaContent.title}{' '}
              <span className="text-gradient">{ctaContent.titleHighlight}</span>
              <motion.span
                animate={{ opacity: [1, 0.5, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="inline-block ml-2"
              >
                ?
              </motion.span>
            </h2>
            
            <p className="text-xl md:text-2xl text-gray-300 max-w-3xl mx-auto">
              {ctaContent.subtitle}
            </p>
          </div>
          
          {/* Large CTA button */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <Button 
              variant="primary" 
              size="lg" 
              className="text-xl px-16 py-6 group"
              data-testid="cta-final"
              onClick={() => navigate('/upload')}
            >
              <span className="mr-2">{ctaContent.buttonText}</span>
              <motion.span
                animate={{ x: [0, 5, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                →
              </motion.span>
            </Button>
          </motion.div>
          
          {/* Social proof */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.4 }}
            className="flex flex-col items-center gap-4"
          >
            <div className="flex items-center gap-2">
              {[...Array(5)].map((_, i) => (
                <motion.span
                  key={i}
                  initial={{ opacity: 0, scale: 0 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.5 + i * 0.1 }}
                  className="text-yellow-400 text-2xl"
                >
                  ★
                </motion.span>
              ))}
            </div>
            <p className="text-gray-400">
              Join <span className="text-cyber-cyan font-semibold">50,000+ creators</span> making viral content
            </p>
          </motion.div>
          
          {/* Feature highlights */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.6 }}
            className="flex flex-wrap justify-center gap-6 pt-8"
          >
            {[
              { icon: '✔️', text: 'No credit card required' },
              { icon: '⚡', text: 'Generate in seconds' },
              { icon: '🔒', text: 'Your content stays yours' },
            ].map((item, index) => (
              <div key={index} className="flex items-center gap-2 text-gray-300">
                <span className="text-cyber-cyan">{item.icon}</span>
                <span>{item.text}</span>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </Container>
    </section>
  );
};

export default CTA;
