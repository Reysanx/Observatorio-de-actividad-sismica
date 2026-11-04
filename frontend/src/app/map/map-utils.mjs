/**
 * @param {number | null} magnitude
 * @returns {string}
 */
export function formatMagnitude(magnitude) {
  return magnitude === null ? 'ND' : magnitude.toFixed(1);
}

/**
 * @param {number | null} depthKm
 * @returns {string}
 */
export function formatDepth(depthKm) {
  return depthKm === null ? 'ND' : `${depthKm.toFixed(1)} km`;
}

/**
 * @param {number | null} magnitude
 * @returns {number}
 */
export function markerRadius(magnitude) {
  if (magnitude === null) {
    return 5;
  }
  return Math.min(20, Math.max(4, magnitude * 2 + 5));
}

/**
 * @param {number | null} depthKm
 * @returns {string}
 */
export function depthColor(depthKm) {
  if (depthKm === null) {
    return '#64748b';
  }
  if (depthKm < 30) {
    return '#16803c';
  }
  if (depthKm <= 70) {
    return '#c18a00';
  }
  if (depthKm <= 300) {
    return '#d75b13';
  }
  return '#bd2635';
}
