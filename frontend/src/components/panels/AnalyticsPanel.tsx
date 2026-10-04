'use client';

import { MultiSpeciesSnapshot, SimulationSnapshot } from '@/lib/types';
import { speciesColor } from '@/lib/speciesColors';

interface AnalyticsPanelProps {
  snapshots: SimulationSnapshot[];
  multiSnapshots?: MultiSpeciesSnapshot[];
  speciesNames?: string[];
  currentStep: number;
}

export default function AnalyticsPanel({
  snapshots,
  multiSnapshots,
  speciesNames,
  currentStep,
}: AnalyticsPanelProps) {
  if (multiSnapshots && speciesNames) {
    return (
      <MultiSpeciesAnalytics
        snapshots={multiSnapshots}
        speciesNames={speciesNames}
        currentStep={currentStep}
      />
    );
  }

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

function MultiSpeciesAnalytics({
  snapshots,
  speciesNames,
  currentStep,
}: {
  snapshots: MultiSpeciesSnapshot[];
  speciesNames: string[];
  currentStep: number;
}) {
  const snapshot = snapshots[currentStep];
  const firstSnapshot = snapshots[0];
  const finalSnapshot = snapshots[snapshots.length - 1];
  if (!snapshot) return null;

  const width = 280;
  const height = 140;
  const lastIndex = Math.max(1, snapshots.length - 1);

  const seriesMax: Record<string, number> = {};
  speciesNames.forEach((name) => {
    seriesMax[name] = Math.max(1, ...snapshots.map((s) => s.species[name]?.total_abundance ?? 0));
  });

  const xFor = (i: number) => (i / lastIndex) * width;
  const yFor = (name: string, i: number) => {
    const v = snapshots[i].species[name]?.total_abundance ?? 0;
    return height - (v / seriesMax[name]) * height;
  };
  const pointsFor = (name: string) =>
    snapshots.map((_, i) => `${xFor(i)},${yFor(name, i)}`).join(' ');

  return (
    <div className="space-y-4">
      <div className="bg-slate-700 rounded-lg p-4 space-y-3">
        <h3 className="font-semibold text-sm text-emerald-400">📊 Current Step</h3>
        <div className="text-xs text-slate-400">
          Time Step <span className="text-slate-100 font-mono font-bold">{currentStep + 1} / {snapshots.length}</span>
        </div>
        <div className="space-y-2">
          {speciesNames.map((name, i) => {
            const s = snapshot.species[name];
            if (!s) return null;
            return (
              <div key={name} className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-xs text-slate-400">
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: speciesColor(i) }} />
                  {name}
                </span>
                <span className="text-lg font-mono font-bold" style={{ color: speciesColor(i) }}>
                  {s.total_abundance.toFixed(0)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="bg-slate-700 rounded-lg p-4">
        <h3 className="font-semibold text-sm mb-1 text-emerald-400">📉 Population Curves</h3>
        <p className="text-xs text-slate-500 mb-2">
          Each line indexed to that species&apos; own peak (0-100%), so predator and prey of very
          different scale stay legible on one shared axis.
        </p>
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-36 bg-slate-600 rounded">
          {snapshots.length > 1 && (
            <line
              x1={xFor(currentStep)}
              x2={xFor(currentStep)}
              y1={0}
              y2={height}
              stroke="#94a3b8"
              strokeWidth={1}
              strokeDasharray="3,3"
            />
          )}
          {speciesNames.map((name, i) => (
            <polyline
              key={name}
              points={pointsFor(name)}
              fill="none"
              stroke={speciesColor(i)}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ))}
          {speciesNames.map((name, i) => (
            <circle
              key={name}
              cx={xFor(currentStep)}
              cy={yFor(name, currentStep)}
              r={3.5}
              fill={speciesColor(i)}
              stroke="#1a1a19"
              strokeWidth={1}
            >
              <title>
                {name} @ step {currentStep + 1}: {(snapshot.species[name]?.total_abundance ?? 0).toFixed(0)}
              </title>
            </circle>
          ))}
        </svg>
        <div className="flex flex-wrap gap-3 mt-2">
          {speciesNames.map((name, i) => (
            <span key={name} className="flex items-center gap-1.5 text-xs text-slate-300">
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: speciesColor(i) }} />
              {name}
            </span>
          ))}
        </div>
        <p className="text-xs text-slate-400 mt-2">← Drag timeline to scrub →</p>
      </div>

      {finalSnapshot && firstSnapshot && (
        <div className="bg-slate-700 rounded-lg p-4 space-y-2">
          <h3 className="font-semibold text-sm text-emerald-400">📈 Final Results</h3>
          <div className="grid gap-2 text-xs">
            {speciesNames.map((name) => {
              const first = firstSnapshot.species[name];
              const last = finalSnapshot.species[name];
              if (!first || !last) return null;
              const pct = first.total_abundance
                ? ((last.total_abundance - first.total_abundance) / first.total_abundance) * 100
                : 0;
              return (
                <div key={name} className="flex items-center justify-between">
                  <span className="flex items-center gap-2 text-slate-400">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: speciesColor(speciesNames.indexOf(name)) }} />
                    {name}: {first.total_abundance.toFixed(0)} → {last.total_abundance.toFixed(0)}
                  </span>
                  <span className="font-mono text-emerald-300">
                    {pct >= 0 ? '+' : ''}{pct.toFixed(0)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
