'use client';

import { useEffect, useRef } from 'react';
import { SimulationSnapshot } from '@/lib/types';

interface SimulatorMapProps {
  snapshots: SimulationSnapshot[];
  currentStep: number;
}

export default function SimulatorMap({ snapshots, currentStep }: SimulatorMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // MapLibre + Deck.gl initialization would go here
    // For now, show a placeholder
  }, [snapshots, currentStep]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full bg-gradient-to-br from-slate-700 to-slate-900 rounded-lg flex items-center justify-center border border-slate-600"
    >
      <div className="text-center">
        <div className="text-4xl mb-2">🗺️</div>
        <p className="text-slate-300">Interactive Map</p>
        <p className="text-slate-400 text-sm">MapLibre GL + Deck.gl will render here</p>
        {snapshots.length > 0 && (
          <div className="mt-4 text-slate-300 text-xs">
            Step {currentStep + 1} / {snapshots.length}
            <br />
            Abundance: {snapshots[currentStep]?.total_abundance.toFixed(0)}
          </div>
        )}
      </div>
    </div>
  );
}
