import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
  signal,
} from '@angular/core';
import * as L from 'leaflet';
import { EarthquakeDto } from '../api/earthquake-api.service';
import { depthColor, formatDepth, formatMagnitude, markerRadius } from './map-utils.mjs';

// ─── Tipos ───────────────────────────────────────────────────────────────────
type MapProjection = '2d' | '3d';

// ─── Lazy-load de Mapbox GL JS ────────────────────────────────────────────────
// Se importa dinámicamente solo la primera vez que el usuario activa el globo.
// Así el bundle inicial no aumenta de tamaño hasta que se necesite.
let mapboxPromise: Promise<typeof import('mapbox-gl')> | null = null;

function loadMapbox(): Promise<typeof import('mapbox-gl')> {
  mapboxPromise ??= import('mapbox-gl');
  return mapboxPromise;
}

// ─── Token de Mapbox ─────────────────────────────────────────────────────────
// Coloca tu token público aquí o en window.MAPBOX_TOKEN (index.html / Netlify).
// Obtenlo gratis en https://account.mapbox.com
function getMapboxToken(): string {
  return (
    (typeof window !== 'undefined' &&
      (window as unknown as Record<string, string>)['MAPBOX_TOKEN']) ||
    'pk.REEMPLAZA_CON_TU_TOKEN_MAPBOX'
  );
}

// ─── IDs de capas Mapbox ─────────────────────────────────────────────────────
const SOURCE_ID      = 'earthquakes';
const LAYER_CIRCLES  = 'earthquakes-circles';
const LAYER_SELECTED = 'earthquakes-selected';

// ─── Helper: EarthquakeDto[] → GeoJSON FeatureCollection ────────────────────
function toGeoJson(events: EarthquakeDto[]): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: events
      .filter(
        (e) =>
          Number.isFinite(e.geom_lat) &&
          Number.isFinite(e.geom_lon) &&
          e.geom_lat >= -90 &&
          e.geom_lat <= 90 &&
          e.geom_lon >= -180 &&
          e.geom_lon <= 180,
      )
      .map((e) => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [e.geom_lon, e.geom_lat] },
        properties: {
          event_id:   e.event_id,
          mag:        e.mag ?? null,
          depth_km:   e.depth_km ?? null,
          place:      e.place ?? 'Lugar no indicado',
          time_utc:   e.time_utc,
          country_name: e.country_name ?? '',
          adm0_a3:    e.adm0_a3 ?? '',
          admin_name: e.admin_name ?? '',
          name_es:    e.name_es ?? '',
          ingestion_latency_seconds: e.ingestion_latency_seconds ?? null,
          // Precalculados con las mismas funciones originales de map-utils.mjs
          radius:      markerRadius(e.mag),
          depth_color: depthColor(e.depth_km),
        },
      })),
  };
}

// ─── Componente ──────────────────────────────────────────────────────────────
@Component({
  selector: 'app-earthquake-map',
  standalone: true,
  template: `
    <!-- Contenedor Leaflet 2D (siempre en el DOM) -->
    <div
      #leafletEl
      class="map-canvas"
      [class.map-canvas--hidden]="projection() === '3d'"
      role="application"
      aria-label="Mapa de terremotos 2D"
    ></div>

    <!-- Contenedor Mapbox 3D (inicializado lazy en el primer cambio a 3D) -->
    <div
      #mapboxEl
      class="map-canvas map-canvas--3d"
      [class.map-canvas--hidden]="projection() === '2d'"
      role="application"
      aria-label="Globo terráqueo 3D de terremotos"
      aria-hidden="{{ projection() === '2d' }}"
    ></div>

    <!-- Toggle 2D / 3D flotante (ui-craft) -->
    <div class="view-toggle" role="group" aria-label="Proyección del mapa">
      <button
        type="button"
        class="toggle-btn"
        [class.toggle-btn--active]="projection() === '2d'"
        (click)="setProjection('2d')"
        [attr.aria-pressed]="projection() === '2d'"
        title="Vista plana 2D (Leaflet / OpenStreetMap)"
      >
        <!-- mapa cuadrícula -->
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
             viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true">
          <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/>
          <line x1="9" y1="3" x2="9" y2="18"/>
          <line x1="15" y1="6" x2="15" y2="21"/>
        </svg>
        <span>2D</span>
      </button>

      <button
        type="button"
        class="toggle-btn"
        [class.toggle-btn--active]="projection() === '3d'"
        (click)="setProjection('3d')"
        [attr.aria-pressed]="projection() === '3d'"
        title="Globo terráqueo 3D (Mapbox)"
      >
        <!-- globo -->
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14"
             viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <line x1="2" y1="12" x2="22" y2="12"/>
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10
                   15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
        </svg>
        <span>3D</span>
      </button>
    </div>

    <!-- Indicador de carga del globo (solo se muestra en la primera carga) -->
    @if (globeLoading()) {
      <div class="globe-loading" role="status" aria-live="polite">
        <span class="globe-loading__spinner" aria-hidden="true"></span>
        Cargando globo…
      </div>
    }
  `,
  styles: [`
    :host {
      display: block;
      position: relative;
      min-height: 360px;
      height: min(68vh, 760px);
    }

    /* ── Contenedores de mapa ───────────────────────────────────────── */
    .map-canvas {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      min-height: 360px;
      background: #e7eef1;
      transition: opacity 280ms ease;
    }

    .map-canvas--3d {
      background: #0d1117;
    }

    /* Ocultar visualmente pero mantener en DOM para que Leaflet/Mapbox
       no pierdan su tamaño y estado interno */
    .map-canvas--hidden {
      opacity: 0;
      pointer-events: none;
      z-index: 0;
    }

    .map-canvas:not(.map-canvas--hidden) {
      opacity: 1;
      pointer-events: auto;
      z-index: 1;
    }

    /* ── Toggle flotante ─────────────────────────────────────────────── */
    .view-toggle {
      position: absolute;
      top: 12px;
      right: 12px;
      z-index: 20;
      display: flex;
      align-items: center;
      gap: 2px;
      padding: 3px;
      background: rgba(13, 17, 23, 0.80);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 10px;
      box-shadow:
        0 4px 20px rgba(0, 0, 0, 0.45),
        0 1px 4px rgba(0, 0, 0, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
    }

    .toggle-btn {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 6px 12px;
      border: none;
      border-radius: 7px;
      background: transparent;
      color: rgba(255, 255, 255, 0.45);
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      cursor: pointer;
      transition:
        background 150ms ease,
        color 150ms ease,
        box-shadow 150ms ease;
      line-height: 1;
      white-space: nowrap;
      user-select: none;
      -webkit-user-select: none;
    }

    .toggle-btn:hover {
      color: rgba(255, 255, 255, 0.82);
      background: rgba(255, 255, 255, 0.07);
    }

    .toggle-btn--active {
      background: rgba(99, 179, 237, 0.16);
      color: #93c5fd;
      box-shadow:
        0 0 0 1px rgba(99, 179, 237, 0.28),
        inset 0 1px 2px rgba(0, 0, 0, 0.3);
    }

    .toggle-btn--active:hover {
      background: rgba(99, 179, 237, 0.22);
      color: #bfdbfe;
    }

    /* ── Indicador de carga del globo ───────────────────────────────── */
    .globe-loading {
      position: absolute;
      inset: 0;
      z-index: 15;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      background: rgba(13, 17, 23, 0.72);
      color: rgba(255, 255, 255, 0.7);
      font-size: 0.85rem;
      letter-spacing: 0.03em;
      pointer-events: none;
    }

    .globe-loading__spinner {
      width: 18px;
      height: 18px;
      border: 2px solid rgba(99, 179, 237, 0.25);
      border-top-color: #93c5fd;
      border-radius: 50%;
      animation: spin 0.75s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    /* ── Popup oscuro (override de Mapbox) ──────────────────────────── */
    ::ng-deep .mapboxgl-popup-content {
      background: #1a2232;
      border: 1px solid rgba(255, 255, 255, 0.10);
      border-radius: 10px;
      box-shadow: 0 8px 28px rgba(0, 0, 0, 0.6);
      padding: 12px 14px;
      color: #e2e8f0;
      font-family: inherit;
      font-size: 0.82rem;
      max-width: 240px;
      min-width: 180px;
    }

    ::ng-deep .mapboxgl-popup-anchor-bottom .mapboxgl-popup-tip { border-top-color:    #1a2232 !important; }
    ::ng-deep .mapboxgl-popup-anchor-top    .mapboxgl-popup-tip { border-bottom-color: #1a2232 !important; }
    ::ng-deep .mapboxgl-popup-anchor-left   .mapboxgl-popup-tip { border-right-color:  #1a2232 !important; }
    ::ng-deep .mapboxgl-popup-anchor-right  .mapboxgl-popup-tip { border-left-color:   #1a2232 !important; }

    ::ng-deep .earthquake-popup strong {
      display: block;
      font-size: 0.95rem;
      color: #93c5fd;
      margin-bottom: 8px;
      font-weight: 700;
    }

    ::ng-deep .earthquake-popup dl {
      margin: 0;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 2px 8px;
    }

    ::ng-deep .earthquake-popup dt {
      color: rgba(226, 232, 240, 0.5);
      font-weight: 500;
      white-space: nowrap;
    }

    ::ng-deep .earthquake-popup dd {
      margin: 0;
      color: #e2e8f0;
      word-break: break-word;
    }

    ::ng-deep .mapboxgl-popup-close-button {
      color: rgba(226, 232, 240, 0.45);
      font-size: 16px;
      line-height: 1;
      padding: 4px 8px;
      background: transparent;
    }

    ::ng-deep .mapboxgl-popup-close-button:hover {
      color: #e2e8f0;
      background: rgba(255, 255, 255, 0.06);
    }
  `],
})
export class EarthquakeMapComponent implements AfterViewInit, OnChanges, OnDestroy {

  // ── Interfaz pública (INTOCABLE) ──────────────────────────────────────────
  @Input() events: EarthquakeDto[] = [];
  @Input() selectedEventId: string | null = null;
  @Output() eventSelected = new EventEmitter<string>();

  @ViewChild('leafletEl', { static: true })
  private readonly leafletEl!: ElementRef<HTMLDivElement>;

  @ViewChild('mapboxEl', { static: true })
  private readonly mapboxEl!: ElementRef<HTMLDivElement>;

  // ── Estado interno ────────────────────────────────────────────────────────
  readonly projection  = signal<MapProjection>('2d');
  readonly globeLoading = signal(false);

  // ── Leaflet (2D) ──────────────────────────────────────────────────────────
  private leafletMap?: L.Map;
  private markers?: L.LayerGroup;
  private leafletReady = false;

  // ── Mapbox (3D) — se inicializa de forma lazy ─────────────────────────────
  // Usamos `unknown` para evitar importar tipos de Mapbox en el bundle inicial.
  // El tipo real es `mapboxgl.Map` y se conoce en tiempo de ejecución.
  private mapboxMap?: unknown;
  private mapboxReady = false;
  private mapboxModule?: typeof import('mapbox-gl');
  private rotationId?: number;
  private userInteracting = false;

  // ── Ciclo de vida ─────────────────────────────────────────────────────────

  ngAfterViewInit(): void {
    this.initLeaflet();
  }

  ngOnChanges(_changes: SimpleChanges): void {
    this.renderLeaflet();
    this.renderMapbox();
  }

  ngOnDestroy(): void {
    this.stopRotation();
    this.leafletMap?.remove();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (this.mapboxMap as any)?.remove?.();
    this.leafletReady = false;
    this.mapboxReady  = false;
  }

  // ── API pública: cambiar proyección ───────────────────────────────────────

  setProjection(mode: MapProjection): void {
    if (this.projection() === mode) return;
    this.projection.set(mode);

    if (mode === '3d') {
      void this.ensureMapboxReady();
    } else {
      this.stopRotation();
      // Forzar recalculo de tamaño de Leaflet al volver a ser visible
      requestAnimationFrame(() => this.leafletMap?.invalidateSize());
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  LEAFLET — Mapa 2D (código original inalterado)
  // ══════════════════════════════════════════════════════════════════════════

  private initLeaflet(): void {
    this.leafletMap = L.map(this.leafletEl.nativeElement, {
      zoomControl: true,
      scrollWheelZoom: true,
    }).setView([12, 0], 2);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(this.leafletMap);

    this.markers = L.layerGroup().addTo(this.leafletMap);
    this.leafletReady = true;
    void this.loadCountries();
    this.renderLeaflet();
  }

  private async loadCountries(): Promise<void> {
    try {
      const response = await fetch('/datos/paises.geojson');
      if (!response.ok) throw new Error(`paises.geojson returned HTTP ${response.status}`);
      const countries = (await response.json()) as GeoJSON.GeoJsonObject;
      if (!this.leafletMap) return;

      L.geoJSON(countries, {
        style: {
          color: '#80939a',
          weight: 0.7,
          fillColor: '#f4f7f8',
          fillOpacity: 0.2,
        },
      }).addTo(this.leafletMap);
    } catch (error) {
      console.error('No se pudo cargar el catálogo de países.', error);
    }
  }

  private renderLeaflet(): void {
    if (!this.leafletReady || !this.leafletMap || !this.markers) return;

    this.markers.clearLayers();
    for (const event of this.events) {
      if (
        !Number.isFinite(event.geom_lat) ||
        !Number.isFinite(event.geom_lon) ||
        event.geom_lat < -90 || event.geom_lat > 90 ||
        event.geom_lon < -180 || event.geom_lon > 180
      ) continue;

      const marker = L.circleMarker([event.geom_lat, event.geom_lon], {
        radius: markerRadius(event.mag),
        color: event.event_id === this.selectedEventId ? '#102f45' : '#ffffff',
        weight: event.event_id === this.selectedEventId ? 3 : 1.5,
        fillColor: depthColor(event.depth_km),
        fillOpacity: event.event_id === this.selectedEventId ? 1 : 0.88,
      });
      marker.bindPopup(this.createLeafletPopup(event));
      marker.addTo(this.markers);
      marker.on('click', () => this.eventSelected.emit(event.event_id));
      this.makeMarkerKeyboardAccessible(marker, event);

      if (event.event_id === this.selectedEventId) {
        this.leafletMap.setView(
          [event.geom_lat, event.geom_lon],
          Math.max(this.leafletMap.getZoom(), 4),
          { animate: false },
        );
        marker.openPopup();
      }
    }
  }

  private makeMarkerKeyboardAccessible(marker: L.CircleMarker, event: EarthquakeDto): void {
    const element = marker.getElement();
    if (!element) return;
    const place = event.place || 'Lugar no indicado';
    const utc = this.formatUtc(event.time_utc);
    element.setAttribute('role', 'button');
    element.setAttribute('tabindex', '0');
    element.setAttribute('aria-label', `Magnitud ${formatMagnitude(event.mag)}, ${place}, ${utc}`);
    element.addEventListener('keydown', (keyEvent: Event) => {
      const kev = keyEvent as KeyboardEvent;
      if (kev.key === 'Enter' || kev.key === ' ') {
        keyEvent.preventDefault();
        this.eventSelected.emit(event.event_id);
        marker.openPopup();
      }
    });
  }

  private createLeafletPopup(event: EarthquakeDto): HTMLElement {
    const popup = document.createElement('section');
    popup.className = 'earthquake-popup';

    const title = document.createElement('strong');
    title.textContent = `Magnitud ${formatMagnitude(event.mag)}`;
    popup.append(title);

    const rows: Array<[string, string]> = [
      ['Lugar',       event.place || 'Lugar no indicado'],
      ['Profundidad', formatDepth(event.depth_km)],
      ['Hora UTC',    this.formatUtc(event.time_utc)],
      ['País',        this.countryLabel(event)],
      ['ID',          event.event_id],
    ];
    if (event.ingestion_latency_seconds != null) {
      rows.push(['Latencia de ingesta', `${event.ingestion_latency_seconds.toFixed(1)} s`]);
    }

    const details = document.createElement('dl');
    for (const [label, value] of rows) {
      const dt = document.createElement('dt');
      dt.textContent = label;
      const dd = document.createElement('dd');
      dd.textContent = value;
      details.append(dt, dd);
    }
    popup.append(details);
    return popup;
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  MAPBOX — Globo 3D (inicialización lazy)
  // ══════════════════════════════════════════════════════════════════════════

  private async ensureMapboxReady(): Promise<void> {
    if (this.mapboxReady) {
      this.startRotation();
      this.renderMapbox();
      return;
    }

    this.globeLoading.set(true);

    try {
      const mapboxgl = await loadMapbox();
      this.mapboxModule = mapboxgl;
      mapboxgl.default.accessToken = getMapboxToken();
      (mapboxgl.default as unknown as { workerUrl: string }).workerUrl = '/mapbox-gl-csp-worker.js';

      const map = new mapboxgl.default.Map({
        container: this.mapboxEl.nativeElement,
        style: 'mapbox://styles/mapbox/dark-v11',
        center: [0, 20],
        zoom: 1.6,
        projection: 'globe',
        attributionControl: false,
      });

      map.addControl(new mapboxgl.default.AttributionControl({ compact: true }), 'bottom-left');
      map.addControl(new mapboxgl.default.NavigationControl(), 'bottom-right');

      map.on('load', () => {
        this.mapboxMap = map;
        this.addMapboxLayers(map, mapboxgl);
        this.bindMapboxInteractions(map, mapboxgl);

        map.setFog({
          color: 'rgb(10, 15, 30)',
          'high-color': 'rgb(26, 54, 110)',
          'horizon-blend': 0.04,
          'space-color': 'rgb(4, 7, 18)',
          'star-intensity': 0.6,
        });

        this.mapboxReady = true;
        this.globeLoading.set(false);
        this.renderMapbox();
        this.startRotation();
      });
    } catch (error) {
      console.error('No se pudo cargar Mapbox GL JS.', error);
      this.globeLoading.set(false);
      // Revertir al 2D si falla la carga
      this.projection.set('2d');
    }
  }

  private addMapboxLayers(map: mapboxgl.Map, _mb: typeof import('mapbox-gl')): void {
    map.addSource(SOURCE_ID, {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    });

    // Círculos normales
    map.addLayer({
      id: LAYER_CIRCLES,
      type: 'circle',
      source: SOURCE_ID,
      filter: ['!=', ['get', 'event_id'], ''],
      paint: {
        'circle-radius': [
          'interpolate', ['linear'], ['coalesce', ['get', 'mag'], 0],
          -2, 4,  0, 5,  3, 8,  5, 13,  7, 19,  9, 20,
        ],
        'circle-color':          ['get', 'depth_color'],
        'circle-opacity':         0.88,
        'circle-stroke-width':    1.5,
        'circle-stroke-color':   'rgba(255,255,255,0.65)',
        'circle-stroke-opacity':  0.7,
      },
    });

    // Círculo del evento seleccionado (encima, con borde resaltado)
    map.addLayer({
      id: LAYER_SELECTED,
      type: 'circle',
      source: SOURCE_ID,
      filter: ['==', ['get', 'event_id'], ''],
      paint: {
        'circle-radius': [
          'interpolate', ['linear'], ['coalesce', ['get', 'mag'], 0],
          -2, 5,  0, 6,  3, 10,  5, 15,  7, 21,  9, 22,
        ],
        'circle-color':          ['get', 'depth_color'],
        'circle-opacity':         1,
        'circle-stroke-width':    3,
        'circle-stroke-color':   '#102f45',
        'circle-stroke-opacity':  1,
      },
    });
  }

  private bindMapboxInteractions(map: mapboxgl.Map, mapboxgl: typeof import('mapbox-gl')): void {
    const popup = new mapboxgl.default.Popup({ closeButton: true, closeOnClick: false, maxWidth: '260px' });

    for (const layerId of [LAYER_CIRCLES, LAYER_SELECTED]) {
      map.on('mouseenter', layerId, () => { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', layerId, () => { map.getCanvas().style.cursor = ''; });

      map.on('click', layerId, (ev) => {
        const feature = ev.features?.[0] as mapboxgl.MapboxGeoJSONFeature | undefined;
        if (!feature || feature.geometry.type !== 'Point') return;

        const props = feature.properties as Record<string, unknown>;
        const eventId = props['event_id'] as string;
        this.eventSelected.emit(eventId);
        this.stopRotation();

        const coords = [...(feature.geometry as GeoJSON.Point).coordinates] as [number, number];
        while (Math.abs(ev.lngLat.lng - coords[0]) > 180) {
          coords[0] += ev.lngLat.lng > coords[0] ? 360 : -360;
        }
        popup.setLngLat(coords).setDOMContent(this.buildMapboxPopupDom(props)).addTo(map);
      });
    }

    const pause  = () => { this.userInteracting = true;  this.stopRotation(); };
    const resume = () => { this.userInteracting = false; this.startRotation(); };
    map.on('mousedown',  pause);  map.on('touchstart', pause);  map.on('dragstart', pause);
    map.on('mouseup',    resume); map.on('touchend',   resume); map.on('dragend',   resume);
  }

  private renderMapbox(): void {
    if (!this.mapboxReady || !this.mapboxMap) return;
    const map = this.mapboxMap as mapboxgl.Map;
    const source = map.getSource(SOURCE_ID) as mapboxgl.GeoJSONSource | undefined;
    if (!source) return;

    source.setData(toGeoJson(this.events));

    const selectedId = this.selectedEventId ?? '';
    if (map.getLayer(LAYER_CIRCLES))  map.setFilter(LAYER_CIRCLES,  ['!=', ['get', 'event_id'], selectedId]);
    if (map.getLayer(LAYER_SELECTED)) map.setFilter(LAYER_SELECTED, ['==', ['get', 'event_id'], selectedId]);

    if (this.selectedEventId) {
      const sel = this.events.find((e) => e.event_id === this.selectedEventId);
      if (sel && Number.isFinite(sel.geom_lat) && Number.isFinite(sel.geom_lon)) {
        map.flyTo({
          center: [sel.geom_lon, sel.geom_lat],
          zoom: Math.max(map.getZoom(), 4),
          duration: 900,
          essential: true,
        });
      }
    }
  }

  // ── Rotación suave del globo ───────────────────────────────────────────────

  private startRotation(): void {
    if (this.rotationId !== undefined || this.userInteracting || this.projection() !== '3d') return;
    const spin = () => {
      if (!this.mapboxMap || this.projection() !== '3d' || this.userInteracting) {
        this.rotationId = undefined;
        return;
      }
      const map = this.mapboxMap as mapboxgl.Map;
      const c = map.getCenter();
      c.lng -= 0.07;
      map.setCenter(c);
      this.rotationId = requestAnimationFrame(spin);
    };
    this.rotationId = requestAnimationFrame(spin);
  }

  private stopRotation(): void {
    if (this.rotationId !== undefined) {
      cancelAnimationFrame(this.rotationId);
      this.rotationId = undefined;
    }
  }

  // ── DOM del popup Mapbox ──────────────────────────────────────────────────

  private buildMapboxPopupDom(props: Record<string, unknown>): HTMLElement {
    const section = document.createElement('section');
    section.className = 'earthquake-popup';

    const mag     = props['mag'] as number | null;
    const depth   = props['depth_km'] as number | null;
    const adm0    = props['adm0_a3'] as string;
    const country = (props['country_name'] as string) ||
                    (props['name_es'] as string) ||
                    (props['admin_name'] as string) || 'País no indicado';
    const latency = props['ingestion_latency_seconds'] as number | null;

    const title = document.createElement('strong');
    title.textContent = `Magnitud ${mag === null ? 'ND' : mag.toFixed(1)}`;
    section.append(title);

    const rows: Array<[string, string]> = [
      ['Lugar',       (props['place'] as string) || 'Lugar no indicado'],
      ['Profundidad', depth === null ? 'ND' : `${depth.toFixed(1)} km`],
      ['Hora UTC',    this.formatUtc(props['time_utc'] as string)],
      ['País',        adm0 === 'N/A' ? 'Sin país asignado' : country],
      ['ID',          props['event_id'] as string],
    ];
    if (latency !== null) rows.push(['Latencia ingesta', `${(latency as number).toFixed(1)} s`]);

    const dl = document.createElement('dl');
    for (const [label, value] of rows) {
      const dt = document.createElement('dt'); dt.textContent = label;
      const dd = document.createElement('dd'); dd.textContent = value;
      dl.append(dt, dd);
    }
    section.append(dl);
    return section;
  }

  // ── Utilidades compartidas ────────────────────────────────────────────────

  private countryLabel(event: EarthquakeDto): string {
    if (event.adm0_a3 === 'N/A') return 'Sin país asignado';
    return event.country_name || event.name_es || event.admin_name || 'País no indicado';
  }

  private formatUtc(value: string): string {
    const ts = new Date(value);
    return Number.isNaN(ts.getTime())
      ? 'Hora no disponible'
      : ts.toISOString().replace('T', ' ').replace('.000Z', ' UTC');
  }
}
