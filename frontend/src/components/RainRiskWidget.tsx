import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { ClearApi } from '../api';
import { CloudRain, Droplets, Thermometer, AlertTriangle } from 'lucide-react';
import type { RainRisk } from '../types';

const BAND: Record<
  RainRisk['risk_band'],
  { label: string; pill: string; bar: string; text: string }
> = {
  high:     { label: 'High',     pill: 'bg-red-100 text-red-700 border-red-300',            bar: 'bg-red-500',     text: 'text-red-600' },
  moderate: { label: 'Moderate', pill: 'bg-amber-100 text-amber-700 border-amber-300',      bar: 'bg-amber-500',   text: 'text-amber-600' },
  low:      { label: 'Low',      pill: 'bg-emerald-100 text-emerald-700 border-emerald-300', bar: 'bg-emerald-500', text: 'text-emerald-600' },
  unknown:  { label: 'Unknown',  pill: 'bg-slate-100 text-slate-500 border-slate-300',       bar: 'bg-slate-300',   text: 'text-slate-500' },
};

export default function RainRiskWidget({
  corridor,
  scope,
}: {
  corridor: string | null;
  scope: 'operator' | 'citizen';
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['rain-risk', corridor, scope],
    queryFn: () => ClearApi.rainRisk(corridor as string, scope),
    enabled: !!corridor,
    refetchInterval: 5 * 60 * 1000, // live nowcast — refresh every 5 min
  });

  const shell = (children: ReactNode) => (
    <div className="p-4 rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center gap-2 text-slate-700 font-semibold mb-3">
        <CloudRain className="w-4 h-4 text-sky-500" />
        Rain &amp; Water-logging
      </div>
      {children}
    </div>
  );

  if (!corridor) return shell(<div className="text-slate-400 text-sm">No corridor to assess.</div>);
  if (isLoading) return shell(<div className="text-slate-400 text-sm animate-pulse">Checking live rain…</div>);
  if (isError) return shell(<div className="text-red-500 text-sm">Couldn’t load rain risk.</div>);
  if (!data) return shell(null);

  if (!data.available) {
    return shell(
      <div className="flex items-center gap-2 text-slate-500 bg-slate-50 p-2 rounded text-sm border border-slate-100">
        <AlertTriangle className="w-4 h-4 shrink-0" />
        <span>
          No live rain data for {data.corridor}
          {data.reason ? ` (${data.reason})` : ''}.
        </span>
      </div>
    );
  }

  const band = BAND[data.risk_band] ?? BAND.unknown;
  const pct = Math.min(100, Math.max(0, data.rain_clog_score));

  return shell(
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-baseline gap-1.5">
          <span className={`text-3xl font-bold ${band.text}`}>{data.rain_clog_score.toFixed(0)}</span>
          <span className="text-xs text-slate-400">/ 100</span>
        </div>
        <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${band.pill}`}>
          {band.label} risk
        </span>
      </div>

      <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full ${band.bar} transition-all`} style={{ width: `${pct}%` }} />
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-500">Clearance ETA impact</span>
        <span className="font-semibold text-slate-800">×{data.rain_multiplier.toFixed(2)}</span>
      </div>

      {data.rain && (
        <div className="grid grid-cols-2 gap-2 pt-1">
          <Stat icon={<Droplets className="w-4 h-4 text-sky-500 shrink-0" />} label="Intensity" value={`${data.rain.intensity} mm/min`} />
          <Stat icon={<CloudRain className="w-4 h-4 text-sky-500 shrink-0" />} label="Today" value={`${data.rain.accumulation} mm`} />
          <Stat icon={<Thermometer className="w-4 h-4 text-orange-400 shrink-0" />} label="Temp" value={`${data.rain.temperature}°C`} />
          <Stat icon={<Droplets className="w-4 h-4 text-slate-400 shrink-0" />} label="Humidity" value={`${data.rain.humidity}%`} />
        </div>
      )}

      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
        <span>Hyperlocal nowcast · Weather Union</span>
        {data.stale && (
          <span className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200">cached</span>
        )}
      </div>
    </div>
  );
}

function Stat({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="bg-slate-50 p-2 rounded border border-slate-100 flex items-center gap-2">
      {icon}
      <div>
        <div className="text-[11px] text-slate-500 leading-tight">{label}</div>
        <div className="text-sm font-semibold text-slate-800">{value}</div>
      </div>
    </div>
  );
}
