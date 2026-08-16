// Simulation configuration and result types

export interface NicheParams {
  temperature_opt: number;
  temperature_sigma: number;
  precipitation_opt: number;
  precipitation_sigma: number;
  floor?: number;
}

export interface DispersalParams {
  kernel_type: "gaussian" | "exponential" | "fat_tail";
  sigma: number;
  fraction: number;
  alpha?: number;
  stratified_fraction?: number;
  jump_distance?: number;
  boundary_mode?: "reflecting" | "absorbing";
}

export interface DemographyParams {
  r: number;
  m: number;
  allee_threshold?: number;
}

export interface SimulationConfig {
  region: string;
  species_name: string;
  bbox: [number, number, number, number];
  resolution_deg: number;
  temperature_opt: number;
  temperature_sigma: number;
  precipitation_opt: number;
  precipitation_sigma: number;
  niche_floor: number;
  carrying_capacity: number;
  demography: DemographyParams;
  dispersal: DispersalParams;
  n_steps: number;
  seed_x?: number;
  seed_y?: number;
}

export interface SimulationSnapshot {
  step: number;
  time: number;
  total_abundance: number;
  occupied_cells: number;
  max_density: number;
  front_distance_km: number;
  grid_data?: number[][];
}

export interface SimulationProgress {
  step: number;
  total_steps: number;
  percent: number;
  current_snapshot: SimulationSnapshot;
}

export interface Taxon {
  key: number;
  name: string;
  canonicalName?: string;
  rank?: string;
}

export interface Occurrence {
  key: number;
  datasetKey: string;
  scientificName: string;
  decimalLatitude: number;
  decimalLongitude: number;
  year?: number;
  coordinateUncertaintyInMeters?: number;
}

export interface OccurrenceSearchResponse {
  count: number;
  total: number;
  limit: number;
  offset: number;
  results: Occurrence[];
  taxon_name: string;
}

export interface Preset {
  name: string;
  description: string;
  region: string;
  bbox: [number, number, number, number];
  species_name: string;
  temperature_opt: number;
  temperature_sigma: number;
  precipitation_opt: number;
  precipitation_sigma: number;
  carrying_capacity: number;
  r: number;
  m: number;
  dispersal_kernel: string;
  dispersal_sigma: number;
  dispersal_fraction: number;
  alpha?: number;
  stratified_fraction?: number;
  jump_distance?: number;
}
