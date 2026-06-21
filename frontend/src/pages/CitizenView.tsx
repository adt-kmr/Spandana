import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, X, AlertTriangle } from 'lucide-react';
import IncidentQueue from '../components/IncidentQueue';
import MapLayer from '../components/MapLayer';
import SlaWidget from '../components/SlaWidget';
import CitizenReportForm from '../components/CitizenReportForm';
import DiversionAid from '../components/DiversionAid';
import RouteRainCheck from '../components/RouteRainCheck';
import CitizenSeverityCheck from '../components/CitizenSeverityCheck';
import type { IncidentRow } from '../types';

export default function CitizenView() {
  const [selectedIncident, setSelectedIncident] = useState<IncidentRow | null>(null);
  const [reportOpen, setReportOpen] = useState(false);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') setReportOpen(false); };
    if (reportOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleEsc);
    } else {
      document.body.style.overflow = 'auto';
    }
    return () => {
      document.body.style.overflow = 'auto';
      window.removeEventListener('keydown', handleEsc);
    };
  }, [reportOpen]);

  return (
    <div className="min-h-screen flex flex-col p-4 md:p-8 gap-6 max-w-[1600px] mx-auto w-full">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between brutal-card bg-brutal-green p-6 border-[6px] gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter drop-shadow-[2px_2px_0_rgba(0,0,0,1)] text-white">Citizen Portal</h1>
          <p className="text-xl font-bold mt-2 text-black bg-white inline-block px-2 border-2 border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]">View active incidents and report new ones.</p>
        </div>
        <Link to="/" className="brutal-btn bg-white hover:bg-gray-100 flex items-center justify-center gap-2">
          <ArrowLeft size={20} className="stroke-[3]" /> Gateway
        </Link>
      </div>

      <div className="grid grid-cols-12 gap-6 pb-4">
        {/* Left: Report Form & SLA */}
        <div className="col-span-12 md:col-span-4 lg:col-span-3 flex flex-col gap-6 min-h-[500px] lg:min-h-0">
          <button
            onClick={() => setReportOpen(true)}
            className="brutal-card border-[6px] bg-brutal-blue p-6 text-left flex items-center justify-between gap-4 hover:bg-brutal-yellow transition-colors group shrink-0"
          >
            <div>
              <h2 className="text-2xl font-black uppercase text-white group-hover:text-black">Report an Incident</h2>
              <p className="font-bold text-sm text-white group-hover:text-black mt-1">Tap to open the report form.</p>
            </div>
            <AlertTriangle size={32} className="stroke-[3] text-white group-hover:text-black shrink-0" />
          </button>
           <RouteRainCheck />
           <div className="h-32 shrink-0 brutal-card border-[6px] bg-white p-4">
             <SlaWidget />
           </div>
           <CitizenSeverityCheck />
        </div>

        {/* Middle: Map */}
        <div className="col-span-12 md:col-span-8 lg:col-span-6 flex flex-col gap-6 min-h-[500px] lg:h-[70vh]">
          <div className="flex-1 bg-white border-[6px] border-black rounded-xl shadow-[8px_8px_0_0_rgba(0,0,0,1)] relative overflow-hidden flex flex-col">
             <MapLayer scope="citizen" />
          </div>
          {selectedIncident && (
            <div className="shrink-0">
              <DiversionAid scope="citizen" corridor={selectedIncident.corridor || ''} />
            </div>
          )}
        </div>

        {/* Right: Incident Queue */}
        <div className="col-span-12 lg:col-span-3 brutal-card border-[6px] overflow-hidden flex flex-col p-4 bg-white min-h-[500px] lg:h-[70vh]">
          <h2 className="text-2xl font-black uppercase mb-4 border-b-4 border-black pb-2">Active Feed</h2>
          <div className="flex-1 overflow-y-auto">
            <IncidentQueue scope="citizen" onSelect={setSelectedIncident} />
          </div>
        </div>
      </div>

      {reportOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setReportOpen(false)}
          />
          <div className="brutal-card bg-brutal-bg w-full max-w-2xl z-10 p-6 md:p-8 flex flex-col max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-6 border-b-4 border-black pb-4">
              <h2 className="text-3xl md:text-4xl font-black uppercase tracking-tighter">Report an Incident</h2>
              <button
                onClick={() => setReportOpen(false)}
                className="brutal-btn bg-brutal-pink text-white hover:bg-white hover:text-black p-2"
                aria-label="Close"
              >
                <X size={24} className="stroke-[3]" />
              </button>
            </div>
            <CitizenReportForm />
          </div>
        </div>
      )}
    </div>
  );
}
