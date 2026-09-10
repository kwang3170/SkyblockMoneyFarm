import { useEffect, useState } from 'react';
import type { Product, Status } from './types';

export const API = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');
export async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API}${path}`, { signal });
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  return response.json() as Promise<T>;
}
export const productPath = (id: string) => `/api/products/${encodeURIComponent(id)}`;
export function useMarket() {
  const [products, setProducts] = useState<Product[]>([]);
  const [status, setStatus] = useState<Status | null>(null);
  const [connection, setConnection] = useState('connecting');
  const [error, setError] = useState('');
  useEffect(() => {
    let stopped = false;
    let socket: WebSocket | undefined;
    let reconnect: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;
    const controller = new AbortController();
    const refresh = () => {
      void get<Status>('/api/status', controller.signal).then(value => { if (!stopped) { setStatus(value); setError(''); } })
        .catch((e: unknown) => { if (!stopped) setError(e instanceof Error ? e.message : 'API unavailable'); });
      // REST fallback also supports a separate headless collector process.
      void get<Product[]>('/api/products', controller.signal).then(value => { if (!stopped) setProducts(value); }).catch(() => {});
    };
    function connect() {
      socket = new WebSocket(`${API.replace(/^http/, 'ws')}/ws`);
      socket.onopen = () => { attempts = 0; setConnection('connected'); refresh(); };
      socket.onmessage = event => {
        try {
          const data = JSON.parse(String(event.data)) as { type: string; products?: Product[] };
          if (data.type === 'snapshot' && data.products) { setProducts(data.products); refresh(); }
        } catch { setError('Invalid market message'); }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (stopped) return;
        setConnection('reconnecting');
        reconnect = setTimeout(connect, Math.min(30000, 1000 * 2 ** attempts++));
      };
    }
    refresh(); connect();
    const timer = setInterval(refresh, 15000);
    return () => { stopped = true; controller.abort(); clearInterval(timer); clearTimeout(reconnect); socket?.close(); };
  }, []);
  return { products, status, connection, error };
}
export function useStored<T>(key: string, initial: T): [T, (value: T | ((previous: T) => T)) => void] {
  const [value, setValue] = useState<T>(() => { try { const saved = localStorage.getItem(key); return saved ? JSON.parse(saved) as T : initial; } catch { return initial; } });
  useEffect(() => { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Private mode or full storage: keep session state. */ } }, [key, value]);
  return [value, setValue];
}
