import { useEffect, useState } from 'react';
import { History, SkipForward } from 'lucide-react';
import { get, productPath } from '../api';
import { date } from '../format';
export default function HistoryScrubber({ product, updated, at, onChange, start, end }: { product: string; updated: number; at: number | null; onChange: (value: number | null) => void; start: number; end: number | null }) {
  const [timestamps, setTimestamps] = useState<number[]>([]), [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    void get<number[]>(`${productPath(product)}/snapshots?start=${start}${end != null ? `&end=${end}` : ''}`, controller.signal)
      .then(value => { setTimestamps(value); setError(''); }).catch(() => { if (!controller.signal.aborted) setError('History unavailable'); });
    return () => controller.abort();
  }, [product, updated, start, end]);
  const index = at == null ? timestamps.length - 1 : timestamps.reduce((found, time, i) => time <= at ? i : found, 0);
  return <div className="history-scrubber"><div className="flex items-center gap-2"><History size={14}/><span>Book replay</span><b>{at == null ? 'Latest book' : date(at)}</b></div>
    <div className="scrubber-line"><input aria-label="Historical order book timestamp" type="range" min="0" max={Math.max(0, timestamps.length - 1)} value={Math.max(index, 0)} disabled={!timestamps.length} onChange={e => onChange(timestamps[Number(e.target.value)])}/><button className={at == null ? 'active' : ''} onClick={() => onChange(null)}><SkipForward size={13}/> Latest</button></div>
    <div className="scrubber-ends"><span>{error || date(timestamps[0])}</span><span>{timestamps.length.toLocaleString()} snapshots · price chart stays in selected range</span><span>{date(timestamps.at(-1))}</span></div>
  </div>;
}
