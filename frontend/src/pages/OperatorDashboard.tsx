import { useState } from 'react';
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
    <div className="h-full flex flex-col gap-4 max-w-[1600px] mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Operator Console</h1>
          <p className="text-slate-500 text-sm">Real-time incident triage and dispatch support.</p>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4 flex-1 min-h-0">
        {/* Left Column: Queue */}
        <div className="col-span-12 lg:col-span-3 bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col">
          <IncidentQueue scope="operator" onSelect={setSelectedIncident} />
        </div>

        {/* Middle Column: Map & Selected Details */}
        <div className="col-span-12 lg:col-span-6 flex flex-col gap-4 min-h-0">
          <div className="flex-1 min-h-0 relative">
             <MapLayer scope="operator" />
          </div>
          
          <div className="h-64 shrink-0">
            {selectedIncident ? (
              <IncidentDetails incident={selectedIncident} />
            ) : (
              <div className="h-full bg-white rounded-xl border border-slate-200 shadow-sm flex items-center justify-center text-slate-500">
                Select an incident from the queue to view analysis.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Dispatch & Metrics */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-4 min-h-0">
          <div className="flex-1 min-h-0">
            <DispatchPanel incident={selectedIncident} />
          </div>
          
          <div className="h-32 shrink-0">
             <SlaWidget />
          </div>

          <div className="h-40 shrink-0">
             <MetricsWidget />
          </div>
        </div>
      </div>
    </div>
  );
}
