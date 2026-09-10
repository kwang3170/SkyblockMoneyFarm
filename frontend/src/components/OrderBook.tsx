import { useEffect, useState } from 'react';
import { get, productPath } from '../api';
import { date, number } from '../format';
import type { Book, Level } from '../types';

function accumulated(levels: Level[]) { let total = 0; return levels.map(level => ({ ...level, total: total += level.amount })); }
export default function OrderBook({ product, updated, at }: { product: string; updated: number; at: number | null }) {
  const [book, setBook] = useState<Book | null>(null), [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setBook(null);
    void get<Book>(`${productPath(product)}/book${at != null ? `?at=${at}` : ''}`, controller.signal)
      .then(value => { setBook(value); setError(''); }).catch((e: unknown) => { if (!controller.signal.aborted) { setBook(null); setError(e instanceof Error ? e.message : 'Book unavailable'); } });
    return () => controller.abort();
  }, [product, updated, at]);
  const bids = accumulated(book?.bids ?? []), asks = accumulated(book?.asks ?? []);
  const max = Math.max(bids.at(-1)?.total ?? 0, asks.at(-1)?.total ?? 0, 1);
  const prices = [...bids, ...asks].map(x => x.price);
  const minPrice = Math.min(...prices), maxPrice = Math.max(...prices);
  const x = (price: number) => 8 + (price - minPrice) / (maxPrice - minPrice || 1) * 284;
  const depthPath = (levels: ReturnType<typeof accumulated>) => levels.length ? `M${x(levels[0].price)},88 ` + levels.map(l => `L${x(l.price)},${88 - l.total / max * 72}`).join(' ') + ` L${x(levels.at(-1)!.price)},88 Z` : '';
  return <section className="book-panel"><div className="panel-heading"><h2>Order book</h2><span className={`book-mode ${at != null ? 'historical' : ''}`}>{at != null ? 'REPLAY' : 'LATEST'}</span></div>
    <div className="book-columns"><span>Price <small>coins</small></span><span>Amount</span><span>Cumulative</span></div>
    <div className="book-levels asks">{asks.map((level, i) => <div key={i} className="book-row"><i style={{ width: `${level.total / max * 100}%` }}/><span className="negative">{number(level.price)}</span><span>{number(level.amount, true)}</span><span>{number(level.total, true)}</span></div>)}</div>
    <div className="book-spread"><strong>{number(asks[0]?.price)}</strong><span>Spread {number(asks[0] && bids[0] ? asks[0].price - bids[0].price : null)}</span></div>
    <div className="book-levels bids">{bids.map((level, i) => <div key={i} className="book-row"><i style={{ width: `${level.total / max * 100}%` }}/><span className="positive">{number(level.price)}</span><span>{number(level.amount, true)}</span><span>{number(level.total, true)}</span></div>)}</div>
    {error && <p className="empty negative">{error}</p>}
    <div className="depth"><div className="depth-caption"><span className="positive">Buy orders</span><span className="negative">Sell offers</span></div>
      <svg viewBox="0 0 300 95" role="img" aria-label="Cumulative order-book depth by price"><path d={depthPath(bids)} fill="#41d6ad22" stroke="#41d6ad" strokeWidth="1.5"/><path d={depthPath(asks)} fill="#f0788622" stroke="#f07886" strokeWidth="1.5"/></svg>
      <div className="depth-caption"><span>{number(bids.at(-1)?.price, true)}</span><span>{number(asks.at(-1)?.price, true)}</span></div>
    </div><div className="book-time">{book ? date(book.timestamp) : 'Loading book…'} · {bids.length}/{asks.length} levels</div>
  </section>;
}
