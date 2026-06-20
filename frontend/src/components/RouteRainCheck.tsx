import { useState } from 'react';
import RainRiskWidget from './RainRiskWidget';

const CORRIDORS = [
  'Sarjapur Road', 'ORR East', 'ORR West', 'Hosur Road', 'Old Madras Road',
  'Mysore Road', 'MG Road', 'Residency Road', 'Bellary Road', 'Kanakapura Road',
  'Brigade Road', 'Richmond Road', 'Tumkur Road', 'Magadi Road',
];

export default function RouteRainCheck() {
  const [corridor, setCorridor] = useState<string>('Sarjapur Road');

  return (
    <div className="shrink-0 brutal-card border-[6px] bg-white p-4">
      <h2 className="text-lg font-black uppercase mb-2">Check your route</h2>
      <select
        value={corridor}
        onChange={(e) => setCorridor(e.target.value)}
        className="w-full border-4 border-black rounded p-2 text-sm font-bold mb-3 shadow-[2px_2px_0_0_rgba(0,0,0,1)] focus:outline-none focus:ring-4 focus:ring-brutal-blue bg-white"
      >
        {CORRIDORS.map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>
      <RainRiskWidget corridor={corridor} scope="citizen" />
    </div>
  );
}
