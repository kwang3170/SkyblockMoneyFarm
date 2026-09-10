import { useEffect, useRef, useState } from 'react';
import { CandlestickSeries, ColorType, createChart, HistogramSeries, LineSeries, type IChartApi, type ISeriesApi, type Logical, type LogicalRange, type UTCTimestamp } from 'lightweight-charts';
import { MousePointer2, Minus, TrendingUp, Square, Type, Undo2, Trash2 } from 'lucide-react';
import { get, productPath, useStored } from '../api';
import { bollinger, ema, sma, vwap } from '../chart/indicators';
import type { Anchor, Candle, Drawing, Indicator, Interval, Tool } from '../types';

interface Props { product: string; updated: number; interval: Interval; mode: 'candles' | 'line'; overlay: boolean; indicators: Indicator[]; start: number; end: number | null }
const colors = { green: '#41d6ad', red: '#f07886', blue: '#71a8ff', gold: '#e9bd6e' };
export default function MarketChart({ product, updated, interval, mode, overlay, indicators, start, end }: Props) {
  const host = useRef<HTMLDivElement>(null), canvas = useRef<HTMLCanvasElement>(null);
  const chart = useRef<IChartApi | null>(null), priceSeries = useRef<ISeriesApi<'Candlestick'> | ISeriesApi<'Line'> | null>(null);
  const previousView = useRef<{ context: string; range: LogicalRange | null; count: number }>({ context: '', range: null, count: 0 });
  const [data, setData] = useState<{ buy: Candle[]; sell: Candle[] }>({ buy: [], sell: [] });
  const [error, setError] = useState(''), [loading, setLoading] = useState(true);
  const [drawings, setDrawings] = useStored<Drawing[]>(`bazaar.drawings.${product}`, []);
  const [tool, setTool] = useState<Tool>('cursor');
  const pending = useRef<Anchor | null>(null), latestDrawings = useRef(drawings), latestTool = useRef(tool);
  latestDrawings.current = drawings; latestTool.current = tool;
  useEffect(() => { pending.current = null; }, [tool]);
  useEffect(() => {
    const controller = new AbortController();
    const query = `interval=${interval}&start=${start}${end != null ? `&end=${end}` : ''}`;
    setLoading(true);
    void Promise.all([get<Candle[]>(`${productPath(product)}/candles?${query}&price_type=insta_buy_price`, controller.signal),
      get<Candle[]>(`${productPath(product)}/candles?${query}&price_type=insta_sell_price`, controller.signal)])
      .then(([buy, sell]) => { setData({ buy, sell }); setError(''); setLoading(false); })
      .catch((e: unknown) => { if (!controller.signal.aborted) { setError(e instanceof Error ? e.message : 'Could not load chart'); setLoading(false); } });
    return () => controller.abort();
  }, [product, updated, interval, start, end]);

  useEffect(() => {
    if (!host.current) return;
    const instance = createChart(host.current, {
      autoSize: true, layout: { background: { type: ColorType.Solid, color: '#101720' }, textColor: '#8c9caf', fontSize: 12, fontFamily: 'ui-monospace, monospace', attributionLogo: true },
      grid: { vertLines: { color: '#1a2430' }, horzLines: { color: '#1a2430' } },
      rightPriceScale: { borderColor: '#26313e', scaleMargins: { top: 0.1, bottom: 0.24 } },
      timeScale: { borderColor: '#26313e', timeVisible: true, secondsVisible: false },
      crosshair: { vertLine: { color: '#718096' }, horzLine: { color: '#718096' } },
    });
    chart.current = instance;
    const main = mode === 'candles' ? instance.addSeries(CandlestickSeries, { upColor: colors.green, downColor: colors.red, wickUpColor: colors.green, wickDownColor: colors.red, borderVisible: false })
      : instance.addSeries(LineSeries, { color: colors.green, lineWidth: 2 });
    priceSeries.current = main;
    const volume = instance.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: 'volume', lastValueVisible: false, priceLineVisible: false });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    const bid = overlay ? instance.addSeries(LineSeries, { color: colors.blue, lineWidth: 1, title: 'Insta-sell', priceLineVisible: false }) : null;
    const points = data.buy.map(c => ({ time: c.bucket_start / 1000, value: c.close }));
    main.setData(mode === 'candles' ? data.buy.map(c => ({ time: c.bucket_start / 1000 as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close }))
      : points.map(p => ({ ...p, time: p.time as UTCTimestamp })));
    volume.setData(data.buy.map(c => ({ time: c.bucket_start / 1000 as UTCTimestamp, value: c.estimated_volume, color: c.close >= c.open ? '#235547' : '#55353e' })));
    bid?.setData(data.sell.map(c => ({ time: c.bucket_start / 1000 as UTCTimestamp, value: c.close })));
    function line(values: { time: number; value: number }[], color: string, title: string) {
      instance.addSeries(LineSeries, { color, lineWidth: 1, title, priceLineVisible: false, lastValueVisible: false })
        .setData(values.map(p => ({ ...p, time: p.time as UTCTimestamp })));
    }
    if (indicators.includes('SMA')) line(sma(points), colors.gold, 'SMA 20');
    if (indicators.includes('EMA')) line(ema(points), '#ce9cf4', 'EMA 20');
    if (indicators.includes('BB')) { const bands = bollinger(points); line(bands.upper, '#7c869c', 'BB upper'); line(bands.middle, '#a3b1c4', 'BB 20'); line(bands.lower, '#7c869c', 'BB lower'); }
    if (indicators.includes('VWAP')) line(vwap(data.buy.map(c => ({ time: c.bucket_start / 1000, value: (c.high + c.low + c.close) / 3, volume: c.estimated_volume }))), '#e9955e', 'VWAP proxy');
    const context = `${product}/${interval}/${start}/${end}`;
    const saved = previousView.current;
    if (saved.context === context && saved.range && data.buy.length) {
      const shift = Number(saved.range.to) >= saved.count - 1 ? Math.max(0, data.buy.length - saved.count) : 0;
      instance.timeScale().setVisibleLogicalRange({ from: Number(saved.range.from) + shift, to: Number(saved.range.to) + shift });
    } else instance.timeScale().fitContent();
    instance.subscribeClick(event => {
      const active = latestTool.current;
      if (active === 'cursor' || !event.point || typeof event.time !== 'number') return;
      const price = main.coordinateToPrice(event.point.y);
      if (price === null) return;
      const anchor = { time: event.time as number, price };
      if ((active === 'trend' || active === 'rectangle') && !pending.current) { pending.current = anchor; return; }
      const text = active === 'note' ? window.prompt('Chart note') : undefined;
      if (active === 'note' && !text) return;
      const drawing: Drawing = { id: crypto.randomUUID(), tool: active, start: pending.current ?? anchor,
        end: pending.current ? anchor : undefined, text: text ?? undefined };
      pending.current = null;
      setDrawings(previous => [...previous, drawing]); setTool('cursor');
    });
    let frame = 0;
    // An anchor may fall between bars after an interval change; interpolate its
    // logical position rather than requiring an exact candle timestamp match.
    const timeX = (time: number) => {
      const exact = instance.timeScale().timeToCoordinate(time as UTCTimestamp);
      if (exact !== null || !data.buy.length) return exact;
      let low = 0, high = data.buy.length;
      while (low < high) { const middle = Math.floor((low + high) / 2); if (data.buy[middle].bucket_start / 1000 < time) low = middle + 1; else high = middle; }
      const duration = { '1m': 60, '5m': 300, '15m': 900, '1h': 3600, '4h': 14400, '1d': 86400 }[interval];
      const left = Math.max(0, low - 1), leftTime = data.buy[left].bucket_start / 1000;
      const span = low > 0 && low < data.buy.length ? data.buy[low].bucket_start / 1000 - leftTime : duration;
      return instance.timeScale().logicalToCoordinate((left + (time - leftTime) / span) as Logical);
    };
    const paint = () => {
      const surface = canvas.current, element = host.current;
      if (!surface || !element) return;
      const width = element.clientWidth, height = element.clientHeight, dpr = window.devicePixelRatio || 1;
      if (surface.width !== width * dpr || surface.height !== height * dpr) { surface.width = width * dpr; surface.height = height * dpr; }
      const ctx = surface.getContext('2d');
      if (ctx) {
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, width, height); ctx.save();
        ctx.beginPath(); ctx.rect(0, 0, instance.timeScale().width(), height - 28); ctx.clip();
        ctx.strokeStyle = colors.gold; ctx.fillStyle = colors.gold; ctx.lineWidth = 1.4; ctx.font = '13px sans-serif';
        for (const drawing of latestDrawings.current) {
          const x = timeX(drawing.start.time), y = main.priceToCoordinate(drawing.start.price);
          if (y === null) continue;
          if (drawing.tool === 'horizontal') { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); continue; }
          if (x === null) continue;
          if (drawing.tool === 'note') { ctx.fillText(drawing.text ?? '', x + 5, y - 6); continue; }
          if (!drawing.end) continue;
          const x2 = timeX(drawing.end.time), y2 = main.priceToCoordinate(drawing.end.price);
          if (x2 === null || y2 === null) continue;
          if (drawing.tool === 'trend') { ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x2, y2); ctx.stroke(); }
          else { ctx.fillStyle = '#e9bd6e16'; ctx.fillRect(x, y, x2 - x, y2 - y); ctx.strokeRect(x, y, x2 - x, y2 - y); ctx.fillStyle = colors.gold; }
        }
        if (pending.current) { const x = instance.timeScale().timeToCoordinate(pending.current.time as UTCTimestamp), y = main.priceToCoordinate(pending.current.price); if (x !== null && y !== null) { ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fill(); } }
        ctx.restore();
      }
      frame = requestAnimationFrame(paint);
    };
    frame = requestAnimationFrame(paint);
    return () => { previousView.current = { context, range: instance.timeScale().getVisibleLogicalRange(), count: data.buy.length }; cancelAnimationFrame(frame); instance.remove(); chart.current = null; priceSeries.current = null; };
  }, [data, mode, overlay, indicators]);
  return <div className="chart-shell">
    <div className="drawing-tools" aria-label="Drawing tools">
      {([{ id: 'cursor', Icon: MousePointer2, label: 'Pan and inspect' }, { id: 'horizontal', Icon: Minus, label: 'Horizontal line' },
        { id: 'trend', Icon: TrendingUp, label: 'Trend line (two clicks)' }, { id: 'rectangle', Icon: Square, label: 'Rectangle (two clicks)' },
        { id: 'note', Icon: Type, label: 'Text note' }] as const).map(({ id, Icon, label }) => <button key={id} title={label} aria-label={label} aria-pressed={tool === id} className={tool === id ? 'active' : ''} onClick={() => setTool(id)}><Icon size={17}/></button>)}
      <span className="tool-divider"/>
      <button title="Undo drawing" aria-label="Undo drawing" disabled={!drawings.length} onClick={() => setDrawings(drawings.slice(0, -1))}><Undo2 size={17}/></button>
      <button title="Clear drawings" aria-label="Clear drawings" disabled={!drawings.length} onClick={() => setDrawings([])}><Trash2 size={17}/></button>
    </div>
    <div className="chart-stage"><div ref={host} className="chart-host"/><canvas ref={canvas} className="drawing-canvas"/>
      <div className="chart-legend"><span className="positive">━ Insta-buy</span>{overlay && <span className="blue">━ Insta-sell</span>}<span>Sampled quotes · UTC</span></div>
      <span className="volume-label">EST. VOLUME{data.buy.length === 2000 ? ' · LATEST 2,000 CANDLES' : ''}</span>
      {tool !== 'cursor' && <div className="chart-hint">{tool === 'trend' || tool === 'rectangle' ? 'Click two points on the chart' : 'Click the chart to place your drawing'}</div>}
      {error ? <div className="chart-message negative">{error}</div> : !data.buy.length && <div className="chart-message">{loading ? 'Loading market history…' : 'No observations in this range. Choose a wider range or let the collector run.'}</div>}
    </div>
  </div>;
}
