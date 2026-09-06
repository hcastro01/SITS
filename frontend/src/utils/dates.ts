export const ECUADOR_TIME_ZONE = 'America/Guayaquil';

const dateTimeFormatter = new Intl.DateTimeFormat('es-EC', {
  dateStyle: 'long',
  timeStyle: 'short',
  timeZone: ECUADOR_TIME_ZONE,
});

const dateFormatter = new Intl.DateTimeFormat('es-EC', {
  day: '2-digit',
  month: 'long',
  year: 'numeric',
  timeZone: ECUADOR_TIME_ZONE,
});

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : dateTimeFormatter.format(parsed);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value);
  const parsed = new Date(dateOnly ? `${value}T12:00:00-05:00` : value);
  return Number.isNaN(parsed.getTime()) ? value : dateFormatter.format(parsed);
}

export function todayInEcuador(): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric', month: '2-digit', day: '2-digit', timeZone: ECUADOR_TIME_ZONE,
  }).formatToParts(new Date());
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${value.year}-${value.month}-${value.day}`;
}

export function humanizeCode(value: string | null | undefined): string {
  if (!value) return '—';
  return value.toLowerCase().replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase());
}
