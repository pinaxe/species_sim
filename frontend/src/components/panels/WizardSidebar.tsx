'use client';

import { useState } from 'react';
import { ChevronRight, Zap } from 'lucide-react';
import { SimulationConfig } from '@/lib/types';

interface WizardSidebarProps {
  onRunSimulation: (config: SimulationConfig) => void;
  proMode: boolean;
  onProModeChange: (enabled: boolean) => void;
  isRunning: boolean;
}

export default function WizardSidebar({
  onRunSimulation,
  proMode,
  onProModeChange,
  isRunning,
}: WizardSidebarProps) {
  const [step, setStep] = useState(1);

  const handleRunDemo = () => {
    const config: SimulationConfig = {
      region: 'demo',
      species_name: 'Demo Species',
      bbox: [-125, 25, -66, 49],
      resolution_deg: 0.25,
      temperature_opt: 15,
      temperature_sigma: 8,
      precipitation_opt: 900,
      precipitation_sigma: 300,
      niche_floor: 0.1,
      carrying_capacity: 1000,
      demography: { r: 0.1, m: 0.05 },
      dispersal: {
        kernel_type: 'gaussian',
        sigma: 10,
        fraction: 0.1,
      },
      n_steps: 100,
    };
    onRunSimulation(config);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-4 border-b border-slate-700">
        <h2 className="text-lg font-bold text-emerald-400">Welcome</h2>
        <p className="text-xs text-slate-400 mt-1">3-Step Quick Start</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
        {/* Step 1 */}
        <div className={`space-y-2 p-3 rounded ${step === 1 ? 'bg-slate-700' : ''}`}>
          <button
            onClick={() => setStep(1)}
            className="flex items-center justify-between w-full text-left"
          >
            <span className="font-semibold">1. Pick a Species</span>
            <ChevronRight className="w-4 h-4" />
          </button>
          {step === 1 && (
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Search species..."
                className="w-full px-3 py-2 bg-slate-600 rounded text-sm placeholder-slate-400 text-slate-100"
              />
              <p className="text-xs text-slate-400">Or try a preset...</p>
            </div>
          )}
        </div>

        {/* Step 2 */}
        <div className={`space-y-2 p-3 rounded ${step === 2 ? 'bg-slate-700' : ''}`}>
          <button
            onClick={() => setStep(2)}
            className="flex items-center justify-between w-full text-left"
          >
            <span className="font-semibold">2. Choose a Region</span>
            <ChevronRight className="w-4 h-4" />
          </button>
          {step === 2 && (
            <div className="text-xs text-slate-400">
              Region selector coming soon...
            </div>
          )}
        </div>

        {/* Step 3 */}
        <div className={`space-y-2 p-3 rounded ${step === 3 ? 'bg-slate-700' : ''}`}>
          <button
            onClick={() => setStep(3)}
            className="flex items-center justify-between w-full text-left"
          >
            <span className="font-semibold">3. Simulate & Explore</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <button
          onClick={handleRunDemo}
          disabled={isRunning}
          className="w-full px-4 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded font-semibold text-sm transition-colors flex items-center justify-center gap-2"
        >
          <Zap className="w-4 h-4" />
          Run Demo Simulation
        </button>
      </div>

      {/* Footer */}
      <div className="border-t border-slate-700 px-4 py-3">
        <label className="flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={proMode}
            onChange={(e) => onProModeChange(e.target.checked)}
            className="rounded"
          />
          <span>Pro Mode (Advanced)</span>
        </label>
      </div>
    </div>
  );
}
