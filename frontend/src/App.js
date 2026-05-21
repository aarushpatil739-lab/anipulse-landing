import React, { useEffect } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/sections/Navbar';
import Hero from './components/sections/Hero';
import Features from './components/sections/Features';
import HowItWorks from './components/sections/HowItWorks';
import DemoPreview from './components/sections/DemoPreview';
import CTA from './components/sections/CTA';
import Footer from './components/sections/Footer';
import Upload from './pages/Upload';

// Home page component
const HomePage = () => (
  <>
    <Hero />
    <Features />
    <HowItWorks />
    <DemoPreview />
    <CTA />
  </>
);

function App() {
  useEffect(() => {
    // Smooth scroll behavior
    document.documentElement.style.scrollBehavior = 'smooth';
    
    // Set dark theme
    document.documentElement.classList.add('dark');
  }, []);
  
  return (
    <BrowserRouter>
      <div className="App min-h-screen bg-cyber-darker overflow-x-hidden">
        <Routes>
          <Route path="/" element={
            <>
              <Navbar />
              <main>
                <HomePage />
              </main>
              <Footer />
            </>
          } />
          <Route path="/upload" element={<Upload />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
