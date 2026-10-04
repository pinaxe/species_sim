'use client';

import { useEffect, useState } from 'react';
import { Plus, Trash2, Zap, Globe, Sparkles } from 'lucide-react';
import {
  InteractionConfig,
  InteractionPreset,
  MultiSpeciesConfig,
  SpeciesConfig,
} from '@/lib/types';
import { bioSimAPI } from '@/lib/api';
import { speciesColor } from '@/lib/speciesColors';

interface Region {
  id: string;
  name: string;
  bbox: [number, number, number, number];
  description: string;
  center: [number, number];
}

interface MultiSpeciesBuilderProps {
  regions: Region[];
  onRunSimulation: (config: MultiSpeciesConfig) => void;
  isRunning: boolean;
}

function blankSpecies(index: number): SpeciesConfig {
  return {
    name: `Species ${index + 1}`,
    temperature_opt: 15,
    temperature_sigma: 10,
    precipitation_opt: 900,
    precipitation_sigma: 600,
    niche_floor: 0.02,
    carrying_capacity: 1000,
    demography: { r: 0.3, m: 0.05 },
    dispersal: { kernel_type: 'gaussian', sigma: 15, fraction: 0.25 },
    initial_population: 200,
  };
}

export default function MultiSpeciesBuilder({
  regions,
  onRunSimulation,
  isRunning,
}: MultiSpeciesBuilderProps) {
  const [region, setRegion] = useState<Region>(regions[0]);
  const [nSteps, setNSteps] = useState(100);
  const [species, setSpecies] = useState<SpeciesConfig[]>([]);
  const [interactions, setInteractions] = useState<InteractionConfig[]>([]);
  const [presets, setPresets] = useState<Record<string, InteractionPreset>>({});
  const [presetsLoaded, setPresetsLoaded] = useState(false);

  const [newEdge, setNewEdge] = useState({ affected: '', other: '', coefficient: -0.5 });

  useEffect(() => {
    if (presetsLoaded) return;
    bioSimAPI
      .listInteractionPresets()
      .then((data) => {
        setPresets(data);
        setPresetsLoaded(true);
      })
      .catch((err) => {
        console.error('Failed to load interaction presets:', err);
        setPresetsLoaded(true);
      });
  }, [presetsLoaded]);

  const applyPreset = (preset: InteractionPreset) => {
    setSpecies(preset.species.map((s) => ({ ...s })));
    setInteractions(preset.interactions.map((e) => ({ ...e })));
  };

  const addSpecies = () => {
    setSpecies((prev) => [...prev, blankSpecies(prev.length)]);
  };

  const updateSpecies = (index: number, patch: Partial<SpeciesConfig>) => {
    setSpecies((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  const removeSpecies = (index: number) => {
    const name = species[index]?.name;
    setSpecies((prev) => prev.filter((_, i) => i !== index));
    setInteractions((prev) => prev.filter((e) => e.affected !== name && e.other !== name));
  };

  const addPredatorPreyPair = () => {
    const { affected: prey, other: predator } = newEdge;
    if (!prey || !predator || prey === predator) return;
    setInteractions((prev) => [
      ...prev.filter(
        (e) => !((e.affected === prey && e.other === predator) || (e.affected === predator && e.other === prey)),
      ),
      { affected: prey, other: predator, coefficient: -Math.abs(newEdge.coefficient) },
      { affected: predator, other: prey, coefficient: Math.abs(newEdge.coefficient) * 0.3 },
    ]);
  };

  const addCustomEdge = () => {
    const { affected, other, coefficient } = newEdge;
    if (!affected || !other || affected === other) return;
    setInteractions((prev) => [
      ...prev.filter((e) => !(e.affected === affected && e.other === other)),
      { affected, other, coefficient },
    ]);
  };

  const removeEdge = (index: number) => {
    setInteractions((prev) => prev.filter((_, i) => i !== index));
  };

  const handleRun = () => {
    if (species.length === 0) return;
    const config: MultiSpeciesConfig = {
      region: region.id,
      bbox: region.bbox,
      resolution_deg: 0.25,
      species,
      interactions,
      n_steps: nSteps,
    };
    onRunSimulation(config);
  };

  return (
    <div className="space-y-4">
      {/* Food web presets */}
      <div className="space-y-2 p-3 rounded bg-slate-700">
        <p className="font-semibold flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-400" />
          Quick start: food webs
        </p>
        <div className="grid grid-cols-1 gap-2">
          {Object.values(presets).map((preset) => (
            <button
              key={preset.name}
              onClick={() => applyPreset(preset)}
              className="text-left p-2 bg-slate-600 hover:bg-slate-500 rounded border border-slate-600 transition-colors"
            >
              <p className="text-sm font-medium text-slate-100">{preset.name}</p>
              <p className="text-xs text-slate-400">
                {preset.species.map((s) => s.name).join(' ↔ ')}
              </p>
            </button>
          ))}
          {presetsLoaded && Object.keys(presets).length === 0 && (
            <p className="text-xs text-slate-400">No presets available (backend offline?)</p>
          )}
        </div>
      </div>

      {/* Region */}
      <div className="space-y-2 p-3 rounded bg-slate-700">
        <p className="font-semibold">Region</p>
        <div className="space-y-1 max-h-32 overflow-y-auto">
          {regions.map((r) => (
            <button
              key={r.id}
              onClick={() => setRegion(r)}
              className={`w-full text-left p-2 rounded transition-colors flex items-center gap-2 ${
                region.id === r.id
                  ? 'bg-emerald-600 border border-emerald-500'
                  : 'bg-slate-600 hover:bg-slate-500 border border-slate-600'
              }`}
            >
              <Globe className="w-3.5 h-3.5 flex-shrink-0 text-emerald-300" />
              <span className="text-sm">{r.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Species list */}
      <div className="space-y-2 p-3 rounded bg-slate-700">
        <div className="flex items-center justify-between">
          <p className="font-semibold">Species ({species.length})</p>
          <button
            onClick={addSpecies}
            className="flex items-center gap-1 text-xs px-2 py-1 bg-slate-600 hover:bg-slate-500 rounded"
          >
            <Plus className="w-3 h-3" /> Add
          </button>
        </div>

        {species.length === 0 && (
          <p className="text-xs text-slate-400">
            Pick a food web preset above, or add species manually to build your own.
          </p>
        )}

        <div className="space-y-2">
          {species.map((s, i) => (
            <div key={i} className="p-2 bg-slate-600 bg-opacity-60 rounded border border-slate-600 space-y-2">
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: speciesColor(i) }}
                />
                <input
                  value={s.name}
                  onChange={(e) => updateSpecies(i, { name: e.target.value })}
                  className="flex-1 bg-slate-700 rounded px-2 py-1 text-sm text-slate-100"
                />
                <button onClick={() => removeSpecies(i)} className="p-1 hover:bg-slate-500 rounded">
                  <Trash2 className="w-3.5 h-3.5 text-slate-300" />
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <label className="space-y-1">
                  <span className="text-slate-400">Initial population</span>
                  <input
                    type="number"
                    value={s.initial_population}
                    onChange={(e) => updateSpecies(i, { initial_population: Number(e.target.value) })}
                    className="w-full bg-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-slate-400">Carrying capacity (K)</span>
                  <input
                    type="number"
                    value={s.carrying_capacity}
                    onChange={(e) => updateSpecies(i, { carrying_capacity: Number(e.target.value) })}
                    className="w-full bg-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-slate-400">Growth rate (r)</span>
                  <input
                    type="number"
                    step="0.01"
                    value={s.demography.r}
                    onChange={(e) =>
                      updateSpecies(i, { demography: { ...s.demography, r: Number(e.target.value) } })
                    }
                    className="w-full bg-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-slate-400">Mortality</span>
                  <input
                    type="number"
                    step="0.01"
                    value={s.demography.m}
                    onChange={(e) =>
                      updateSpecies(i, { demography: { ...s.demography, m: Number(e.target.value) } })
                    }
                    className="w-full bg-slate-700 rounded px-2 py-1 text-slate-100"
                  />
                </label>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Interactions */}
      {species.length >= 2 && (
        <div className="space-y-2 p-3 rounded bg-slate-700">
          <p className="font-semibold">Interactions</p>
          <p className="text-xs text-slate-400">
            Negative = harmed by the other species (prey); positive = benefits from it (predator).
          </p>

          <div className="space-y-1">
            {interactions.map((e, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-xs bg-slate-600 bg-opacity-60 rounded px-2 py-1.5"
              >
                <span>
                  <span className="font-medium text-slate-100">{e.affected}</span>
                  <span className="text-slate-400"> {e.coefficient >= 0 ? 'gains from' : 'harmed by'} </span>
                  <span className="font-medium text-slate-100">{e.other}</span>
                  <span className="text-slate-400"> ({e.coefficient.toFixed(2)})</span>
                </span>
                <button onClick={() => removeEdge(i)} className="p-1 hover:bg-slate-500 rounded">
                  <Trash2 className="w-3 h-3 text-slate-300" />
                </button>
              </div>
            ))}
            {interactions.length === 0 && (
              <p className="text-xs text-slate-400">No interactions yet -- both species will grow independently.</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs pt-1">
            <select
              value={newEdge.affected}
              onChange={(e) => setNewEdge((p) => ({ ...p, affected: e.target.value }))}
              className="bg-slate-600 rounded px-2 py-1.5 text-slate-100"
            >
              <option value="">Prey / affected...</option>
              {species.map((s) => (
                <option key={s.name} value={s.name}>{s.name}</option>
              ))}
            </select>
            <select
              value={newEdge.other}
              onChange={(e) => setNewEdge((p) => ({ ...p, other: e.target.value }))}
              className="bg-slate-600 rounded px-2 py-1.5 text-slate-100"
            >
              <option value="">Predator / other...</option>
              {species.map((s) => (
                <option key={s.name} value={s.name}>{s.name}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              step="0.05"
              value={newEdge.coefficient}
              onChange={(e) => setNewEdge((p) => ({ ...p, coefficient: Number(e.target.value) }))}
              className="w-20 bg-slate-600 rounded px-2 py-1.5 text-xs text-slate-100"
              title="Coefficient magnitude"
            />
            <button
              onClick={addPredatorPreyPair}
              disabled={!newEdge.affected || !newEdge.other || newEdge.affected === newEdge.other}
              className="flex-1 text-xs px-2 py-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 rounded"
            >
              Add as predator/prey pair
            </button>
          </div>
          <button
            onClick={addCustomEdge}
            disabled={!newEdge.affected || !newEdge.other || newEdge.affected === newEdge.other}
            className="w-full text-xs px-2 py-1.5 bg-slate-600 hover:bg-slate-500 disabled:opacity-40 rounded"
          >
            Or add just the one edge above ({newEdge.affected || '...'} affected by {newEdge.other || '...'})
          </button>
        </div>
      )}

      {/* Steps */}
      <div className="space-y-2 p-3 rounded bg-slate-700">
        <label className="flex items-center justify-between text-sm">
          <span>Time steps</span>
          <input
            type="number"
            value={nSteps}
            onChange={(e) => setNSteps(Number(e.target.value))}
            className="w-20 bg-slate-600 rounded px-2 py-1 text-right"
          />
        </label>
      </div>

      <button
        onClick={handleRun}
        disabled={isRunning || species.length === 0}
        className="w-full px-4 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-600 disabled:opacity-50 rounded font-semibold text-sm transition-colors flex items-center justify-center gap-2"
      >
        <Zap className="w-4 h-4" />
        Run Multi-Species Simulation
      </button>
    </div>
  );
}
