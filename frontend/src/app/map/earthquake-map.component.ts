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
} from '@angular/core';
import * as L from 'leaflet';
import { EarthquakeDto } from '../api/earthquake-api.service';
import { depthColor, formatDepth, formatMagnitude, markerRadius } from './map-utils.mjs';

@Component({
  selector: 'app-earthquake-map',
  standalone: true,
  template: '<div #mapElement class="map-canvas" role="application" aria-label="Mapa de terremotos"></div>',
  styles: [`
    :host {
      display: block;
      min-height: 360px;
      height: min(68vh, 760px);
    }

    .map-canvas {
      width: 100%;
      height: 100%;
      min-height: 360px;
      background: #e7eef1;
    }
  `],
})
export class EarthquakeMapComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() events: EarthquakeDto[] = [];
  @Input() selectedEventId: string | null = null;
  @Output() eventSelected = new EventEmitter<string>();
  @ViewChild('mapElement', { static: true })
  private mapElement!: ElementRef<HTMLDivElement>;

  private map?: L.Map;
  private markers?: L.LayerGroup;
  private ready = false;

  ngAfterViewInit(): void {
    this.map = L.map(this.mapElement.nativeElement, {
      zoomControl: true,
      scrollWheelZoom: true,
    }).setView([12, 0], 2);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(this.map);

    this.markers = L.layerGroup().addTo(this.map);
    this.ready = true;
    void this.loadCountries();
    this.renderEvents();
  }

  ngOnChanges(_changes: SimpleChanges): void {
    this.renderEvents();
  }

  ngOnDestroy(): void {
    this.map?.remove();
    this.ready = false;
  }

  private async loadCountries(): Promise<void> {
    try {
      const response = await fetch('/datos/paises.geojson');
      if (!response.ok) {
        throw new Error(`paises.geojson returned HTTP ${response.status}`);
      }
      const countries = (await response.json()) as GeoJSON.GeoJsonObject;
      if (!this.map) {
        return;
      }

      L.geoJSON(countries, {
        style: {
          color: '#80939a',
          weight: 0.7,
          fillColor: '#f4f7f8',
          fillOpacity: 0.2,
        },
      }).addTo(this.map);
    } catch (error) {
      console.error('No se pudo cargar el catálogo de países.', error);
    }
  }

  private renderEvents(): void {
    if (!this.ready || !this.map || !this.markers) {
      return;
    }

    this.markers.clearLayers();
    for (const event of this.events) {
      if (
        !Number.isFinite(event.geom_lat) ||
        !Number.isFinite(event.geom_lon) ||
        event.geom_lat < -90 ||
        event.geom_lat > 90 ||
        event.geom_lon < -180 ||
        event.geom_lon > 180
      ) {
        continue;
      }

      const marker = L.circleMarker([event.geom_lat, event.geom_lon], {
        radius: markerRadius(event.mag),
        color: event.event_id === this.selectedEventId ? '#102f45' : '#ffffff',
        weight: event.event_id === this.selectedEventId ? 3 : 1.5,
        fillColor: depthColor(event.depth_km),
        fillOpacity: event.event_id === this.selectedEventId ? 1 : 0.88,
      });
      marker.bindPopup(this.createPopup(event));
      marker.addTo(this.markers);
      marker.on('click', () => this.eventSelected.emit(event.event_id));
      this.makeMarkerKeyboardAccessible(marker, event);
      if (event.event_id === this.selectedEventId) {
        this.map.setView([event.geom_lat, event.geom_lon], Math.max(this.map.getZoom(), 4), {
          animate: false,
        });
        marker.openPopup();
      }
    }
  }

  private makeMarkerKeyboardAccessible(marker: L.CircleMarker, event: EarthquakeDto): void {
    const element = marker.getElement();
    if (!element) {
      return;
    }

    const place = event.place || 'Lugar no indicado';
    const utc = this.formatUtc(event.time_utc);
    element.setAttribute('role', 'button');
    element.setAttribute('tabindex', '0');
    element.setAttribute(
      'aria-label',
      `Magnitud ${formatMagnitude(event.mag)}, ${place}, ${utc}`,
    );
    element.addEventListener('keydown', (keyEvent: Event) => {
      const keyboardEvent = keyEvent as KeyboardEvent;
      if (keyboardEvent.key === 'Enter' || keyboardEvent.key === ' ') {
        keyEvent.preventDefault();
        this.eventSelected.emit(event.event_id);
        marker.openPopup();
      }
    });
  }

  private createPopup(event: EarthquakeDto): HTMLElement {
    const popup = document.createElement('section');
    popup.className = 'earthquake-popup';

    const title = document.createElement('strong');
    title.textContent = `Magnitud ${formatMagnitude(event.mag)}`;
    popup.append(title);

    const rows: Array<[string, string]> = [
      ['Lugar', event.place || 'Lugar no indicado'],
      ['Profundidad', formatDepth(event.depth_km)],
      ['Hora UTC', this.formatUtc(event.time_utc)],
      ['País', this.countryLabel(event)],
      ['ID', event.event_id],
    ];
    if (event.ingestion_latency_seconds != null) {
      rows.push(['Latencia de ingesta', `${event.ingestion_latency_seconds.toFixed(1)} s`]);
    }

    const details = document.createElement('dl');
    for (const [label, value] of rows) {
      const term = document.createElement('dt');
      term.textContent = label;
      const description = document.createElement('dd');
      description.textContent = value;
      details.append(term, description);
    }
    popup.append(details);
    return popup;
  }

  private countryLabel(event: EarthquakeDto): string {
    if (event.adm0_a3 === 'N/A') {
      return 'Sin país asignado';
    }
    return event.country_name || event.name_es || event.admin_name || 'País no indicado';
  }

  private formatUtc(value: string): string {
    const timestamp = new Date(value);
    return Number.isNaN(timestamp.getTime())
      ? 'Hora no disponible'
      : `${timestamp.toISOString().replace('T', ' ').replace('.000Z', ' UTC')}`;
  }
}
