export interface Product {
  product_id: string; name: string; timestamp: number;
  insta_buy_price: number | null; insta_sell_price: number | null;
  best_ask: number | null; best_bid: number | null;
  buy_order_volume: number; sell_offer_volume: number;
  insta_buy_moving_week: number; insta_sell_moving_week: number;
  buy_order_count: number; sell_offer_count: number;
  spread: number | null; spread_pct: number | null;
  flip_profit: number | null; flip_margin_pct: number | null;
  estimated_hourly_profit: number | null; estimated_hourly_volume: number;
  npc_sell_price: number | null; npc_ratio: number | null; imbalance: number | null;
  change_24h_pct: number | null;
}
export interface Candle { bucket_start: number; open: number; high: number; low: number; close: number; sample_count: number; estimated_volume: number; first_timestamp: number; last_timestamp: number }
export interface Level { price: number; amount: number; orders: number }
export interface Book { product_id: string; timestamp: number; bids: Level[]; asks: Level[] }
export interface Status { state: string; last_update: number | null; first_update: number | null; poll_interval: number; rate_limit_remaining: number | null; stale: boolean; source: string | null; tax_rate: number; error: string | null; order_book_depth: number }
export type Interval = '1m' | '5m' | '15m' | '1h' | '4h' | '1d';
export type Indicator = 'SMA' | 'EMA' | 'BB' | 'VWAP';
export type Tool = 'cursor' | 'horizontal' | 'trend' | 'rectangle' | 'note';
export interface Anchor { time: number; price: number }
export interface Drawing { id: string; tool: Exclude<Tool, 'cursor'>; start: Anchor; end?: Anchor; text?: string }
