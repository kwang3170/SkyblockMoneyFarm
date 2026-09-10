import { useMemo, useState } from 'react';
import { SlidersHorizontal } from 'lucide-react';
import type { Product } from '../types';
import { number, percent, tone } from '../format';
const columns: { key: keyof Product; label: string; format?: 'percent' | 'compact' }[] = [
  { key: 'name', label: 'Product' }, { key: 'insta_buy_price', label: 'Insta-buy' }, { key: 'insta_sell_price', label: 'Insta-sell' },
  { key: 'spread_pct', label: 'Spread %', format: 'percent' }, { key: 'flip_margin_pct', label: 'Net margin', format: 'percent' },
  { key: 'flip_profit', label: 'Profit / unit' }, { key: 'estimated_hourly_profit', label: 'Est. profit / h', format: 'compact' },
  { key: 'estimated_hourly_volume', label: 'Est. volume / h', format: 'compact' }, { key: 'imbalance', label: 'Imbalance' },
  { key: 'npc_ratio', label: 'NPC ratio' }, { key: 'change_24h_pct', label: '24h', format: 'percent' },
];
export default function Screener({ products, select }: { products: Product[]; select: (id: string) => void }) {
  const [minVolume, setMinVolume] = useState(''), [minMargin, setMinMargin] = useState(''), [maxSpread, setMaxSpread] = useState('');
  const [sort, setSort] = useState<keyof Product>('estimated_hourly_profit'), [asc, setAsc] = useState(false);
  const rows = useMemo(() => products.filter(p => (minVolume === '' || p.estimated_hourly_volume >= Number(minVolume)) &&
    (minMargin === '' || (p.flip_margin_pct != null && p.flip_margin_pct >= Number(minMargin))) &&
    (maxSpread === '' || (p.spread_pct != null && p.spread_pct <= Number(maxSpread))))
    .sort((a, b) => { const x = a[sort], y = b[sort]; if (x == null) return 1; if (y == null) return -1;
      return (typeof x === 'string' ? x.localeCompare(String(y)) : Number(x) - Number(y)) * (asc ? 1 : -1); }), [products, minVolume, minMargin, maxSpread, sort, asc]);
  return <section className="screener panel"><div className="screener-toolbar"><div className="flex items-center gap-2"><SlidersHorizontal size={15}/><h2>Market screener</h2><span className="count">{rows.length}</span></div>
    <div className="filters"><label>Min vol / h<input aria-label="Minimum hourly volume" type="number" min="0" value={minVolume} placeholder="Any" onChange={e => setMinVolume(e.target.value)}/></label><label>Min margin %<input aria-label="Minimum margin" type="number" value={minMargin} placeholder="Any" onChange={e => setMinMargin(e.target.value)}/></label><label>Max spread %<input aria-label="Maximum spread" type="number" value={maxSpread} placeholder="Any" onChange={e => setMaxSpread(e.target.value)}/></label><button onClick={() => { setMinVolume(''); setMinMargin(''); setMaxSpread(''); }}>Reset</button></div></div>
    <div className="screener-scroll"><table><thead><tr>{columns.map(col => <th key={col.key}><button onClick={() => { if (sort === col.key) setAsc(!asc); else { setSort(col.key); setAsc(col.key === 'name'); } }}>{col.label}{sort === col.key ? asc ? ' ↑' : ' ↓' : ''}</button></th>)}</tr></thead><tbody>{rows.map(p => <tr key={p.product_id}>{columns.map(col => {
      const value = p[col.key]; return <td key={col.key} className={['flip_profit', 'flip_margin_pct', 'estimated_hourly_profit', 'change_24h_pct'].includes(col.key) ? tone(value as number | null) : ''}>
        {col.key === 'name' ? <button onClick={() => select(p.product_id)}>{p.name}</button> : col.format === 'percent' ? percent(value as number | null) : number(value as number | null, col.format === 'compact')}</td>;
    })}</tr>)}</tbody></table>{!rows.length && <p className="empty">No products match these filters.</p>}</div>
  </section>;
}
