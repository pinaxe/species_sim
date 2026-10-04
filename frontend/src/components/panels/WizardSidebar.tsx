'use client';

import { useState, useEffect } from 'react';
import { ChevronRight, Zap, Search, Globe, Users } from 'lucide-react';
import { MultiSpeciesConfig, SimulationConfig, Taxon } from '@/lib/types';
import { bioSimAPI } from '@/lib/api';
import MultiSpeciesBuilder from './MultiSpeciesBuilder';

interface Region {
  id: string;
  name: string;
  bbox: [number, number, number, number];
  description: string;
  center: [number, number];
}

interface WizardSidebarProps {
  onRunSimulation: (config: SimulationConfig) => void;
  onRunMultiSpeciesSimulation: (config: MultiSpeciesConfig) => void;
  proMode: boolean;
  onProModeChange: (enabled: boolean) => void;
  isRunning: boolean;
}

const REGIONS: Region[] = [
  {
    id: 'contiguous_usa',
    name: 'Contiguous USA',
    bbox: [-125, 25, -66, 49],
    description: 'Continental United States',
    center: [-95.5, 37],
  },
  {
    id: 'europe',
    name: 'Europe',
    bbox: [-10, 35, 40, 71],
    description: 'European continent',
    center: [15, 53],
  },
  {
    id: 'africa',
    name: 'Africa',
    bbox: [-17, -35, 52, 37],
    description: 'African continent',
    center: [17.5, 1],
  },
  {
    id: 'asia',
    name: 'Asia',
    bbox: [50, -10, 150, 70],
    description: 'Asian continent',
    center: [100, 30],
  },
  {
    id: 'australia',
    name: 'Australia',
    bbox: [113, -44, 154, -10],
    description: 'Australia & Oceania',
    center: [133.5, -27],
  },
  {
    id: 'south_america',
    name: 'South America',
    bbox: [-82, -56, -35, 13],
    description: 'South American continent',
    center: [-58.5, -15],
  },
];

export default function WizardSidebar({
  onRunSimulation,
  onRunMultiSpeciesSimulation,
  proMode,
  onProModeChange,
  isRunning,
}: WizardSidebarProps) {
  const [mode, setMode] = useState<'single' | 'multi'>('single');
  const [step, setStep] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Taxon[]>([]);
  const [selectedSpecies, setSelectedSpecies] = useState<Taxon | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState<Region>(REGIONS[0]);

  // Search species when query changes
  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await bioSimAPI.searchTaxa(searchQuery, 5);
        setSearchResults(results);
      } catch (error) {
        console.error('Search failed:', error);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300); // Debounce 300ms

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleSelectSpecies = (species: Taxon) => {
    setSelectedSpecies(species);
    setSearchQuery('');
    setSearchResults([]);
  };

  const handleSelectRegion = (region: Region) => {
    setSelectedRegion(region);
  };

  const handleRunSimulation = () => {
    const config: SimulationConfig = {
      region: selectedRegion.id,
      species_name: selectedSpecies?.name || 'Demo Species',
      bbox: selectedRegion.bbox,
      resolution_deg: 0.25,
      temperature_opt: 15,
      temperature_sigma: 15,
      precipitation_opt: 1000,
      precipitation_sigma: 500,
      niche_floor: 0.01,
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
      <div className="px-4 py-4 border-b border-slate-700 space-y-3">
        <div>
          <h2 className="text-lg font-bold text-emerald-400">Welcome</h2>
          <p className="text-xs text-slate-400 mt-1">
            {mode === 'single' ? '3-Step Quick Start' : 'Build a food web and watch it balance'}
          </p>
        </div>
        <div className="flex gap-1 bg-slate-900 rounded p-1">
          <button
            onClick={() => setMode('single')}
            className={`flex-1 text-xs font-medium py-1.5 rounded transition-colors ${
              mode === 'single' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Single species
          </button>
          <button
            onClick={() => setMode('multi')}
            className={`flex-1 text-xs font-medium py-1.5 rounded transition-colors flex items-center justify-center gap-1 ${
              mode === 'multi' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Users className="w-3 h-3" /> Multi-species
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {mode === 'multi' && (
          <MultiSpeciesBuilder
            regions={REGIONS}
            onRunSimulation={onRunMultiSpeciesSimulation}
            isRunning={isRunning}
          />
        )}

        {mode === 'single' && (
        <>
        {/* Step 1 */}
        <div className={`space-y-2 p-3 rounded transition-colors ${step === 1 ? 'bg-slate-700' : 'hover:bg-slate-800'}`}>
          <button
            onClick={() => setStep(1)}
            className="flex items-center justify-between w-full text-left"
          >
            <span className="font-semibold">1. Pick a Species</span>
            {selectedSpecies && <span className="text-xs text-emerald-400">✓</span>}
            <ChevronRight className="w-4 h-4" />
          </button>

          {step === 1 && (
            <div className="space-y-2">
              <div className="relative">
                <div className="absolute left-2 top-2.5">
                  <Search className="w-3 h-3 text-slate-400" />
                </div>
                <input
                  type="text"
                  placeholder="e.g. Quercus alba..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-7 pr-3 py-2 bg-slate-600 rounded text-sm placeholder-slate-400 text-slate-100"
                />
              </div>

              {selectedSpecies && (
                <div className="p-2 bg-emerald-900 bg-opacity-30 rounded border border-emerald-600">
                  <p className="text-sm font-semibold text-emerald-300">{selectedSpecies.name}</p>
                  {selectedSpecies.canonicalName && (
                    <p className="text-xs text-slate-400">{selectedSpecies.canonicalName}</p>
                  )}
                </div>
              )}

              {isSearching && (
                <p className="text-xs text-slate-400 animate-pulse">Searching...</p>
              )}

              {searchResults.length > 0 && (
                <div className="bg-slate-600 rounded max-h-40 overflow-y-auto">
                  {searchResults.map((species) => (
                    <button
                      key={species.key}
                      onClick={() => handleSelectSpecies(species)}
                      className="w-full text-left px-3 py-2 hover:bg-slate-500 transition-colors border-b border-slate-700 last:border-b-0"
                    >
                      <p className="text-sm font-medium text-slate-100">{species.name}</p>
                      {species.canonicalName && (
                        <p className="text-xs text-slate-400">{species.canonicalName}</p>
                      )}
                    </button>
                  ))}
                </div>
              )}

              {searchQuery.length >= 2 && searchResults.length === 0 && !isSearching && (
                <p className="text-xs text-slate-400">No species found</p>
              )}
            </div>
          )}
        </div>

        {/* Step 2 */}
        <div className={`space-y-2 p-3 rounded transition-colors ${step === 2 ? 'bg-slate-700' : 'hover:bg-slate-800'}`}>
          <button
            onClick={() => setStep(2)}
            className="flex items-center justify-between w-full text-left"
          >
            <span className="font-semibold">2. Choose a Region</span>
            {selectedRegion && <span className="text-xs text-emerald-400">✓</span>}
            <ChevronRight className="w-4 h-4" />
          </button>

          {step === 2 && (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {REGIONS.map((region) => (
                <button
                  key={region.id}
                  onClick={() => handleSelectRegion(region)}
                  className={`w-full text-left p-2 rounded transition-colors ${
                    selectedRegion.id === region.id
                      ? 'bg-emerald-600 border border-emerald-500'
                      : 'bg-slate-600 hover:bg-slate-500 border border-slate-600'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <Globe className="w-4 h-4 mt-0.5 flex-shrink-0 text-emerald-300" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-100">{region.name}</p>
                      <p className="text-xs text-slate-300">{region.description}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        {region.bbox[0].toFixed(1)}°W - {region.bbox[2].toFixed(1)}°E
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Step 3 */}
        <div className={`space-y-2 p-3 rounded transition-colors ${step === 3 ? 'bg-slate-700' : 'hover:bg-slate-800'}`}>
          <button
            onClick={() => setStep(3)}
            className="flex items-center justify-between w-full text-left"
          >
            <span className="font-semibold">3. Simulate & Explore</span>
            <ChevronRight className="w-4 h-4" />
          </button>

          {step === 3 && selectedSpecies && selectedRegion && (
            <div className="space-y-2 p-2 bg-slate-600 bg-opacity-50 rounded">
              <div className="text-xs space-y-1">
                <p>
                  <span className="text-slate-400">Species:</span>{' '}
                  <span className="text-emerald-300 font-semibold">{selectedSpecies.name}</span>
                </p>
                <p>
                  <span className="text-slate-400">Region:</span>{' '}
                  <span className="text-emerald-300 font-semibold">{selectedRegion.name}</span>
                </p>
                <p className="text-slate-400">Ready to simulate! 🌱</p>
              </div>
            </div>
          )}
        </div>

        <button
          onClick={handleRunSimulation}
          disabled={isRunning || !selectedSpecies}
          className="w-full px-4 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-600 disabled:opacity-50 rounded font-semibold text-sm transition-colors flex items-center justify-center gap-2 mt-2"
        >
          <Zap className="w-4 h-4" />
          Run Simulation
        </button>
        </>
        )}
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
