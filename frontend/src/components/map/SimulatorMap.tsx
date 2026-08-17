'use client';

import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { SimulationSnapshot, SimulationConfig } from '@/lib/types';

interface SimulatorMapProps {
  snapshots: SimulationSnapshot[];
  currentStep: number;
  config?: SimulationConfig;
}

export default function SimulatorMap({ snapshots, currentStep, config }: SimulatorMapProps) {
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
    if (!mapReady || !map.current || !config) return;

    const [west, south, east, north] = config.bbox;

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
            name: config.region,
            species: config.species_name,
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
  }, [config, mapReady]);

  return (
    <div className="w-full h-full rounded-lg border border-slate-600 relative overflow-hidden bg-slate-900">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Info overlay */}
      {config && mapReady && (
        <div className="absolute top-4 left-4 bg-slate-900 bg-opacity-80 text-emerald-300 px-3 py-2 rounded text-xs z-10 border border-emerald-600">
          <p className="font-semibold">{config.region.replace('_', ' ').toUpperCase()}</p>
          <p className="text-emerald-200 text-xs">🌱 {config.species_name}</p>
        </div>
      )}

      {/* Step info overlay */}
      {snapshots.length > 0 && mapReady && (
        <div className="absolute bottom-4 left-4 bg-slate-900 bg-opacity-80 text-emerald-300 px-3 py-2 rounded text-xs z-10 border border-emerald-600">
          <p className="font-semibold">Step {currentStep + 1} / {snapshots.length}</p>
          <p className="text-emerald-200">Population: {snapshots[currentStep]?.total_abundance.toFixed(0)}</p>
          <p className="text-emerald-200">Area: {snapshots[currentStep]?.occupied_cells} cells</p>
        </div>
      )}

      {/* No data message */}
      {!config && !mapReady && (
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

      {/* Attribution */}
      {mapReady && (
        <div className="absolute bottom-1 right-2 text-xs text-slate-400 z-5">
          © OpenStreetMap contributors
        </div>
      )}
    </div>
  );
}
