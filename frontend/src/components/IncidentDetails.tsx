import { useQuery } from '@tanstack/react-query';
import { ClearApi } from '../api';
import { Activity, Clock, ServerCrash } from 'lucide-react';
import type { IncidentRow } from '../types';
import DiversionAid from './DiversionAid';
import RainRiskWidget from './RainRiskWidget';

export default function IncidentDetails({ incident }: { incident: IncidentRow }) {
  const { data: health, isLoading: isHealthLoading, isError: isHealthError } = useQuery({
    queryKey: ['health'],
    queryFn: () => ClearApi.health(),
    refetchInterval: 30000, // re-check every 30s so a transient boot-time reading self-corrects
    retry: 3,
  });

  const severityUp = health?.models?.severity;
  const clearanceUp = health?.models?.clearance;

  const { data: severity, isError: isSevError, error: sevError } = useQuery({
    queryKey: ['severity', incident.event_id],
    queryFn: () => ClearApi.severity(incident.event_id),
    enabled: !!severityUp,
  });

  const { data: clearance, isError: isClrError, error: clrError } = useQuery({
    queryKey: ['clearance', incident.event_id],
    queryFn: () => ClearApi.clearance(incident.event_id),
    enabled: !!clearanceUp,
  });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full">
      <div className="p-4 border-b border-slate-100 bg-slate-50">
        <h2 className="text-lg font-bold text-slate-800">Incident Intelligence</h2>
        <p className="text-sm text-slate-500 font-mono mt-1">{incident.event_id}</p>
      </div>

      <div className="p-4 space-y-4 flex-1 overflow-auto">
        {/* Severity Card */}
        <div className="p-4 rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 text-slate-700 font-semibold mb-3">
            <Activity className="w-4 h-4 text-blue-500" />
            Severity Analysis
          </div>
          
          {isHealthLoading ? (
            <div className="text-slate-400 text-sm animate-pulse">Checking…</div>
          ) : isHealthError || !health ? (
            <div className="flex items-center gap-2 text-red-600 bg-red-50 p-2 rounded text-sm">
              <ServerCrash className="w-4 h-4" /> Can't reach service
            </div>
          ) : !severityUp ? (
            <div className="flex items-center gap-2 text-amber-600 bg-amber-50 p-2 rounded text-sm">
              <ServerCrash className="w-4 h-4" /> Model Offline
            </div>
          ) : isSevError ? (
            <div className="text-red-500 text-sm">{sevError instanceof Error ? sevError.message : 'Analysis failed'}</div>
          ) : !severity ? (
            <div className="text-slate-400 text-sm animate-pulse">Analyzing severity...</div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(severity).map(([key, value]) => (
                <div key={key} className="bg-slate-50 p-2 rounded border border-slate-100">
                  <div className="text-xs text-slate-500 capitalize">{key.replace(/_/g, ' ')}</div>
                  <div className="font-medium text-slate-800">{String(value)}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Clearance Card */}
        <div className="p-4 rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 text-slate-700 font-semibold mb-3">
            <Clock className="w-4 h-4 text-indigo-500" />
            Clearance Estimate
          </div>

          {isHealthLoading ? (
            <div className="text-slate-400 text-sm animate-pulse">Checking…</div>
          ) : isHealthError || !health ? (
            <div className="flex items-center gap-2 text-red-600 bg-red-50 p-2 rounded text-sm">
              <ServerCrash className="w-4 h-4" /> Can't reach service
            </div>
          ) : !clearanceUp ? (
            <div className="flex items-center gap-2 text-amber-600 bg-amber-50 p-2 rounded text-sm">
              <ServerCrash className="w-4 h-4" /> Model Offline
            </div>
          ) : isClrError ? (
            <div className="text-red-500 text-sm">{clrError instanceof Error ? clrError.message : 'Analysis failed'}</div>
          ) : !clearance ? (
            <div className="text-slate-400 text-sm animate-pulse">Estimating clearance...</div>
          ) : (
            <div className="flex flex-col items-center justify-center py-4">
              {clearance.p50 !== undefined ? (
                <>
                  <div className="text-3xl font-bold text-indigo-600">~{String(clearance.p50)} min</div>
                  <div className="text-sm text-slate-500 mt-1">
                    (P50; {String(clearance.p10)}–{String(clearance.p90)})
                  </div>
                </>
              ) : (
                <div className="text-sm text-slate-600 flex flex-col gap-1 w-full">
                  {Object.entries(clearance).map(([k,v]) => (
                    <div key={k} className="flex justify-between border-b pb-1">
                      <span className="text-slate-500 capitalize">{k}</span>
                      <span className="font-semibold">{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Diversion Aid Card */}
        {incident.corridor && (
          <DiversionAid scope="operator" corridor={incident.corridor} />
        )}

        {/* Rain & Water-logging Card */}
        <RainRiskWidget corridor={incident.corridor} scope="operator" />
      </div>
    </div>
  );
}

