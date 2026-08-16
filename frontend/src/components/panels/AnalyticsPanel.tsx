'use client';

import { SimulationSnapshot } from '@/lib/types';

interface AnalyticsPanelProps {
  snapshots: SimulationSnapshot[];
  currentStep: number;
}

export default function AnalyticsPanel({ snapshots, currentStep }: AnalyticsPanelProps) {
  const snapshot = snapshots[currentStep];

  if (!snapshot) return null;

  return (
    <div className="space-y-4">
      <div className="bg-slate-700 rounded-lg p-4 space-y-3">
        <h3 className="font-semibold text-sm">Invasion Metrics</h3>

        <div>
          <div className="text-xs text-slate-400">Total Abundance</div>
          <div className="text-lg font-mono font-bold">
            {snapshot.total_abundance.toFixed(0)}
          </div>
        </div>

        <div>
          <div className="text-xs text-slate-400">Occupied Cells</div>
          <div className="text-lg font-mono font-bold">
            {snapshot.occupied_cells}
          </div>
        </div>

        <div>
          <div className="text-xs text-slate-400">Front Distance</div>
          <div className="text-lg font-mono font-bold">
            {snapshot.front_distance_km.toFixed(1)} km
          </div>
        </div>

        <div>
          <div className="text-xs text-slate-400">Max Density</div>
          <div className="text-lg font-mono font-bold">
            {snapshot.max_density.toFixed(0)}
          </div>
        </div>
      </div>

      <div className="bg-slate-700 rounded-lg p-4">
        <h3 className="font-semibold text-sm mb-3">Population Trend</h3>
        <div className="h-40 bg-slate-600 rounded flex items-end justify-between p-2 gap-1">
          {snapshots.map((s, i) => (
            <div
              key={i}
              className={`flex-1 rounded-t transition-colors ${
                i === currentStep ? 'bg-emerald-500' : 'bg-emerald-700'
              }`}
              style={{
                height: `${(s.total_abundance / Math.max(...snapshots.map(x => x.total_abundance)) || 1) * 100}%`,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
