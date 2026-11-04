import { DatePipe, DecimalPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { EMPTY, Subject, Subscription, catchError, finalize, forkJoin, merge, of, switchMap, tap, timer } from 'rxjs';
import {
  DashboardFilters,
  DistributionResponse,
  EarthquakeApiService,
  EarthquakeDto,
  EarthquakePage,
  GeoStat,
  GeoStatsResponse,
  HealthResponse,
  HistoricalComparisonResponse,
  HourlyStatsResponse,
  ReplayStateResponse,
} from './api/earthquake-api.service';
import { hourlyMaximum, hourlyPolyline, searchLoadedEvents, utcToDatetimeInput, validateFilterDraft } from './dashboard-utils.mjs';
import { EarthquakeMapComponent } from './map/earthquake-map.component';
import { formatDepth, formatMagnitude } from './map/map-utils.mjs';

type RangePreset = '1h' | '6h' | '24h' | 'custom';
type FilterDraft = Record<
  'start_utc' | 'end_utc' | 'mag_min' | 'mag_max' | 'depth_min_km' | 'depth_max_km' | 'adm0_a3' | 'continent' | 'subregion',
  string
>;
type SortColumn = 'time_utc' | 'mag' | 'country_name';

const PAGE_SIZE = 100;

function createDraft(start: Date, end: Date): FilterDraft {
  return {
    start_utc: utcToDatetimeInput(start.toISOString()),
    end_utc: utcToDatetimeInput(end.toISOString()),
    mag_min: '',
    mag_max: '',
    depth_min_km: '',
    depth_max_km: '',
    adm0_a3: '',
    continent: '',
    subregion: '',
  };
}

function createDefaultDraft(): FilterDraft {
  const end = new Date();
  return createDraft(new Date(end.getTime() - 24 * 60 * 60 * 1000), end);
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [DatePipe, DecimalPipe, EarthquakeMapComponent],
  templateUrl: './app.html',
  styleUrl: './app.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App implements OnInit, OnDestroy {
  private readonly api = inject(EarthquakeApiService);
  private readonly subscriptions = new Subscription();
  private readonly refreshRequests = new Subject<void>();

  readonly viewScope = signal<'live' | 'replay'>('live');
  readonly replayState = signal<ReplayStateResponse | null>(null);
  readonly isReplayMode = computed(() => this.viewScope() === 'replay');
  readonly hasActiveReplay = computed(() => this.replayState()?.active ?? false);

  readonly events = signal<EarthquakeDto[]>([]);
  readonly eventTotal = signal<number | null>(null);
  readonly geoStats = signal<GeoStat[]>([]);
  readonly hourlyStats = signal<HourlyStatsResponse['items']>([]);
  readonly distributions = signal<DistributionResponse | null>(null);
  readonly comparison = signal<HistoricalComparisonResponse | null>(null);
  readonly knownGeoStats = signal<GeoStat[]>([]);
  readonly filterDraft = signal<FilterDraft>(createDefaultDraft());
  readonly appliedFilters = signal<DashboardFilters>(this.defaultAppliedFilters());
  readonly rangePreset = signal<RangePreset>('24h');
  readonly filterError = signal<string | null>(null);
  readonly tableSearch = signal('');
  readonly sortColumn = signal<SortColumn>('time_utc');
  readonly sortDescending = signal(true);
  readonly offset = signal(0);
  readonly selectedEventId = signal<string | null>(null);
  readonly connection = signal<'checking' | 'connected' | 'disconnected'>('checking');
  readonly lastRefresh = signal<string | null>(null);
  readonly latestIngestion = signal<string | null>(null);
  readonly errorMessage = signal<string | null>(null);
  readonly dataError = signal<string | null>(null);
  readonly dashboardLoading = signal(true);

  readonly countryOptions = computed(() =>
    [...this.knownGeoStats()]
      .sort((left, right) => left.country_name.localeCompare(right.country_name, 'es'))
      .filter((country, index, list) => list.findIndex((other) => other.adm0_a3 === country.adm0_a3) === index),
  );
  readonly continentOptions = computed(() =>
    [...new Set(this.knownGeoStats().map((item) => item.continent).filter((value): value is string => !!value))]
      .sort((left, right) => left.localeCompare(right, 'es')),
  );
  readonly subregionOptions = computed(() =>
    [...new Set(this.knownGeoStats().map((item) => item.subregion).filter((value): value is string => !!value))]
      .sort((left, right) => left.localeCompare(right, 'es')),
  );
  readonly magnitudeBars = computed(() => this.toBars(this.distributions()?.magnitude_bins ?? []));
  readonly depthBars = computed(() => this.toBars(this.distributions()?.depth_bins ?? []));
  readonly hourlyPoints = computed(() => hourlyPolyline(this.hourlyStats()));
  readonly hourlyPeak = computed(() => hourlyMaximum(this.hourlyStats()));
  readonly visibleEvents = computed(() => {
    const items = searchLoadedEvents(this.events(), this.tableSearch());
    const column = this.sortColumn();
    const direction = this.sortDescending() ? -1 : 1;
    return [...items].sort((left, right) => {
      if (column === 'time_utc') {
        return direction * (Date.parse(left.time_utc) - Date.parse(right.time_utc));
      }
      if (column === 'mag') {
        const leftMag = left.mag ?? Number.NEGATIVE_INFINITY;
        const rightMag = right.mag ?? Number.NEGATIVE_INFINITY;
        return direction * (leftMag - rightMag);
      }
      return direction * left.country_name.localeCompare(right.country_name, 'es');
    });
  });
  readonly selectedEvent = computed(
    () => this.events().find((event) => event.event_id === this.selectedEventId()) ?? null,
  );
  readonly canGoBack = computed(() => this.offset() > 0);
  readonly canGoForward = computed(
    () => this.eventTotal() !== null && this.offset() + PAGE_SIZE < (this.eventTotal() ?? 0),
  );

  ngOnInit(): void {
    this.subscriptions.add(
      merge(timer(0, 60_000), this.refreshRequests)
        .pipe(
          switchMap(() => {
            this.dashboardLoading.set(true);
            const filters = this.appliedFilters();
            const offset = this.offset();
            const scope = this.viewScope();
            const replayRun = this.replayState();
            const runId = scope === 'replay' ? (replayRun?.run_id ?? null) : null;

            if (scope === 'replay' && !runId) {
              this.events.set([]);
              this.eventTotal.set(0);
              this.geoStats.set([]);
              this.hourlyStats.set([]);
              this.distributions.set(null);
              this.comparison.set(null);
              this.dashboardLoading.set(false);
              return EMPTY;
            }

            return forkJoin({
              page: this.api.getEarthquakes(filters, PAGE_SIZE, offset, scope, runId),
              geo: this.api.getGeoStats(filters, scope, runId),
              hourly: this.api.getHourlyStats(filters, scope, runId),
              distributions: this.api.getDistributions(filters, scope, runId),
              comparison: scope === 'live' ? this.api.getHistoricalComparison(filters) : of(null),
            }).pipe(
              tap((snapshot) => this.acceptDashboard(snapshot)),
              catchError((error: unknown) => {
                this.dataError.set(this.describeError(error));
                return EMPTY;
              }),
              finalize(() => this.dashboardLoading.set(false)),
            );
          }),
        )
        .subscribe(),
    );

    this.subscriptions.add(
      timer(0, 15_000)
        .pipe(
          switchMap(() =>
            forkJoin({
              health: this.api.getHealth(),
              replay: this.api.getReplayState().pipe(catchError(() => of(null))),
            }).pipe(
              tap(({ health, replay }) => {
                this.acceptHealth(health);
                if (replay) {
                  this.replayState.set(replay);
                }
              }),
              catchError((error: unknown) => {
                this.connection.set('disconnected');
                this.errorMessage.set(this.describeError(error));
                return EMPTY;
              }),
            ),
          ),
        )
        .subscribe(),
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
    this.refreshRequests.complete();
  }

  setViewScope(scope: 'live' | 'replay'): void {
    if (this.viewScope() === scope) {
      return;
    }
    this.viewScope.set(scope);
    this.offset.set(0);
    this.selectedEventId.set(null);
    if (scope === 'replay' && !this.replayState()?.run_id) {
      this.api.getReplayState().pipe(
        tap((replay) => {
          this.replayState.set(replay);
          this.refreshRequests.next();
        }),
        catchError(() => {
          this.refreshRequests.next();
          return EMPTY;
        }),
      ).subscribe();
    } else {
      this.refreshRequests.next();
    }
  }

  setRangePreset(preset: RangePreset): void {
    this.rangePreset.set(preset);
    if (preset === 'custom') {
      return;
    }
    const end = new Date();
    const durationHours = preset === '1h' ? 1 : preset === '6h' ? 6 : 24;
    this.filterDraft.update((draft) => ({
      ...draft,
      start_utc: utcToDatetimeInput(new Date(end.getTime() - durationHours * 60 * 60 * 1000).toISOString()),
      end_utc: utcToDatetimeInput(end.toISOString()),
    }));
  }

  updateDraft(field: keyof FilterDraft, event: Event): void {
    const value = (event.target as HTMLInputElement | HTMLSelectElement).value;
    this.filterDraft.update((draft) => ({ ...draft, [field]: value }));
    if (field === 'start_utc' || field === 'end_utc') {
      this.rangePreset.set('custom');
    }
  }

  applyFilters(event?: Event): void {
    event?.preventDefault();
    const result = validateFilterDraft(this.filterDraft());
    this.filterError.set(result.error);
    if (!result.filters) {
      return;
    }
    this.offset.set(0);
    this.selectedEventId.set(null);
    this.appliedFilters.set(result.filters);
    this.refreshRequests.next();
  }

  resetFilters(): void {
    this.filterDraft.set(createDefaultDraft());
    this.rangePreset.set('24h');
    this.filterError.set(null);
    this.offset.set(0);
    this.selectedEventId.set(null);
    const result = validateFilterDraft(this.filterDraft());
    if (result.filters) {
      this.appliedFilters.set(result.filters);
      this.refreshRequests.next();
    }
  }

  selectPage(pageOffset: number): void {
    this.offset.set(Math.max(0, pageOffset));
    this.selectedEventId.set(null);
    this.refreshRequests.next();
  }

  searchRows(event: Event): void {
    this.tableSearch.set((event.target as HTMLInputElement).value);
  }

  sortBy(column: SortColumn): void {
    if (this.sortColumn() === column) {
      this.sortDescending.update((descending) => !descending);
    } else {
      this.sortColumn.set(column);
      this.sortDescending.set(column === 'time_utc');
    }
  }

  selectEvent(event: EarthquakeDto): void {
    this.selectedEventId.set(event.event_id);
  }

  selectEventId(eventId: string): void {
    this.selectedEventId.set(eventId);
  }

  clearSelection(): void {
    this.selectedEventId.set(null);
  }

  pageLabel(): string {
    if (this.eventTotal() === null || this.eventTotal() === 0) {
      return '0 eventos';
    }
    const start = this.offset() + 1;
    const end = Math.min(this.offset() + PAGE_SIZE, this.eventTotal() ?? 0);
    return `${start}–${end} de ${this.eventTotal()}`;
  }

  formatMagnitude(value: number | null): string {
    return formatMagnitude(value);
  }

  formatDepth(value: number | null): string {
    return formatDepth(value);
  }

  formatBin(value: number): string {
    return Number.isInteger(value) ? String(value) : value.toFixed(1);
  }

  compareRatio(value: number | null): string {
    return value === null ? 'No disponible' : `${value.toFixed(2)}×`;
  }

  private defaultAppliedFilters(): DashboardFilters {
    const validated = validateFilterDraft(createDefaultDraft());
    return validated.filters ?? {
      start_utc: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      end_utc: new Date().toISOString(),
    };
  }

  private acceptDashboard(snapshot: {
    page: EarthquakePage;
    geo: GeoStatsResponse;
    hourly: HourlyStatsResponse;
    distributions: DistributionResponse;
    comparison: HistoricalComparisonResponse | null;
  }): void {
    this.events.set(snapshot.page.items);
    this.eventTotal.set(snapshot.page.total);
    this.geoStats.set(snapshot.geo.items);
    this.hourlyStats.set(snapshot.hourly.items);
    this.distributions.set(snapshot.distributions);
    this.comparison.set(snapshot.comparison);
    this.knownGeoStats.update((known) => {
      const merged = new Map(known.map((item) => [item.adm0_a3, item]));
      for (const item of snapshot.geo.items) {
        merged.set(item.adm0_a3, item);
      }
      return [...merged.values()];
    });
    if (
      this.selectedEventId() &&
      !snapshot.page.items.some((event) => event.event_id === this.selectedEventId())
    ) {
      this.selectedEventId.set(null);
    }
    this.lastRefresh.set(new Date().toISOString());
    this.dataError.set(null);
  }

  private acceptHealth(health: HealthResponse): void {
    this.latestIngestion.set(health.last_event_ingested_at ?? null);
    this.errorMessage.set(null);
    this.connection.set('connected');
  }

  private toBars(bins: Array<{ bin_start: number; bin_end: number; count: number }>): Array<{
    bin_start: number;
    bin_end: number;
    count: number;
    width: number;
  }> {
    const maximum = Math.max(1, ...bins.map((bin) => bin.count));
    return bins.map((bin) => ({ ...bin, width: (bin.count / maximum) * 100 }));
  }

  private describeError(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      return `La API respondió con un error (${error.status || 'sin respuesta'}).`;
    }
    return 'No se pudo contactar con la API.';
  }
}
