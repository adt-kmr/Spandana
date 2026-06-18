import IncidentQueue from '../components/IncidentQueue';
import MapLayer from '../components/MapLayer';
import SlaWidget from '../components/SlaWidget';
import CitizenReportForm from '../components/CitizenReportForm';

export default function CitizenView() {
  return (
    <div className="h-full flex flex-col gap-4 max-w-[1200px] mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Citizen Portal</h1>
          <p className="text-slate-500 text-sm">View active incidents and report new ones.</p>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4 flex-1 min-h-0">
        {/* Left: Report Form & SLA */}
        <div className="col-span-12 md:col-span-4 lg:col-span-3 flex flex-col gap-4 min-h-0">
           <CitizenReportForm />
           <div className="h-32 shrink-0">
             <SlaWidget />
           </div>
        </div>

        {/* Middle: Map */}
        <div className="col-span-12 md:col-span-8 lg:col-span-6 flex flex-col min-h-0">
          <div className="flex-1 min-h-0 relative">
             <MapLayer scope="citizen" />
          </div>
        </div>

        {/* Right: Incident Queue */}
        <div className="col-span-12 lg:col-span-3 bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col min-h-[400px]">
          <IncidentQueue scope="citizen" />
        </div>
      </div>
    </div>
  );
}
