'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';

interface TimelineHUDProps {
  totalSteps: number;
  currentStep: number;
  onStepChange: (step: number) => void;
  isRunning: boolean;
  year: number;
  abundanceLabel: string;
}

export default function TimelineHUD({
  totalSteps,
  currentStep,
  onStepChange,
  isRunning,
  year,
  abundanceLabel,
}: TimelineHUDProps) {
  const handlePrevStep = () => {
    if (currentStep > 0) {
      onStepChange(currentStep - 1);
    }
  };

  const handleNextStep = () => {
    if (currentStep < totalSteps - 1) {
      onStepChange(currentStep + 1);
    }
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onStepChange(Math.min(parseInt(e.target.value), totalSteps - 1));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <div>
          <span className="font-semibold">Year {year}</span>
          <span className="text-slate-400 ml-2">
            Step {currentStep + 1} / {totalSteps}
          </span>
        </div>
        <div className="text-xs text-slate-400">Abundance: {abundanceLabel}</div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handlePrevStep}
          disabled={isRunning || currentStep === 0}
          className="p-2 hover:bg-slate-700 disabled:opacity-50 rounded transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <input
          type="range"
          min="0"
          max={totalSteps - 1}
          value={currentStep}
          onChange={handleSliderChange}
          disabled={isRunning}
          className="flex-1 h-2 bg-slate-600 rounded appearance-none cursor-pointer disabled:opacity-50"
          style={{
            background: `linear-gradient(to right, rgb(16, 185, 129) 0%, rgb(16, 185, 129) ${
              (currentStep / (totalSteps - 1)) * 100
            }%, rgb(51, 65, 85) ${(currentStep / (totalSteps - 1)) * 100}%, rgb(51, 65, 85) 100%)`,
          }}
        />

        <button
          onClick={handleNextStep}
          disabled={isRunning || currentStep === totalSteps - 1}
          className="p-2 hover:bg-slate-700 disabled:opacity-50 rounded transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
