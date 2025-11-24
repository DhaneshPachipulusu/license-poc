import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow, differenceInDays, parseISO } from 'date-fns';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString: string): string {
  return format(parseISO(dateString), 'MMM d, yyyy');
}

export function formatDateTime(dateString: string): string {
  return format(parseISO(dateString), 'MMM d, yyyy h:mm a');
}

export function formatRelative(dateString: string): string {
  return formatDistanceToNow(parseISO(dateString), { addSuffix: true });
}

export function daysUntilExpiry(validUntil: string): number {
  return differenceInDays(parseISO(validUntil), new Date());
}

export function isExpiringSoon(validUntil: string, thresholdDays = 30): boolean {
  const days = daysUntilExpiry(validUntil);
  return days <= thresholdDays && days > 0;
}

export function isExpired(validUntil: string): boolean {
  return daysUntilExpiry(validUntil) <= 0;
}

export function getTierColor(tier: string): string {
  const colors: Record<string, string> = {
    trial: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    basic: 'bg-sky-500/20 text-sky-400 border-sky-500/30',
    pro: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
    enterprise: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  };
  return colors[tier.toLowerCase()] || colors.basic;
}

export function getStatusColor(status: string, validUntil?: string): string {
  if (status === 'revoked') {
    return 'bg-red-500/20 text-red-400 border-red-500/30';
  }
  if (validUntil && isExpired(validUntil)) {
    return 'bg-red-500/20 text-red-400 border-red-500/30';
  }
  if (validUntil && isExpiringSoon(validUntil)) {
    return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
  }
  return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
}

export function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}