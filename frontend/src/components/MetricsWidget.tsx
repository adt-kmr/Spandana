import { useQuery } from '@tanstack/react-query';
import { ClearApi } from '../api';
import { BarChart3 } from 'lucide-react';

export default function MetricsWidget() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['metrics'],
    queryFn: () => ClearApi.metrics(),
  });

  if (isLoading) return <div className="animate-pulse bg-white p-4 rounded-xl border border-slate-200 h-32" />;

  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col h-full">
      <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 mb-3">
        <BarChart3 className="w-4 h-4 text-purple-500" />
        System Metrics
      </h3>
      
      {isError ? (
        <div className="text-red-500 text-sm">Failed to load metrics.</div>
      ) : (
        <div className="flex-1 overflow-auto text-sm space-y-3">
           <div>
             <span className="text-slate-500 block mb-1">Clearance Error (MAE)</span>
             {data?.clearance_error && typeof data.clearance_error === 'object' ? (
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(data.clearance_error).map(([k,v]) => (
                    <div key={k} className="bg-slate-50 p-1.5 rounded border border-slate-100 flex justify-between">
                      <span className="text-xs text-slate-500 capitalize">{k}</span>
                      <span className="font-semibold">{String(v)}</span>
                    </div>
                  ))}
                </div>
             ) : (
                <div className="text-slate-700 font-medium">{String(data?.clearance_error ?? '—')}</div>
             )}
           </div>

           {data?.history && data.history.length > 0 && (
             <div>
               <span className="text-slate-500 block mb-1">Recent Updates</span>
               <div className="space-y-1">
                 {data.history.slice(0, 3).map((h, i) => (
                   <div key={i} className="flex justify-between text-xs bg-slate-50 p-1.5 rounded">
                     <span className="font-medium text-slate-700">{h.model} ({h.metric})</span>
                     <span className="text-slate-600">{h.value}</span>
                   </div>
                 ))}
               </div>
             </div>
           )}
        </div>
      )}
    </div>
  );
}
