import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Activity, Map, Users, AlertTriangle } from 'lucide-react';

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-brutal-bg font-sans selection:bg-black selection:text-white pb-20">
      
      {/* Navigation */}
      <nav className="p-6 border-b-4 border-black bg-white flex justify-between items-center sticky top-0 z-50">
        <div className="text-3xl font-black tracking-tighter">CLEAR.</div>
        <div className="space-x-4">
          <Link to="/citizen" className="font-bold hover:underline decoration-4 underline-offset-4">Citizen Portal</Link>
          <Link to="/operator" className="brutal-btn bg-brutal-yellow inline-flex items-center gap-2">
            Operator Console <ArrowRight size={18} className="stroke-[3]" />
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="max-w-6xl mx-auto px-6 py-20 lg:py-32 grid md:grid-cols-2 gap-12 items-center">
        <div>
          <div className="inline-block px-4 py-2 bg-brutal-green border-4 border-black font-bold uppercase tracking-wider mb-6 rotate-[-2deg] shadow-[4px_4px_0_0_#000]">
            Command Center OS
          </div>
          <h1 className="text-6xl lg:text-8xl font-black leading-none mb-6 tracking-tighter uppercase">
            Anticipate<br/>
            <span className="text-brutal-pink">Congestion</span><br/>
            Before it forms.
          </h1>
          <p className="text-2xl font-medium mb-10 border-l-8 border-black pl-6 py-2 bg-white/50">
            CLEAR is a decision-support module that transforms raw incident reports into actionable dispatch and diversion recommendations.
          </p>
          <div className="flex flex-wrap gap-6">
            <Link to="/operator" className="brutal-btn bg-brutal-blue text-white hover:bg-brutal-blue/90 text-xl inline-flex items-center gap-3">
              Launch Console <Activity size={24} className="stroke-[3]" />
            </Link>
            <Link to="/citizen" className="brutal-btn bg-white hover:bg-gray-100 text-xl inline-flex items-center gap-3">
              Report Incident <AlertTriangle size={24} className="stroke-[3]" />
            </Link>
          </div>
        </div>
        
        <div className="relative">
          <div className="brutal-card bg-brutal-yellow p-8 aspect-square flex flex-col justify-between rotate-[2deg]">
            <div className="flex justify-between items-start">
              <div className="w-16 h-16 rounded-full bg-white border-4 border-black flex items-center justify-center shadow-[4px_4px_0_0_#000]">
                <Map size={32} className="text-black" />
              </div>
              <div className="px-4 py-2 bg-black text-white font-bold rounded-full border-4 border-black">
                System Active
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="h-4 bg-black w-3/4 border-2 border-black rounded-full" />
              <div className="h-4 bg-black w-1/2 border-2 border-black rounded-full" />
              <div className="h-4 bg-black w-5/6 border-2 border-black rounded-full" />
            </div>
            
            <div className="mt-8 p-6 bg-white border-4 border-black rounded-xl">
              <div className="flex justify-between items-center mb-2">
                <span className="font-bold text-lg">Clearance Prediction</span>
                <span className="font-black text-xl text-brutal-pink">P50 45m</span>
              </div>
              <div className="w-full bg-gray-200 h-6 border-2 border-black rounded-full overflow-hidden">
                <div className="bg-brutal-pink w-[45%] h-full border-r-2 border-black" />
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Problem Section */}
      <section className="bg-brutal-pink py-24 border-y-4 border-black mt-12">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-5xl md:text-7xl font-black mb-16 text-center uppercase tracking-tighter text-white drop-shadow-[4px_4px_0_rgba(0,0,0,1)]">
            The Problem
          </h2>
          
          <div className="grid md:grid-cols-2 gap-12">
            <div className="brutal-card bg-white p-8 md:p-12">
              <div className="w-16 h-16 bg-brutal-yellow border-4 border-black rounded-xl mb-8 flex items-center justify-center shadow-[4px_4px_0_0_#000]">
                <AlertTriangle size={32} />
              </div>
              <h3 className="text-3xl font-black mb-6 uppercase">Event-Driven Congestion</h3>
              <p className="text-lg font-medium leading-relaxed">
                Political rallies, festivals, sports events, construction activities, and sudden gatherings create localized traffic breakdowns.
              </p>
            </div>
            
            <div className="brutal-card bg-brutal-yellow p-8 md:p-12">
              <h3 className="text-3xl font-black mb-6 uppercase">Why It's Hard Today</h3>
              <ul className="space-y-4 text-lg font-medium">
                <li className="flex items-start gap-4">
                  <div className="w-8 h-8 bg-black text-white flex items-center justify-center font-bold flex-shrink-0 mt-1 border-2 border-white rounded-full">1</div>
                  <span>Event impact is not quantified in advance.</span>
                </li>
                <li className="flex items-start gap-4">
                  <div className="w-8 h-8 bg-black text-white flex items-center justify-center font-bold flex-shrink-0 mt-1 border-2 border-white rounded-full">2</div>
                  <span>Resource deployment is purely experience-driven.</span>
                </li>
                <li className="flex items-start gap-4">
                  <div className="w-8 h-8 bg-black text-white flex items-center justify-center font-bold flex-shrink-0 mt-1 border-2 border-white rounded-full">3</div>
                  <span>No structured post-event learning system.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Gateway Section */}
      <section className="max-w-6xl mx-auto px-6 py-32 text-center">
        <h2 className="text-6xl font-black mb-12 uppercase tracking-tighter">Enter the System</h2>
        
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          <Link to="/operator" className="group">
            <div className="brutal-card bg-brutal-blue p-12 h-full flex flex-col items-center justify-center hover:bg-brutal-yellow transition-colors">
              <div className="bg-white p-6 border-4 border-black rounded-full mb-8 shadow-[4px_4px_0_0_#000] group-hover:scale-110 transition-transform">
                <Activity size={48} />
              </div>
              <h3 className="text-4xl font-black mb-4 uppercase text-white group-hover:text-black">Operator<br/>Console</h3>
              <p className="font-bold text-lg text-white group-hover:text-black mb-8">Access dispatch logs, AI predictions, and corridor analysis.</p>
              <div className="bg-black text-white px-6 py-2 font-bold uppercase rounded-full">Authorized Personnel</div>
            </div>
          </Link>

          <Link to="/citizen" className="group">
            <div className="brutal-card bg-white p-12 h-full flex flex-col items-center justify-center hover:bg-brutal-green transition-colors">
              <div className="bg-brutal-green group-hover:bg-white p-6 border-4 border-black rounded-full mb-8 shadow-[4px_4px_0_0_#000] group-hover:scale-110 transition-transform">
                <Users size={48} />
              </div>
              <h3 className="text-4xl font-black mb-4 uppercase">Citizen<br/>Portal</h3>
              <p className="font-bold text-lg mb-8">Report incidents directly and view live SLA status.</p>
              <div className="bg-black text-white px-6 py-2 font-bold uppercase rounded-full">Public Access</div>
            </div>
          </Link>
        </div>
      </section>

    </div>
  );
};
