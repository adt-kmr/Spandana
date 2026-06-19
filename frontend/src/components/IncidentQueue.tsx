import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ClearApi } from '../api';
import { AlertTriangle, Clock, MapPin, CheckCircle2 } from 'lucide-react';
import type { IncidentRow } from '../types';

export default function IncidentQueue({ scope, onSelect }: { scope: 'operator' | 'citizen', onSelect?: (incident: IncidentRow) => void }) {
  const [search, setSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState<string>('All');

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['incidents', scope],
    queryFn: () => ClearApi.incidents(100, scope),
  });

  const filteredIncidents = useMemo(() => {
    const incidents = data?.incidents || [];
    return incidents.filter(inc => {
      if (search) {
        const q = search.toLowerCase();
        const matchesEventId = inc.event_id?.toLowerCase().includes(q);
        const matchesCorridor = inc.corridor?.toLowerCase().includes(q);
        const matchesCause = inc.event_cause?.toLowerCase().includes(q);
        if (!matchesEventId && !matchesCorridor && !matchesCause) return false;
      }
      
      if (priorityFilter !== 'All') {
        const p = inc.priority?.toLowerCase() || 'unknown';
        if (p !== priorityFilter.toLowerCase()) return false;
      }
      return true;
    });
  }, [data?.incidents, search, priorityFilter]);

  if (isLoading) return <div className="p-8 text-center text-slate-500 animate-pulse">Loading incidents...</div>;
  
  if (isError) {
    return (
      <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">
        <div className="font-semibold flex items-center gap-2"><AlertTriangle className="w-5 h-5"/> Failed to load queue</div>
        <div className="text-sm mt-1">{error instanceof Error ? error.message : 'Unknown error'}</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-col p-4 border-b-4 border-black bg-white sticky top-0 z-10 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-black uppercase text-black flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-brutal-pink" />
            Active Queue
          </h2>
          <span className="text-sm text-black bg-brutal-yellow px-2.5 py-1 rounded-full font-bold whitespace-nowrap ml-2 border-2 border-black">
            {filteredIncidents.length} of {data?.count || 0}
          </span>
        </div>

        <input 
          type="text" 
          placeholder="Search ID, corridor, cause..." 
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full border-4 border-black rounded p-2 text-sm focus:outline-none focus:ring-4 focus:ring-brutal-blue font-bold shadow-[2px_2px_0_0_rgba(0,0,0,1)] transition-shadow"
        />

        <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: 'none' }}>
          {['All', 'Critical', 'High', 'Medium', 'Low'].map(p => (
            <button
              key={p}
              onClick={() => setPriorityFilter(p)}
              className={`brutal-badge cursor-pointer whitespace-nowrap transition-transform active:translate-y-0.5 shadow-[2px_2px_0_0_rgba(0,0,0,1)] ${
                priorityFilter === p 
                  ? 'bg-black text-white' 
                  : 'bg-white text-black hover:bg-slate-100'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-y-auto flex-1 p-2 space-y-2">
        {filteredIncidents.length === 0 ? (
          <div className="p-8 text-center text-slate-500 font-bold">No incidents match your filters.</div>
        ) : (
          filteredIncidents.map((inc) => (
            <button
              key={inc.event_id}
              onClick={() => onSelect?.(inc)}
              className="w-full text-left bg-white p-4 rounded-xl border-4 border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)] hover:-translate-y-1 hover:shadow-[6px_6px_0_0_rgba(0,0,0,1)] transition-all focus:outline-none focus:ring-4 focus:ring-brutal-blue"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-black uppercase tracking-wide border-2 border-black
                    ${inc.priority === 'critical' ? 'bg-brutal-pink text-black' : 
                      inc.priority === 'high' ? 'bg-brutal-yellow text-black' :
                      inc.priority === 'medium' ? 'bg-brutal-blue text-white' : 
                      'bg-slate-200 text-black'}`}>
                    {inc.priority || 'UNKNOWN'}
                  </span>
                  <span className="text-sm font-black text-black capitalize">
                    {inc.event_cause?.replace('_', ' ') || 'Unknown Cause'}
                  </span>
                </div>
                <div className="text-xs font-bold text-slate-500">
                  {inc.start_ist ? new Date(inc.start_ist).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                </div>
              </div>
              
              <div className="flex items-center gap-1.5 text-sm font-bold text-slate-700 mb-3">
                <MapPin className="w-4 h-4 text-black shrink-0" />
                <span className="truncate">{inc.corridor || 'Unknown Location'}</span>
              </div>

              <div className="flex items-center justify-between text-xs font-bold">
                <div className="flex items-center gap-1.5">
                  {inc.event_observed === 1 ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-brutal-green" />
                      <span className="text-brutal-green">Cleared in {inc.duration_minutes}m</span>
                    </>
                  ) : (
                    <>
                      <Clock className="w-4 h-4 text-brutal-pink" />
                      <span className="text-black">Unresolved / in progress</span>
                    </>
                  )}
                </div>
                {Boolean(inc.requires_road_closure) && (
                  <span className="text-white font-black border-2 border-black px-1.5 py-0.5 rounded bg-brutal-pink shadow-[2px_2px_0_0_rgba(0,0,0,1)]">
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
