import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import IncidentQueue from '../components/IncidentQueue';
import IncidentDetails from '../components/IncidentDetails';
import MapLayer from '../components/MapLayer';
import DispatchPanel from '../components/DispatchPanel';
import SlaWidget from '../components/SlaWidget';
import MetricsWidget from '../components/MetricsWidget';
import type { IncidentRow } from '../types';

export default function OperatorDashboard() {
  const [selectedIncident, setSelectedIncident] = useState<IncidentRow | undefined>();

  return (
    <div className="min-h-screen flex flex-col p-4 md:p-8 gap-6 max-w-[1600px] mx-auto w-full">
      <div className="flex items-center justify-between brutal-card bg-brutal-yellow p-6 border-[6px]">
        <div>
          <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter drop-shadow-[2px_2px_0_rgba(0,0,0,1)]">Operator Console</h1>
          <p className="text-xl font-bold mt-2">Real-time incident triage and dispatch support.</p>
        </div>
        <Link to="/" className="brutal-btn bg-white hover:bg-gray-100 flex items-center gap-2">
          <ArrowLeft size={20} className="stroke-[3]" /> Gateway
        </Link>
      </div>

      <div className="grid grid-cols-12 gap-6 flex-1 min-h-[800px]">
        {/* Left Column: Queue */}
        <div className="col-span-12 lg:col-span-3 brutal-card border-[6px] overflow-hidden flex flex-col p-4 bg-white">
          <h2 className="text-2xl font-black uppercase mb-4 border-b-4 border-black pb-2">Incident Queue</h2>
          <div className="flex-1 overflow-y-auto">
            <IncidentQueue scope="operator" onSelect={setSelectedIncident} />
          </div>
        </div>

        {/* Middle Column: Map & Selected Details */}
        <div className="col-span-12 lg:col-span-6 flex flex-col gap-6 min-h-0">
          <div className="flex-1 brutal-card border-[6px] relative overflow-hidden bg-white">
             <MapLayer scope="operator" />
          </div>
          
          <div className="h-64 shrink-0 brutal-card border-[6px] bg-brutal-blue p-4 flex flex-col">
            <h2 className="text-xl text-white font-black uppercase mb-2">Analysis</h2>
            <div className="flex-1 bg-white border-4 border-black rounded-lg overflow-hidden p-2">
              {selectedIncident ? (
                <IncidentDetails incident={selectedIncident} />
              ) : (
                <div className="h-full flex items-center justify-center text-lg font-bold">
                  Select an incident from the queue.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Dispatch & Metrics */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-6 min-h-0">
          <div className="flex-1 brutal-card border-[6px] bg-brutal-green p-4 flex flex-col">
             <h2 className="text-xl font-black uppercase mb-2">Dispatch</h2>
             <div className="flex-1 bg-white border-4 border-black rounded-lg p-2 overflow-y-auto">
               <DispatchPanel incident={selectedIncident} />
             </div>
          </div>
          
          <div className="h-32 shrink-0 brutal-card border-[6px] bg-white p-4">
             <SlaWidget />
          </div>

          <div className="h-40 shrink-0 brutal-card border-[6px] bg-white p-4">
             <MetricsWidget />
          </div>
        </div>
      </div>
    </div>
  );
}
