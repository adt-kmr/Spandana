import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import IncidentQueue from '../components/IncidentQueue';
import MapLayer from '../components/MapLayer';
import SlaWidget from '../components/SlaWidget';
import CitizenReportForm from '../components/CitizenReportForm';

export default function CitizenView() {
  return (
    <div className="min-h-screen flex flex-col p-4 md:p-8 gap-6 max-w-[1600px] mx-auto w-full">
      <div className="flex items-center justify-between brutal-card bg-brutal-green p-6 border-[6px]">
        <div>
          <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter drop-shadow-[2px_2px_0_rgba(0,0,0,1)] text-white">Citizen Portal</h1>
          <p className="text-xl font-bold mt-2 text-black bg-white inline-block px-2 border-2 border-black">View active incidents and report new ones.</p>
        </div>
        <Link to="/" className="brutal-btn bg-white hover:bg-gray-100 flex items-center gap-2">
          <ArrowLeft size={20} className="stroke-[3]" /> Gateway
        </Link>
      </div>

      <div className="grid grid-cols-12 gap-6 flex-1 min-h-[800px]">
        {/* Left: Report Form & SLA */}
        <div className="col-span-12 md:col-span-4 lg:col-span-3 flex flex-col gap-6 min-h-0">
           <div className="brutal-card border-[6px] bg-brutal-blue p-4 flex-1">
             <h2 className="text-2xl font-black uppercase mb-4 border-b-4 border-black pb-2 text-white">Report</h2>
             <div className="bg-white border-4 border-black p-4 rounded-lg">
               <CitizenReportForm />
             </div>
           </div>
           <div className="h-32 shrink-0 brutal-card border-[6px] bg-white p-4">
             <SlaWidget />
           </div>
        </div>

        {/* Middle: Map */}
        <div className="col-span-12 md:col-span-8 lg:col-span-6 flex flex-col min-h-0">
          <div className="flex-1 brutal-card border-[6px] relative overflow-hidden bg-white">
             <MapLayer scope="citizen" />
          </div>
        </div>

        {/* Right: Incident Queue */}
        <div className="col-span-12 lg:col-span-3 brutal-card border-[6px] overflow-hidden flex flex-col p-4 bg-white min-h-[400px]">
          <h2 className="text-2xl font-black uppercase mb-4 border-b-4 border-black pb-2">Active Feed</h2>
          <div className="flex-1 overflow-y-auto">
            <IncidentQueue scope="citizen" />
          </div>
        </div>
      </div>
    </div>
  );
}
