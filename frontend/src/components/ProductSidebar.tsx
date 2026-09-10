import { useMemo, useState } from 'react';
import { Search, Star } from 'lucide-react';
import type { Product } from '../types';
import { number, percent, tone } from '../format';
interface Props { products: Product[]; selected: string; watchlist: string[]; select: (id: string) => void; toggle: (id: string) => void }
export default function ProductSidebar({ products, selected, watchlist, select, toggle }: Props) {
  const [search, setSearch] = useState(''), [onlyStars, setOnlyStars] = useState(false);
  const [sort, setSort] = useState<keyof Product>('name'), [asc, setAsc] = useState(true);
  const rows = useMemo(() => products.filter(p => (!onlyStars || watchlist.includes(p.product_id)) && `${p.name} ${p.product_id}`.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => { const av = a[sort], bv = b[sort]; if (av == null) return 1; if (bv == null) return -1; return (typeof av === 'string' ? av.localeCompare(String(bv)) : Number(av) - Number(bv)) * (asc ? 1 : -1); }), [products, search, sort, asc, onlyStars, watchlist]);
  function order(key: keyof Product) { if (sort === key) setAsc(!asc); else { setSort(key); setAsc(key === 'name'); } }
  return <aside className="sidebar panel"><div className="panel-heading"><h2>Markets</h2><span className="count">{products.length}</span></div>
    <div className="sidebar-tabs"><button className={!onlyStars ? 'selected' : ''} onClick={() => setOnlyStars(false)}>All products</button><button className={onlyStars ? 'selected' : ''} onClick={() => setOnlyStars(true)}><Star size={13}/> Watchlist <span>{watchlist.length}</span></button></div>
    <label className="search"><Search size={16}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search Bazaar" aria-label="Search products"/></label>
    <div className="sidebar-scroll"><table className="market-table"><thead><tr>{([['name', 'Product'], ['insta_buy_price', 'Buy'], ['insta_sell_price', 'Sell'], ['spread_pct', 'Spread'], ['change_24h_pct', '24h']] as const).map(([key, label]) => <th key={key}><button onClick={() => order(key)}>{label}{sort === key ? asc ? ' ↑' : ' ↓' : ''}</button></th>)}</tr></thead>
      <tbody>{rows.map(p => <tr key={p.product_id} className={selected === p.product_id ? 'selected-row' : ''}>
        <td><div className="product-cell"><button className={`star ${watchlist.includes(p.product_id) ? 'starred' : ''}`} aria-label={`Watch ${p.name}`} aria-pressed={watchlist.includes(p.product_id)} onClick={() => toggle(p.product_id)}><Star size={13} fill={watchlist.includes(p.product_id) ? 'currentColor' : 'none'}/></button><button className="product-name" onClick={() => select(p.product_id)} title={p.name}>{p.name}<small>{p.product_id}</small></button></div></td>
        <td>{number(p.insta_buy_price, true)}</td><td>{number(p.insta_sell_price, true)}</td><td>{number(p.spread_pct)}%</td><td className={tone(p.change_24h_pct)}>{percent(p.change_24h_pct)}</td>
      </tr>)}</tbody></table>{rows.length === 0 && <p className="empty">{products.length ? 'No products match.' : 'Waiting for the first snapshot…'}</p>}</div>
    <div className="sidebar-foot">Prices in coins <span>✧</span></div>
  </aside>;
}
