import { useQuery } from '@tanstack/react-query';
import { ClearApi } from '../api';
import { Activity, ServerCrash } from 'lucide-react';

export default function HealthBadge() {
  const { data, isError } = useQuery({
    queryKey: ['health'],
    queryFn: () => ClearApi.health(),
    refetchInterval: 30000, // Poll every 30s
  });

  if (isError || !data || data.status !== 'ok') {
    return (
      <div className="flex items-center gap-2 text-red-400 bg-slate-800 px-3 py-1.5 rounded-full text-sm font-medium border border-red-500/30">
        <ServerCrash className="w-4 h-4" />
        <span>Service Unavailable</span>
      </div>
    );
  }

  const allModelsUp = data.models.severity && data.models.clearance && data.models.forecast;

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border ${allModelsUp ? 'text-emerald-400 bg-slate-800 border-emerald-500/30' : 'text-amber-400 bg-slate-800 border-amber-500/30'
      }`}>
      <Activity className="w-4 h-4" />
      <span>{allModelsUp ? 'All Systems Operational' : 'Models Degraded'}</span>
    </div>
  );
}
