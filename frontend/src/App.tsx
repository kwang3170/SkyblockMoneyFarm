import { useState } from 'react';
import { Activity, Radio, X } from 'lucide-react';
import { API, productPath, useMarket, useStored } from './api';
import { date, number, percent, tone } from './format';
import type { Indicator, Interval } from './types';
import ProductSidebar from './components/ProductSidebar';
import MarketChart from './components/MarketChart';
import OrderBook from './components/OrderBook';
import ProductStats from './components/ProductStats';
import Screener from './components/Screener';
import HistoryScrubber from './components/HistoryScrubber';

export default function App() {
  const { products, status, connection, error } = useMarket();
  const [selected, setSelected] = useState('ENCHANTED_DIAMOND');
  const [tabs, setTabs] = useStored<string[]>('bazaar.tabs', ['ENCHANTED_DIAMOND']);
  const [watchlist, setWatchlist] = useStored<string[]>('bazaar.watchlist', ['ENCHANTED_DIAMOND', 'BOOSTER_COOKIE']);
  const [interval, setInterval] = useState<Interval>('5m'), [mode, setMode] = useState<'candles' | 'line'>('candles');
  const [overlay, setOverlay] = useState(true), [indicators, setIndicators] = useState<Indicator[]>([]);
  const [at, setAt] = useState<number | null>(null);
  const [range, setRange] = useState<{ start: number; end: number | null }>({ start: 0, end: null });
  const [from, setFrom] = useState(''), [to, setTo] = useState(''), [rangeError, setRangeError] = useState('');
  const product = products.find(p => p.product_id === selected) ?? products[0];
  const active = product?.product_id ?? selected;
  const select = (id: string) => { setSelected(id); setAt(null); setTabs(previous => previous.includes(id) ? previous : [...previous, id]); };
  const exportQuery = `start=${range.start}${range.end != null ? `&end=${range.end}` : ''}`;
  return <div className="terminal">
    <header className="topbar"><div className="brand"><Activity size={22}/><strong>BAZAAR</strong><span>/</span><span>TERMINAL</span></div><div className="top-right"><span className="network">HYPIXEL SKYBLOCK</span><span className={`feed-badge ${status?.source === 'synthetic' ? 'demo' : ''}`}><Radio size={13}/>{status?.source === 'synthetic' ? 'SYNTHETIC DATA' : 'MARKET DATA'}</span></div></header>
    {error && <div role="alert" className="error-banner">API unavailable · {error}</div>}
    <main className="workspace"><ProductSidebar products={products} selected={active} watchlist={watchlist} select={select} toggle={id => setWatchlist(previous => previous.includes(id) ? previous.filter(x => x !== id) : [...previous, id])}/>
      <section className="center panel"><div className="product-tabs">{tabs.map(id => <div key={id} className={active === id ? 'tab active-tab' : 'tab'}><button onClick={() => select(id)}>{products.find(p => p.product_id === id)?.name ?? id.replaceAll('_', ' ')}</button><button aria-label={`Close ${id}`} onClick={() => { const remaining = tabs.filter(x => x !== id); setTabs(remaining); if (active === id) setSelected(remaining[0] ?? products[0]?.product_id ?? ''); }}><X size={12}/></button></div>)}</div>
        <div className="instrument"><div className="instrument-title"><span className="item-mark">✧</span><div><h1>{product?.name ?? 'Bazaar markets'}</h1><span>{active} <b>BAZAAR</b></span></div></div><div className="headline-price"><strong>{number(product?.insta_buy_price)}</strong><span className={tone(product?.change_24h_pct)}>{percent(product?.change_24h_pct)} <span className="muted">24h</span></span></div></div>
        <div className="quote-strip"><div><span>Insta-sell</span><b className="blue">{number(product?.insta_sell_price)}</b></div><div><span>Spread</span><b>{number(product?.spread_pct)}%</b></div><div><span>Net margin</span><b className={tone(product?.flip_margin_pct)}>{percent(product?.flip_margin_pct)}</b></div><div><span>Weekly buy activity</span><b>{number(product?.insta_buy_moving_week, true)}</b></div></div>
        <div className="chart-controls"><div className="segmented">{(['1m', '5m', '15m', '1h', '4h', '1d'] as Interval[]).map(value => <button key={value} className={interval === value ? 'active' : ''} onClick={() => setInterval(value)}>{value}</button>)}</div><select aria-label="Chart type" value={mode} onChange={e => setMode(e.target.value as 'candles' | 'line')}><option value="candles">Candles</option><option value="line">Line</option></select><label><input type="checkbox" checked={overlay} onChange={e => setOverlay(e.target.checked)}/> Insta-sell</label></div>
        <div className="indicator-controls"><span>INDICATORS</span>{(['SMA', 'EMA', 'BB', 'VWAP'] as Indicator[]).map(value => <button key={value} className={indicators.includes(value) ? 'active' : ''} onClick={() => setIndicators(previous => previous.includes(value) ? previous.filter(x => x !== value) : [...previous, value])}>{value}{value === 'VWAP' ? ' proxy' : value === 'BB' ? ' 20, 2' : ' 20'}</button>)}</div>
        <MarketChart key={active} product={active} updated={product?.timestamp ?? 0} interval={interval} mode={mode} overlay={overlay} indicators={indicators} start={range.start} end={range.end}/>
        <div className="range-controls"><span>History range</span><label>From<input aria-label="History range start" type="datetime-local" value={from} onChange={e => setFrom(e.target.value)}/></label><label>To<input aria-label="History range end" type="datetime-local" value={to} onChange={e => setTo(e.target.value)}/></label><button onClick={() => {
          const start = from ? new Date(from).getTime() : 0, end = to ? new Date(to).getTime() : null;
          if (!Number.isFinite(start) || (end !== null && (!Number.isFinite(end) || end < start))) { setRangeError('End must follow start.'); return; }
          setRange({ start, end }); setRangeError(''); setAt(null);
        }}>Apply</button><button onClick={() => { setRange({ start: 0, end: null }); setFrom(''); setTo(''); setRangeError(''); setAt(null); }}>All</button><div className="export-links"><a href={`${API}${productPath(active)}/export?${exportQuery}&format=csv`}>CSV ↓</a><a href={`${API}${productPath(active)}/export?${exportQuery}&format=parquet`}>Parquet ↓</a></div></div>
        {rangeError && <p className="negative px-4 py-2" role="alert">{rangeError}</p>}
        <HistoryScrubber product={active} updated={product?.timestamp ?? 0} at={at} onChange={setAt} start={range.start} end={range.end}/>
      </section>
      <aside className="right-panel panel"><OrderBook product={active} updated={at == null ? product?.timestamp ?? 0 : 0} at={at}/><ProductStats product={product} tax={status?.tax_rate ?? 0.01125}/></aside>
      <Screener products={products} select={select}/>
    </main><footer className="statusbar"><span className={connection === 'connected' ? 'positive' : 'negative'}>● {connection}</span><span>Last snapshot {date(status?.last_update)}</span><span>Poll {status?.poll_interval ?? 30}s</span><span>Rate limit {status?.rate_limit_remaining ?? 'not supplied'}</span><span className="ml-auto">{status?.stale ? 'STALE DATA' : status?.state?.toUpperCase()} · UTC CHARTS</span></footer>
  </div>;
}
