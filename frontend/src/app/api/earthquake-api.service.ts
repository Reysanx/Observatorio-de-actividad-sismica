import { HttpClient, HttpParams } from '@angular/common/http';
import { InjectionToken, Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL');

export interface DashboardFilters {
  start_utc: string;
  end_utc: string;
  mag_min?: number;
  mag_max?: number;
  depth_min_km?: number;
  depth_max_km?: number;
  adm0_a3?: string;
  continent?: string;
  subregion?: string;
}

export interface HistogramBin {
  bin_start: number;
  bin_end: number;
  count: number;
}

export interface GeoStat {
  adm0_a3: string;
  country_name: string;
  continent: string | null;
  subregion: string | null;
  event_count: number;
  magnitude_count: number;
  average_magnitude: number | null;
  maximum_magnitude: number | null;
}

export interface GeoStatsResponse {
  items: GeoStat[];
  scope: 'live' | 'replay';
  run_id: string | null;
}

export interface HourlyStat {
  hour_utc: string;
  event_count: number;
  magnitude_count: number;
  average_magnitude: number | null;
}

export interface HourlyStatsResponse {
  items: HourlyStat[];
  scope: 'live' | 'replay';
  run_id: string | null;
}

export interface DistributionResponse {
  magnitude_bins: HistogramBin[];
  depth_bins: HistogramBin[];
  magnitude_null_count: number;
  depth_null_count: number;
  depth_p90_km: number | null;
  depth_population_count: number;
  depth_percentile_method: 'hyndman_fan_type_7';
  depth_period_start_utc: string;
  depth_period_end_utc: string;
  scope: 'live' | 'replay';
  run_id: string | null;
}

export interface HistoricalComparisonResponse {
  calculated_at: string;
  window_start_utc: string;
  window_end_utc: string;
  magnitude_threshold: number;
  recent_event_count: number;
  historical_2025_event_count: number;
  historical_days: number;
  historical_daily_average: number;
  historical_daily_population_stddev: number;
  recent_standard_deviations_from_mean: number | null;
  deviation_band: 'within_1_sd' | 'between_1_and_2_sd' | 'beyond_2_sd' | 'unavailable';
  ratio_to_historical_daily_average: number | null;
  adm0_a3: string | null;
  continent: string | null;
  subregion: string | null;
}

export interface EarthquakeDto {
  event_id: string;
  mag: number | null;
  depth_km: number | null;
  time_utc: string;
  updated_utc: string;
  ingested_at: string | null;
  geom_lon: number;
  geom_lat: number;
  adm0_a3: string;
  country_name: string;
  name_es: string | null;
  admin_name: string | null;
  place: string | null;
  ingestion_latency_seconds?: number | null;
}

export interface EarthquakePage {
  items: EarthquakeDto[];
  total: number;
  limit: number;
  offset: number;
  scope: 'live' | 'replay';
  run_id?: string | null;
}

export interface HealthResponse {
  status: string;
  last_event_ingested_at?: string | null;
}

export interface ReplayStateResponse {
  run_id: string | null;
  active: boolean;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  events_received: number;
  events_processed: number;
  events_quarantined: number;
}

@Injectable({ providedIn: 'root' })
export class EarthquakeApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  getEarthquakes(
    filters: DashboardFilters,
    limit = 100,
    offset = 0,
    scope: 'live' | 'replay' = 'live',
    runId?: string | null,
  ): Observable<EarthquakePage> {
    let params = this.filterParams(filters)
      .set('limit', limit)
      .set('offset', offset)
      .set('scope', scope);
    if (scope === 'replay' && runId) {
      params = params.set('run_id', runId);
    }

    return this.http.get<EarthquakePage>(
      `${this.baseUrl}/api/v1/earthquakes`,
      { params },
    );
  }

  getGeoStats(
    filters: DashboardFilters,
    scope: 'live' | 'replay' = 'live',
    runId?: string | null,
  ): Observable<GeoStatsResponse> {
    let params = this.filterParams(filters).set('scope', scope);
    if (scope === 'replay' && runId) {
      params = params.set('run_id', runId);
    }
    return this.http.get<GeoStatsResponse>(
      `${this.baseUrl}/api/v1/stats/geo`,
      { params },
    );
  }

  getHourlyStats(
    filters: DashboardFilters,
    scope: 'live' | 'replay' = 'live',
    runId?: string | null,
  ): Observable<HourlyStatsResponse> {
    let params = this.filterParams(filters).set('scope', scope);
    if (scope === 'replay' && runId) {
      params = params.set('run_id', runId);
    }
    return this.http.get<HourlyStatsResponse>(
      `${this.baseUrl}/api/v1/stats/hourly`,
      { params },
    );
  }

  getDistributions(
    filters: DashboardFilters,
    scope: 'live' | 'replay' = 'live',
    runId?: string | null,
  ): Observable<DistributionResponse> {
    let params = this.filterParams(filters).set('scope', scope);
    if (scope === 'replay' && runId) {
      params = params.set('run_id', runId);
    }
    return this.http.get<DistributionResponse>(
      `${this.baseUrl}/api/v1/stats/distributions`,
      { params },
    );
  }

  getHistoricalComparison(filters: DashboardFilters): Observable<HistoricalComparisonResponse> {
    // The API contract fixes the comparison to a rolling 24-hour M4.5+ window
    // and accepts geographic filters only.
    return this.http.get<HistoricalComparisonResponse>(
      `${this.baseUrl}/api/v1/stats/historical-comparison`,
      { params: this.geographicParams(filters) },
    );
  }

  getHealth(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>(`${this.baseUrl}/api/v1/health`);
  }

  getReplayState(): Observable<ReplayStateResponse> {
    return this.http.get<ReplayStateResponse>(`${this.baseUrl}/api/v1/replay/state`);
  }

  private filterParams(filters: DashboardFilters): HttpParams {
    let params = new HttpParams()
      .set('start_utc', filters.start_utc)
      .set('end_utc', filters.end_utc);
    for (const key of ['mag_min', 'mag_max', 'depth_min_km', 'depth_max_km'] as const) {
      const value = filters[key];
      if (value !== undefined) {
        params = params.set(key, value);
      }
    }
    return this.appendGeographicParams(params, filters);
  }

  private geographicParams(filters: DashboardFilters): HttpParams {
    return this.appendGeographicParams(new HttpParams(), filters);
  }

  private appendGeographicParams(params: HttpParams, filters: DashboardFilters): HttpParams {
    let result = params;
    for (const key of ['adm0_a3', 'continent', 'subregion'] as const) {
      const value = filters[key];
      if (value) {
        result = result.set(key, value);
      }
    }
    return result;
  }
}
