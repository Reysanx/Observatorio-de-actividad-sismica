import assert from 'node:assert/strict';
import test from 'node:test';
import {
  datetimeInputToUtc,
  formatReplayBadge,
  hourlyMaximum,
  hourlyPolyline,
  searchLoadedEvents,
  utcToDatetimeInput,
  validateFilterDraft,
} from '../src/app/dashboard-utils.mjs';

const validDraft = {
  start_utc: '2026-11-01T10:00',
  end_utc: '2026-11-02T10:00',
  mag_min: '',
  mag_max: '',
  depth_min_km: '',
  depth_max_km: '',
  adm0_a3: '',
  continent: '',
  subregion: '',
};

test('datetime-local filters are interpreted and serialized as UTC, not browser local time', () => {
  assert.equal(datetimeInputToUtc('2026-11-02T12:30'), '2026-11-02T12:30:00.000Z');
  assert.equal(utcToDatetimeInput('2026-11-02T12:30:00Z'), '2026-11-02T12:30');
  assert.equal(datetimeInputToUtc('not-a-date'), null);
});

test('filter validation preserves negative scientific values and sends only set filters', () => {
  const result = validateFilterDraft({
    ...validDraft,
    mag_min: '-1.2',
    depth_min_km: '-2.5',
    adm0_a3: 'N/A',
  });
  assert.equal(result.error, null);
  assert.deepEqual(result.filters, {
    start_utc: '2026-11-01T10:00:00.000Z',
    end_utc: '2026-11-02T10:00:00.000Z',
    mag_min: -1.2,
    depth_min_km: -2.5,
    adm0_a3: 'N/A',
  });
});

test('invalid range and inverted numeric bounds are rejected without filters', () => {
  assert.match(
    validateFilterDraft({ ...validDraft, start_utc: '2026-11-02T10:00' }).error,
    /anterior/,
  );
  assert.match(
    validateFilterDraft({ ...validDraft, mag_min: '5', mag_max: '4' }).error,
    /magnitud mínima/,
  );
  assert.match(
    validateFilterDraft({ ...validDraft, depth_min_km: '8', depth_max_km: '2' }).error,
    /profundidad mínima/,
  );
});

test('hourly chart scales the returned buckets and handles a single observation', () => {
  const items = [
    { hour_utc: '2026-11-02T10:00:00Z', event_count: 2 },
    { hour_utc: '2026-11-02T11:00:00Z', event_count: 4 },
  ];
  assert.equal(hourlyMaximum(items), 4);
  assert.match(hourlyPolyline(items), /^12\.0,90\.0 628\.0,12\.0$/);
  assert.equal(hourlyPolyline([{ hour_utc: '2026-11-02T10:00:00Z', event_count: 0 }]), '320.0,168.0');
  assert.equal(hourlyPolyline([]), '');
});

test('loaded-row search is case insensitive and does not mutate the source array', () => {
  const items = [
    { event_id: 'us001', place: 'Chile', country_name: 'Chile' },
    { event_id: 'us002', place: 'Atlantic Ocean', country_name: 'Sin país asignado' },
  ];
  assert.deepEqual(searchLoadedEvents(items, 'ATLANTIC'), [items[1]]);
  assert.deepEqual(searchLoadedEvents(items, ''), items);
  assert.equal(items.length, 2);
});

test('replay badge formatting distinguishes live from replay and displays REPRODUCCION', () => {
  const live = formatReplayBadge('live', null);
  assert.equal(live.isReplay, false);
  assert.equal(live.badgeText, '');
  assert.equal(live.statusSummary, 'En vivo');

  const replayWithRun = formatReplayBadge('replay', { run_id: 'run-2026-test', status: 'completed' });
  assert.equal(replayWithRun.isReplay, true);
  assert.equal(replayWithRun.badgeText, 'REPRODUCCIÓN');
  assert.equal(replayWithRun.statusSummary, 'Ejecución run-2026-test (completed)');

  const replayIdle = formatReplayBadge('replay', null);
  assert.equal(replayIdle.isReplay, true);
  assert.equal(replayIdle.badgeText, 'REPRODUCCIÓN');
  assert.equal(replayIdle.statusSummary, 'Sin ejecución');
});
