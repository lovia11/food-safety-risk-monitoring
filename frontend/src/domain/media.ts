export const LIGHTBOX_MIN_ZOOM = 0.5;
export const LIGHTBOX_MAX_ZOOM = 2.5;
export const LIGHTBOX_ZOOM_STEP = 0.25;

export function clampLightboxZoom(value: number) {
  return Math.min(LIGHTBOX_MAX_ZOOM, Math.max(LIGHTBOX_MIN_ZOOM, value));
}
export function moveLightboxIndex(current: number, delta: number, total: number) {
  if (total <= 0) return 0;
  return (current + delta + total) % total;
}
