import { useQuery } from '@tanstack/react-query';
import { ClearApi } from '../api';
import { Target, Info } from 'lucide-react';

export default function SlaWidget() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['sla'],
    queryFn: () => ClearApi.sla('operator'),
  });

  if (isLoading) return <div className="animate-pulse bg-white p-4 rounded-xl border border-slate-200 h-32" />;

  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col h-full">
      <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 mb-3">
        <Target className="w-4 h-4 text-emerald-500" />
        SLA Performance
      </h3>
      
      {isError ? (
        <div className="text-red-500 text-sm">Failed to load SLA.</div>
      ) : (
        <div className="flex-1 flex flex-col justify-center">
          {data?.sla_pct === null ? (
            <p className="text-slate-500 text-sm font-medium italic">N/A — no resolved incidents yet</p>
          ) : (
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold text-emerald-600">{data?.sla_pct}%</span>
              <span className="text-sm text-slate-500 font-medium">met SLA</span>
            </div>
          )}
          <div className="mt-3 flex items-start gap-1.5 text-xs text-slate-500 bg-slate-50 p-2 rounded border border-slate-100">
            <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span>
              {data?.note || `Computed only over the resolved subset (${data?.resolved_subset_size || 0} incidents). Threshold: ${data?.threshold_minutes || 0}m.`}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
