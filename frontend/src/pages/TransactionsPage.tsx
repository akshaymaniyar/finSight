import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeftRight, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { getTransactions, updateTransaction } from '../api/transactions';
import type { TransactionFilters } from '../api/transactions';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import CategoryBadge from '../components/CategoryBadge';
import { formatCurrency, formatDate } from '../utils/formatters';

const CATEGORIES = [
  'Food & Dining',
  'Shopping',
  'Transportation',
  'Entertainment',
  'Utilities',
  'Health',
  'Education',
  'Travel',
  'Groceries',
  'Fuel',
  'Insurance',
  'Subscriptions',
  'EMI',
  'Rent',
  'Investment',
  'Self Transfer',
  'Income',
  'Salary',
  'Cashback',
  'Refund',
  'UPI',
  'ATM',
  'Government',
  'Charity',
  'Personal Care',
  'Home',
  'Other',
];

const PAGE_SIZE = 25;

export default function TransactionsPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<TransactionFilters>({
    limit: PAGE_SIZE,
    offset: 0,
  });
  const [search, setSearch] = useState('');
  const [hideSelfTransfers, setHideSelfTransfers] = useState(false);
  const [hideInvestments, setHideInvestments] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const activeFilters: TransactionFilters = {
    ...filters,
    search: search || undefined,
    exclude_self_transfers: hideSelfTransfers || undefined,
    exclude_investments: hideInvestments || undefined,
  };

  const { data, isLoading } = useQuery({
    queryKey: ['transactions', activeFilters],
    queryFn: () => getTransactions(activeFilters),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, category }: { id: number; category: string }) =>
      updateTransaction(id, { category }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      setEditingId(null);
    },
  });

  const setFilter = useCallback(
    (key: keyof TransactionFilters, value: string) => {
      setFilters((prev) => ({
        ...prev,
        [key]: value || undefined,
        offset: 0,
      }));
    },
    []
  );

  const totalPages = Math.ceil((data?.total || 0) / PAGE_SIZE);
  const currentPage = Math.floor((filters.offset || 0) / PAGE_SIZE) + 1;

  const goToPage = (page: number) => {
    setFilters((prev) => ({
      ...prev,
      offset: (page - 1) * PAGE_SIZE,
    }));
  };

  const transactions = data?.transactions || [];

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Transactions</h1>
        <p className="text-sm text-gray-500 mt-1">
          {data?.total !== undefined ? `${data.total} transactions found` : 'Browse and filter your transactions'}
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 space-y-4">
        <div className="flex flex-wrap gap-3">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search merchant, description..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setFilters((prev) => ({ ...prev, offset: 0 }));
              }}
              className="w-full pl-9 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>

          <select
            value={filters.category || ''}
            onChange={(e) => setFilter('category', e.target.value)}
            className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          <select
            value={filters.card_type || ''}
            onChange={(e) => setFilter('card_type', e.target.value)}
            className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Card Types</option>
            <option value="credit_card">Credit Card</option>
            <option value="debit_card">Debit Card</option>
            <option value="account">Account</option>
          </select>

          <select
            value={filters.bank_name || ''}
            onChange={(e) => setFilter('bank_name', e.target.value)}
            className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Banks</option>
            <option value="HDFC">HDFC</option>
            <option value="ICICI">ICICI</option>
            <option value="SBI">SBI</option>
            <option value="Axis">Axis</option>
            <option value="Kotak">Kotak</option>
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={filters.date_from || ''}
              onChange={(e) => setFilter('date_from', e.target.value)}
              className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <span className="text-gray-400 text-sm">to</span>
            <input
              type="date"
              value={filters.date_to || ''}
              onChange={(e) => setFilter('date_to', e.target.value)}
              className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={hideSelfTransfers}
              onChange={(e) => setHideSelfTransfers(e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            Hide Self Transfers
          </label>

          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={hideInvestments}
              onChange={(e) => setHideInvestments(e.target.checked)}
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            Hide Investments
          </label>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <LoadingSpinner size={32} text="Loading transactions..." className="py-16" />
      ) : transactions.length === 0 ? (
        <EmptyState
          icon={ArrowLeftRight}
          title="No transactions found"
          description="Try adjusting your filters or sync more bank statements."
        />
      ) : (
        <>
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50/50">
                    <th className="px-5 py-3">Date</th>
                    <th className="px-5 py-3">Merchant</th>
                    <th className="px-5 py-3">Amount</th>
                    <th className="px-5 py-3">Category</th>
                    <th className="px-5 py-3 hidden md:table-cell">Bank</th>
                    <th className="px-5 py-3 hidden lg:table-cell">Card Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {transactions.map((txn) => (
                    <tr key={txn.id} className="hover:bg-gray-50/50 transition-colors">
                      <td className="px-5 py-3 text-sm text-gray-500 whitespace-nowrap">
                        {formatDate(txn.transaction_date)}
                      </td>
                      <td className="px-5 py-3 text-sm font-medium text-gray-900 max-w-[200px] truncate">
                        {txn.merchant}
                      </td>
                      <td className="px-5 py-3 text-sm font-semibold whitespace-nowrap">
                        <span
                          className={
                            txn.transaction_type.toUpperCase() === 'DEBIT' ? 'text-red-600' : 'text-green-600'
                          }
                        >
                          {txn.transaction_type.toUpperCase() === 'DEBIT' ? '-' : '+'}
                          {formatCurrency(Number(txn.amount))}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        {editingId === txn.id ? (
                          <select
                            defaultValue={txn.category}
                            onChange={(e) =>
                              updateMutation.mutate({ id: txn.id, category: e.target.value })
                            }
                            onBlur={() => setEditingId(null)}
                            autoFocus
                            className="px-2 py-1 border border-indigo-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          >
                            {CATEGORIES.map((c) => (
                              <option key={c} value={c}>
                                {c}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <CategoryBadge
                            category={txn.category}
                            clickable
                            onClick={() => setEditingId(txn.id)}
                          />
                        )}
                      </td>
                      <td className="px-5 py-3 text-sm text-gray-500 hidden md:table-cell">
                        {txn.bank_name || 'N/A'}
                      </td>
                      <td className="px-5 py-3 text-sm text-gray-500 hidden lg:table-cell capitalize">
                        {txn.card_type?.replace('_', ' ')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Showing {(filters.offset || 0) + 1}-
                {Math.min((filters.offset || 0) + PAGE_SIZE, data?.total || 0)} of {data?.total}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => goToPage(currentPage - 1)}
                  disabled={currentPage <= 1}
                  className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft size={16} />
                </button>
                <span className="text-sm text-gray-600 px-2">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => goToPage(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                  className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
