'use client';

import { useState, useEffect } from 'react';
import { MapIcon, Settings, Play, Pause, RotateCcw } from 'lucide-react';
import SimulatorMap from '@/components/map/SimulatorMap';
import WizardSidebar from '@/components/panels/WizardSidebar';
import AnalyticsPanel from '@/components/panels/AnalyticsPanel';
import TimelineHUD from '@/components/hud/TimelineHUD';
import { SimulationConfig, SimulationProgress, SimulationSnapshot } from '@/lib/types';
import { bioSimAPI } from '@/lib/api';

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [proMode, setProMode] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [simulationProgress, setSimulationProgress] = useState<SimulationProgress | null>(null);
  const [snapshots, setSnapshots] = useState<SimulationSnapshot[]>([]);
  const [currentStep, setCurrentStep] = useState(0);

  const handleRunSimulation = async (config: SimulationConfig) => {
    setIsRunning(true);
    setSnapshots([]);
    setCurrentStep(0);

    let stepCount = 0;

    try {
      await bioSimAPI.runSimulation(config, (progress) => {
        // Delay each update with cumulative delay so steps animate sequentially
        const delay = stepCount * 150; // 150ms per step
        stepCount++;

        setTimeout(() => {
          setSimulationProgress(progress);
          setSnapshots((prev) => [...prev, progress.current_snapshot]);
          setCurrentStep(progress.step);
        }, delay);
      });
    } catch (error) {
      console.error('Simulation failed:', error);
    } finally {
      // Wait for all animations to complete before marking as done
      setTimeout(() => setIsRunning(false), stepCount * 150);
    }
  };

  const handleReset = () => {
    setSnapshots([]);
    setCurrentStep(0);
    setSimulationProgress(null);
    setIsRunning(false);
  };

  return (
    <div className="flex h-screen bg-slate-900 text-slate-50">
      {/* Sidebar */}
      <div
        className={`transition-all duration-300 ${
          sidebarOpen ? 'w-96' : 'w-0'
        } overflow-hidden bg-slate-800 border-r border-slate-700 flex flex-col`}
      >
        {sidebarOpen && (
          <WizardSidebar
            onRunSimulation={handleRunSimulation}
            proMode={proMode}
            onProModeChange={setProMode}
            isRunning={isRunning}
          />
        )}
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-slate-800 border-b border-slate-700 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-slate-700 rounded transition-colors"
            >
              <MapIcon className="w-5 h-5" />
            </button>
            <h1 className="text-lg font-semibold">BioSim-Engine</h1>
            <span className="text-xs text-slate-400">Drop • Seed • Simulate</span>
          </div>

          <div className="flex items-center gap-2">
            {snapshots.length > 0 && (
              <>
                <button
                  onClick={() => setIsRunning(!isRunning)}
                  className="p-2 hover:bg-slate-700 rounded transition-colors"
                >
                  {isRunning ? (
                    <Pause className="w-5 h-5" />
                  ) : (
                    <Play className="w-5 h-5" />
                  )}
                </button>
                <button
                  onClick={handleReset}
                  className="p-2 hover:bg-slate-700 rounded transition-colors"
                >
                  <RotateCcw className="w-5 h-5" />
                </button>
              </>
            )}
            <button className="p-2 hover:bg-slate-700 rounded transition-colors">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Map and Analytics */}
        <div className="flex-1 flex gap-4 p-4 overflow-hidden">
          <div className="flex-1 flex flex-col gap-4">
            <SimulatorMap snapshots={snapshots} currentStep={currentStep} />

            {snapshots.length > 0 && (
              <div className="bg-slate-700 rounded-lg p-4 border border-slate-600 space-y-3">
                <div className="flex justify-between items-center">
                  <h3 className="font-semibold text-sm text-emerald-300">
                    {isRunning ? '▶ Running Simulation' : '✓ Simulation Complete'}
                  </h3>
                  {isRunning && <span className="text-xs text-slate-400 animate-pulse">Live update...</span>}
                </div>

                {/* Progress Bar */}
                {isRunning && (
                  <div className="w-full bg-slate-600 rounded overflow-hidden h-2">
                    <div
                      className="bg-emerald-500 h-full transition-all"
                      style={{ width: `${(currentStep / (simulationProgress?.total_steps || 50)) * 100}%` }}
                    />
                  </div>
                )}

                <div className="space-y-3 text-sm">
                  <div className="flex justify-between items-center py-2 border-b border-slate-600">
                    <span className="text-slate-400">Progress:</span>
                    <span className="font-mono font-bold text-emerald-300 text-base">
                      Step {currentStep + 1} / {simulationProgress?.total_steps || 50}
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-2 bg-slate-600 bg-opacity-50 px-2 rounded">
                    <span className="text-slate-300">📊 Population:</span>
                    <span className="font-mono font-bold text-emerald-400 text-xl min-w-fit">
                      {(simulationProgress?.current_snapshot?.total_abundance || snapshots[currentStep]?.total_abundance || 0).toFixed(0)}
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-2 bg-slate-600 bg-opacity-50 px-2 rounded">
                    <span className="text-slate-300">🗺️ Area:</span>
                    <span className="font-mono font-bold text-emerald-400 text-xl min-w-fit">
                      {(simulationProgress?.current_snapshot?.occupied_cells || snapshots[currentStep]?.occupied_cells || 0)} cells
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-2 bg-slate-600 bg-opacity-50 px-2 rounded">
                    <span className="text-slate-300">📍 Range:</span>
                    <span className="font-mono font-bold text-emerald-400 text-xl min-w-fit">
                      {(simulationProgress?.current_snapshot?.front_distance_km || snapshots[currentStep]?.front_distance_km || 0).toFixed(1)} km
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-2 bg-slate-600 bg-opacity-50 px-2 rounded">
                    <span className="text-slate-300">👥 Max Density:</span>
                    <span className="font-mono font-bold text-emerald-400 text-base min-w-fit">
                      {(simulationProgress?.current_snapshot?.max_density || snapshots[currentStep]?.max_density || 0).toFixed(0)}
                    </span>
                  </div>
                </div>

                {!isRunning && (
                  <div className="border-t border-slate-600 pt-3 mt-3">
                    <p className="text-xs text-slate-400 mb-2">📈 Growth Summary:</p>
                    <ul className="text-xs text-slate-300 space-y-1">
                      <li>✓ Population: {snapshots[0]?.total_abundance.toFixed(0)} → {snapshots[snapshots.length - 1]?.total_abundance.toFixed(0)} (+{((snapshots[snapshots.length - 1]?.total_abundance || 0 - snapshots[0]?.total_abundance || 1) / (snapshots[0]?.total_abundance || 1) * 100).toFixed(0)}%)</li>
                      <li>✓ Area: {snapshots[snapshots.length - 1]?.occupied_cells} cells invaded</li>
                      <li>✓ Range: {snapshots[snapshots.length - 1]?.front_distance_km.toFixed(1)} km spread</li>
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {snapshots.length > 0 && (
            <div className="w-80 overflow-y-auto">
              <AnalyticsPanel snapshots={snapshots} currentStep={currentStep} />
            </div>
          )}
        </div>

        {/* Timeline HUD */}
        {snapshots.length > 0 && (
          <div className="bg-slate-800 border-t border-slate-700 p-4">
            <TimelineHUD
              snapshots={snapshots}
              currentStep={currentStep}
              onStepChange={setCurrentStep}
              isRunning={isRunning}
            />
          </div>
        )}
      </div>
    </div>
  );
}
