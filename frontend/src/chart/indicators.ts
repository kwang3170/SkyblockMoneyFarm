/** Pure indicators on observed candle closes; no UI or chart-library dependencies. */
export interface Point { time: number; value: number }
export interface WeightedPoint extends Point { volume: number }
function checkPeriod(period: number): void { if (!Number.isInteger(period) || period < 1) throw new Error('Period must be a positive integer'); }
export function sma(points: Point[], period = 20): Point[] {
  checkPeriod(period); let sum = 0;
  return points.flatMap((point, i) => { sum += point.value; if (i >= period) sum -= points[i - period].value; return i >= period - 1 ? [{ time: point.time, value: sum / period }] : []; });
}
export function ema(points: Point[], period = 20): Point[] {
  checkPeriod(period); if (points.length < period) return [];
  let value = points.slice(0, period).reduce((total, point) => total + point.value, 0) / period;
  const output = [{ time: points[period - 1].time, value }];
  for (let i = period; i < points.length; i++) { value += (points[i].value - value) * 2 / (period + 1); output.push({ time: points[i].time, value }); }
  return output;
}
export function bollinger(points: Point[], period = 20, deviations = 2): { upper: Point[]; middle: Point[]; lower: Point[] } {
  const middle = sma(points, period), upper: Point[] = [], lower: Point[] = [];
  middle.forEach((point, i) => { const variance = points.slice(i, i + period).reduce((sum, p) => sum + (p.value - point.value) ** 2, 0) / period;
    const width = Math.sqrt(variance) * deviations; upper.push({ time: point.time, value: point.value + width }); lower.push({ time: point.time, value: point.value - width }); });
  return { upper, middle, lower };
}
/** UTC-day reset. Weights are estimated volume, so UI labels this a proxy. */
export function vwap(points: WeightedPoint[]): Point[] {
  let day = -1, volume = 0, weighted = 0;
  return points.flatMap(point => { const current = Math.floor(point.time / 86400); if (current !== day) { day = current; volume = 0; weighted = 0; }
    volume += point.volume; weighted += point.value * point.volume;
    return volume > 0 ? [{ time: point.time, value: weighted / volume }] : []; });
}
