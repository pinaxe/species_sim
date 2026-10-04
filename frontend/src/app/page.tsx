'use client';

import { useState, useEffect } from 'react';
import { MapIcon, Settings, Play, Pause, RotateCcw } from 'lucide-react';
import SimulatorMap from '@/components/map/SimulatorMap';
import WizardSidebar from '@/components/panels/WizardSidebar';
import AnalyticsPanel from '@/components/panels/AnalyticsPanel';
import TimelineHUD from '@/components/hud/TimelineHUD';
import {
  MultiSpeciesConfig,
  MultiSpeciesProgress,
  MultiSpeciesSnapshot,
  SimulationConfig,
  SimulationProgress,
  SimulationSnapshot,
} from '@/lib/types';
import { bioSimAPI } from '@/lib/api';
import { speciesColor } from '@/lib/speciesColors';

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [proMode, setProMode] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [resultMode, setResultMode] = useState<'single' | 'multi'>('single');
  const [simulationProgress, setSimulationProgress] = useState<SimulationProgress | null>(null);
  const [snapshots, setSnapshots] = useState<SimulationSnapshot[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [currentConfig, setCurrentConfig] = useState<SimulationConfig | null>(null);

  const [multiProgress, setMultiProgress] = useState<MultiSpeciesProgress | null>(null);
  const [multiSnapshots, setMultiSnapshots] = useState<MultiSpeciesSnapshot[]>([]);
  const [multiConfig, setMultiConfig] = useState<MultiSpeciesConfig | null>(null);

  const handleRunSimulation = async (config: SimulationConfig) => {
    setResultMode('single');
    setCurrentConfig(config);
    setMultiConfig(null);
    setMultiSnapshots([]);
    setIsRunning(true);
    setSnapshots([]);
    setCurrentStep(0);

    let stepCount = 0;

    try {
      await bioSimAPI.runSimulation(config, (progress) => {
        // Debug: log received data
        if (stepCount === 0 || stepCount % 10 === 0) {
          console.log(`Step ${progress.step}:`, {
            population: progress.current_snapshot?.total_abundance,
            cells: progress.current_snapshot?.occupied_cells,
            range: progress.current_snapshot?.front_distance_km,
            density: progress.current_snapshot?.max_density,
          });
        }

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

  const handleRunMultiSpeciesSimulation = async (config: MultiSpeciesConfig) => {
    setResultMode('multi');
    setMultiConfig(config);
    setCurrentConfig(null);
    setSnapshots([]);
    setIsRunning(true);
    setMultiSnapshots([]);
    setCurrentStep(0);

    let stepCount = 0;

    try {
      await bioSimAPI.runMultiSpeciesSimulation(config, (progress) => {
        const delay = stepCount * 150; // 150ms per step, matches single-species pacing
        stepCount++;

        setTimeout(() => {
          setMultiProgress(progress);
          setMultiSnapshots((prev) => [...prev, progress.current_snapshot]);
          setCurrentStep(progress.step);
        }, delay);
      });
    } catch (error) {
      console.error('Multi-species simulation failed:', error);
    } finally {
      setTimeout(() => setIsRunning(false), stepCount * 150);
    }
  };

  const handleReset = () => {
    setSnapshots([]);
    setMultiSnapshots([]);
    setCurrentStep(0);
    setSimulationProgress(null);
    setMultiProgress(null);
    setIsRunning(false);
  };

  const isMulti = resultMode === 'multi';
  const hasResults = isMulti ? multiSnapshots.length > 0 : snapshots.length > 0;
  const totalSteps = isMulti
    ? multiProgress?.total_steps ?? multiConfig?.n_steps ?? 50
    : simulationProgress?.total_steps ?? 50;
  const speciesNames = multiConfig?.species.map((s) => s.name) ?? [];
  const currentMultiSnapshot = multiSnapshots[currentStep];

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
            onRunMultiSpeciesSimulation={handleRunMultiSpeciesSimulation}
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
            {hasResults && (
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
            <SimulatorMap
              snapshots={snapshots}
              multiSnapshots={isMulti ? multiSnapshots : undefined}
              speciesNames={isMulti ? speciesNames : undefined}
              currentStep={currentStep}
              config={currentConfig || undefined}
              multiConfig={isMulti ? multiConfig || undefined : undefined}
            />

            {hasResults && !isMulti && (
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

            {hasResults && isMulti && currentMultiSnapshot && (
              <div className="bg-slate-700 rounded-lg p-4 border border-slate-600 space-y-3">
                <div className="flex justify-between items-center">
                  <h3 className="font-semibold text-sm text-emerald-300">
                    {isRunning ? '▶ Running Simulation' : '✓ Simulation Complete'}
                  </h3>
                  {isRunning && <span className="text-xs text-slate-400 animate-pulse">Live update...</span>}
                </div>

                {isRunning && (
                  <div className="w-full bg-slate-600 rounded overflow-hidden h-2">
                    <div
                      className="bg-emerald-500 h-full transition-all"
                      style={{ width: `${(currentStep / totalSteps) * 100}%` }}
                    />
                  </div>
                )}

                <div className="flex justify-between items-center py-2 border-b border-slate-600 text-sm">
                  <span className="text-slate-400">Progress:</span>
                  <span className="font-mono font-bold text-emerald-300 text-base">
                    Step {currentStep + 1} / {totalSteps}
                  </span>
                </div>

                <div className="space-y-2">
                  {speciesNames.map((name, i) => {
                    const snap = currentMultiSnapshot.species[name];
                    if (!snap) return null;
                    return (
                      <div
                        key={name}
                        className="flex items-center justify-between py-2 bg-slate-600 bg-opacity-50 px-3 rounded"
                      >
                        <span className="flex items-center gap-2 text-slate-300 text-sm">
                          <span
                            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                            style={{ backgroundColor: speciesColor(i) }}
                          />
                          {name}
                        </span>
                        <span className="font-mono font-bold text-xl" style={{ color: speciesColor(i) }}>
                          {snap.total_abundance.toFixed(0)}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {!isRunning && (
                  <div className="border-t border-slate-600 pt-3 mt-3">
                    <p className="text-xs text-slate-400 mb-2">📈 Growth Summary:</p>
                    <ul className="text-xs text-slate-300 space-y-1">
                      {speciesNames.map((name) => {
                        const first = multiSnapshots[0]?.species[name];
                        const last = multiSnapshots[multiSnapshots.length - 1]?.species[name];
                        if (!first || !last) return null;
                        const pct = first.total_abundance
                          ? ((last.total_abundance - first.total_abundance) / first.total_abundance) * 100
                          : 0;
                        return (
                          <li key={name}>
                            ✓ {name}: {first.total_abundance.toFixed(0)} → {last.total_abundance.toFixed(0)} ({pct >= 0 ? '+' : ''}{pct.toFixed(0)}%)
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {hasResults && (
            <div className="w-80 overflow-y-auto">
              <AnalyticsPanel
                snapshots={snapshots}
                multiSnapshots={isMulti ? multiSnapshots : undefined}
                speciesNames={isMulti ? speciesNames : undefined}
                currentStep={currentStep}
              />
            </div>
          )}
        </div>

        {/* Timeline HUD */}
        {hasResults && (
          <div className="bg-slate-800 border-t border-slate-700 p-4">
            <TimelineHUD
              totalSteps={isMulti ? multiSnapshots.length : snapshots.length}
              currentStep={currentStep}
              onStepChange={setCurrentStep}
              isRunning={isRunning}
              year={isMulti ? currentMultiSnapshot?.time ?? 0 : snapshots[currentStep]?.time ?? 0}
              abundanceLabel={
                isMulti
                  ? speciesNames
                      .map((n) => `${n}: ${currentMultiSnapshot?.species[n]?.total_abundance.toFixed(0) ?? 0}`)
                      .join('  ·  ')
                  : (snapshots[currentStep]?.total_abundance ?? 0).toFixed(0)
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}
