import { format, parseISO } from 'date-fns';

export function formatCurrency(amount: number | string): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(num));
}

export function formatCurrencyExact(amount: number | string): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Math.abs(num));
}

export function formatDate(date: string): string {
  try {
    return format(parseISO(date), 'MMM d, yyyy');
  } catch {
    return date;
  }
}

export function formatMonth(month: string): string {
  try {
    return format(parseISO(month + '-01'), 'MMMM yyyy');
  } catch {
    return month;
  }
}

const CATEGORY_COLORS: Record<string, string> = {
  'Food & Dining': '#EF4444',
  'Shopping': '#F59E0B',
  'Transportation': '#3B82F6',
  'Entertainment': '#8B5CF6',
  'Utilities': '#6366F1',
  'Health': '#EC4899',
  'Education': '#14B8A6',
  'Travel': '#F97316',
  'Groceries': '#22C55E',
  'Fuel': '#64748B',
  'Insurance': '#0EA5E9',
  'Subscriptions': '#A855F7',
  'EMI': '#DC2626',
  'Rent': '#7C3AED',
  'Investment': '#059669',
  'Self Transfer': '#6B7280',
  'Income': '#10B981',
  'Salary': '#10B981',
  'Cashback': '#84CC16',
  'Refund': '#06B6D4',
  'Other': '#94A3B8',
  'UPI': '#8B5CF6',
  'ATM': '#F59E0B',
  'Government': '#0369A1',
  'Charity': '#D946EF',
  'Personal Care': '#FB923C',
  'Home': '#2563EB',
};

export function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || '#94A3B8';
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'completed':
    case 'parsed':
      return 'text-green-600 bg-green-50';
    case 'in_progress':
    case 'pending':
      return 'text-yellow-600 bg-yellow-50';
    case 'failed':
      return 'text-red-600 bg-red-50';
    case 'not_synced':
      return 'text-gray-400 bg-gray-50';
    case 'no_transactions':
      return 'text-blue-600 bg-blue-50';
    default:
      return 'text-gray-500 bg-gray-50';
  }
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}
