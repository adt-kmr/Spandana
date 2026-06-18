import { useQuery } from '@tanstack/react-query';
import { ClearApi } from '../api';
import { AlertTriangle, Clock, MapPin, CheckCircle2 } from 'lucide-react';
import type { IncidentRow } from '../types';

export default function IncidentQueue({ scope, onSelect }: { scope: 'operator' | 'citizen', onSelect?: (incident: IncidentRow) => void }) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['incidents', scope],
    queryFn: () => ClearApi.incidents(100, scope),
  });

  if (isLoading) return <div className="p-8 text-center text-slate-500 animate-pulse">Loading incidents...</div>;
  
  if (isError) {
    return (
      <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">
        <div className="font-semibold flex items-center gap-2"><AlertTriangle className="w-5 h-5"/> Failed to load queue</div>
        <div className="text-sm mt-1">{error instanceof Error ? error.message : 'Unknown error'}</div>
      </div>
    );
  }

  const incidents = data?.incidents || [];

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b border-slate-200 bg-white sticky top-0 z-10">
        <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          Active Incident Queue
        </h2>
        <span className="text-sm text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full font-medium">
          {data?.count || 0} Total
        </span>
      </div>

      <div className="overflow-y-auto flex-1 p-2 space-y-2">
        {incidents.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No incidents reported.</div>
        ) : (
          incidents.map((inc) => (
            <button
              key={inc.event_id}
              onClick={() => onSelect?.(inc)}
              className="w-full text-left bg-white p-4 rounded-xl border border-slate-200 shadow-sm hover:border-blue-400 hover:shadow-md transition-all focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wide
                    ${inc.priority === 'critical' ? 'bg-red-100 text-red-700' : 
                      inc.priority === 'high' ? 'bg-amber-100 text-amber-700' :
                      inc.priority === 'medium' ? 'bg-blue-100 text-blue-700' : 
                      'bg-slate-100 text-slate-700'}`}>
                    {inc.priority || 'UNKNOWN'}
                  </span>
                  <span className="text-sm font-semibold text-slate-700 capitalize">
                    {inc.event_cause?.replace('_', ' ') || 'Unknown Cause'}
                  </span>
                </div>
                <div className="text-xs text-slate-400">
                  {inc.start_ist ? new Date(inc.start_ist).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                </div>
              </div>
              
              <div className="flex items-center gap-1.5 text-sm text-slate-600 mb-3">
                <MapPin className="w-4 h-4 text-slate-400 shrink-0" />
                <span className="truncate">{inc.corridor || 'Unknown Location'}</span>
              </div>

              <div className="flex items-center justify-between text-xs font-medium">
                <div className="flex items-center gap-1.5 text-slate-500">
                  {inc.event_observed === 1 ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      <span className="text-emerald-600">Cleared in {inc.duration_minutes}m</span>
                    </>
                  ) : (
                    <>
                      <Clock className="w-4 h-4 text-amber-500" />
                      <span className="text-amber-600">Unresolved / in progress</span>
                    </>
                  )}
                </div>
                {Boolean(inc.requires_road_closure) && (
                  <span className="text-red-500 font-semibold border border-red-200 px-1.5 rounded bg-red-50">
                    Road Closed
                  </span>
                )}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
