import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, CreditCard, Building2, ChevronDown, ChevronUp, ChevronRight, Eye, X, BarChart3, List, Edit2, Check } from 'lucide-react';
import { updateTransaction, getMatchingTransactions } from '../api/transactions';
import CategorySelect from '../components/CategorySelect';
import { getStatements, getStatement } from '../api/statements';
import type { Statement } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import CategoryBadge from '../components/CategoryBadge';
import { formatDate, formatCurrency, formatMonth, truncate, getStatusColor } from '../utils/formatters';

export default function StatementsPage() {
  const location = useLocation();
  // Route-based type filtering
  const routeType = location.pathname === '/cc-statements'
    ? 'credit_card'
    : location.pathname === '/bank-statements'
    ? 'bank_account'
    : '';

  const [bankFilter, setBankFilter] = useState('');
  const [monthFilter, setMonthFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState(routeType);
  const [viewMode, setViewMode] = useState<'table' | 'monthly'>('table');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [rawModalId, setRawModalId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['statements', bankFilter, monthFilter, statusFilter],
    queryFn: () =>
      getStatements({
        bank_name: bankFilter || undefined,
        month: monthFilter || undefined,
        parse_status: statusFilter || undefined,
        limit: 100,
      }),
  });

  const { data: expandedStatement } = useQuery({
    queryKey: ['statement-detail', expandedId],
    queryFn: () => getStatement(expandedId!),
    enabled: expandedId !== null,
  });

  const { data: rawStatement } = useQuery({
    queryKey: ['statement-raw', rawModalId],
    queryFn: () => getStatement(rawModalId!),
    enabled: rawModalId !== null,
  });

  const allStatements = data?.statements || [];

  // Apply type filter (Credit Card vs Bank Account) on frontend
  const effectiveTypeFilter = typeFilter || routeType;
  const statements = effectiveTypeFilter
    ? allStatements.filter((s) => {
        const bankLower = (s.bank_name || '').toLowerCase();
        const subjectLower = (s.email_subject || '').toLowerCase();
        const isCC = bankLower.includes('credit card') || subjectLower.includes('credit card');
        if (effectiveTypeFilter === 'credit_card') return isCC;
        if (effectiveTypeFilter === 'bank_account') return !isCC;
        return true;
      })
    : allStatements;

  // Extract unique banks and months for filters
  const banks = [...new Set(allStatements.map((s) => s.bank_name).filter(Boolean))].sort();
  const months = [...new Set(
    allStatements.map((s) => s.statement_month?.slice(0, 7)).filter(Boolean)
  )].sort().reverse();

  const toggleExpand = (id: number) => {
    setExpandedId(expandedId === id ? null : id);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full py-32">
        <LoadingSpinner size={40} text="Loading statements..." />
      </div>
    );
  }

  const effectiveType = typeFilter || routeType;

  const pageTitle = effectiveType === 'credit_card'
    ? 'Credit Card Statements'
    : effectiveType === 'bank_account'
    ? 'Bank Account Statements'
    : 'All Statements';

  const PageIcon = effectiveType === 'credit_card' ? CreditCard : effectiveType === 'bank_account' ? Building2 : FileText;

  // Monthly aggregation for monthly view
  const monthlyData = months.map((month) => {
    const monthStatements = statements.filter((s) => s.statement_month?.slice(0, 7) === month);
    const totalTxns = monthStatements.reduce((sum, s) => sum + (s.transaction_count || 0), 0);
    const totalDue = monthStatements.reduce((sum, s) => sum + (s.total_amount_due || 0), 0);
    const bankNames = [...new Set(monthStatements.map((s) => s.bank_name).filter(Boolean))];
    return { month, statements: monthStatements, totalTxns, totalDue, bankNames };
  });

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <PageIcon size={24} className="text-indigo-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{pageTitle}</h1>
            <p className="text-sm text-gray-500 mt-0.5">{statements.length} statements found</p>
          </div>
        </div>
        <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setViewMode('table')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              viewMode === 'table' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <List size={14} />
            Table
          </button>
          <button
            onClick={() => setViewMode('monthly')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              viewMode === 'monthly' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <BarChart3 size={14} />
            Monthly
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        {!routeType && (
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          >
            <option value="">All Types</option>
            <option value="credit_card">Credit Card Statements</option>
            <option value="bank_account">Bank Account Statements</option>
          </select>
        )}
        <select
          value={bankFilter}
          onChange={(e) => setBankFilter(e.target.value)}
          className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        >
          <option value="">All Banks</option>
          {banks.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
        <select
          value={monthFilter}
          onChange={(e) => setMonthFilter(e.target.value)}
          className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        >
          <option value="">All Months</option>
          {months.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        >
          <option value="">All Statuses</option>
          <option value="parsed">Parsed</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
          <option value="no_transactions">No Transactions</option>
        </select>
      </div>

      {/* Monthly View */}
      {viewMode === 'monthly' && (
        <div className="space-y-4">
          {monthlyData.length === 0 ? (
            <EmptyState icon={FileText} title="No statements found" description="Sync your bank statement emails to see them here." />
          ) : (
            monthlyData.map(({ month, statements: monthStmts, totalTxns, totalDue, bankNames }) => (
              <div key={month} className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-lg font-bold text-gray-900">{formatMonth(month)}</h3>
                  <span className="text-sm text-gray-500">{monthStmts.length} statements</span>
                </div>
                {/* Aggregate summary */}
                <div className="flex flex-wrap gap-4 mb-4 text-sm">
                  <span className="text-gray-500">{totalTxns} transactions</span>
                  {totalDue > 0 && (
                    <span className="font-semibold text-red-600">
                      Total Due: {formatCurrency(totalDue)}
                    </span>
                  )}
                </div>
                <div className="space-y-3">
                  {monthStmts.map((stmt) => (
                    <MonthlyStatementCard key={stmt.id} statement={stmt} />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Table View */}
      {viewMode === 'table' && statements.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No statements found"
          description="Sync your bank statement emails to see them here."
        />
      ) : viewMode === 'table' && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50/50">
                  <th className="px-5 py-3 w-8" />
                  <th className="px-5 py-3">Statement Month</th>
                  <th className="px-5 py-3">Bank</th>
                  <th className="px-5 py-3">Subject</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Txns</th>
                  <th className="px-5 py-3 hidden md:table-cell">Amount Due</th>
                  <th className="px-5 py-3 w-10" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {statements.map((stmt: Statement) => (
                  <StatementRow
                    key={stmt.id}
                    statement={stmt}
                    isExpanded={expandedId === stmt.id}
                    onToggle={() => toggleExpand(stmt.id)}
                    onViewRaw={() => setRawModalId(stmt.id)}
                    expandedData={expandedId === stmt.id ? expandedStatement : undefined}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Raw content modal */}
      {rawModalId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="text-base font-semibold text-gray-900">Raw Email Content</h3>
              <button
                onClick={() => setRawModalId(null)}
                className="p-1.5 rounded-md hover:bg-gray-100 transition-colors"
              >
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {rawStatement?.raw_content ? (
                <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono leading-relaxed">
                  {rawStatement.raw_content}
                </pre>
              ) : (
                <p className="text-sm text-gray-400">No raw content available</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatementRow({
  statement,
  isExpanded,
  onToggle,
  onViewRaw,
  expandedData,
}: {
  statement: Statement;
  isExpanded: boolean;
  onToggle: () => void;
  onViewRaw: () => void;
  expandedData?: Statement;
}) {
  return (
    <>
      <tr
        onClick={onToggle}
        className="hover:bg-gray-50/50 transition-colors cursor-pointer"
      >
        <td className="px-5 py-3">
          {isExpanded ? (
            <ChevronUp size={16} className="text-gray-400" />
          ) : (
            <ChevronDown size={16} className="text-gray-400" />
          )}
        </td>
        <td className="px-5 py-3 text-sm text-gray-500 whitespace-nowrap">
          {statement.statement_month ? formatMonth(statement.statement_month.slice(0, 7)) : formatDate(statement.email_date)}
        </td>
        <td className="px-5 py-3 text-sm font-medium text-gray-900">{statement.bank_name}</td>
        <td className="px-5 py-3 text-sm text-gray-600">
          <div className="whitespace-normal break-words max-w-md">
            {statement.email_subject}
          </div>
        </td>
        <td className="px-5 py-3">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
              statement.parse_status
            )}`}
          >
            {statement.parse_status}
          </span>
        </td>
        <td className="px-5 py-3 text-sm text-gray-500">{statement.transaction_count}</td>
        <td className="px-5 py-3 hidden md:table-cell text-sm">
          {statement.total_amount_due != null ? (
            <span className="font-semibold text-red-600">{formatCurrency(statement.total_amount_due)}</span>
          ) : (
            <span className="text-gray-300">-</span>
          )}
        </td>
        <td className="px-5 py-3">
          <button
            onClick={(e) => {
              e.stopPropagation();
              openPdf(statement.id);
            }}
            className="p-1.5 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            title="View statement PDF"
          >
            <Eye size={16} />
          </button>
        </td>
      </tr>
      {isExpanded && expandedData?.transactions && expandedData.transactions.length > 0 && (
        <tr>
          <td colSpan={8} className="px-5 py-3 bg-gray-50/50">
            <ExpandedTransactions transactions={expandedData.transactions} />
          </td>
        </tr>
      )}
      {isExpanded && expandedData?.transactions && expandedData.transactions.length === 0 && (
        <tr>
          <td colSpan={8} className="px-5 py-6 bg-gray-50/50 text-center text-sm text-gray-400">
            No transactions in this statement
          </td>
        </tr>
      )}
    </>
  );
}


const CATEGORIES = [
  'Food & Dining', 'Shopping', 'Groceries', 'Housing', 'Transportation',
  'Bills & Utilities', 'Entertainment', 'Health & Wellness', 'Education',
  'Insurance', 'Loans', 'Investments', 'Subscriptions', 'Family & Social',
  'Domestic Help', 'Children', 'ATM & Cash', 'Salary & Income',
  'Investment Returns', 'Refunds & Cashback', 'Transfers', 'Uncategorized',
];


function ExpandedTransactions({ transactions }: { transactions: import('../types').Transaction[] }) {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [showApplyAll, setShowApplyAll] = useState<{
    txnId: number;
    merchant: string;
    category: string;
    matchCount: number;
  } | null>(null);

  const updateMut = useMutation({
    mutationFn: ({ id, ...payload }: { id: number; category?: string; sub_category?: string; apply_to_all?: boolean; save_rule?: boolean }) =>
      updateTransaction(id, payload),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['statement-detail'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });

      // If there are matching transactions, offer to apply to all
      if (data.applied_to_count === 0 && variables.category) {
        getMatchingTransactions(variables.id).then((match) => {
          if (match.count > 1) {
            setShowApplyAll({
              txnId: variables.id,
              merchant: match.merchant,
              category: variables.category!,
              matchCount: match.count - 1,
            });
          }
        });
      }
      setEditingId(null);
    },
  });

  const applyAllMut = useMutation({
    mutationFn: ({ id, category }: { id: number; category: string }) =>
      updateTransaction(id, { category, apply_to_all: true, save_rule: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['statement-detail'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      setShowApplyAll(null);
    },
  });

  const handleCategoryChange = (txnId: number, category: string) => {
    setSelectedCategory(category);
    updateMut.mutate({ id: txnId, category });
  };

  return (
    <>
      <div className="rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="text-left text-xs font-medium text-gray-500 bg-gray-100/50">
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2">Merchant</th>
              <th className="px-4 py-2">Amount</th>
              <th className="px-4 py-2">Category</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {transactions.map((txn) => (
              <tr key={txn.id}>
                <td className="px-4 py-2 text-xs text-gray-500">{formatDate(txn.transaction_date)}</td>
                <td className="px-4 py-2 text-xs font-medium text-gray-800 whitespace-normal break-words max-w-xs">
                  {txn.merchant}
                </td>
                <td className="px-4 py-2 text-xs font-semibold whitespace-nowrap">
                  <span
                    className={
                      txn.transaction_type.toUpperCase() === 'DEBIT' ? 'text-red-600' : 'text-green-600'
                    }
                  >
                    {txn.transaction_type.toUpperCase() === 'DEBIT' ? '-' : '+'}
                    {formatCurrency(Number(txn.amount))}
                  </span>
                </td>
                <td className="px-4 py-2 relative">
                  {editingId === txn.id ? (
                    <CategorySelect
                      value={txn.category}
                      subValue={txn.sub_category}
                      compact
                      onChange={(cat, sub) => {
                        updateMut.mutate({ id: txn.id, category: cat, sub_category: sub || undefined });
                      }}
                      onClose={() => setEditingId(null)}
                    />
                  ) : (
                    <div className="flex items-center gap-1.5 group">
                      <div className="flex flex-col">
                        <CategoryBadge category={txn.category} />
                        {txn.sub_category && txn.sub_category !== txn.category && (
                          <span className="text-[10px] text-gray-400 mt-0.5">{txn.sub_category}</span>
                        )}
                      </div>
                      <button
                        onClick={() => setEditingId(txn.id)}
                        className="p-0.5 text-gray-300 hover:text-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Change category"
                      >
                        <Edit2 size={11} />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Apply to all dialog */}
      {showApplyAll && (
        <div className="mt-3 bg-indigo-50 border border-indigo-200 rounded-lg p-3">
          <p className="text-sm text-indigo-800 mb-2">
            Apply <strong>{showApplyAll.category}</strong> to all{' '}
            <strong>{showApplyAll.matchCount}</strong> other transactions from{' '}
            <strong>{showApplyAll.merchant}</strong>?
          </p>
          <p className="text-xs text-indigo-600 mb-3">
            This will also save the rule for future auto-categorization.
          </p>
          <div className="flex gap-2">
            <button
              onClick={() =>
                applyAllMut.mutate({
                  id: showApplyAll.txnId,
                  category: showApplyAll.category,
                })
              }
              disabled={applyAllMut.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              <Check size={12} />
              {applyAllMut.isPending ? 'Applying...' : `Yes, apply to all ${showApplyAll.matchCount}`}
            </button>
            <button
              onClick={() => setShowApplyAll(null)}
              className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              No, just this one
            </button>
          </div>
        </div>
      )}
    </>
  );
}


/** Open a decrypted statement PDF in a new tab */
function openPdf(statementId: number) {
  const token = localStorage.getItem('finsight_token');
  fetch(`/api/pdf/${statementId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((res) => {
      if (res.ok) return res.blob();
      return null;
    })
    .then((blob) => {
      if (blob) {
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
      }
    })
    .catch(() => {});
}


function MonthlyStatementCard({ statement: stmt }: { statement: import('../types').Statement }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const { data: detail } = useQuery({
    queryKey: ['statement-detail', stmt.id],
    queryFn: () => getStatement(stmt.id),
    enabled: isExpanded,
  });

  return (
    <div className="border border-gray-100 rounded-lg overflow-hidden">
      <div
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? (
          <ChevronDown size={14} className="text-gray-400 shrink-0" />
        ) : (
          <ChevronRight size={14} className="text-gray-400 shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-semibold text-indigo-600">{stmt.bank_name || 'Unknown'}</span>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${getStatusColor(stmt.parse_status)}`}>
              {stmt.parse_status}
            </span>
          </div>
          <p className="text-xs text-gray-600 leading-relaxed line-clamp-1">
            {stmt.email_subject}
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-gray-400">{stmt.transaction_count} txns</span>
          {stmt.total_amount_due != null && stmt.total_amount_due > 0 && (
            <span className="text-xs font-semibold text-red-600">
              Due: {formatCurrency(stmt.total_amount_due)}
            </span>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); openPdf(stmt.id); }}
            className="p-1.5 rounded-md hover:bg-indigo-50 text-gray-400 hover:text-indigo-600 transition-colors"
            title="View PDF"
          >
            <Eye size={14} />
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="border-t border-gray-100 p-3 bg-gray-50/50">
          {detail?.transactions && detail.transactions.length > 0 ? (
            <ExpandedTransactions transactions={detail.transactions} />
          ) : detail?.transactions && detail.transactions.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-4">No transactions in this statement</p>
          ) : (
            <div className="flex justify-center py-4">
              <LoadingSpinner size={20} text="Loading transactions..." />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
