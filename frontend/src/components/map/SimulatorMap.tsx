'use client';

import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { MultiSpeciesConfig, MultiSpeciesSnapshot, SimulationSnapshot, SimulationConfig } from '@/lib/types';
import { speciesColor } from '@/lib/speciesColors';

interface SimulatorMapProps {
  snapshots: SimulationSnapshot[];
  multiSnapshots?: MultiSpeciesSnapshot[];
  speciesNames?: string[];
  currentStep: number;
  config?: SimulationConfig;
  multiConfig?: MultiSpeciesConfig;
}

export default function SimulatorMap({
  snapshots,
  multiSnapshots,
  speciesNames,
  currentStep,
  config,
  multiConfig,
}: SimulatorMapProps) {
  const isMulti = !!multiSnapshots && !!speciesNames;
  const bbox = multiConfig?.bbox ?? config?.bbox;
  const regionLabel = multiConfig?.region ?? config?.region;
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    // Verify container has dimensions
    if (!mapContainer.current.clientWidth || !mapContainer.current.clientHeight) {
      setTimeout(() => {
        console.warn('Map container has no dimensions, retrying...');
      }, 100);
      return;
    }

    const osmStyle = {
      version: 8,
      name: 'OSM',
      sources: {
        osm: {
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          minzoom: 0,
          maxzoom: 18,
          attribution: '© OpenStreetMap contributors',
        } as any,
      },
      layers: [
        {
          id: 'osm-layer',
          type: 'raster',
          source: 'osm',
        } as any,
      ],
    } as any;

    try {
      map.current = new maplibregl.Map({
        container: mapContainer.current,
        style: osmStyle,
        center: [-95.5, 37],
        zoom: 3,
      });

      // Set mapReady after a short delay to ensure rendering
      const timer = setTimeout(() => {
        setMapReady(true);
        console.log('Map initialized');
      }, 1000);

      map.current.on('error', (e: any) => {
        console.error('Map error:', e);
        setError('Failed to load map tiles');
      });

      return () => {
        clearTimeout(timer);
        if (map.current) {
          try {
            map.current.remove();
          } catch (e) {
            console.error('Error removing map:', e);
          }
          map.current = null;
        }
      };
    } catch (err) {
      console.error('Map init error:', err);
      setError(err instanceof Error ? err.message : 'Failed to initialize map');
    }
  }, []);

  // Update region boundaries when map is ready and config changes
  useEffect(() => {
    if (!mapReady || !map.current || !bbox) return;

    const [west, south, east, north] = bbox;

    // Fit map to region bounds
    map.current.fitBounds(
      [
        [west, south],
        [east, north],
      ],
      { padding: 40 }
    );

    // Remove existing region layer if it exists
    if (map.current.getLayer('region-fill')) {
      map.current.removeLayer('region-fill');
    }
    if (map.current.getLayer('region-border')) {
      map.current.removeLayer('region-border');
    }
    if (map.current.getSource('region')) {
      map.current.removeSource('region');
    }

    // Create GeoJSON for region bounds
    const regionGeoJSON: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south],
              ],
            ],
          },
          properties: {
            name: regionLabel,
            species: config?.species_name ?? speciesNames?.join(', '),
          },
        },
      ],
    };

    // Add source
    map.current.addSource('region', {
      type: 'geojson',
      data: regionGeoJSON,
    });

    // Add fill layer
    map.current.addLayer({
      id: 'region-fill',
      type: 'fill',
      source: 'region',
      paint: {
        'fill-color': '#10b981',
        'fill-opacity': 0.2,
      },
    });

    // Add border layer
    map.current.addLayer({
      id: 'region-border',
      type: 'line',
      source: 'region',
      paint: {
        'line-color': '#10b981',
        'line-width': 2,
      },
    });

    // Add popup on hover
    map.current.on('mouseenter', 'region-fill', () => {
      if (map.current) {
        map.current.getCanvas().style.cursor = 'pointer';
      }
    });

    map.current.on('mouseleave', 'region-fill', () => {
      if (map.current) {
        map.current.getCanvas().style.cursor = '';
      }
    });
  }, [bbox, regionLabel, mapReady]);

  // Render population as dots, updating each step. In multi-species mode each
  // species gets its own source/layer, colored by its fixed identity color
  // (see lib/speciesColors) instead of the single-species density ramp.
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;

    const desiredIds = isMulti ? speciesNames!.map((name) => `population-${name}`) : ['population'];

    // Tear down any population layer/source left over from a previous run
    // (a mode switch, or a different species list).
    (m.getStyle()?.layers ?? []).forEach((layer) => {
      if (layer.id.startsWith('population') && !desiredIds.includes(layer.id) && m.getLayer(layer.id)) {
        m.removeLayer(layer.id);
      }
    });
    Object.keys(m.getStyle()?.sources ?? {}).forEach((sourceId) => {
      if (sourceId.startsWith('population') && !desiredIds.includes(sourceId) && m.getSource(sourceId)) {
        m.removeSource(sourceId);
      }
    });

    if (isMulti) {
      const snapshot = multiSnapshots![currentStep];
      speciesNames!.forEach((name, i) => {
        const id = `population-${name}`;
        const points = snapshot?.species[name]?.population_points || [];
        const geojson: GeoJSON.FeatureCollection = {
          type: 'FeatureCollection',
          features: points.map(([lon, lat, pop]) => ({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [lon, lat] },
            properties: { population: pop },
          })),
        };

        const existingSource = m.getSource(id) as maplibregl.GeoJSONSource | undefined;
        if (existingSource) {
          existingSource.setData(geojson);
          return;
        }

        m.addSource(id, { type: 'geojson', data: geojson });
        m.addLayer({
          id,
          type: 'circle',
          source: id,
          paint: {
            'circle-radius': ['interpolate', ['linear'], ['get', 'population'], 0, 3, 10, 5, 100, 9, 1000, 14],
            'circle-color': speciesColor(i),
            'circle-opacity': 0.8,
            'circle-stroke-width': 1,
            'circle-stroke-color': '#0d0d0d',
          },
        });
      });
      return;
    }

    const snapshot = snapshots[currentStep];
    const points = snapshot?.population_points || [];

    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: points.map(([lon, lat, pop]) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [lon, lat] },
        properties: { population: pop },
      })),
    };

    const existingSource = m.getSource('population') as maplibregl.GeoJSONSource | undefined;
    if (existingSource) {
      existingSource.setData(geojson);
      return;
    }

    m.addSource('population', {
      type: 'geojson',
      data: geojson,
    });

    m.addLayer({
      id: 'population',
      type: 'circle',
      source: 'population',
      paint: {
        'circle-radius': [
          'interpolate',
          ['linear'],
          ['get', 'population'],
          0, 3,
          10, 5,
          100, 9,
          1000, 14,
        ],
        'circle-color': [
          'interpolate',
          ['linear'],
          ['get', 'population'],
          0, '#fde68a',
          10, '#f59e0b',
          100, '#dc2626',
          1000, '#7f1d1d',
        ],
        'circle-opacity': 0.75,
        'circle-stroke-width': 1,
        'circle-stroke-color': '#451a03',
      },
    });
  }, [snapshots, multiSnapshots, speciesNames, currentStep, mapReady, isMulti]);

  return (
    <div className="w-full h-full rounded-lg border border-slate-600 relative overflow-hidden bg-slate-900">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Info overlay */}
      {regionLabel && mapReady && (
        <div className="absolute top-4 left-4 bg-slate-900 bg-opacity-80 text-emerald-300 px-3 py-2 rounded text-xs z-10 border border-emerald-600">
          <p className="font-semibold">{regionLabel.replace('_', ' ').toUpperCase()}</p>
          {isMulti ? (
            <div className="space-y-0.5 mt-1">
              {speciesNames!.map((name, i) => (
                <p key={name} className="flex items-center gap-1.5 text-emerald-200 text-xs">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: speciesColor(i) }} />
                  {name}
                </p>
              ))}
            </div>
          ) : (
            <p className="text-emerald-200 text-xs">🌱 {config?.species_name}</p>
          )}
        </div>
      )}

      {/* Step info overlay */}
      {isMulti && multiSnapshots!.length > 0 && mapReady && (
        <div className="absolute bottom-4 left-4 bg-slate-900 bg-opacity-80 text-emerald-300 px-3 py-2 rounded text-xs z-10 border border-emerald-600">
          <p className="font-semibold">Step {currentStep + 1} / {multiSnapshots!.length}</p>
          {speciesNames!.map((name, i) => (
            <p key={name} className="flex items-center gap-1.5 text-emerald-200">
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: speciesColor(i) }} />
              {name}: {multiSnapshots![currentStep]?.species[name]?.total_abundance.toFixed(0) ?? 0}
            </p>
          ))}
        </div>
      )}
      {!isMulti && snapshots.length > 0 && mapReady && (
        <div className="absolute bottom-4 left-4 bg-slate-900 bg-opacity-80 text-emerald-300 px-3 py-2 rounded text-xs z-10 border border-emerald-600">
          <p className="font-semibold">Step {currentStep + 1} / {snapshots.length}</p>
          <p className="text-emerald-200">Population: {snapshots[currentStep]?.total_abundance.toFixed(0)}</p>
          <p className="text-emerald-200">Area: {snapshots[currentStep]?.occupied_cells} cells</p>
        </div>
      )}

      {/* No data message */}
      {!regionLabel && !mapReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-40 z-5">
          <div className="text-center text-slate-300">
            <p className="text-sm">Select a species and region to start</p>
          </div>
        </div>
      )}

      {/* Loading/Error indicator */}
      {!mapReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-40 z-5">
          <div className="text-center">
            {error ? (
              <>
                <p className="text-red-400 text-sm">Error loading map: {error}</p>
                <p className="text-slate-300 text-xs mt-2">Check browser console for details</p>
              </>
            ) : (
              <div className="text-slate-300 animate-pulse">Initializing map...</div>
            )}
          </div>
        </div>
      )}

      {/* Population legend */}
      {mapReady && isMulti && multiSnapshots!.length > 0 && (
        <div className="absolute top-4 right-4 bg-slate-900 bg-opacity-80 text-slate-200 px-3 py-2 rounded text-xs z-10 border border-slate-600">
          <p className="font-semibold mb-1">Species (dot size = local density)</p>
          <div className="space-y-1">
            {speciesNames!.map((name, i) => (
              <div key={name} className="flex items-center gap-1.5">
                <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: speciesColor(i) }} />
                <span>{name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {mapReady && !isMulti && snapshots.length > 0 && (
        <div className="absolute top-4 right-4 bg-slate-900 bg-opacity-80 text-slate-200 px-3 py-2 rounded text-xs z-10 border border-slate-600">
          <p className="font-semibold mb-1">Population density</p>
          <div className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-[#fde68a]" />
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-[#f59e0b]" />
            <span className="inline-block w-3 h-3 rounded-full bg-[#dc2626]" />
            <span className="inline-block w-3.5 h-3.5 rounded-full bg-[#7f1d1d]" />
            <span className="ml-1">low → high</span>
          </div>
        </div>
      )}

      {/* Attribution */}
      {mapReady && (
        <div className="absolute bottom-1 right-2 text-xs text-slate-400 z-5">
          © OpenStreetMap contributors
        </div>
      )}
    </div>
  );
}
