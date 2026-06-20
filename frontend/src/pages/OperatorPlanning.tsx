import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, LogOut, Shield, Construction, Truck, Info, Calendar, MapPin, ArrowRight, AlertTriangle } from 'lucide-react';
import { ClearApi, ApiError } from '../api';
import { clearOperatorToken } from '../auth';

export default function OperatorPlanning() {
  const navigate = useNavigate();

  // Simulator Form State
  const [eventDate, setEventDate] = useState('');
  const [eventType, setEventType] = useState('');
  const [selectedCorridor, setSelectedCorridor] = useState('');
  const [selectedIncidentId, setSelectedIncidentId] = useState('');

  // Resource Planner Form State
  const [attendees, setAttendees] = useState<number>(0);
  const [roadClosures, setRoadClosures] = useState<number>(0);
  const [plannerEventType, setPlannerEventType] = useState('');

  // Validation errors
  const [plannerError, setPlannerError] = useState<string | null>(null);
  const [simulatorError, setSimulatorError] = useState<string | null>(null);

  // Queries
  const { data: eventTypesData } = useQuery({
    queryKey: ['eventTypes'],
    queryFn: () => ClearApi.eventTypes('operator'),
  });

  const { data: corridorsData } = useQuery({
    queryKey: ['corridorsRisk', 'operator'],
    queryFn: () => ClearApi.corridorsRisk('operator'),
  });

  const { data: incidentsData } = useQuery({
    queryKey: ['incidents', 'operator'],
    queryFn: () => ClearApi.incidents(100, 'operator'),
  });

  // Query selected incident's clearance to get base_minutes
  const { data: clearanceData } = useQuery({
    queryKey: ['clearance', selectedIncidentId],
    queryFn: () => ClearApi.clearance(selectedIncidentId),
    enabled: !!selectedIncidentId,
  });

  // Mutations
  const impactMutation = useMutation({
    mutationFn: (req: { event_type?: string; base_minutes?: number; base_risk?: number }) =>
      ClearApi.eventImpact(req, 'operator'),
    onError: (err) => {
      setSimulatorError(err instanceof ApiError ? err.detail : err.message);
    },
    onSuccess: () => {
      setSimulatorError(null);
    }
  });

  const resourceMutation = useMutation({
    mutationFn: (req: { attendees: number; road_closures?: number; event_type?: string }) =>
      ClearApi.resourcePlan(req),
    onError: (err) => {
      setPlannerError(err instanceof ApiError ? err.detail : err.message);
    },
    onSuccess: () => {
      setPlannerError(null);
    }
  });

  const handleLogout = () => {
    clearOperatorToken();
    navigate('/operator/login');
  };

  // Find risk of chosen corridor
  const chosenCorridorRisk = corridorsData?.corridors?.find(c => c.corridor === selectedCorridor)?.risk;

  // Extract base minutes from selected incident clearance (using p50)
  const baseMinutes = selectedIncidentId && clearanceData && 'p50' in clearanceData
    ? (clearanceData.p50 as number)
    : undefined;

  const handleSimulate = (e: React.FormEvent) => {
    e.preventDefault();
    setSimulatorError(null);
    impactMutation.mutate({
      event_type: eventType || undefined,
      base_risk: chosenCorridorRisk !== undefined ? chosenCorridorRisk : undefined,
      base_minutes: baseMinutes,
    });
  };

  const handleGeneratePlan = (e: React.FormEvent) => {
    e.preventDefault();
    setPlannerError(null);
    if (attendees < 0 || roadClosures < 0) {
      setPlannerError('Attendees and Road Closures must be non-negative values.');
      return;
    }
    resourceMutation.mutate({
      attendees,
      road_closures: roadClosures,
      event_type: plannerEventType || undefined,
    });
  };

  return (
    <div className="min-h-screen flex flex-col p-4 md:p-8 gap-6 max-w-[1600px] mx-auto w-full">
      {/* Header bar consistent with OperatorDashboard */}
      <div className="flex flex-col md:flex-row md:items-center justify-between brutal-card bg-brutal-yellow p-6 border-[6px] gap-4">
        <div>
          <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter drop-shadow-[2px_2px_0_rgba(0,0,0,1)]">Planning Studio</h1>
          <p className="text-xl font-bold mt-2 font-sans text-black">Event simulations and resource dispatch optimization.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-4">
          <Link to="/operator" className="brutal-btn bg-white hover:bg-gray-100 flex items-center justify-center gap-2">
            <ArrowLeft size={20} className="stroke-[3]" /> Operator Console
          </Link>
          <Link to="/" className="brutal-btn bg-white hover:bg-gray-100 flex items-center justify-center gap-2">
            Gateway
          </Link>
          <button onClick={handleLogout} className="brutal-btn bg-brutal-pink text-white hover:opacity-90 flex items-center justify-center gap-2">
            <LogOut size={20} className="stroke-[3]" /> Log out
          </button>
        </div>
      </div>

      {/* Main Panels Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Panel A: Event Impact Simulator */}
        <div className="brutal-card border-[6px] bg-white p-6 flex flex-col">
          <h2 className="text-2xl font-black uppercase mb-4 border-b-4 border-black pb-2 flex items-center gap-2">
            <Calendar className="stroke-[3] text-brutal-blue" />
            Event Impact Simulator
          </h2>

          <form onSubmit={handleSimulate} className="space-y-4 flex-1 flex flex-col">
            <div>
              <label className="block text-sm font-black uppercase mb-1">Event Date</label>
              <input
                type="date"
                required
                value={eventDate}
                onChange={e => setEventDate(e.target.value)}
                className="w-full border-4 border-black rounded p-2 text-md font-bold focus:outline-none focus:ring-4 focus:ring-brutal-blue bg-white shadow-[4px_4px_0_0_#000]"
              />
            </div>

            <div>
              <label className="block text-sm font-black uppercase mb-1">Event Type</label>
              <select
                value={eventType}
                onChange={e => setEventType(e.target.value)}
                className="w-full border-4 border-black rounded p-2 text-md font-bold focus:outline-none focus:ring-4 focus:ring-brutal-blue bg-white shadow-[4px_4px_0_0_#000]"
              >
                <option value="">Normal (None)</option>
                {eventTypesData?.event_types?.map(t => (
                  <option key={t} value={t}>{t.replace(/_/g, ' ').toUpperCase()}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-black uppercase mb-1">Corridor Base Risk (Optional)</label>
              <select
                value={selectedCorridor}
                onChange={e => setSelectedCorridor(e.target.value)}
                className="w-full border-4 border-black rounded p-2 text-md font-bold focus:outline-none focus:ring-4 focus:ring-brutal-blue bg-white shadow-[4px_4px_0_0_#000]"
              >
                <option value="">Select corridor for base risk...</option>
                {corridorsData?.corridors?.map(c => (
                  <option key={c.corridor} value={c.corridor}>
                    {c.corridor} (Risk: {c.risk})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-black uppercase mb-1">Baseline Clearance Incident (Optional)</label>
              <select
                value={selectedIncidentId}
                onChange={e => setSelectedIncidentId(e.target.value)}
                className="w-full border-4 border-black rounded p-2 text-md font-bold focus:outline-none focus:ring-4 focus:ring-brutal-blue bg-white shadow-[4px_4px_0_0_#000]"
              >
                <option value="">Select incident to fetch base clearance...</option>
                {incidentsData?.incidents?.filter(inc => inc.status === 'open').map(inc => (
                  <option key={inc.event_id} value={inc.event_id}>
                    {inc.event_id.slice(0, 8)}... - {inc.corridor || 'Unknown Corridor'} ({inc.event_cause || 'Unknown Cause'})
                  </option>
                ))}
              </select>
              {selectedIncidentId && (
                <div className="mt-2 text-xs font-bold text-slate-500 font-mono">
                  {clearanceData ? (
                    'p50' in clearanceData ? (
                      `Loaded Clearance Baseline: ${clearanceData.p50} min`
                    ) : (
                      'Clearance baseline loaded.'
                    )
                  ) : (
                    'Fetching clearance estimate...'
                  )}
                </div>
              )}
            </div>

            {simulatorError && (
              <div className="bg-brutal-pink text-white font-bold border-4 border-black p-3 text-center uppercase shadow-[4px_4px_0_0_#000] flex items-center justify-center gap-2">
                <AlertTriangle />
                {simulatorError}
              </div>
            )}

            <div className="pt-2">
              <button
                type="submit"
                disabled={impactMutation.isPending}
                className="w-full brutal-btn bg-brutal-blue text-white hover:opacity-90 disabled:opacity-50 text-lg"
              >
                {impactMutation.isPending ? 'Simulating...' : 'Simulate Impact'}
              </button>
            </div>
          </form>

          {/* Results section */}
          {impactMutation.data && (
            <div className="mt-6 border-4 border-black p-4 rounded-xl bg-brutal-yellow shadow-[4px_4px_0_0_#000] text-black">
              <h3 className="text-xl font-black uppercase mb-3 border-b-2 border-black pb-1">Simulation Results</h3>
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="flex flex-col items-center justify-center bg-white border-4 border-black p-4 rounded-xl shadow-[4px_4px_0_0_#000] min-w-[120px]">
                  <span className="text-xs font-black uppercase tracking-wider text-slate-500">Multiplier</span>
                  <span className="text-3xl font-black">{impactMutation.data.multiplier}x</span>
                </div>

                <div className="flex-1 space-y-3 w-full">
                  {(impactMutation.data.adjusted_risk !== undefined && chosenCorridorRisk !== undefined) && (
                    <div className="flex justify-between items-center bg-white border-2 border-black p-2 rounded-lg font-bold">
                      <span className="uppercase text-sm">Risk Score:</span>
                      <div className="flex items-center gap-2 font-mono">
                        <span className="text-slate-500">{chosenCorridorRisk}</span>
                        <ArrowRight size={16} />
                        <span className="text-brutal-pink">{impactMutation.data.adjusted_risk}</span>
                      </div>
                    </div>
                  )}

                  {(impactMutation.data.adjusted_clearance_minutes !== undefined && baseMinutes !== undefined) && (
                    <div className="flex justify-between items-center bg-white border-2 border-black p-2 rounded-lg font-bold">
                      <span className="uppercase text-sm">Clearance Time:</span>
                      <div className="flex items-center gap-2 font-mono">
                        <span className="text-slate-500">{baseMinutes} min</span>
                        <ArrowRight size={16} />
                        <span className="text-brutal-blue">{impactMutation.data.adjusted_clearance_minutes} min</span>
                      </div>
                    </div>
                  )}

                  {chosenCorridorRisk === undefined && baseMinutes === undefined && (
                    <p className="text-sm font-semibold">
                      Event type <span className="font-mono bg-white px-1 border border-black rounded">{impactMutation.data.event_type}</span> increases risks and clearance times by a factor of {impactMutation.data.multiplier}.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Panel B: Resource Planner */}
        <div className="brutal-card border-[6px] bg-white p-6 flex flex-col">
          <h2 className="text-2xl font-black uppercase mb-4 border-b-4 border-black pb-2 flex items-center gap-2">
            <Shield className="stroke-[3] text-brutal-green" />
            Resource Planner
          </h2>

          <form onSubmit={handleGeneratePlan} className="space-y-4 flex-1 flex flex-col">
            <div>
              <label className="block text-sm font-black uppercase mb-1">Expected Attendees</label>
              <input
                type="number"
                min="0"
                required
                value={attendees}
                onChange={e => setAttendees(parseInt(e.target.value) || 0)}
                className="w-full border-4 border-black rounded p-2 text-md font-bold focus:outline-none focus:ring-4 focus:ring-brutal-blue bg-white shadow-[4px_4px_0_0_#000]"
              />
            </div>

            <div>
              <label className="block text-sm font-black uppercase mb-1">Required Road Closures</label>
              <input
                type="number"
                min="0"
                required
                value={roadClosures}
                onChange={e => setRoadClosures(parseInt(e.target.value) || 0)}
                className="w-full border-4 border-black rounded p-2 text-md font-bold focus:outline-none focus:ring-4 focus:ring-brutal-blue bg-white shadow-[4px_4px_0_0_#000]"
              />
            </div>

            <div>
              <label className="block text-sm font-black uppercase mb-1">Event Type (Optional)</label>
              <select
                value={plannerEventType}
                onChange={e => setPlannerEventType(e.target.value)}
                className="w-full border-4 border-black rounded p-2 text-md font-bold focus:outline-none focus:ring-4 focus:ring-brutal-blue bg-white shadow-[4px_4px_0_0_#000]"
              >
                <option value="">Normal (None)</option>
                {eventTypesData?.event_types?.map(t => (
                  <option key={t} value={t}>{t.replace(/_/g, ' ').toUpperCase()}</option>
                ))}
              </select>
            </div>

            {plannerError && (
              <div className="bg-brutal-pink text-white font-bold border-4 border-black p-3 text-center uppercase shadow-[4px_4px_0_0_#000] flex items-center justify-center gap-2">
                <AlertTriangle />
                {plannerError}
              </div>
            )}

            <div className="pt-2">
              <button
                type="submit"
                disabled={resourceMutation.isPending}
                className="w-full brutal-btn bg-brutal-green text-white hover:opacity-90 disabled:opacity-50 text-lg"
              >
                {resourceMutation.isPending ? 'Generating...' : 'Generate Plan'}
              </button>
            </div>
          </form>

          {/* Results section */}
          {resourceMutation.data && (
            <div className="mt-6 border-4 border-black p-4 rounded-xl bg-brutal-bg shadow-[4px_4px_0_0_#000] text-black flex flex-col gap-4">
              <div className="flex justify-between items-center border-b-2 border-black pb-2">
                <h3 className="text-xl font-black uppercase">Deployment Plan</h3>
                {resourceMutation.data.note && (
                  <span
                    title={resourceMutation.data.note}
                    className="cursor-help inline-flex items-center gap-1 text-xs bg-white border-2 border-black px-2 py-0.5 rounded font-mono shadow-[2px_2px_0_0_rgba(0,0,0,1)] hover:bg-slate-50"
                  >
                    <Info size={12} /> Info
                  </span>
                )}
              </div>

              <div className="grid grid-cols-3 gap-3">
                {/* Officers Stat */}
                <div className="flex flex-col items-center bg-white border-2 border-black p-3 rounded-lg text-center">
                  <Shield size={24} className="text-brutal-blue mb-1" />
                  <span className="text-[10px] uppercase font-black text-slate-500">Officers</span>
                  <span className="text-xl font-black">{resourceMutation.data.officers}</span>
                  <span className="text-[9px] font-bold text-slate-400 font-mono">
                    (base {resourceMutation.data.officers_base})
                  </span>
                </div>

                {/* Barricades Stat */}
                <div className="flex flex-col items-center bg-white border-2 border-black p-3 rounded-lg text-center">
                  <Construction size={24} className="text-brutal-yellow mb-1" />
                  <span className="text-[10px] uppercase font-black text-slate-500">Barricades</span>
                  <span className="text-xl font-black">{resourceMutation.data.barricades}</span>
                </div>

                {/* Tow Trucks Stat */}
                <div className="flex flex-col items-center bg-white border-2 border-black p-3 rounded-lg text-center">
                  <Truck size={24} className="text-brutal-pink mb-1" />
                  <span className="text-[10px] uppercase font-black text-slate-500">Tow Trucks</span>
                  <span className="text-xl font-black">{resourceMutation.data.tow_trucks}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
