/**
 * @typedef {{
 *   start_utc: string,
 *   end_utc: string,
 *   mag_min?: number,
 *   mag_max?: number,
 *   depth_min_km?: number,
 *   depth_max_km?: number,
 *   adm0_a3?: string,
 *   continent?: string,
 *   subregion?: string
 * }} AppliedFilters
 */

/**
 * Convert a datetime-local value explicitly interpreted as UTC into an ISO timestamp.
 * The UI labels these inputs UTC so browser-local timezone conversion is deliberately avoided.
 * @param {string} value
 * @returns {string | null}
 */
export function datetimeInputToUtc(value) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) {
    return null;
  }
  const date = new Date(`${value}:00Z`);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

/**
 * @param {string} value
 * @returns {string}
 */
export function utcToDatetimeInput(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().slice(0, 16);
}

/**
 * @param {Record<string, string>} draft
 * @returns {{ filters: AppliedFilters | null, error: string | null }}
 */
export function validateFilterDraft(draft) {
  const start = datetimeInputToUtc(draft['start_utc'] ?? '');
  const end = datetimeInputToUtc(draft['end_utc'] ?? '');
  if (!start || !end) {
    return { filters: null, error: 'Introduce fechas válidas en UTC.' };
  }
  if (Date.parse(start) >= Date.parse(end)) {
    return { filters: null, error: 'La fecha inicial debe ser anterior a la fecha final.' };
  }

  /** @type {AppliedFilters} */
  const filters = { start_utc: start, end_utc: end };
  for (const key of ['mag_min', 'mag_max', 'depth_min_km', 'depth_max_km']) {
    const raw = (draft[key] ?? '').trim();
    if (!raw) {
      continue;
    }
    const value = Number(raw);
    if (!Number.isFinite(value)) {
      return { filters: null, error: 'Los límites de magnitud y profundidad deben ser números finitos.' };
    }
    filters[key] = value;
  }

  if (filters.mag_min !== undefined && filters.mag_max !== undefined && filters.mag_min > filters.mag_max) {
    return { filters: null, error: 'La magnitud mínima no puede superar la máxima.' };
  }
  if (
    filters.depth_min_km !== undefined &&
    filters.depth_max_km !== undefined &&
    filters.depth_min_km > filters.depth_max_km
  ) {
    return { filters: null, error: 'La profundidad mínima no puede superar la máxima.' };
  }

  for (const key of ['adm0_a3', 'continent', 'subregion']) {
    const value = (draft[key] ?? '').trim();
    if (value) {
      filters[key] = value;
    }
  }
  return { filters, error: null };
}

/**
 * Build a scaled SVG polyline from the hourly buckets returned by the API.
 * Missing buckets are not invented; each plotted point represents an API result.
 * @param {Array<{ hour_utc: string, event_count: number }>} items
 * @param {number} width
 * @param {number} height
 * @returns {string}
 */
export function hourlyPolyline(items, width = 640, height = 180) {
  if (items.length === 0) {
    return '';
  }
  const padding = 12;
  const max = Math.max(1, ...items.map((item) => item.event_count));
  const plotWidth = width - padding * 2;
  const plotHeight = height - padding * 2;
  return items
    .map((item, index) => {
      const x = items.length === 1 ? width / 2 : padding + (index / (items.length - 1)) * plotWidth;
      const y = height - padding - (item.event_count / max) * plotHeight;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}

/**
 * @param {Array<{ hour_utc: string, event_count: number }>} items
 * @returns {number}
 */
export function hourlyMaximum(items) {
  return items.reduce((maximum, item) => Math.max(maximum, item.event_count), 0);
}

/**
 * Search applies only to the loaded table page. It never changes dashboard queries.
 * @param {Array<{ event_id: string, place: string | null, country_name: string }>} items
 * @param {string} query
 * @returns {typeof items}
 */
export function searchLoadedEvents(items, query) {
  const needle = query.trim().toLocaleLowerCase();
  if (!needle) {
    return items;
  }
  return items.filter((item) =>
    `${item.event_id} ${item.place ?? ''} ${item.country_name}`.toLocaleLowerCase().includes(needle),
  );
}


/**
 * Format replay run status and badge text according to TC-11.
 * @param {'live' | 'replay'} scope
 * @param {{ run_id?: string | null, status?: string } | null} replayState
 * @returns {{ isReplay: boolean, badgeText: string, statusSummary: string }}
 */
export function formatReplayBadge(scope, replayState) {
  const isReplay = scope === 'replay';
  return {
    isReplay,
    badgeText: isReplay ? 'REPRODUCCIÓN' : '',
    statusSummary: isReplay
      ? (replayState?.run_id ? `Ejecución ${replayState.run_id} (${replayState.status ?? 'idle'})` : 'Sin ejecución')
      : 'En vivo',
  };
}
