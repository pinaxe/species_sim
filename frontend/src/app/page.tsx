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

    try {
      await bioSimAPI.runSimulation(config, (progress) => {
        setSimulationProgress(progress);
        setSnapshots((prev) => [...prev, progress.current_snapshot]);
        setCurrentStep(progress.step);
      });
    } catch (error) {
      console.error('Simulation failed:', error);
    } finally {
      setIsRunning(false);
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
          <div className="flex-1">
            <SimulatorMap snapshots={snapshots} currentStep={currentStep} />
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
