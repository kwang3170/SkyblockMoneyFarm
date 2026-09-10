import { number, percent, tone } from '../format';
import type { Product } from '../types';
export default function ProductStats({ product: p, tax }: { product: Product | undefined; tax: number }) {
  if (!p) return null;
  const npcBetter = p.npc_sell_price != null && p.insta_sell_price != null && p.npc_sell_price > p.insta_sell_price * (1 - tax);
  const stats: [string, string, string?][] = [
    ['Profit / unit', number(p.flip_profit), tone(p.flip_profit)], ['Net flip margin', percent(p.flip_margin_pct), tone(p.flip_margin_pct)],
    ['Est. profit / hour', number(p.estimated_hourly_profit, true), tone(p.estimated_hourly_profit)],
    ['Est. throughput / hour', number(p.estimated_hourly_volume, true)], ['Spread', `${number(p.spread)} (${number(p.spread_pct)}%)`],
    ['Buy order quantity', number(p.buy_order_volume, true)], ['Sell offer quantity', number(p.sell_offer_volume, true)],
    ['Weekly insta-buy activity', number(p.insta_buy_moving_week, true)], ['Weekly insta-sell activity', number(p.insta_sell_moving_week, true)],
    ['Buy / sell order counts', `${number(p.buy_order_count)} / ${number(p.sell_offer_count)}`],
    ['Book imbalance', `${number(p.imbalance)}×`], ['NPC sell price', number(p.npc_sell_price)], ['Bazaar / NPC (pre-tax)', p.npc_ratio == null ? '—' : `${number(p.npc_ratio)}×`],
  ];
  return <section className="stats-panel"><div className="panel-heading"><h2>Product statistics</h2><span className="muted small">LATEST</span></div>
    <dl>{stats.map(([label, value, color]) => <div key={label}><dt>{label}</dt><dd className={color}>{value}</dd></div>)}</dl>
    {npcBetter && <div className="npc-notice">NPC pays more than a taxed instant sell.</div>}
    <p className="stats-note">Tax {(tax * 100).toFixed(3)}%. Hourly profit is a throughput estimate, not a fill forecast. Weekly activity includes outstanding orders.</p>
  </section>;
}
