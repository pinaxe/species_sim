'use client';

import { SimulationSnapshot } from '@/lib/types';

interface AnalyticsPanelProps {
  snapshots: SimulationSnapshot[];
  currentStep: number;
}

export default function AnalyticsPanel({ snapshots, currentStep }: AnalyticsPanelProps) {
  const snapshot = snapshots[currentStep];
  const finalSnapshot = snapshots[snapshots.length - 1];

  if (!snapshot) return null;

  // Calculate growth rate
  const growthRate = snapshots.length > 1
    ? ((finalSnapshot.total_abundance - snapshots[0].total_abundance) / snapshots[0].total_abundance * 100)
    : 0;

  return (
    <div className="space-y-4">
      <div className="bg-slate-700 rounded-lg p-4 space-y-4">
        <h3 className="font-semibold text-sm text-emerald-400">📊 Current Step</h3>

        <div className="grid gap-3">
          <div>
            <div className="text-xs text-slate-400">Time Step</div>
            <div className="text-lg font-mono font-bold">{currentStep + 1} / {snapshots.length}</div>
          </div>

          <div>
            <div className="text-xs text-slate-400">Population</div>
            <div className="text-lg font-mono font-bold text-emerald-300">
              {snapshot.total_abundance.toFixed(0)}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-400">Occupied Cells</div>
            <div className="text-lg font-mono font-bold text-emerald-300">
              {snapshot.occupied_cells}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-400">Max Density</div>
            <div className="text-lg font-mono font-bold text-emerald-300">
              {snapshot.max_density.toFixed(0)}
            </div>
          </div>

          <div>
            <div className="text-xs text-slate-400">Range Edge Distance</div>
            <div className="text-lg font-mono font-bold text-emerald-300">
              {snapshot.front_distance_km.toFixed(1)} km
            </div>
          </div>
        </div>
      </div>

      <div className="bg-slate-700 rounded-lg p-4 space-y-3">
        <h3 className="font-semibold text-sm text-emerald-400">📈 Final Results</h3>

        <div className="grid gap-3 text-xs">
          <div>
            <div className="text-slate-400">Population Growth</div>
            <div className="font-mono text-emerald-300">
              {growthRate > 0 ? '+' : ''}{growthRate.toFixed(1)}%
            </div>
          </div>

          <div>
            <div className="text-slate-400">Expansion Speed</div>
            <div className="font-mono text-emerald-300">
              {(finalSnapshot.front_distance_km / snapshots.length).toFixed(2)} km/step
            </div>
          </div>

          <div>
            <div className="text-slate-400">Invasiveness Score</div>
            <div className="font-mono text-emerald-300">
              {(finalSnapshot.occupied_cells > 50 ? 'High' : finalSnapshot.occupied_cells > 20 ? 'Medium' : 'Low')}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-slate-700 rounded-lg p-4">
        <h3 className="font-semibold text-sm mb-3 text-emerald-400">📉 Abundance Curve</h3>
        <div className="h-40 bg-slate-600 rounded flex items-end justify-between p-2 gap-1">
          {snapshots.map((s, i) => (
            <div
              key={i}
              className={`flex-1 rounded-t transition-all ${
                i === currentStep ? 'bg-emerald-400 shadow-lg shadow-emerald-500' : 'bg-emerald-700 opacity-70'
              }`}
              style={{
                height: `${(s.total_abundance / Math.max(...snapshots.map(x => x.total_abundance)) || 1) * 100}%`,
                minHeight: '2px',
              }}
              title={`Step ${i}: ${s.total_abundance.toFixed(0)}`}
            />
          ))}
        </div>
        <p className="text-xs text-slate-400 mt-2">← Drag timeline to scrub →</p>
      </div>
    </div>
  );
}
