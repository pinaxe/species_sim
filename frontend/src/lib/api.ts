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
    return new Promise((resolve, reject) => {
      const url = `${API_URL}/api/v1/simulation/run`;
      const eventSource = new EventSource(url);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.error) {
            reject(new Error(data.error));
          } else {
            onProgress(data);
          }
        } catch (err) {
          console.error('Failed to parse progress:', err);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        reject(new Error('Simulation stream closed unexpectedly'));
      };
    });
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
