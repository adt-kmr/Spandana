import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ClearApi } from '../api';
import type { DispatchUnit, IncidentRow } from '../types';
import { Send, CheckCircle2, AlertCircle } from 'lucide-react';

export default function DispatchPanel({ incident }: { incident?: IncidentRow }) {
  const [units] = useState<DispatchUnit[]>([
    { unit_id: 'UNIT-001', lat: 12.971, lon: 77.594 },
    { unit_id: 'UNIT-002', lat: 12.960, lon: 77.580 },
  ]);

  const suggestMutation = useMutation({
    mutationFn: () => ClearApi.dispatchSuggest({ units, max_incidents: 5 }),
  });

  const confirmMutation = useMutation({
    mutationFn: (recId: number) => ClearApi.dispatchConfirm({ recommendation_id: recId }),
  });

  if (!incident) {
    return (
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col items-center justify-center text-center h-full text-slate-500">
        <Send className="w-8 h-8 mb-2 text-slate-300" />
        <p>Select an incident to manage dispatch.</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col h-full">
      <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
        <Send className="w-5 h-5 text-blue-500" />
        Dispatch Management
      </h2>

      <div className="flex-1">
        {confirmMutation.isSuccess ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-emerald-600 bg-emerald-50 rounded-lg p-6 border border-emerald-200">
            <CheckCircle2 className="w-10 h-10 mb-2" />
            <p className="font-bold">Dispatch Confirmed</p>
            <p className="text-sm mt-1 text-emerald-700">Units have been notified. Awaiting human execution.</p>
            <div className="mt-4 text-xs bg-white px-3 py-1 rounded-full border border-emerald-200">
              Autonomous Actuation: <span className="font-bold">false</span>
            </div>
          </div>
        ) : suggestMutation.isSuccess && suggestMutation.data ? (
          <div className="space-y-4">
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
              <h3 className="font-bold text-blue-800 text-sm mb-2">Suggested Dispatch</h3>
              <pre className="text-xs text-blue-900 bg-blue-100/50 p-2 rounded overflow-auto max-h-32">
                {JSON.stringify(suggestMutation.data, null, 2)}
              </pre>
              
              {!suggestMutation.data.recommendation_id && (
                 <div className="mt-3 flex items-start gap-2 text-amber-700 bg-amber-100 p-2 rounded text-xs font-medium">
                   <AlertCircle className="w-4 h-4 shrink-0" />
                   Degraded mode: FIFO queue only. Confirmation disabled.
                 </div>
              )}
            </div>

            {suggestMutation.data.recommendation_id && (
              <button
                onClick={() => confirmMutation.mutate(suggestMutation.data.recommendation_id as number)}
                disabled={confirmMutation.isPending}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold py-3 rounded-lg shadow-sm transition-all"
              >
                {confirmMutation.isPending ? 'Confirming...' : 'Confirm Dispatch Suggestion'}
              </button>
            )}
            
            <p className="text-xs text-slate-500 text-center font-medium flex items-center justify-center gap-1">
              <AlertCircle className="w-3 h-3" />
              Awaiting operator confirmation. No automatic activation.
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full">
             <button
                onClick={() => suggestMutation.mutate()}
                disabled={suggestMutation.isPending}
                className="bg-slate-800 hover:bg-slate-900 text-white px-6 py-2 rounded-lg font-medium transition-colors"
             >
               {suggestMutation.isPending ? 'Analyzing...' : 'Generate Suggestion'}
             </button>
             {suggestMutation.isError && (
               <p className="text-red-500 text-sm mt-4 text-center">
                 {suggestMutation.error instanceof Error ? suggestMutation.error.message : 'Error generating suggestion'}
               </p>
             )}
          </div>
        )}
      </div>
    </div>
  );
}
