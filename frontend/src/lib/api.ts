import axios, { AxiosInstance } from 'axios';
import {
  NicheParams,
  Occurrence,
  OccurrenceSearchResponse,
  Preset,
  SimulationConfig,
  SimulationProgress,
  Taxon,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class BioSimAPI {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/api/v1`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // GBIF endpoints
  async searchTaxa(query: string, limit: number = 10): Promise<Taxon[]> {
    const response = await this.client.get('/gbif/taxa/search', {
      params: { query, limit },
    });
    return response.data.results || [];
  }

  async searchOccurrences(
    taxonKey: number,
    limit: number = 5000,
    geometry?: string,
    yearStart?: number,
    yearEnd?: number,
  ): Promise<OccurrenceSearchResponse> {
    const response = await this.client.post('/gbif/occurrences/search', {
      taxon_key: taxonKey,
      limit,
      geometry,
      year_start: yearStart,
      year_end: yearEnd,
    });
    return response.data;
  }

  async thinOccurrences(
    taxonKey: number,
    limit: number = 5000,
    gridSizeKm: number = 10.0,
  ): Promise<OccurrenceSearchResponse> {
    const response = await this.client.post('/gbif/occurrences/thin', {
      taxon_key: taxonKey,
      limit,
    }, {
      params: { grid_size_km: gridSizeKm },
    });
    return response.data;
  }

  async fitNiche(taxonKey: number, limit: number = 5000): Promise<NicheParams> {
    const response = await this.client.post('/gbif/niche/fit', {
      taxon_key: taxonKey,
      limit,
    });
    return response.data;
  }

  // Raster endpoints
  async listRasterLayers(): Promise<any[]> {
    const response = await this.client.get('/rasters/layers');
    return response.data.layers || [];
  }

  async clipRaster(
    layerName: string,
    bbox: [number, number, number, number],
    resolutionDeg?: number,
  ): Promise<any> {
    const response = await this.client.post('/rasters/clip', {
      layer_name: layerName,
      bbox,
      resolution_deg: resolutionDeg,
    });
    return response.data;
  }

  // Simulation endpoints
  async estimateSimulationDuration(config: SimulationConfig): Promise<number> {
    const response = await this.client.post('/simulation/estimate', config);
    return response.data.estimated_seconds || 0;
  }

  async runSimulation(
    config: SimulationConfig,
    onProgress: (progress: SimulationProgress) => void,
  ): Promise<void> {
    console.log('Starting simulation request to:', `${API_URL}/api/v1/simulation/run`);

    const response = await fetch(`${API_URL}/api/v1/simulation/run`, {
      method: 'GET', // Use GET for EventSource-style streaming
    });

    console.log('Response status:', response.status, response.statusText);

    if (!response.ok) {
      const text = await response.text();
      console.error('Error response:', text);
      throw new Error(`Simulation request failed: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';
    let eventCount = 0;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log(`Stream ended. Total events: ${eventCount}`);
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines[lines.length - 1]; // Keep incomplete line

        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6); // Remove 'data: ' prefix
              const data = JSON.parse(jsonStr);
              eventCount++;

              if (eventCount <= 3 || eventCount % 10 === 0) {
                console.log(`Event ${eventCount}:`, data);
              }

              if (data.error) {
                throw new Error(data.error);
              }
              onProgress(data);
            } catch (err) {
              console.error('Failed to parse SSE data:', err, 'line:', line);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  async listPresets(): Promise<Record<string, Preset>> {
    const response = await this.client.get('/simulation/presets');
    return response.data.presets || {};
  }

  async getPreset(presetId: string): Promise<Preset> {
    const response = await this.client.get(`/simulation/presets/${presetId}`);
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      return response.status === 200;
    } catch {
      return false;
    }
  }
}

export const bioSimAPI = new BioSimAPI();
