import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Activity, Users, AlertTriangle, X, ExternalLink } from 'lucide-react';

import heroImg from '../assets/traffic-hero.png';
import secondaryImg from '../assets/traffic-secondary.png';

const TEAM = [
  { name: "Jaiveer Singh",     linkedin: "https://www.linkedin.com/in/jaiveersingh2007/" },
  { name: "Harkamal Singh",    linkedin: "https://www.linkedin.com/in/harkamal-singh-3b85b1316/" },
  { name: "Aditya (Thetsu)",   linkedin: "https://www.linkedin.com/in/thetsu-aditya/" },
  { name: "Dhruv Srivastava",  linkedin: "https://www.linkedin.com/in/dhruv-srivas-tava/" },
];

export const LandingPage: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsModalOpen(false);
    };
    if (isModalOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleEsc);
    } else {
      document.body.style.overflow = 'auto';
    }
    return () => {
      document.body.style.overflow = 'auto';
      window.removeEventListener('keydown', handleEsc);
    };
  }, [isModalOpen]);

  return (
    <div className="min-h-screen bg-brutal-bg font-sans selection:bg-black selection:text-white pb-20 overflow-x-hidden">
      
      {/* Navigation - sticky as requested */}
      <nav className="p-6 border-b-4 border-black bg-white flex justify-between items-center sticky top-0 z-50">
        <div className="text-3xl font-black tracking-tighter">CLEAR.</div>
        <div className="space-x-4 flex items-center">
          <Link to="/citizen" className="font-bold hover:underline decoration-4 underline-offset-4 hidden sm:block">Citizen Portal</Link>
          <Link to="/operator" className="brutal-btn bg-brutal-yellow inline-flex items-center gap-2 py-2 px-4">
            Operator Console <ArrowRight size={18} className="stroke-[3]" />
          </Link>
        </div>
      </nav>

      {/* 1) HERO — THE PROBLEM */}
      <section 
        className="relative flex items-center justify-center min-h-[80vh] border-b-8 border-black overflow-hidden"
      >
        {/* Background Image with overlay */}
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${heroImg})` }}
        />
        <div className="absolute inset-0 bg-brutal-yellow/80 mix-blend-multiply" />
        <div className="absolute inset-0 bg-black/40" />

        <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-black uppercase tracking-tighter text-white drop-shadow-[4px_4px_0_rgba(0,0,0,1)] mb-8">
            Event-Driven Congestion Forms Faster Than Authorities Can React.
          </h1>
          <p className="text-xl md:text-3xl font-bold text-white bg-black inline-block px-4 py-2 border-4 border-white shadow-[8px_8px_0_0_#000]">
            Bengaluru traffic breaks down in minutes.
          </p>
        </div>
      </section>

      {/* 2) WHY IT'S HARD */}
      <section className="relative py-24 border-b-8 border-black">
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${secondaryImg})` }}
        />
        <div className="absolute inset-0 bg-black/80" />

        <div className="relative z-10 max-w-6xl mx-auto px-6">
          <h2 className="text-5xl md:text-7xl font-black mb-16 text-center uppercase tracking-tighter text-brutal-yellow drop-shadow-[4px_4px_0_rgba(0,0,0,1)]">
            Why It's Hard Today
          </h2>
          
          <div className="grid md:grid-cols-3 gap-8">
            <div className="brutal-card bg-white p-8">
              <div className="w-16 h-16 bg-brutal-pink border-4 border-black rounded-full mb-8 flex items-center justify-center shadow-[4px_4px_0_0_#000] text-3xl font-black text-white">1</div>
              <p className="text-xl font-bold leading-relaxed uppercase">
                Event impact is not quantified in advance.
              </p>
            </div>
            
            <div className="brutal-card bg-white p-8">
              <div className="w-16 h-16 bg-brutal-pink border-4 border-black rounded-full mb-8 flex items-center justify-center shadow-[4px_4px_0_0_#000] text-3xl font-black text-white">2</div>
              <p className="text-xl font-bold leading-relaxed uppercase">
                Resource deployment is purely experience-driven.
              </p>
            </div>

            <div className="brutal-card bg-white p-8">
              <div className="w-16 h-16 bg-brutal-pink border-4 border-black rounded-full mb-8 flex items-center justify-center shadow-[4px_4px_0_0_#000] text-3xl font-black text-white">3</div>
              <p className="text-xl font-bold leading-relaxed uppercase">
                No structured post-event learning system.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 3) HOW WE SOLVE IT */}
      <section className="py-24 bg-brutal-bg border-b-8 border-black">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-5xl md:text-7xl font-black mb-16 text-center uppercase tracking-tighter text-black drop-shadow-[4px_4px_0_#ffdc00]">
            The CLEAR Approach
          </h2>
          
          <div className="max-w-4xl mx-auto mb-16 text-center">
            <p className="text-2xl font-bold border-4 border-black p-6 bg-white shadow-[8px_8px_0_0_#000]">
              CLEAR is a decision-support engine that turns raw incident reports into ranked, confidence-aware recommendations. We advise—human operators confirm.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="brutal-card bg-brutal-green p-6 text-white flex flex-col items-center text-center">
              <Activity className="w-12 h-12 mb-4 border-2 border-white rounded-full p-2 bg-black" />
              <h3 className="text-xl font-black uppercase mb-2">Clearance Time</h3>
              <p className="font-bold text-sm">Prediction with P10–P90 confidence ranges.</p>
            </div>
            <div className="brutal-card bg-brutal-pink p-6 text-white flex flex-col items-center text-center">
              <AlertTriangle className="w-12 h-12 mb-4 border-2 border-white rounded-full p-2 bg-black" />
              <h3 className="text-xl font-black uppercase mb-2">Severity Scoring</h3>
              <p className="font-bold text-sm">Algorithmically rank active incidents.</p>
            </div>
            <div className="brutal-card bg-brutal-blue p-6 text-white flex flex-col items-center text-center">
              <Activity className="w-12 h-12 mb-4 border-2 border-white rounded-full p-2 bg-black" />
              <h3 className="text-xl font-black uppercase mb-2">Risk Nowcast</h3>
              <p className="font-bold text-sm">3-hour forward looking corridor risk analysis.</p>
            </div>
            <div className="brutal-card bg-brutal-yellow p-6 text-black flex flex-col items-center text-center">
              <AlertTriangle className="w-12 h-12 mb-4 border-2 border-black rounded-full p-2 bg-white" />
              <h3 className="text-xl font-black uppercase mb-2">Hotspots</h3>
              <p className="font-bold text-sm">Real-time geographical cluster detection.</p>
            </div>
          </div>
        </div>
      </section>

      {/* 4) ENTER THE SYSTEM */}
      <section className="py-32 bg-white">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <h2 className="text-6xl md:text-8xl font-black mb-16 uppercase tracking-tighter drop-shadow-[4px_4px_0_#ffdc00]">
            Enter the System
          </h2>
          
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <Link to="/operator" className="group">
              <div className="brutal-card bg-brutal-blue p-12 h-full flex flex-col items-center justify-center hover:bg-brutal-yellow transition-colors">
                <div className="bg-white p-6 border-4 border-black rounded-full mb-8 shadow-[4px_4px_0_0_#000] group-hover:scale-110 transition-transform">
                  <Activity size={48} className="text-black" />
                </div>
                <h3 className="text-4xl font-black mb-4 uppercase text-white group-hover:text-black">Operator<br/>Console</h3>
                <div className="bg-black text-white px-6 py-2 font-bold uppercase rounded-full mt-auto">Requires Access Code</div>
              </div>
            </Link>

            <Link to="/citizen" className="group">
              <div className="brutal-card bg-brutal-green p-12 h-full flex flex-col items-center justify-center hover:bg-brutal-yellow transition-colors">
                <div className="bg-white p-6 border-4 border-black rounded-full mb-8 shadow-[4px_4px_0_0_#000] group-hover:scale-110 transition-transform">
                  <Users size={48} className="text-black" />
                </div>
                <h3 className="text-4xl font-black mb-4 uppercase text-white group-hover:text-black">Citizen<br/>Portal</h3>
                <div className="bg-black text-white px-6 py-2 font-bold uppercase rounded-full mt-auto">Public Access</div>
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t-8 border-black bg-brutal-yellow py-12">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="text-4xl font-black tracking-tighter">CLEAR.</div>
          <div className="flex gap-8">
            <button 
              onClick={() => setIsModalOpen(true)} 
              className="font-bold text-xl hover:underline decoration-4 underline-offset-4 uppercase bg-transparent border-none cursor-pointer p-0"
            >
              Contact Us
            </button>
          </div>
        </div>
      </footer>

      {/* TEAM OVERLAY MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-black/70 backdrop-blur-sm" 
            onClick={() => setIsModalOpen(false)}
          />
          <div className="brutal-card bg-brutal-bg w-full max-w-3xl z-10 p-6 md:p-8 flex flex-col max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-8 border-b-4 border-black pb-4">
              <h2 className="text-3xl md:text-5xl font-black uppercase tracking-tighter">Meet The Team</h2>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="brutal-btn bg-brutal-pink text-white hover:bg-white hover:text-black p-2"
                aria-label="Close"
              >
                <X size={24} className="stroke-[3]" />
              </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              {TEAM.map((member) => (
                <div key={member.name} className="brutal-card bg-white p-6 flex flex-col gap-4">
                  <h3 className="text-2xl font-black uppercase">{member.name}</h3>
                  <div className="mt-auto pt-4">
                    <a 
                      href={member.linkedin} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="brutal-btn bg-brutal-blue text-white hover:opacity-90 inline-flex items-center gap-2 py-2 px-4 w-full justify-center"
                    >
                      <ExternalLink size={20} /> LinkedIn
                    </a>
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t-4 border-black pt-6 text-center">
              <span className="brutal-badge bg-brutal-yellow text-black text-lg md:text-xl block py-3">
                Thapar Institute of Engineering and Technology
              </span>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
