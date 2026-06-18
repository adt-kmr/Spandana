import Navbar from './components/Navbar';
import Hero from './sections/Hero';
import Problem from './sections/Problem';
import Vision from './sections/Vision';
import WhyThisMatters from './sections/WhyThisMatters';
import IntelligenceEngine from './sections/IntelligenceEngine';
import Architecture from './sections/Architecture';
import WhatWeLearned from './sections/WhatWeLearned';
import LookingAhead from './sections/LookingAhead';
import About from './sections/About';
import Footer from './sections/Footer';

export default function App() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <hr className="section-divider" />
        <Problem />
        <hr className="section-divider" />
        <Vision />
        <hr className="section-divider" />
        <WhyThisMatters />
        <hr className="section-divider" />
        <IntelligenceEngine />
        <hr className="section-divider" />
        <Architecture />
        <hr className="section-divider" />
        <WhatWeLearned />
        <LookingAhead />
        <hr className="section-divider" />
        <About />
      </main>
      <Footer />
    </>
  );
}

