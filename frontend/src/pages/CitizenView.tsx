import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import IncidentQueue from '../components/IncidentQueue';
import MapLayer from '../components/MapLayer';
import SlaWidget from '../components/SlaWidget';
import CitizenReportForm from '../components/CitizenReportForm';
import DiversionAid from '../components/DiversionAid';
import RouteRainCheck from '../components/RouteRainCheck';
import type { IncidentRow } from '../types';

export default function CitizenView() {
  const [selectedIncident, setSelectedIncident] = useState<IncidentRow | null>(null);

  return (
    <div className="min-h-screen lg:h-[100dvh] lg:overflow-hidden flex flex-col p-4 md:p-8 gap-6 max-w-[1600px] mx-auto w-full">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between brutal-card bg-brutal-green p-6 border-[6px] gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter drop-shadow-[2px_2px_0_rgba(0,0,0,1)] text-white">Citizen Portal</h1>
          <p className="text-xl font-bold mt-2 text-black bg-white inline-block px-2 border-2 border-black shadow-[2px_2px_0_0_rgba(0,0,0,1)]">View active incidents and report new ones.</p>
        </div>
        <Link to="/" className="brutal-btn bg-white hover:bg-gray-100 flex items-center justify-center gap-2">
          <ArrowLeft size={20} className="stroke-[3]" /> Gateway
        </Link>
      </div>

      <div className="grid grid-cols-12 gap-6 flex-1 min-h-0 overflow-y-auto lg:overflow-hidden pb-4 lg:pb-0">
        {/* Left: Report Form & SLA */}
        <div className="col-span-12 md:col-span-4 lg:col-span-3 flex flex-col gap-6 min-h-[500px] lg:min-h-0">
           <div className="brutal-card border-[6px] bg-brutal-blue p-4 flex-1 flex flex-col overflow-hidden">
             <h2 className="text-2xl font-black uppercase mb-4 border-b-4 border-black pb-2 text-white">Report</h2>
             <div className="bg-white border-4 border-black p-4 rounded-lg flex-1 overflow-y-auto shadow-[4px_4px_0_0_rgba(0,0,0,1)]">
               <CitizenReportForm />
             </div>
           </div>
           <RouteRainCheck />
           <div className="h-32 shrink-0 brutal-card border-[6px] bg-white p-4">
             <SlaWidget />
           </div>
        </div>

        {/* Middle: Map */}
        <div className="col-span-12 md:col-span-8 lg:col-span-6 flex flex-col gap-6 min-h-[500px] lg:min-h-0">
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
        <div className="col-span-12 lg:col-span-3 brutal-card border-[6px] overflow-hidden flex flex-col p-4 bg-white min-h-[500px] lg:min-h-0">
          <h2 className="text-2xl font-black uppercase mb-4 border-b-4 border-black pb-2">Active Feed</h2>
          <div className="flex-1 overflow-y-auto">
            <IncidentQueue scope="citizen" onSelect={setSelectedIncident} />
          </div>
        </div>
      </div>
    </div>
  );
}
