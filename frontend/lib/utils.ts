import { format, formatDistanceToNow, isPast, differenceInDays } from 'date-fns';

export const formatDate = (dateString: string): string => {
  try {
    return format(new Date(dateString), 'MMM dd, yyyy HH:mm');
  } catch {
    return 'Invalid date';
  }
};

export const formatDateShort = (dateString: string): string => {
  try {
    return format(new Date(dateString), 'MMM dd, yyyy');
  } catch {
    return 'Invalid date';
  }
};

export const formatRelative = (dateString: string): string => {
  try {
    return formatDistanceToNow(new Date(dateString), { addSuffix: true });
  } catch {
    return 'Unknown';
  }
};

export const isExpired = (dateString: string): boolean => {
  try {
    return isPast(new Date(dateString));
  } catch {
    return false;
  }
};

export const daysUntilExpiry = (dateString: string): number => {
  try {
    return differenceInDays(new Date(dateString), new Date());
  } catch {
    return 0;
  }
};

export const isExpiringSoon = (dateString: string, days: number = 7): boolean => {
  const daysLeft = daysUntilExpiry(dateString);
  return daysLeft >= 0 && daysLeft <= days;
};

export const getLicenseStatus = (license: any): {
  status: 'active' | 'expired' | 'expiring_soon' | 'revoked';
  label: string;
  color: string;
} => {
  if (license.revoked) {
    return { status: 'revoked', label: 'Revoked', color: 'red' };
  }
  
  if (isExpired(license.license_json?.valid_till || license.valid_till)) {
    return { status: 'expired', label: 'Expired', color: 'gray' };
  }
  
  if (isExpiringSoon(license.license_json?.valid_till || license.valid_till)) {
    return { status: 'expiring_soon', label: 'Expiring Soon', color: 'yellow' };
  }
  
  return { status: 'active', label: 'Active', color: 'green' };
};

export const truncate = (str: string, length: number = 20): string => {
  if (str.length <= length) return str;
  return str.substring(0, length) + '...';
};

export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
};