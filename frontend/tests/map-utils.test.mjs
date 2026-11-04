import assert from 'node:assert/strict';
import test from 'node:test';
import {
  depthColor,
  formatDepth,
  formatMagnitude,
  markerRadius,
} from '../src/app/map/map-utils.mjs';

test('missing magnitude and depth are presented as ND', () => {
  assert.equal(formatMagnitude(null), 'ND');
  assert.equal(formatDepth(null), 'ND');
});

test('negative values are preserved in labels and only marker size is clamped', () => {
  assert.equal(formatMagnitude(-0.5), '-0.5');
  assert.equal(formatDepth(-1.25), '-1.3 km');
  assert.equal(markerRadius(-0.5), 4);
  assert.equal(markerRadius(null), 5);
});

test('depth bands match the product legend, including their boundaries', () => {
  assert.equal(depthColor(29.9), '#16803c');
  assert.equal(depthColor(30), '#c18a00');
  assert.equal(depthColor(70), '#c18a00');
  assert.equal(depthColor(70.1), '#d75b13');
  assert.equal(depthColor(300), '#d75b13');
  assert.equal(depthColor(300.1), '#bd2635');
  assert.equal(depthColor(null), '#64748b');
});
