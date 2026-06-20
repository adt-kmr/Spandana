import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, LogOut } from 'lucide-react';
import SlaWidget from '../components/SlaWidget';
import MetricsWidget from '../components/MetricsWidget';
import { useQuery } from '@tanstack/react-query';
import { ClearApi } from '../api';
import { clearOperatorToken } from '../auth';

export default function OperatorStats() {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearOperatorToken();
    navigate('/operator/login');
  };

  const { data: hotspots, isLoading: isHotspotsLoading } = useQuery({
    queryKey: ['hotspots'],
    queryFn: () => ClearApi.hotspots(5, 20),
  });

  const { data: risks, isLoading: isRisksLoading } = useQuery({
    queryKey: ['corridorsRisk', 'operator'],
    queryFn: () => ClearApi.corridorsRisk('operator'),
  });

  const { data: accuracy, isLoading: isAccuracyLoading } = useQuery({
    queryKey: ['metricsByEvent'],
    queryFn: () => ClearApi.metricsByEvent(),
  });

  return (
    <div className="min-h-screen flex flex-col p-4 md:p-8 gap-6 max-w-[1600px] mx-auto w-full">
      <div className="flex flex-col md:flex-row md:items-center justify-between brutal-card bg-brutal-yellow p-6 border-[6px] gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter drop-shadow-[2px_2px_0_rgba(0,0,0,1)]">Operations Stats</h1>
          <p className="text-xl font-bold mt-2">System performance and predictive insights.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-4">
          <Link to="/operator/planning" className="brutal-btn bg-brutal-green text-black hover:opacity-90 flex items-center justify-center gap-2">
            Planning Studio
          </Link>
          <Link to="/operator" className="brutal-btn bg-white hover:bg-gray-100 flex items-center justify-center gap-2">
            <ArrowLeft size={20} className="stroke-[3]" /> Console
          </Link>
          <button onClick={handleLogout} className="brutal-btn bg-brutal-pink text-white hover:opacity-90 flex items-center justify-center gap-2">
            <LogOut size={20} className="stroke-[3]" /> Log out
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 flex-1">
        {/* Row 1: SLA & Metrics */}
        <div className="col-span-1 lg:col-span-1 flex flex-col gap-6">
          <div className="brutal-card border-[6px] bg-white p-4">
            <SlaWidget />
          </div>
          <div className="brutal-card border-[6px] bg-white p-4 flex-1">
            <MetricsWidget />
          </div>
        </div>

        {/* Corridor Risk */}
        <div className="col-span-1 lg:col-span-1 brutal-card border-[6px] bg-white p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4 border-b-4 border-black pb-2">
            <h2 className="text-2xl font-black uppercase">Corridor Risk</h2>
            {risks?.note && <span className="brutal-badge bg-brutal-yellow text-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] text-xs">Degraded</span>}
          </div>
          <div className="flex-1 overflow-y-auto pr-2 space-y-4">
            {isRisksLoading ? (
              <div className="animate-pulse h-10 bg-slate-200 rounded"></div>
            ) : risks?.corridors && risks.corridors.length > 0 ? (
              risks.corridors.map(c => (
                <div key={c.corridor} className="flex flex-col gap-1">
                  <div className="flex justify-between items-end">
                    <span className="font-bold text-lg truncate" title={c.corridor}>{c.corridor}</span>
                    <div className="flex items-center gap-2">
                      <span className="font-black text-xl">{c.risk}</span>
                      {c.stale && <span className="text-[10px] font-bold bg-brutal-pink px-1 rounded border-2 border-black">STALE</span>}
                    </div>
                  </div>
                  <div className="h-4 border-2 border-black rounded-full overflow-hidden bg-slate-100 relative">
                    <div 
                      className={`h-full border-r-2 border-black ${c.risk > 70 ? 'bg-brutal-pink' : c.risk > 40 ? 'bg-brutal-yellow' : 'bg-brutal-green'}`}
                      style={{ width: `${Math.min(c.risk, 100)}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <p className="font-bold text-slate-500">No risk data available.</p>
            )}
          </div>
        </div>

        {/* Hotspots */}
        <div className="col-span-1 lg:col-span-1 brutal-card border-[6px] bg-white p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4 border-b-4 border-black pb-2">
            <h2 className="text-2xl font-black uppercase">Hotspots</h2>
            <span className="brutal-badge bg-black text-white shadow-[2px_2px_0_0_rgba(0,0,0,1)] text-xs">
              {hotspots?.n_clusters || 0} Clusters
            </span>
          </div>
          <div className="flex-1 overflow-y-auto pr-2">
            {isHotspotsLoading ? (
              <div className="animate-pulse h-10 bg-slate-200 rounded"></div>
            ) : hotspots?.clusters && hotspots.clusters.length > 0 ? (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b-4 border-black text-sm uppercase">
                    <th className="pb-2">ID</th>
                    <th className="pb-2">Size</th>
                    <th className="pb-2 text-right">Top Corridor</th>
                  </tr>
                </thead>
                <tbody className="text-sm font-bold">
                  {hotspots.clusters.map(cluster => (
                    <tr key={cluster.cluster_id} className="border-b-2 border-black last:border-0">
                      <td className="py-3">#{cluster.cluster_id}</td>
                      <td className="py-3">
                        <span className="brutal-badge bg-brutal-pink text-white">{cluster.size}</span>
                      </td>
                      <td className="py-3 text-right truncate max-w-[120px]">{cluster.top_corridor || 'Unknown'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="font-bold text-slate-500">No hotspot data available.</p>
            )}
          </div>
        </div>
      </div>

      {/* Post-event Accuracy Section */}
      <div className="brutal-card border-[6px] bg-white p-6 mt-6 flex flex-col">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 border-b-4 border-black pb-2 gap-2">
          <h2 className="text-2xl font-black uppercase">Post-Event Accuracy</h2>
          {accuracy && (
            <span className="brutal-badge bg-brutal-yellow text-black shadow-[2px_2px_0_0_rgba(0,0,0,1)] text-xs font-bold whitespace-nowrap self-start">
              Overall MAE: {accuracy.overall_mae_minutes} min (n={accuracy.n})
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          {isAccuracyLoading ? (
            <div className="animate-pulse h-10 bg-slate-200 rounded"></div>
          ) : accuracy?.by_event && accuracy.by_event.length > 0 ? (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b-4 border-black text-sm uppercase">
                  <th className="pb-2">Event Cause / Type</th>
                  <th className="pb-2">MAE (min)</th>
                  <th className="pb-2 text-right font-black">Sample Size (n)</th>
                </tr>
              </thead>
              <tbody className="text-sm font-bold">
                {accuracy.by_event.map((row, index) => {
                  const isLowSample = row.n < 32;
                  return (
                    <tr
                      key={`${row.event_cause}-${index}`}
                      className={`border-b-2 border-black last:border-0 ${isLowSample ? 'opacity-50' : ''}`}
                    >
                      <td className="py-3 flex items-center gap-2">
                        <span className="capitalize">{row.event_cause.replace(/_/g, ' ')}</span>
                        {isLowSample && (
                          <span className="text-[9px] font-black uppercase border border-black bg-white text-slate-500 px-1 py-0.5 rounded shadow-[1px_1px_0_0_rgba(0,0,0,1)]">
                            low sample
                          </span>
                        )}
                      </td>
                      <td className="py-3 font-mono">{row.mae_minutes.toFixed(2)} min</td>
                      <td className="py-3 text-right">
                        <span className={`brutal-badge text-xs ${isLowSample ? 'bg-slate-200 text-slate-500' : 'bg-brutal-green text-black'}`}>
                          {row.n}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <p className="font-bold text-slate-500">No event-level metrics yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
