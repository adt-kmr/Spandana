import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ClearApi } from '../api';
import type { CitizenReport } from '../types';
import { Send, AlertTriangle } from 'lucide-react';

export default function CitizenReportForm() {
  const [formData, setFormData] = useState<CitizenReport>({
    latitude: 12.9716,
    longitude: 77.5946,
    corridor: '',
    event_cause: 'breakdown',
    description: '',
  });

  const mutation = useMutation({
    mutationFn: (data: CitizenReport) => ClearApi.citizenReport(data),
    onSuccess: () => {
      setFormData({
        latitude: 12.9716,
        longitude: 77.5946,
        corridor: '',
        event_cause: 'breakdown',
        description: '',
      });
      alert('Report submitted successfully. Thank you!');
    },
    onError: (err) => {
      alert(`Failed to submit report: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  });

  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <h3 className="font-bold text-slate-800 flex items-center gap-2 mb-4">
        <AlertTriangle className="w-4 h-4 text-amber-500" />
        Report an Incident
      </h3>
      <form onSubmit={(e) => { e.preventDefault(); mutation.mutate(formData); }} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Corridor / Location</label>
          <input
            type="text"
            required
            value={formData.corridor}
            onChange={e => setFormData({ ...formData, corridor: e.target.value })}
            className="w-full border border-slate-300 rounded-md p-2 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            placeholder="e.g. Hosur Road"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Event Cause</label>
          <select
            value={formData.event_cause}
            onChange={e => setFormData({ ...formData, event_cause: e.target.value })}
            className="w-full border border-slate-300 rounded-md p-2 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          >
            <option value="breakdown">Breakdown</option>
            <option value="accident">Accident</option>
            <option value="tree_fall">Tree Fall</option>
            <option value="water_logging">Water Logging</option>
            <option value="pot_holes">Potholes</option>
            <option value="public_event">Public Event</option>
            <option value="others">Others</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Description (Optional)</label>
          <textarea
            value={formData.description}
            onChange={e => setFormData({ ...formData, description: e.target.value })}
            className="w-full border border-slate-300 rounded-md p-2 text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
            rows={3}
            placeholder="More details about the incident..."
          />
        </div>
        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold py-2 rounded-lg shadow-sm transition-all flex items-center justify-center gap-2"
        >
          <Send className="w-4 h-4" />
          {mutation.isPending ? 'Submitting...' : 'Submit Report'}
        </button>
      </form>
    </div>
  );
}
