export function number(value: number | null | undefined, compact = false): string {
  if (value == null || !Number.isFinite(value)) return '—';
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2, notation: compact ? 'compact' : 'standard' }).format(value);
}
export function percent(value: number | null | undefined): string {
  return value == null ? '—' : `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
}
export function tone(value: number | null | undefined): string { return value == null ? 'muted' : value >= 0 ? 'positive' : 'negative'; }
export function date(value: number | null | undefined): string { return value ? new Date(value).toLocaleString() : '—'; }
