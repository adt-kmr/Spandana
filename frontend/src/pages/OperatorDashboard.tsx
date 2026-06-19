import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, BarChart3, LogOut } from 'lucide-react';
import { clearOperatorToken } from '../auth';
import IncidentQueue from '../components/IncidentQueue';
import IncidentDetails from '../components/IncidentDetails';
import MapLayer from '../components/MapLayer';
import DispatchPanel from '../components/DispatchPanel';
import type { IncidentRow } from '../types';

export default function OperatorDashboard() {
  const [selectedIncident, setSelectedIncident] = useState<IncidentRow | undefined>();
  const navigate = useNavigate();

  const handleLogout = () => {
    clearOperatorToken();
    navigate('/operator/login');
  };

  return (
    <div className="min-h-screen lg:h-[100dvh] lg:overflow-hidden flex flex-col p-4 md:p-8 gap-6 max-w-[1600px] mx-auto w-full">
      <div className="flex flex-col md:flex-row md:items-center justify-between brutal-card bg-brutal-yellow p-6 border-[6px] gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter drop-shadow-[2px_2px_0_rgba(0,0,0,1)]">Operator Console</h1>
          <p className="text-xl font-bold mt-2">Real-time incident triage and dispatch support.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-4">
          <Link to="/operator/stats" className="brutal-btn bg-brutal-blue text-white hover:opacity-90 flex items-center justify-center gap-2">
            <BarChart3 size={20} className="stroke-[3]" /> Dashboard Stats
          </Link>
          <Link to="/" className="brutal-btn bg-white hover:bg-gray-100 flex items-center justify-center gap-2">
            <ArrowLeft size={20} className="stroke-[3]" /> Gateway
          </Link>
          <button onClick={handleLogout} className="brutal-btn bg-brutal-pink text-white hover:opacity-90 flex items-center justify-center gap-2">
            <LogOut size={20} className="stroke-[3]" /> Log out
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6 flex-1 min-h-0 overflow-y-auto lg:overflow-hidden pb-4 lg:pb-0">
        {/* Left Column: Queue */}
        <div className="col-span-12 lg:col-span-3 brutal-card border-[6px] overflow-hidden flex flex-col p-4 bg-white min-h-[500px] lg:min-h-0">
          <h2 className="text-2xl font-black uppercase mb-4 border-b-4 border-black pb-2">Incident Queue</h2>
          <div className="flex-1 overflow-y-auto">
            <IncidentQueue scope="operator" onSelect={setSelectedIncident} />
          </div>
        </div>

        {/* Middle Column: Map & Selected Details */}
        <div className="col-span-12 lg:col-span-6 flex flex-col gap-6 min-h-[600px] lg:min-h-0">
          {/* Map Blur Fix: explicitly applying styles without transition-transform/hover effects */}
          <div className="flex-1 bg-white border-black border-[6px] rounded-xl shadow-[8px_8px_0_0_rgba(0,0,0,1)] relative overflow-hidden flex flex-col">
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

        {/* Right Column: Dispatch */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-6 min-h-[500px] lg:min-h-0">
          <div className="flex-1 brutal-card border-[6px] bg-brutal-green p-4 flex flex-col overflow-hidden">
             <h2 className="text-xl font-black uppercase mb-2">Dispatch</h2>
             <div className="flex-1 bg-white border-4 border-black rounded-lg p-2 overflow-y-auto">
               <DispatchPanel incident={selectedIncident} />
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
