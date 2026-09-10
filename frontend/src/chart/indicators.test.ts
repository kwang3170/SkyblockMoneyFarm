import { describe, expect, it } from 'vitest';
import { bollinger, ema, sma, vwap } from './indicators';
const points = [1, 2, 3, 4, 5].map((value, time) => ({ time, value }));
describe('research indicators', () => {
  it('computes SMA after warmup', () => expect(sma(points, 3).map(p => p.value)).toEqual([2, 3, 4]));
  it('seeds EMA with SMA', () => expect(ema(points, 3).map(p => p.value)).toEqual([2, 3, 4]));
  it('uses population standard deviation for Bollinger bands', () => { const bands = bollinger(points, 3); expect(bands.middle[0].value).toBe(2); expect(bands.upper[0].value).toBeCloseTo(2 + 2 * Math.sqrt(2 / 3)); });
  it('resets VWAP at UTC midnight and skips zero-volume observations', () => {
    expect(vwap([{ time: 0, value: 50, volume: 0 }, { time: 1, value: 10, volume: 2 }, { time: 2, value: 20, volume: 2 }, { time: 86400, value: 30, volume: 1 }]))
      .toEqual([{ time: 1, value: 10 }, { time: 2, value: 15 }, { time: 86400, value: 30 }]);
  });
  it('handles insufficient history and invalid periods', () => { expect(sma(points, 20)).toEqual([]); expect(ema(points, 20)).toEqual([]); expect(() => sma(points, 0)).toThrow(); });
});
