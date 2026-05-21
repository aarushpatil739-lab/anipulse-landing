import React, { useEffect } from 'react';
import './App.css';
import Navbar from './components/sections/Navbar';
import Hero from './components/sections/Hero';
import Features from './components/sections/Features';
import HowItWorks from './components/sections/HowItWorks';
import DemoPreview from './components/sections/DemoPreview';
import CTA from './components/sections/CTA';
import Footer from './components/sections/Footer';

function App() {
  useEffect(() => {
    // Smooth scroll behavior
    document.documentElement.style.scrollBehavior = 'smooth';
    
    // Set dark theme
    document.documentElement.classList.add('dark');
  }, []);
  
  return (
    <div className="App min-h-screen bg-cyber-darker overflow-x-hidden">
      <Navbar />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <DemoPreview />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}

export default App;
