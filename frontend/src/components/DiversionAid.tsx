import { useQuery } from '@tanstack/react-query';
import { ClearApi } from '../api';
import { Shuffle, HelpCircle } from 'lucide-react';

interface DiversionAidProps {
  corridor: string;
  scope: 'operator' | 'citizen';
}

export default function DiversionAid({ corridor, scope }: DiversionAidProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['diversions', corridor, scope],
    queryFn: () => ClearApi.diversions(corridor, scope),
    enabled: !!corridor,
  });

  if (!corridor) {
    return (
      <div className="brutal-card p-4 bg-white border-4 border-black text-center text-sm font-bold text-slate-500">
        No corridor selected to show diversion options.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="animate-pulse bg-white border-4 border-black rounded-xl h-32 w-full" />
    );
  }

  if (isError) {
    return (
      <div className="brutal-card p-4 bg-brutal-pink text-white border-4 border-black font-bold text-sm">
        Error loading diversions: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="brutal-card bg-white border-4 border-black p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between border-b-2 border-black pb-2">
        <h3 className="text-md font-black uppercase tracking-tight flex items-center gap-2">
          <Shuffle size={18} className="stroke-[3]" />
          Diversions — {data.blocked_corridor}
        </h3>
      </div>

      {data.has_diversion && data.alternates && data.alternates.length > 0 ? (
        <div className="space-y-2">
          {data.alternates.map((alt, index) => {
            const isPrimary = alt.rank === 'primary';
            const isLargeDelta = alt.delta_minutes >= 10;
            return (
              <div
                key={`${alt.corridor}-${index}`}
                className="flex items-center justify-between border-2 border-black p-2 rounded-lg bg-brutal-bg font-bold text-sm"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-mono text-xs bg-black text-white px-1.5 py-0.5 rounded">
                    #{index + 1}
                  </span>
                  <span className="truncate" title={alt.corridor}>
                    {alt.corridor}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`text-[10px] font-black uppercase border border-black rounded px-1.5 py-0.5 ${
                      isPrimary ? 'bg-brutal-green text-black' : 'bg-white text-slate-600'
                    }`}
                  >
                    {alt.rank}
                  </span>
                  <span
                    className={`brutal-badge text-xs shadow-[2px_2px_0_0_rgba(0,0,0,1)] ${
                      isLargeDelta ? 'bg-brutal-pink text-white' : 'bg-brutal-yellow text-black'
                    }`}
                  >
                    +{alt.delta_minutes} min
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex items-start gap-2 bg-slate-50 border-2 border-black p-3 rounded-lg text-xs font-semibold text-slate-600">
          <HelpCircle size={16} className="shrink-0 text-slate-400 mt-0.5" />
          <p>{data.note || 'No predefined diversion routes found for this corridor.'}</p>
        </div>
      )}
    </div>
  );
}
