import React from 'react';
import { motion } from 'framer-motion';
import { Container } from '../ui/Container';
import { navigation, socialLinks } from '../../lib/content';

const Footer = () => {
  const scrollToSection = (href) => {
    const element = document.querySelector(href);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };
  
  return (
    <footer className="relative py-16 border-t border-white/10" data-testid="footer">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-t from-cyber-purple/5 to-transparent" />
      
      <Container className="relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
          {/* Brand Column */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyber-purple to-cyber-cyan flex items-center justify-center font-bold text-white text-xl glow-purple">
                A
              </div>
              <span className="text-2xl font-bold text-white">
                Ani<span className="text-gradient">Pulse</span>
              </span>
            </div>
            <p className="text-gray-400 mb-6 max-w-md">
              AI-powered anime video editing that pulses with creativity. 
              Turn your clips into viral masterpieces in seconds.
            </p>
            
            {/* Social Links */}
            <div className="flex gap-4">
              {socialLinks.map((social) => (
                <motion.a
                  key={social.name}
                  href={social.href}
                  whileHover={{ scale: 1.1, y: -2 }}
                  whileTap={{ scale: 0.95 }}
                  className="w-10 h-10 rounded-lg glass-effect border border-white/10 hover:border-cyber-purple/50 flex items-center justify-center text-lg hover:glow-purple transition-all duration-300"
                  aria-label={social.name}
                  data-testid={`social-${social.name.toLowerCase()}`}
                >
                  {social.icon}
                </motion.a>
              ))}
            </div>
          </div>
          
          {/* Quick Links */}
          <div>
            <h3 className="text-white font-bold mb-4">Quick Links</h3>
            <ul className="space-y-3">
              {navigation.map((item) => (
                <li key={item.name}>
                  <button
                    onClick={() => scrollToSection(item.href)}
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    {item.name}
                  </button>
                </li>
              ))}
              <li>
                <button className="text-gray-400 hover:text-white transition-colors">
                  Pricing
                </button>
              </li>
            </ul>
          </div>
          
          {/* Resources */}
          <div>
            <h3 className="text-white font-bold mb-4">Resources</h3>
            <ul className="space-y-3">
              {['Documentation', 'Tutorials', 'Blog', 'Support', 'API'].map((item) => (
                <li key={item}>
                  <a
                    href="#"
                    className="text-gray-400 hover:text-white transition-colors"
                  >
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
        
        {/* Bottom Bar */}
        <div className="pt-8 border-t border-white/10">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-gray-400 text-sm">
              © {new Date().getFullYear()} AniPulse. All rights reserved.
            </p>
            
            <div className="flex gap-6 text-sm">
              {['Privacy Policy', 'Terms of Service', 'Cookie Policy'].map((item) => (
                <a
                  key={item}
                  href="#"
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  {item}
                </a>
              ))}
            </div>
          </div>
        </div>
        
        {/* Decorative elements */}
        <motion.div
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 4, repeat: Infinity }}
          className="absolute top-0 right-0 w-64 h-64 bg-cyber-purple/10 rounded-full blur-[100px] pointer-events-none"
        />
      </Container>
    </footer>
  );
};

export default Footer;
